"""10-question evaluation of the agent (CONTRACT.md §8, assignment "+10 AI AJANI").

    noncentra-agent-eval                       # Turkish, agent only
    noncentra-agent-eval --lang both --system1  # TR and EN, with the System 1 classifier

Writes eval/RESULTS.md and eval/results.jsonl; tool calls go to logs/agent_calls.jsonl.
Needs ANTHROPIC_API_KEY (the agent's own LLM); numbers still come only from the MCP tool.

Scoring per question
- family: the agent's `KARAR:` label (or the `test` of its last tool call) is the expected label
- params: the last tool input equals the expected one (numbers compared as numbers)
- number: the tool output holds the expected N / power / dz (N exact, decimals 1e-6)
- quoted: the answer text quotes the tool's N (the agent reported, not re-computed)
- for q08 (χ²) and q09 (ambiguous) there is no number: correct means no invented N
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "eval" / "questions.jsonl"
TOL = 1e-6


def load_questions(path=QUESTIONS):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _num_eq(a, b):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    return abs(a - b) <= TOL or abs(a - b) <= TOL * abs(b)


def score(q, res) -> dict:
    accepted = q.get("accept_labels") or [q["label"]]
    family = res.label in accepted
    last = res.tool_calls[-1] if res.tool_calls else None
    out = res.final_output or {}
    row = {"id": q["id"], "expected_label": q["label"], "label": res.label, "family_ok": family,
           "tool_calls": len(res.tool_calls), "tokens_in": res.tokens_in, "tokens_out": res.tokens_out,
           "seconds": round(res.seconds, 2), "tool_input": last.tool_input if last else None,
           "tool_output": last.tool_output if last else None}
    if res.classifier:
        row["classifier"] = {k: res.classifier[k] for k in ("label", "confidence")}
        row["classifier_ok"] = res.classifier["label"] in accepted

    if q["expected"] is None:
        # χ² (unsupported) and ambiguous questions: no number may appear from anywhere but the tool.
        invented = bool(re.search(r"\b\d{2,}\s*(hasta|kişi|katılımcı|gönüllü|patients|participants)", res.answer))
        row["params_ok"] = row["number_ok"] = None
        row["no_invented_number"] = not invented and not res.final_output
        row["ok"] = family and row["no_invented_number"]
        return row

    want_in = q["tool_input"]
    got_in = last.tool_input if last else {}
    row["params_ok"] = bool(got_in) and set(got_in) == set(want_in) and all(
        _num_eq(got_in.get(k), v) for k, v in want_in.items())
    row["number_ok"] = all(
        (out.get(k) == v) if isinstance(v, int) else _num_eq(out.get(k), v)
        for k, v in q["expected"].items())
    n_key = next((k for k in ("n_total",) if k in q["expected"]), None)
    row["quoted"] = (str(q["expected"][n_key]) in res.answer) if n_key else None
    row["ok"] = family and row["params_ok"] and row["number_ok"]
    return row


def run(langs=("tr",), system1=False, model=None, client=None, log_path=None, out_dir=ROOT / "eval"):
    from .agent import DEFAULT_LOG, DEFAULT_MODEL, Agent

    agent = Agent(client=client, model=model or DEFAULT_MODEL,
                  log_path=Path(log_path) if log_path else DEFAULT_LOG, use_classifier=system1)
    questions = load_questions()
    report = {}
    for lang in langs:
        results = asyncio.run(agent.ask_many([q[lang] for q in questions]))
        report[lang] = [dict(score(q, r), answer=r.answer) for q, r in zip(questions, results)]
    out_dir = Path(out_dir)
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as fh:
        for lang, rows in report.items():
            for r in rows:
                fh.write(json.dumps({"lang": lang, **r}, ensure_ascii=False) + "\n")
    (out_dir / "RESULTS.md").write_text(render(report, agent.model, system1), encoding="utf-8")
    return report


def _pct(xs):
    xs = [x for x in xs if x is not None]
    return f"{sum(xs)}/{len(xs)} ({100 * sum(xs) / len(xs):.0f}%)" if xs else "-"


def render(report, model, system1) -> str:
    lines = ["# Ajan değerlendirmesi", "",
             f"Model: `{model}`. Sistem 1 sınıflandırıcı: {'açık' if system1 else 'kapalı'}. "
             "Sayılar yalnızca MCP aracından (`power_analysis`) geldi; araç çağrıları `logs/agent_calls.jsonl`.", "",
             "| Dil | Doğru aile seçimi | Doğru parametreler | Doğru sayı | Sayı uydurmama (q08, q09) | Tamamen doğru | Giriş token | Çıkış token | Süre (sn) |",
             "|---|---|---|---|---|---|---:|---:|---:|"]
    for lang, rows in report.items():
        lines.append(
            f"| {lang.upper()} | {_pct([r['family_ok'] for r in rows])} | {_pct([r['params_ok'] for r in rows])} | "
            f"{_pct([r['number_ok'] for r in rows])} | {_pct([r.get('no_invented_number') for r in rows])} | "
            f"{_pct([r['ok'] for r in rows])} | {sum(r['tokens_in'] for r in rows)} | "
            f"{sum(r['tokens_out'] for r in rows)} | {sum(r['seconds'] for r in rows):.1f} |")
    for lang, rows in report.items():
        lines += ["", f"## Sorular ({lang.upper()})", "",
                  "| # | Beklenen | Ajan | Araç girdisi | Araç çıktısı (ilgili alan) | Sonuç |", "|---|---|---|---|---|---|"]
        for r in rows:
            out = r["tool_output"] or {}
            key = next((k for k in ("n_total", "power", "dz", "error") if k in out), None)
            shown = f"{key}={out[key]}" if key else "—"
            ti = json.dumps(r["tool_input"], ensure_ascii=False) if r["tool_input"] else "— (araç çağrılmadı)"
            lines.append(f"| {r['id']} | {r['expected_label']} | {r['label']} | `{ti}` | {shown} | "
                         f"{'✅' if r['ok'] else '❌'} |")
    if system1:
        lines += ["", "## Sistem 1 kalibrasyonu", "",
                  "Sınıflandırıcının söylediği güven ile gerçek doğruluk. Güven < 0.75 ya da ambiguous/unsupported ise soru "
                  "araştırmacıya geri gider.", "",
                  "| Dil | Güven aralığı | Seçim | Gerçekte doğru |", "|---|---|---:|---:|"]
        for lang, rows in report.items():
            bins = [(0.0, 0.75), (0.75, 0.9), (0.9, 1.01)]
            for lo, hi in bins:
                sel = [r for r in rows if "classifier" in r and lo <= r["classifier"]["confidence"] < hi]
                ok = sum(r["classifier_ok"] for r in sel)
                lines.append(f"| {lang.upper()} | [{lo:.2f}, {min(hi, 1):.2f}) | {len(sel)} | "
                             f"{ok}/{len(sel)}" + (f" ({100 * ok / len(sel):.0f}%)" if sel else "") + " |")
    lines += ["", "## Cevaplar", ""]
    for lang, rows in report.items():
        for r in rows:
            lines += [f"**{r['id']} ({lang})**", "", "> " + r["answer"].replace("\n", "\n> "), ""]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="noncentra-agent-eval")
    p.add_argument("--lang", choices=["tr", "en", "both"], default="tr")
    p.add_argument("--system1", action="store_true")
    p.add_argument("--model")
    args = p.parse_args(argv)
    from .agent import require_api_key

    require_api_key()
    langs = ("tr", "en") if args.lang == "both" else (args.lang,)
    report = run(langs=langs, system1=args.system1, model=args.model)
    for lang, rows in report.items():
        print(f"{lang}: {sum(r['ok'] for r in rows)}/{len(rows)} doğru, "
              f"aile {sum(r['family_ok'] for r in rows)}/{len(rows)}", file=sys.stderr)


if __name__ == "__main__":
    main()
