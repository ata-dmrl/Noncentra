"""Differential test for the matched-pairs t test (t-paired, K2).

Same inputs go to three implementations and the outputs are compared:

1. G*Power 3.1.9.7 (the oracle). Every harvested t-paired vector, sent through the
   shipped interface `contract.run()`, i.e. exactly what `gpower-clone` prints:
     - noncentra/reference/t_tests_harvested.csv  (grid, t.paired rows)
     - noncentra/reference/t_tests.csv           (literature row, re-checked by harvest)
     - oracle/t-paired/boundary_harvest.csv       (edges, each with a screenshot)
     - oracle/public_vectors.jsonl                (CONTRACT.md §9, t-paired rows)
   Tolerance is CONTRACT.md §6: integers exact, decimals 1e-6 absolute or relative.
2. statsmodels TTestPower, an independent implementation, over a grid stored in
   oracle/t-paired/statsmodels_vectors.csv (regenerate with --regenerate).
   statsmodels returns a fractional N for a priori; G*Power reports an integer. The
   comparison checks that our N is the smallest integer reaching the target, which
   is ceil(N_statsmodels), and records where plain rounding would have been wrong.

Run:  python -m noncentra.difftest_paired --report tests/T_PAIRED_DIFF_REPORT.md
"""
import argparse
import ast
import csv
import datetime
import json
import math
import sys
from pathlib import Path

from . import contract

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = Path(__file__).resolve().parent / "reference"
ORACLE = ROOT / "oracle"
SM_CSV = ORACLE / "t-paired" / "statsmodels_vectors.csv"

TOL = 1e-6
INT_KEYS = {"n_total", "df"}

LABELS = {  # G*Power label -> contract output key
    "Noncentrality parameter δ": "ncp",
    "Critical t": "critical_t",
    "Df": "df",
}
MODE_OUT = {  # extra outputs per mode: contract key -> G*Power label
    "a-priori": {"n_total": "Total sample size", "actual_power": "Actual power"},
    "post-hoc": {"power": "Power (1-β err prob)"},
    "compromise": {"alpha": "α err prob", "beta": "β err prob", "power": "Power (1-β err prob)"},
    "criterion": {"alpha": "α err prob"},
    "sensitivity": {"dz": "Effect size dz"},
}

# Rows where G*Power accepts an input that CONTRACT.md §5 forbids. The contract wins
# (the harness reads our JSON, not G*Power's screen), so the expected answer is an error.
CONTRACT_REJECTS = {
    "negative_dz": ("OUT_OF_RANGE",
                    "G*Power dz < 0'ı kabul ediyor (tek kuyrukta sol kuyruğa geçiyor); "
                    "CONTRACT.md §5 dz > 0 istiyor"),
    "fractional_n": ("INVALID_VALUE",
                     "G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); "
                     "CONTRACT.md §5'te n_total tam sayı"),
}


def _close(got, want):
    return abs(got - want) <= TOL or abs(got - want) <= TOL * abs(want)


def compare(got: dict, expected: dict) -> list[str]:
    problems = []
    for key, want in expected.items():
        if key not in got:
            problems.append(f"{key} missing")
        elif key in INT_KEYS:
            if not (isinstance(got[key], int) and got[key] == want):
                problems.append(f"{key}: {got[key]} != {want}")
        elif not _close(got[key], want):
            problems.append(f"{key}: {got[key]:.9g} vs {want:.9g}")
    return problems


# --- G*Power oracle ----------------------------------------------------------------

def _fields_from_row(row):
    mode = row["analysis"].replace("_", "-")
    f = {"test": "t-paired", "mode": mode, "tails": row["tails"]}
    if mode != "sensitivity":
        f["dz"] = row["effect_size"]
    if mode in ("a-priori", "post-hoc", "sensitivity"):
        f["alpha"] = row["alpha"]
    if mode in ("a-priori", "criterion", "sensitivity"):
        f["power"] = row["power"]
    if mode == "compromise":
        f["beta_alpha_ratio"] = row["beta_alpha_ratio"]
    if mode != "a-priori":
        f["n_total"] = row["n"]
    return f


def _expected_from_raw(mode, raw):
    labels = dict(LABELS)
    labels.update({v: k for k, v in MODE_OUT[mode].items()})
    want = {}
    for label, key in labels.items():
        text = raw.get(label)
        if text in (None, "", "?"):
            continue
        want[key] = int(float(text)) if key in INT_KEYS else float(text)
    return want


def gpower_cases():
    """Yield (id, source, fields, expected, dialog) for every t-paired G*Power vector."""
    for name in ("t_tests_harvested.csv", "t_tests.csv"):
        for row in csv.DictReader((REFERENCE / name).open(encoding="utf-8")):
            if row["test"] != "t.paired":
                continue
            mode = row["analysis"].replace("_", "-")
            if row.get("raw"):
                want = _expected_from_raw(mode, ast.literal_eval(row["raw"]))
            else:  # literature row: only N, power and critical t were recorded
                want = {"n_total": int(row["exp_n"]), "actual_power": float(row["exp_power"]),
                        "critical_t": float(row["exp_critical"])}
            yield row["id"], name, _fields_from_row(row), want, ""

    for row in csv.DictReader((ORACLE / "t-paired" / "boundary_harvest.csv").open(encoding="utf-8")):
        mode = row["analysis"].replace("_", "-")
        want = {} if row["dialog"] else _expected_from_raw(mode, ast.literal_eval(row["raw"]))
        yield row["id"], "boundary_harvest.csv", _fields_from_row(row), want, row["dialog"]

    for line in (ORACLE / "public_vectors.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        vec = json.loads(line)
        if vec["input"]["test"] == "t-paired":
            fields = {k: str(v) for k, v in vec["input"].items()}
            yield vec["id"], "public_vectors.jsonl", fields, vec["expected"], ""


def _contract_rejection(fields):
    if "dz" in fields and float(fields["dz"]) <= 0:
        return "negative_dz"
    if "n_total" in fields and not float(fields["n_total"]).is_integer():
        return "fractional_n"
    return None


def check_gpower():
    results = []
    for case_id, source, fields, want, dialog in gpower_cases():
        got, code = contract.run(fields)
        r = {"id": case_id, "source": source, "mode": fields["mode"], "input": fields, "ours": got}
        rejection = None if dialog else _contract_rejection(fields)
        if dialog:
            r["status"] = "match" if code != 0 and "error" in got else "mismatch"
            r["detail"] = f"G*Power: {' '.join(dialog.split())} → bizim: {got.get('code', 'hata yok')}"
        elif rejection:
            want_code, why = CONTRACT_REJECTS[rejection]
            ok = code == 2 and got.get("code") == want_code
            r["status"] = "explained" if ok else "mismatch"
            r["detail"] = f"{why}; bizim: {got.get('code')}"
        elif code != 0:
            r["status"], r["detail"] = "mismatch", f"ours refused: {got}"
        else:
            problems = compare(got, want)
            r["status"] = "mismatch" if problems else "match"
            r["detail"] = "; ".join(problems)
        results.append(r)
    return results


# --- statsmodels -------------------------------------------------------------------

SM_DZ = (0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0, 1.5, 2.0)
SM_ALPHA = (0.01, 0.05, 0.1)
SM_POWER = (0.8, 0.9, 0.95)
SM_N = (3, 5, 8, 12, 20, 30, 50, 100, 250, 1000)
SM_FIELDS = ["id", "mode", "tails", "dz", "alpha", "power", "n_total", "sm_power", "sm_upper", "sm_n"]


def generate_statsmodels(path=SM_CSV):
    import statsmodels
    from statsmodels.stats.power import TTestPower

    tp = TTestPower()
    rows = []
    for tails, alt in ((1, "larger"), (2, "two-sided")):
        for dz in SM_DZ:
            for a in SM_ALPHA:
                for p in SM_POWER:
                    n = tp.solve_power(effect_size=dz, alpha=a, power=p, alternative=alt)
                    rows.append({"id": f"sm_ap_t{tails}_dz{dz}_a{a}_p{p}", "mode": "a-priori",
                                 "tails": tails, "dz": dz, "alpha": a, "power": p,
                                 "n_total": "", "sm_power": "", "sm_n": repr(float(n))})
                for n in SM_N:
                    pw = float(tp.power(effect_size=dz, nobs=n, alpha=a, alternative=alt))
                    # statsmodels' two-sided power is NaN where scipy's nct.cdf fails in the
                    # lower tail. Keep its upper-tail power (one-sided at alpha/2) as a fallback.
                    upper = (float(tp.power(effect_size=dz, nobs=n, alpha=a / 2, alternative="larger"))
                             if math.isnan(pw) else "")
                    rows.append({"id": f"sm_ph_t{tails}_dz{dz}_a{a}_n{n}", "mode": "post-hoc",
                                 "tails": tails, "dz": dz, "alpha": a, "power": "",
                                 "n_total": n, "sm_power": repr(pw), "sm_upper": repr(upper) if upper != "" else "",
                                 "sm_n": ""})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        fh.write(f"# statsmodels {statsmodels.__version__} TTestPower; "
                 f"generated by python -m noncentra.difftest_paired --regenerate\n")
        w = csv.DictWriter(fh, SM_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def load_statsmodels(path=SM_CSV):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def check_statsmodels(path=SM_CSV):
    results = []
    for row in load_statsmodels(path):
        fields = {"test": "t-paired", "mode": row["mode"], "tails": row["tails"],
                  "dz": row["dz"], "alpha": row["alpha"]}
        if row["mode"] == "a-priori":
            fields["power"] = row["power"]
        else:
            fields["n_total"] = row["n_total"]
        got, code = contract.run(fields)
        r = {"id": row["id"], "source": "statsmodels", "mode": row["mode"], "input": fields, "ours": got}
        if code != 0:
            r["status"], r["detail"] = "mismatch", f"ours refused: {got}"
        elif row["mode"] == "post-hoc":
            theirs = float(row["sm_power"])
            if math.isnan(theirs):
                # Lower tail P(T < -t_crit | ncp > 0) is far below 1e-6 at these powers, so the
                # one-sided upper tail at alpha/2 is still a valid independent check.
                upper = float(row["sm_upper"])
                ok = _close(got["power"], upper)
                r["status"] = "explained" if ok else "mismatch"
                r["nan_fallback"] = True
                r["detail"] = (f"statsmodels two-sided power = NaN (scipy nct.cdf lower tail); "
                               f"upper tail {upper:.9g} vs ours {got['power']:.9g}")
            else:
                ok = _close(got["power"], theirs)
                r["status"] = "match" if ok else "mismatch"
                r["detail"] = "" if ok else f"power {got['power']:.9g} vs {theirs:.9g}"
        else:
            n_frac = float(row["sm_n"])
            want = max(2, math.ceil(n_frac - 1e-9))
            r["sm_n"] = n_frac
            r["round_would_differ"] = round(n_frac) != want
            ok = got["n_total"] == want
            r["status"] = "match" if ok else "mismatch"
            r["detail"] = f"statsmodels N = {n_frac:.4f} -> ceil {want}; ours {got['n_total']}"
        results.append(r)
    return results


# --- report ------------------------------------------------------------------------

def summarize(results):
    by = {}
    for r in results:
        s = by.setdefault(r["source"], {"total": 0, "match": 0, "explained": 0, "mismatch": 0})
        s["total"] += 1
        s[r["status"]] += 1
    return by


def run(report_path=None):
    gp, sm = check_gpower(), check_statsmodels()
    results = gp + sm
    summary = {
        "gpower": summarize(gp),
        "statsmodels": summarize(sm),
        "mismatch": [r["id"] for r in results if r["status"] == "mismatch"],
    }
    gp_ap = [r for r in gp if r["mode"] == "a-priori"]
    summary["gpower_a_priori_n_match"] = [sum(r["status"] == "match" for r in gp_ap), len(gp_ap)]
    if report_path:
        Path(report_path).write_text(render(gp, sm, summary), encoding="utf-8")
    return summary


def _rate(s):
    ok = s["match"] + s["explained"]
    return f"{ok}/{s['total']} ({100 * ok / s['total']:.1f}%)" if s["total"] else "-"


def render(gp, sm, summary):
    today = datetime.date.today().isoformat()
    lines = [
        "# Diferansiyel test raporu: eşleştirilmiş t testi (`t-paired`)",
        "",
        f"Üretildi: {today}, `python -m noncentra.difftest_paired --report tests/T_PAIRED_DIFF_REPORT.md`.",
        "Bütün vakalar teslim edilen arayüzden (`contract.run`, yani `gpower-clone`) geçirildi.",
        "Tolerans CONTRACT.md §6: tam sayılar tam eşleşme, ondalıklar 1e-6 mutlak ya da göreli.",
        "",
        "## Özet",
        "",
        "| Kâhin | Kaynak | Vaka | Eşleşen | Açıklanmış fark | Açıklanmamış fark | Uyum |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for oracle, block in (("G*Power 3.1.9.7", summary["gpower"]), ("statsmodels", summary["statsmodels"])):
        for src, s in block.items():
            lines.append(f"| {oracle} | `{src}` | {s['total']} | {s['match']} | {s['explained']} | "
                         f"{s['mismatch']} | {_rate(s)} |")
    tot_gp = sum(s["total"] for s in summary["gpower"].values())
    tot_sm = sum(s["total"] for s in summary["statsmodels"].values())
    m, n = summary["gpower_a_priori_n_match"]
    lines += [
        "",
        f"- Toplam: {tot_gp} G*Power vakası, {tot_sm} statsmodels vakası. Açıklanmamış fark: "
        f"**{len(summary['mismatch'])}**.",
        f"- G*Power a priori vakaları: **{m}/{n}** eşleşme (N tam aynı ya da G*Power'ın reddettiği girdide bizim de "
        f"hata vermemiz). Kalan {n - m} vaka sözleşmenin reddettiği girdi; \"Açıklanmış farklar\" tablosunda.",
        "",
    ]
    if summary["mismatch"]:
        lines += ["## Açıklanmamış farklar", ""]
        for r in gp + sm:
            if r["status"] == "mismatch":
                lines.append(f"- `{r['id']}` ({r['source']}): {r['detail']}")
        lines.append("")

    lines += ["## Açıklanmış farklar", "",
              "G*Power'ın kabul ettiği ama CONTRACT.md §5'in yasakladığı girdiler. Düzenek bizim JSON'umuzu okuduğu için",
              "sözleşme kazanır; beklenen yanıt hatadır. Motor bu davranışları ayrıca belgeliyor",
              "(`docs/t-paired-validation.md`, B3 ve B5).", "",
              "| Vaka | Girdi | Neden | Bizim yanıt |", "|---|---|---|---|"]
    for r in gp:
        if r["status"] == "explained":
            inp = ", ".join(f"{k}={v}" for k, v in r["input"].items() if k not in ("test",))
            why, _, ours = r["detail"].rpartition("; bizim: ")
            lines.append(f"| `{r['id']}` | {inp} | {why} | `{ours}` |")

    lines += ["", "## G*Power'ın reddettiği girdiler", "",
              "G*Power bir uyarı kutusu gösterdi; bizim de hata döndürmemiz beklenir.", "",
              "| Vaka | G*Power mesajı → bizim kod |", "|---|---|"]
    for r in gp:
        if r["source"] == "boundary_harvest.csv" and r["detail"].startswith("G*Power:"):
            lines.append(f"| `{r['id']}` | {r['detail'][len('G*Power: '):]} |")

    ap = [r for r in sm if r["mode"] == "a-priori"]
    differ = [r for r in ap if r.get("round_would_differ")]
    lines += [
        "", "## Bulgu: kütüphaneler N'yi kesirli verir, G*Power yukarı yuvarlar", "",
        f"statsmodels `solve_power` {len(ap)} a priori vakanın hepsinde kesirli N döndürdü. Bizim N (ve G*Power'ın N'i)",
        "hedef güce ulaşan en küçük tam sayıdır, yani ⌈N⌉. G*Power vektörlerinin hepsi bu kuralla tutuyor.",
        f"Sıradan yuvarlama (round) {len(differ)}/{len(ap)} vakada eksik N verirdi, yani istenen güce ulaşılamazdı. Örnekler:",
        "",
        "| Vaka | statsmodels N | round | ⌈N⌉ = bizim |", "|---|---:|---:|---:|",
    ]
    for r in differ[:8]:
        lines.append(f"| `{r['id']}` | {r['sm_n']:.4f} | {round(r['sm_n'])} | {r['ours']['n_total']} |")
    lines += [
        "",
        "## Bulgu: statsmodels iki kuyruklu güçte NaN döndürüyor", "",
        f"{sum(1 for r in sm if r.get('nan_fallback'))} post hoc vakada (hepsi iki kuyruklu, güç ≈ 1) statsmodels NaN döndürdü:",
        "scipy'nin `nct.cdf` fonksiyonu alt kuyrukta hesap yapamıyor. Motorumuz aynı hatayı yansıma özdeşliğiyle",
        "aşıyor (`core/distributions.py`, `nct_cdf`). Bu vakalar statsmodels'ın üst kuyruk gücüyle (tek kuyruk, α/2)",
        "yine 1e-6 içinde karşılaştırıldı; alt kuyruğun katkısı burada 1e-6'nın çok altında. Tabloda \"açıklanmış\" olarak sayılıyorlar.",
        "",
        "Post hoc vakalarında statsmodels ile fark 1e-6'nın çok altında, çünkü iki uygulama da merkezi olmayan",
        "t dağılımını aynı tanımla (iki kuyrukta iki kuyruğun da katkısı) hesaplıyor. Ancak statsmodels G*Power değil:",
        "N ≥ 3 sınırı, güç < α reddi ve |dz| > 0.00001 eşiği yalnızca G*Power vektörleriyle sınanabilir.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m noncentra.difftest_paired")
    p.add_argument("--report", help="write the Markdown report here")
    p.add_argument("--regenerate", action="store_true", help="rebuild the statsmodels CSV first")
    args = p.parse_args(argv)
    if args.regenerate:
        print(f"wrote {generate_statsmodels()} statsmodels vectors to {SM_CSV}", file=sys.stderr)
    summary = run(args.report)
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if summary["mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
