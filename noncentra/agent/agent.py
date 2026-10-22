"""The agent: Claude + the `power_analysis` MCP tool over stdio.

    noncentra-agent "Aynı hastalarda önce/sonra tansiyon ... kaç hasta gerekir?"

Flow per question
1. Optional System 1 step (classifier.py): label + confidence. Below 0.75, or `ambiguous` /
   `unsupported`, the question goes back to the researcher and no tool is called.
2. Agent loop: Claude sees only the MCP tool list; every tool_use block is forwarded to the MCP
   server (a separate process running noncentra.mcp_contract), and the text result goes back
   as tool_result. Claude never gets the engine in-process, so it cannot compute around it.
3. Every tool call is appended to logs/agent_calls.jsonl (CONTRACT.md §8).

The LLM client is injected, so tests run the whole pipeline with a scripted fake model.
"""
import argparse
import asyncio
import datetime
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .prompts import AGENT_SYSTEM, LABELS

DEFAULT_MODEL = os.environ.get("NONCENTRA_AGENT_MODEL", "claude-sonnet-5-5")
DEFAULT_LOG = Path(os.environ.get("NONCENTRA_AGENT_LOG", "logs/agent_calls.jsonl"))
MAX_TURNS = 6
CONFIDENCE_THRESHOLD = 0.75


@dataclass
class ToolCall:
    tool_input: dict
    tool_output: dict
    tokens_in: int
    tokens_out: int


@dataclass
class AgentResult:
    question: str
    answer: str
    label: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    seconds: float = 0.0
    classifier: dict | None = None
    asked_researcher: bool = False

    @property
    def final_output(self) -> dict | None:
        """Last successful tool output (the number the answer must quote)."""
        for call in reversed(self.tool_calls):
            if "error" not in call.tool_output:
                return call.tool_output
        return None


def parse_label(text: str) -> str | None:
    m = re.search(r"KARAR:\s*([a-z0-9-]+)", text or "")
    return m.group(1) if m and m.group(1) in LABELS else None


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def append_log(path: Path, question: str, call: ToolCall) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": now_iso(), "question": question, "tool_input": call.tool_input,
           "tool_output": call.tool_output, "tokens_in": call.tokens_in, "tokens_out": call.tokens_out}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def server_params():
    from mcp import StdioServerParameters

    return StdioServerParameters(command=sys.executable, args=["-m", "noncentra.mcp_contract"])


class Agent:
    def __init__(self, client=None, model: str = DEFAULT_MODEL, log_path: Path | None = DEFAULT_LOG,
                 use_classifier: bool = False, classifier_model: str | None = None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.log_path = log_path
        self.use_classifier = use_classifier
        self.classifier_model = classifier_model

    async def ask_many(self, questions: list[str]) -> list[AgentResult]:
        """One MCP server process for all questions."""
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        async with stdio_client(server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = [{"name": t.name, "description": t.description or "",
                          "input_schema": t.inputSchema} for t in listed.tools]
                return [await self._ask(session, tools, q) for q in questions]

    def ask(self, question: str) -> AgentResult:
        return asyncio.run(self.ask_many([question]))[0]

    async def _ask(self, session, tools, question) -> AgentResult:
        start = time.perf_counter()
        result = AgentResult(question=question, answer="", label=None)

        if self.use_classifier:
            from .classifier import classify

            verdict = classify(self.client, question, model=self.classifier_model)
            result.classifier = verdict
            result.tokens_in += verdict.get("tokens_in", 0)
            result.tokens_out += verdict.get("tokens_out", 0)
            if (verdict["label"] in ("ambiguous", "unsupported")
                    or verdict["confidence"] < CONFIDENCE_THRESHOLD):
                result.asked_researcher = True
                result.label = verdict["label"] if verdict["label"] in ("ambiguous", "unsupported") else "ambiguous"
                result.answer = (f"Hangi testin uygun olduğundan emin olamadım (önerim: {verdict['label']}, "
                                 f"güven {verdict['confidence']:.2f}). Tasarımı biraz daha anlatır mısınız: "
                                 "ölçümler aynı kişilerde mi, kaç grup var, etki büyüklüğü, α ve güç değerleri neler?"
                                 f"\nKARAR: {result.label}")
                result.seconds = time.perf_counter() - start
                return result

        system = AGENT_SYSTEM
        if result.classifier:
            system += (f"\nÖn sınıflandırma: {result.classifier['label']} "
                       f"(güven {result.classifier['confidence']:.2f}). Yanlışsa düzelt.")
        messages = [{"role": "user", "content": question}]
        for _ in range(MAX_TURNS):
            resp = self.client.messages.create(model=self.model, max_tokens=1024, system=system,
                                               tools=tools, messages=messages)
            t_in, t_out = resp.usage.input_tokens, resp.usage.output_tokens
            result.tokens_in += t_in
            result.tokens_out += t_out
            messages.append({"role": "assistant", "content": [_block_dict(b) for b in resp.content]})
            uses = [b for b in resp.content if b.type == "tool_use"]
            if not uses:
                result.answer = "".join(b.text for b in resp.content if b.type == "text").strip()
                break
            replies = []
            for i, block in enumerate(uses):
                out = await session.call_tool(block.name, block.input)
                text = "".join(getattr(c, "text", "") for c in out.content)
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = {"error": text, "code": "INTERNAL"}
                # Tokens of the model turn that produced the call; split evenly if it made several.
                call = ToolCall(dict(block.input), payload, t_in // len(uses), t_out // len(uses))
                result.tool_calls.append(call)
                if self.log_path:
                    append_log(self.log_path, question, call)
                replies.append({"type": "tool_result", "tool_use_id": block.id, "content": text})
            messages.append({"role": "user", "content": replies})
        else:
            result.answer = "Araç döngüsü sınırına ulaşıldı; sonuç üretilemedi."

        result.label = parse_label(result.answer)
        if result.label is None and result.tool_calls:
            result.label = result.tool_calls[-1].tool_input.get("test")
        result.asked_researcher = not result.tool_calls
        result.seconds = time.perf_counter() - start
        return result


def _block_dict(block) -> dict:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    raise ValueError(f"unexpected content block {block.type}")


def require_api_key():
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("ANTHROPIC_API_KEY tanımlı değil. Ajanın dil modeli için gerekli "
                 "(hesap yine yalnızca MCP aracından gelir): export ANTHROPIC_API_KEY=...")


def main(argv=None):
    p = argparse.ArgumentParser(prog="noncentra-agent", description="Klinik güç analizi ajanı (MCP).")
    p.add_argument("question", help="Türkçe klinik soru (yalnızca kurgusal senaryolar)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--system1", action="store_true", help="önce etiket kısıtlı Sistem 1 sınıflandırıcıyı çalıştır")
    p.add_argument("--log", default=str(DEFAULT_LOG))
    args = p.parse_args(argv)
    require_api_key()
    agent = Agent(model=args.model, log_path=Path(args.log), use_classifier=args.system1)
    res = agent.ask(args.question)
    print(res.answer)
    print(f"\n[{len(res.tool_calls)} araç çağrısı, {res.tokens_in} giriş / {res.tokens_out} çıkış token, "
          f"{res.seconds:.1f} sn]", file=sys.stderr)


if __name__ == "__main__":
    main()
