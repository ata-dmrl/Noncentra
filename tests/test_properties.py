"""Invariants that must hold for any input (seeded random sampling, no extra deps)."""
import numpy as np
import pytest

from noncentra.api import analyze

RNG = np.random.default_rng(20261016)
N_CASES = 60


def _t_case(test):
    return (test, {"tails": int(RNG.choice([1, 2]))}, float(RNG.uniform(0.05, 1.5)),
            int(RNG.integers(3, 300)), float(RNG.uniform(0.001, 0.2)))


def _f_case(test):
    if test == "f.anova_oneway":
        k = int(RNG.integers(2, 8))
        return test, {"groups": k}, float(RNG.uniform(0.05, 0.8)), int(RNG.integers(k + 2, 400)), float(RNG.uniform(0.001, 0.2))
    p = int(RNG.integers(1, 12))
    opts = {"predictors": p}
    if test == "f.regression_r2_increase":
        opts["tested"] = int(RNG.integers(1, p + 1))
    return test, opts, float(RNG.uniform(0.01, 0.6)), int(RNG.integers(p + 3, 400)), float(RNG.uniform(0.001, 0.2))


TESTS = ["t.two_sample", "t.one_sample", "t.paired", "f.anova_oneway", "f.regression_r2", "f.regression_r2_increase"]
CASES = [(_t_case if t.startswith("t.") else _f_case)(t) for t in RNG.choice(TESTS, N_CASES)]
IDS = [f"{c[0]}-{i}" for i, c in enumerate(CASES)]


def sizes(test, n):
    return {"n1": n, "n2": n} if test == "t.two_sample" else {"n": n}


def run(test, options, analysis, **params):
    return analyze({"test": test, "analysis": analysis, "options": options, "params": params})["output"]


def power(test, options, effect, n, alpha):
    return run(test, options, "post_hoc", effect_size=effect, alpha=alpha, sizes=sizes(test, n))["power"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_power_grows_with_n_alpha_and_effect(case):
    test, opts, e, n, a = case
    p = power(*case)
    assert a - 1e-12 <= p <= 1
    assert power(test, opts, e, n + 5, a) >= p
    assert power(test, opts, e, n, min(a * 1.5, 0.5)) >= p
    assert power(test, opts, e * 1.2, n, a) >= p


@pytest.mark.parametrize("case", CASES[:30], ids=IDS[:30])
def test_zero_effect_gives_alpha(case):
    test, opts, _, n, a = case
    assert power(test, opts, 0.0, n, a) == pytest.approx(a, abs=1e-9)


@pytest.mark.parametrize("case", CASES[:30], ids=IDS[:30])
def test_a_priori_returns_smallest_n(case):
    test, opts, e, _, a = case
    out = run(test, opts, "a_priori", effect_size=e, alpha=a, power=0.8)
    n = out["sizes"].get("n1", out["sizes"].get("n"))
    assert out["power"] >= 0.8
    # ANOVA steps in whole groups (G*Power rule), everything else in single units.
    step = opts.get("groups", 1)
    if n - step >= out.get("df_num", 0) + 2 + step:
        assert power(test, opts, e, n - step, a) < 0.8


@pytest.mark.parametrize("case", CASES[:30], ids=IDS[:30])
def test_sensitivity_inverts_post_hoc(case):
    test, opts, _, n, a = case
    out = run(test, opts, "sensitivity", alpha=a, power=0.8, sizes=sizes(test, n))
    assert power(test, opts, out["effect_size"], n, a) == pytest.approx(0.8, abs=1e-8)


@pytest.mark.parametrize("case", CASES[:30], ids=IDS[:30])
def test_compromise_hits_ratio(case):
    test, opts, e, n, _ = case
    out = run(test, opts, "compromise", effect_size=e, beta_alpha_ratio=2.0, sizes=sizes(test, n))
    assert out["beta"] / out["alpha"] == pytest.approx(2.0, rel=1e-6)
