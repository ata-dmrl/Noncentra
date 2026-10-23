"""Harvest CONTRACT.md families from a running G*Power, with a screenshot per case.

Covers what the assignment asks for at the edges: two tails, tiny and huge effects,
power equal to and below alpha, unequal allocation, the smallest N, extreme alpha and
inputs G*Power should refuse, across all five modes. Rows keep whatever G*Power shows,
including refusals (a warning box and '?' outputs); oracle/build_vectors.py turns
refusals into expected-error vectors.

usage: python teardown/harvest_contract.py <gpower_pid> <family> [<family> ...]
       family: t2-indep anova-oneway chi2-contingency multireg-r2
Writes oracle/<family>/harvest.csv and oracle/<family>/screenshots/.
"""
import csv
import ctypes
import itertools
import json
import os
import sys
from pathlib import Path

import win32ui as w
from harvest import SPECS, GPower
from harvest_paired import calculate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = {"t2-indep": "t.two_sample", "anova-oneway": "f.anova_oneway",
          "chi2-contingency": "chi2.contingency", "multireg-r2": "f.regression_r2"}
EFFECT = {"t2-indep": "d", "anova-oneway": "f", "chi2-contingency": "w", "multireg-r2": "f2"}
MEDIUM = {"d": 0.5, "f": 0.25, "w": 0.3, "f2": 0.15}


def cases(fam):
    e = EFFECT[fam]
    m = MEDIUM[e]
    if fam == "t2-indep":
        opts_list = [{"tails": 1}, {"tails": 2}]
        sized = lambda n: {"n1": n, "n2": n}  # noqa: E731
    elif fam == "anova-oneway":
        opts_list = [{"groups": 2}, {"groups": 3}, {"groups": 10}]
        sized = lambda n: {"n": n}  # noqa: E731
    elif fam == "chi2-contingency":
        opts_list = [{"df": 1}, {"df": 5}, {"df": 30}]
        sized = lambda n: {"n": n}  # noqa: E731
    else:
        opts_list = [{"predictors": 1}, {"predictors": 5}, {"predictors": 15}]
        sized = lambda n: {"n": n}  # noqa: E731
    for opts in opts_list:
        # Ordinary a-priori grid and the edges of effect size and power.
        for eff, alpha, power in itertools.product((m * 0.04, m, m * 4), (0.05,), (0.8, 0.95)):
            yield {"analysis": "a_priori", **opts, "effect_size": round(eff, 6), "alpha": alpha, "power": power}
        for power in (0.05, 0.04, 0.999):  # = alpha, < alpha, close to 1
            yield {"analysis": "a_priori", **opts, "effect_size": m, "alpha": 0.05, "power": power}
        for alpha in (0.001, 0.5):
            yield {"analysis": "a_priori", **opts, "effect_size": m, "alpha": alpha, "power": 0.8}
        # Other modes at a moderate N, and the smallest admissible N.
        yield {"analysis": "post_hoc", **opts, "effect_size": m, "alpha": 0.05, **sized(60)}
        yield {"analysis": "compromise", **opts, "effect_size": m, "q": 2, **sized(60)}
        yield {"analysis": "criterion", **opts, "effect_size": m, "power": 0.8, **sized(60)}
        yield {"analysis": "sensitivity", **opts, "alpha": 0.05, "power": 0.8, **sized(60)}
        for n in (2, 3, 7):
            yield {"analysis": "post_hoc", **opts, "effect_size": m, "alpha": 0.05, **sized(n)}
        # Inputs G*Power should refuse.
        yield {"analysis": "a_priori", **opts, "effect_size": 0, "alpha": 0.05, "power": 0.8}
    if fam == "t2-indep":
        # Unequal allocation, both tails, several ratios and effects (the rule G*Power does not document).
        for ratio, d, tails in itertools.product((0.3, 0.5, 1.7, 2, 3, 4.5), (0.3, 0.6), (1, 2)):
            yield {"analysis": "a_priori", "tails": tails, "effect_size": d, "alpha": 0.05, "power": 0.9, "ratio": ratio}
        yield {"analysis": "post_hoc", "tails": 2, "effect_size": 0.5, "alpha": 0.05, "n1": 20, "n2": 45}
        yield {"analysis": "sensitivity", "tails": 2, "alpha": 0.05, "power": 0.8, "n1": 30, "n2": 12}


def fill(gp, test, case):
    spec = SPECS[test]
    gp.select(test, case["analysis"])
    if "tails" in case:
        gp.set("Tail(s)", "Two" if case["tails"] == 2 else "One")
    for opt, label in spec.get("options", {}).items():
        if opt in case:
            gp.set(label, case[opt], exact=True)
    if "effect_size" in case:
        gp.set(spec["effect"], case["effect_size"], exact=True)
    if "alpha" in case:
        gp.set("α err prob", case["alpha"])
    if "power" in case:
        gp.set("Power", case["power"])
    if "q" in case:
        gp.set("β/α ratio", case["q"])
    if "ratio" in case:
        gp.set("Allocation ratio", case["ratio"])
    if "n1" in case:
        gp.set("Sample size group 1", case["n1"])
        gp.set("Sample size group 2", case["n2"])
    if "n" in case:
        gp.set("Total sample size", case["n"])


def main(pid, *families):
    ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    gp = GPower(int(pid))
    # A minimised window has no client area to capture; show it without taking focus.
    w.user32.ShowWindow(gp.hwnd, 4)  # SW_SHOWNOACTIVATE
    for fam in families:
        test = SOURCE[fam]
        out_dir = ROOT / "oracle" / fam
        shots = out_dir / "screenshots"
        os.makedirs(shots, exist_ok=True)
        rows = []
        for i, case in enumerate(cases(fam)):
            rid = f"g{i:03d}_{case['analysis']}"
            try:
                fill(gp, test, case)
                out, files = calculate(gp, str(shots / rid))
            except Exception as exc:  # one stuck case must not lose the rest
                print(f"{fam} {rid} {case}: {exc!r}", file=sys.stderr)
                w.dismiss_dialogs(gp.pid)
                continue
            rows.append({"id": rid, "test": test, "analysis": case["analysis"], "case": json.dumps(case),
                         "dialog": out.get("_dialog", ""),
                         "screenshots": " ".join(Path(f).name for f in files), "raw": repr(out)})
            print(fam, rid, out.get("Total sample size"), (out.get("_dialog") or "")[:60])
        with (out_dir / "harvest.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, ["id", "test", "analysis", "case", "dialog", "screenshots", "raw"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"{fam}: {len(rows)} rows -> {out_dir / 'harvest.csv'}")


if __name__ == "__main__":
    main(*sys.argv[1:])
