"""Agent pipeline with a scripted fake LLM: real MCP server process, real logging, real scoring.

The fake model only decides *which tool input to send*; every number in the results must come
back from the MCP server (noncentra.mcp_contract), never from the fake.
"""
import json
from types import SimpleNamespace as NS

import pytest

pytest.importorskip("mcp")

from noncentra.agent import evaluate  # noqa: E402
from noncentra.agent.agent import Agent, parse_label  # noqa: E402

QUESTIONS = evaluate.load_questions()
LOG_FIELDS = {"ts", "question", "tool_input", "tool_output", "tokens_in", "tokens_out"}


def text(t):
    return NS(type="text", text=t)


def tool_use(i, inp):
    return NS(type="tool_use", id=f"tu_{i}", name="power_analysis", input=inp)


def response(blocks, t_in=500, t_out=60):
    return NS(content=blocks, usage=NS(input_tokens=t_in, output_tokens=t_out),
              stop_reason="tool_use" if any(b.type == "tool_use" for b in blocks) else "end_turn")


class ScriptedModel:
    """Plays the expected behaviour for each eval question; quotes the tool's number back."""

    def __init__(self, by_question):
        self.by_question = by_question
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if kw.get("tool_choice", {}).get("name") == "classify":
            q = self.by_question[kw["messages"][0]["content"]]
            return response([tool_use(0, {"label": q["label"], "confidence": 0.95})], 200, 20)
        msgs = kw["messages"]
        q = self.by_question[msgs[0]["content"]]
        if len(msgs) == 1:
            if q["tool_input"] is None and q["label"] == "chi2-contingency":
                return response([tool_use(1, {"test": "chi2-contingency", "mode": "a-priori", "w": 0.3,
                                              "alpha": 0.05, "power": 0.8, "df": 1})])
            if q["tool_input"] is None:
                return response([text("Etki büyüklüğü, α, güç ve hipotezin yönü nedir? 'Orta' için dz = 0.5 "
                                      "varsayabilirim ama onayınızı isterim.\nKARAR: ambiguous")])
            return response([text("Hesaplıyorum."), tool_use(1, q["tool_input"])])
        result = json.loads(msgs[-1]["content"][0]["content"])
        if "error" in result:
            return response([text(f"Araç bu testi desteklemiyor ({result['code']}); sayı vermiyorum.\n"
                                  f"KARAR: {q['label']}")])
        value = result.get("n_total", result.get("power", result.get("dz")))
        return response([text(f"Sonuç: {value}.\nKARAR: {q['label']}")])


@pytest.fixture
def model():
    return ScriptedModel({q["tr"]: q for q in QUESTIONS} | {q["en"]: q for q in QUESTIONS})


def test_parse_label():
    assert parse_label("...\nKARAR: t-paired") == "t-paired"
    assert parse_label("KARAR: bilmem") is None


def test_single_question_goes_through_mcp(model, tmp_path):
    log = tmp_path / "calls.jsonl"
    res = Agent(client=model, log_path=log).ask(QUESTIONS[0]["tr"])
    assert res.label == "t-paired"
    assert res.final_output["n_total"] == 45          # from the MCP server, not the model
    assert res.tool_calls[0].tool_output["df"] == 44
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert len(rows) == 1 and set(rows[0]) == LOG_FIELDS
    assert rows[0]["ts"][-6] in "+-"                  # ISO 8601 with time zone
    # The model saw only the MCP tool list.
    assert [t["name"] for t in model.calls[0]["tools"]] == ["power_analysis"]


def test_full_eval_scores_all_ten(model, tmp_path):
    report = evaluate.run(langs=("tr", "en"), client=model, log_path=tmp_path / "calls.jsonl",
                          out_dir=tmp_path)
    for lang in ("tr", "en"):
        rows = report[lang]
        assert len(rows) == 10
        assert all(r["ok"] for r in rows), [r for r in rows if not r["ok"]]
    md = (tmp_path / "RESULTS.md").read_text()
    assert "10/10 (100%)" in md
    q08 = next(r for r in report["tr"] if r["id"] == "q08")
    assert q08["tool_output"]["code"] == "UNSUPPORTED" and q08["no_invented_number"]


def test_system1_low_confidence_goes_back_to_researcher(tmp_path):
    class Unsure(ScriptedModel):
        def create(self, **kw):
            self.calls.append(kw)
            return response([tool_use(0, {"label": "t-paired", "confidence": 0.6})], 200, 20)

    m = Unsure({})
    res = Agent(client=m, log_path=tmp_path / "c.jsonl", use_classifier=True).ask("bir soru")
    assert res.asked_researcher and res.label == "ambiguous" and not res.tool_calls
    assert len(m.calls) == 1                         # the agent model was never asked to compute


def test_scoring_catches_a_wrong_number(model, tmp_path):
    q = QUESTIONS[0]
    res = Agent(client=model, log_path=None).ask(q["tr"])
    bad = dict(q, expected={"n_total": 46})
    assert not evaluate.score(bad, res)["ok"]


def test_gui_token_estimate_uses_real_screenshots():
    from noncentra.agent import gui_tokens

    shots = gui_tokens.screenshot_costs()
    assert len(shots) >= 50
    assert gui_tokens.image_tokens(708, 802) == 758
    assert "Ana pencere" in gui_tokens.render()
