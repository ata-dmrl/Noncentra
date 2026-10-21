"""Matched-pairs t test at the edges, against G*Power 3.1.9.7.

Rows come from oracle/t-paired/boundary_harvest.csv (teardown/harvest_paired.py), each
with a screenshot. Where G*Power and the engine disagree the row is listed in
DIVERGENCES with the reason; those tests are strict xfails, so fixing the engine
turns them into failures until the entry is removed. See docs/t-paired-validation.md.
"""
import csv
from pathlib import Path

import pytest

from noncentra.api import analyze
from noncentra.core.solver import AnalysisError

REFUSED = (ValueError, AnalysisError)

CSV = Path(__file__).resolve().parent.parent / "oracle" / "t-paired" / "boundary_harvest.csv"
ROWS = list(csv.DictReader(CSV.open(encoding="utf-8")))

TOL = 1e-6

POWER_BELOW_ALPHA = "G*Power refuses power < alpha ('Power must be greater than or equal to alpha.'); the engine solves it"
N_FLOOR = "G*Power refuses N < 3 in post hoc and sensitivity; the engine accepts N = 2"
FRACTIONAL_N = "G*Power rounds a fractional N half up (3.4 -> 3, 3.5 -> 4); the engine refuses it"
NEGATIVE_DZ = "for dz < 0 G*Power reports a negative critical t and a one-tailed test turns to the lower tail"

DIVERGENCES = {
    "p016_a_priori": POWER_BELOW_ALPHA,
    "p021_a_priori": POWER_BELOW_ALPHA,
    "p023_a_priori": NEGATIVE_DZ,
    "p029_post_hoc": N_FLOOR,
    "p030_post_hoc": N_FLOOR,
    "p033_post_hoc": FRACTIONAL_N,
    "p034_post_hoc": FRACTIONAL_N,
    "p035_post_hoc": FRACTIONAL_N,
    "p036_post_hoc": FRACTIONAL_N,
    "p037_post_hoc": FRACTIONAL_N,
    "p038_post_hoc": FRACTIONAL_N,
    "p039_post_hoc": FRACTIONAL_N,
    "p040_post_hoc": FRACTIONAL_N,
    "p044_post_hoc": NEGATIVE_DZ,
    "p045_post_hoc": NEGATIVE_DZ,
    "p047_sensitivity": N_FLOOR,
}


def _num(text):
    return None if text in ("", "?", None) else float(text)


def request(row):
    params = {k: _num(row[k]) for k in ("effect_size", "alpha", "power", "beta_alpha_ratio")}
    if row["n"]:
        n = float(row["n"])
        params["sizes"] = {"n": int(n) if n.is_integer() else n}
    return {"test": "t.paired", "analysis": row["analysis"], "options": {"tails": int(row["tails"])},
            "params": {k: v for k, v in params.items() if v is not None}}


def expected(row):
    want = {"noncentrality": row["ncp"], "critical_value": row["critical_t"], "df": row["df"],
            "power": row["power_out"]}
    if row["analysis"] == "a_priori":
        want["n_total"] = row["n_total"]
    if row["analysis"] == "sensitivity":
        want["effect_size"] = row["effect_out"]
    if row["analysis"] in ("criterion", "compromise"):
        want["alpha"] = row["alpha_out"]
        want["beta"] = row["beta_out"]
    return {k: _num(v) for k, v in want.items() if _num(v) is not None}


def check(row):
    if row["dialog"]:
        with pytest.raises(REFUSED):
            analyze(request(row))
        return
    out = analyze(request(row))["output"]
    for key, want in expected(row).items():
        got = out[key]
        assert abs(got - want) <= TOL or abs(got - want) <= TOL * abs(want), f"{key}: got {got}, G*Power {want}"


@pytest.mark.regression
@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_paired_boundary(row):
    if row["id"] not in DIVERGENCES:
        check(row)
        return
    try:
        check(row)
    except (AssertionError, pytest.fail.Exception, *REFUSED):
        pytest.xfail(DIVERGENCES[row["id"]])
    pytest.fail(f"{row['id']} now matches G*Power; remove it from DIVERGENCES")
