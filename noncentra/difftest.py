"""Differential testing: our solver vs G*Power reference values vs statsmodels.

Reference rows live in noncentra/reference/*.csv. The `source` column says where a
row came from; rows marked *-unverified are recalled from the literature and get
replaced by harvested G*Power output (teardown/harvest) once that runs.
"""
import csv
import datetime
import html
import math
from importlib import resources

from .api import analyze

TOL_POWER = 1e-4
TOL_DISPLAY = 1e-6

# statsmodels is an independent implementation; we only use it as a cross-check.
GRID_EFFECTS = (0.2, 0.5, 0.8, 1.2)
GRID_SIZES = (5, 12, 30, 100)
GRID_ALPHAS = (0.01, 0.05)


def _num(value):
    return None if value in ("", None) else float(value)


def load_reference():
    rows = []
    for entry in resources.files("noncentra.reference").iterdir():
        if entry.name.endswith(".csv"):
            with entry.open(encoding="utf-8") as fh:
                rows.extend(csv.DictReader(fh))
    return rows


def request_from_row(row):
    options = {k: int(row[k]) for k in ("tails", "groups", "predictors", "tested") if row.get(k)}
    if row.get("ratio"):
        options["ratio"] = float(row["ratio"])
    params = {"effect_size": _num(row["effect_size"]), "alpha": _num(row["alpha"]),
              "power": _num(row["power"]), "beta_alpha_ratio": _num(row.get("beta_alpha_ratio"))}
    sizes = {k: int(row[k]) for k in ("n1", "n2", "n") if row.get(k)}
    if sizes:
        params["sizes"] = sizes
    return {"test": row["test"], "analysis": row["analysis"], "options": options,
            "params": {k: v for k, v in params.items() if v is not None}}


def check_reference_row(row):
    out = analyze(request_from_row(row))["output"]
    problems = []
    for key in ("n1", "n2", "n"):
        want = row.get(f"exp_{key}")
        if want and out["sizes"].get(key) != int(want):
            problems.append(f"{key}: got {out['sizes'].get(key)}, want {want}")
    # G*Power prints 7 decimals, so harvested rows are held to display precision.
    tol = TOL_DISPLAY if "harvest" in row["source"] else TOL_POWER
    for key, field in (("power", "exp_power"), ("critical_value", "exp_critical"),
                       ("effect_size", "exp_effect"), ("alpha", "exp_alpha")):
        want = _num(row.get(field))
        if want is not None and abs(out[key] - want) > tol:
            problems.append(f"{key}: got {out[key]:.7f}, want {want:.7f}")
    divergence = row.get("known_divergence")
    if problems and divergence:
        # Documented G*Power behaviour we deliberately do not copy (see docs/teardown-report.md).
        # We still require our own answer to be sound: a priori must reach the target power.
        sound = row["analysis"] != "a_priori" or out["power"] >= float(row["power"])
        return {"id": row["id"], "kind": "reference", "source": row["source"], "ok": sound,
                "known_divergence": True,
                "gpower_misses_target": row["analysis"] == "a_priori"
                and float(row["exp_power"]) < float(row["power"]),
                "detail": divergence if sound else f"{divergence}; noncentra misses target power",
                "ours": out}
    return {"id": row["id"], "kind": "reference", "source": row["source"],
            "ok": not problems, "detail": "; ".join(problems), "ours": out}


def statsmodels_cases():
    from statsmodels.stats.power import FTestAnovaPower, FTestPowerF2, TTestIndPower, TTestPower

    ind, one, anova, ftest = TTestIndPower(), TTestPower(), FTestAnovaPower(), FTestPowerF2()
    for d in GRID_EFFECTS:
        for n in GRID_SIZES:
            for a in GRID_ALPHAS:
                for tails, alt in ((2, "two-sided"), (1, "larger")):
                    yield (f"sm_ts_d{d}_n{n}_a{a}_t{tails}", "t.two_sample", {"tails": tails},
                           {"n1": n, "n2": n}, d, a,
                           ind.power(effect_size=d, nobs1=n, alpha=a, ratio=1.0, alternative=alt))
                    yield (f"sm_os_d{d}_n{n}_a{a}_t{tails}", "t.one_sample", {"tails": tails},
                           {"n": n}, d, a,
                           one.power(effect_size=d, nobs=n, alpha=a, alternative=alt))
    for f in (0.1, 0.25, 0.4):
        for k in (2, 3, 5):
            for n in (12, 30, 90, 300):
                for a in GRID_ALPHAS:
                    yield (f"sm_anova_f{f}_k{k}_n{n}_a{a}", "f.anova_oneway", {"groups": k}, {"n": n}, f, a,
                           anova.power(effect_size=f, nobs=n, alpha=a, k_groups=k))
    for f2 in (0.02, 0.15, 0.35):
        for p in (1, 3, 8):
            for n in (15, 40, 120):
                for a in GRID_ALPHAS:
                    # FTestPowerF2 (not FTestPower, whose df arguments are swapped): ncp = f2 * N.
                    yield (f"sm_reg_f2{f2}_p{p}_n{n}_a{a}", "f.regression_r2", {"predictors": p}, {"n": n}, f2, a,
                           ftest.power(effect_size=f2, df_num=p, df_denom=n - p - 1, alpha=a, ncc=1))


def check_statsmodels():
    results = []
    for case_id, test, options, sizes, d, a, theirs in statsmodels_cases():
        out = analyze({"test": test, "analysis": "post_hoc", "options": options,
                       "params": {"effect_size": d, "alpha": a, "sizes": sizes}})["output"]
        theirs = float(theirs)
        if math.isnan(theirs):
            # statsmodels hits the same scipy nct NaN that distributions.nct_cdf works around;
            # the reference is undefined here, so record it without failing.
            results.append({"id": case_id, "kind": "statsmodels", "source": "statsmodels",
                            "ok": True, "reference_nan": True,
                            "detail": f"ours {out['power']:.7f}; statsmodels returned NaN (scipy nct/ncf bug)",
                            "ours": out})
            continue
        results.append({"id": case_id, "kind": "statsmodels", "source": "statsmodels",
                        "ok": abs(out["power"] - theirs) <= TOL_POWER,
                        "detail": f"ours {out['power']:.7f} vs statsmodels {theirs:.7f}",
                        "ours": out})
    return results


def run_diff(report_path=None):
    results = [check_reference_row(r) for r in load_reference()]
    try:
        results += check_statsmodels()
    except ImportError:
        pass
    failed = [r for r in results if not r["ok"]]
    summary = {
        "checked": len(results),
        "failed": len(failed),
        "failures": [{"id": r["id"], "detail": r["detail"]} for r in failed],
        "reference_nan": sum(1 for r in results if r.get("reference_nan")),
        "known_divergence": sum(1 for r in results if r.get("known_divergence")),
        "gpower_misses_target": sum(1 for r in results if r.get("gpower_misses_target")),
        "unverified_reference_rows": sum(1 for r in results
                                         if r["kind"] == "reference" and "unverified" in r["source"]),
    }
    if report_path:
        write_report(report_path, results, summary)
    return summary


def write_report(path, results, summary):
    rows = "\n".join(
        f"<tr class={'ok' if r['ok'] else 'bad'}><td>{html.escape(r['id'])}</td>"
        f"<td>{r['kind']}</td><td>{html.escape(r['source'])}</td>"
        f"<td>{'SAPMA' if r.get('known_divergence') else 'OK' if r['ok'] else 'FARK'}</td>"
        f"<td>{html.escape(r['detail'])}</td></tr>"
        for r in sorted(results, key=lambda r: r["ok"])
    )
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = f"""<!doctype html><meta charset="utf-8"><title>noncentra diff</title>
<style>body{{font:14px system-ui;margin:24px}}table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:4px 8px}}.bad{{background:#fdd}}</style>
<h1>Diferansiyel test raporu</h1><p>{stamp} — {summary['checked']} durum,
{summary['failed']} tolerans dışı, {summary['known_divergence']} bilinen sapma
(G*Power {summary['gpower_misses_target']} durumda kendi hedef gücünü tutturamıyor),
{summary['unverified_reference_rows']} doğrulanmamış referans satırı.</p>
<table><tr><th>id</th><th>tür</th><th>kaynak</th><th>sonuç</th><th>ayrıntı</th></tr>{rows}</table>"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
