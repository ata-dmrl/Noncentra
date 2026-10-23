"""Uyum raporu: run every oracle vector through gpower-clone and write tests/COMPLIANCE.md.

    python tests/run_compliance.py            # uses `gpower-clone` from PATH, or GPOWER_CLONE

Reports, per source and family: how many vectors pass CONTRACT.md §6, the gate metric
(exact N on a-priori vectors, needs >= 90 %), error vectors (error + non-zero exit, and
whether the code matched), and every failure with the reason. Known divergences
(vectors carrying a `note`) are listed separately with their explanation.
"""
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "contract"))
from harness import ROOT, check_vector, command, load, run  # noqa: E402

SOURCES = [("public_vectors.jsonl", "Açık vektörler (CONTRACT §9)"),
           ("gpower_vectors.jsonl", "G*Power arayüzünden toplanan"),
           ("statsmodels_vectors.jsonl", "statsmodels (ölçek)")]
N_FIELDS = ("n1", "n2", "n_total")


def main(out_path=ROOT / "tests" / "COMPLIANCE.md"):
    if command() is None:
        sys.exit("gpower-clone not found; install it or set GPOWER_CLONE")
    _, version, _, _ = run(["--version"])
    rows, gate = [], {"hit": 0, "total": 0}
    for name, label in SOURCES:
        if not (ROOT / "oracle" / name).exists():
            continue
        for v in load(name):
            ok, d = check_vector(v)
            fam = v["input"].get("test", "?")
            if "expected" in v and v["input"].get("mode") == "a-priori":
                want = {k: v["expected"][k] for k in N_FIELDS if k in v["expected"]}
                try:
                    got = json.loads(d["stdout"])
                except (json.JSONDecodeError, TypeError):
                    got = {}
                gate["total"] += 1
                gate["hit"] += all(got.get(k) == x for k, x in want.items())
            rows.append({"source": label, "family": fam, "mode": v["input"].get("mode"), "id": v["id"],
                         "ok": ok, "error_vector": "expected_error" in v, "code_match": d.get("code_match"),
                         "note": v.get("note"), "problem": d.get("problem"), "elapsed": d["elapsed"]})

    by = defaultdict(lambda: [0, 0])
    for r in rows:
        key = (r["source"], r["family"])
        by[key][0] += r["ok"]
        by[key][1] += 1
    rate = gate["hit"] / gate["total"] if gate["total"] else 0
    lines = [
        "# Uyum raporu", "",
        f"Oluşturma: {datetime.datetime.now():%Y-%m-%d %H:%M} · Sürüm: `{version.strip()}`", "",
        f"**Kapı (a-priori vektörlerinde N tam eşleşme):** {gate['hit']} / {gate['total']} = **{rate:.1%}** "
        f"({'GEÇTİ' if rate >= 0.9 else 'KALDI'}, eşik %90)", "",
        f"**Toplam:** {sum(r['ok'] for r in rows)} / {len(rows)} vektör sözleşme kuralına (§6) uyuyor. "
        f"En yavaş çağrı {max((r['elapsed'] for r in rows), default=0):.2f} s (sınır 2 s).", "",
        "| Kaynak | Aile | Geçen | Toplam | Oran |", "|---|---|---|---|---|",
    ]
    for (src, fam), (ok, n) in sorted(by.items()):
        lines.append(f"| {src} | {fam} | {ok} | {n} | {ok / n:.1%} |")
    err = [r for r in rows if r["error_vector"]]
    if err:
        lines += ["", f"**Hata beklenen vektörler:** {sum(r['ok'] for r in err)} / {len(err)} hata verdi; "
                  f"{sum(bool(r['code_match']) for r in err)} tanesinde `code` da eşleşti."]
    known = [r for r in rows if not r["ok"] and r["note"]]
    if known:
        lines += ["", "## Bilinen farklar (açıklamalı)", "", "| Vektör | Açıklama |", "|---|---|"]
        lines += [f"| `{r['id']}` | {r['note']} |" for r in known]
    bad = [r for r in rows if not r["ok"] and not r["note"]]
    lines += ["", f"## Açıklanmamış uyuşmazlıklar ({len(bad)})", ""]
    if bad:
        lines += ["| Vektör | Sorun |", "|---|---|"]
        lines += [f"| `{r['id']}` | {str(r['problem']).replace('|', '/')} |" for r in bad[:200]]
    else:
        lines.append("Yok.")
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{sum(r['ok'] for r in rows)}/{len(rows)} pass, gate {rate:.1%} -> {out_path}")


if __name__ == "__main__":
    main()
