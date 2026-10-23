"""Scale vectors from statsmodels (an independent implementation): python -I oracle/build_statsmodels_vectors.py

CONTRACT/ödev: "Ölçek için R'daki pwr ya da Python'daki statsmodels ile 500'den fazla vektör."
Only post-hoc power is used as an exact expectation: statsmodels solves a-priori N as a
fraction while G*Power reports integers, so a-priori is not comparable directly (that
difference is itself a finding, recorded in LEDGER.md). The fractional N for each a-priori
setting is written to oracle/statsmodels_fractional_n.csv for that analysis.
"""
import csv
import itertools
import json
import math
from pathlib import Path

from statsmodels.stats.power import (FTestAnovaPower, FTestPowerF2, GofChisquarePower, TTestIndPower,
                                     TTestPower)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "oracle" / "statsmodels_vectors.jsonl"
FRAC = ROOT / "oracle" / "statsmodels_fractional_n.csv"
ALPHAS = (0.01, 0.05, 0.1)


def vectors():
    ind, one, anova, f2, chi = TTestIndPower(), TTestPower(), FTestAnovaPower(), FTestPowerF2(), GofChisquarePower()
    for d, n, a, tails, ratio in itertools.product((0.2, 0.5, 0.8, 1.2), (10, 30, 100, 300), ALPHAS, (1, 2), (1, 2)):
        alt = "two-sided" if tails == 2 else "larger"
        n2 = int(n * ratio)
        p = ind.power(effect_size=d, nobs1=n, alpha=a, ratio=n2 / n, alternative=alt)
        yield "t2-indep", {"tails": tails, "d": d, "alpha": a, "n1": n, "n2": n2}, p
    for dz, n, a, tails in itertools.product((0.2, 0.5, 0.8, 1.2), (8, 25, 80, 200), ALPHAS, (1, 2)):
        alt = "two-sided" if tails == 2 else "larger"
        yield "t-paired", {"tails": tails, "dz": dz, "alpha": a, "n_total": n}, one.power(effect_size=dz, nobs=n, alpha=a, alternative=alt)
    for f, k, n, a in itertools.product((0.1, 0.25, 0.4), (2, 3, 5), (30, 90, 300), ALPHAS):
        yield "anova-oneway", {"f": f, "groups": k, "alpha": a, "n_total": n}, anova.power(effect_size=f, nobs=n, alpha=a, k_groups=k)
    for w, df, n, a in itertools.product((0.1, 0.3, 0.5), (1, 3, 5), (30, 100, 300), ALPHAS):
        yield "chi2-contingency", {"w": w, "df": df, "alpha": a, "n_total": n}, chi.power(effect_size=w, nobs=n, alpha=a, n_bins=df + 1)
    for e, p, n, a in itertools.product((0.02, 0.15, 0.35), (1, 3, 8), (30, 100, 300), ALPHAS):
        yield "multireg-r2", {"f2": e, "predictors": p, "alpha": a, "n_total": n}, f2.power(effect_size=e, df_num=p, df_denom=n - p - 1, alpha=a, ncc=1)


def fractional():
    ind, anova, chi = TTestIndPower(), FTestAnovaPower(), GofChisquarePower()
    for d, pw in itertools.product((0.2, 0.5, 0.8), (0.8, 0.95)):
        yield "t2-indep", f"d={d}", pw, 2 * ind.solve_power(effect_size=d, alpha=0.05, power=pw, ratio=1)
    for f, k, pw in itertools.product((0.1, 0.25, 0.4), (3, 5), (0.8, 0.95)):
        yield "anova-oneway", f"f={f},k={k}", pw, anova.solve_power(effect_size=f, alpha=0.05, power=pw, k_groups=k)
    for w, df, pw in itertools.product((0.1, 0.3, 0.5), (1, 5), (0.8, 0.95)):
        yield "chi2-contingency", f"w={w},df={df}", pw, chi.solve_power(effect_size=w, alpha=0.05, power=pw, n_bins=df + 1)


def main():
    count = 0
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for i, (fam, inp, power) in enumerate(vectors()):
            if not math.isfinite(power):
                continue  # statsmodels hits the scipy nct NaN (LEDGER) on a few far tails
            v = {"id": f"statsmodels/{fam}/{i:04d}", "source": "statsmodels",
                 "input": {"test": fam, "mode": "post-hoc", **inp}, "expected": {"power": power}}
            fh.write(json.dumps(v) + "\n")
            count += 1
    with FRAC.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "setting", "power", "statsmodels_n_total", "ceil"])
        for fam, setting, pw, n in fractional():
            w.writerow([fam, setting, pw, f"{n:.4f}", math.ceil(n)])
    print(f"{count} vectors -> {OUT.relative_to(ROOT)}; fractional N table -> {FRAC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
