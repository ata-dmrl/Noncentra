"""`gpower-clone` against CONTRACT.md: public vectors, error format, and the matched-pairs
boundary harvest (oracle/t-paired/boundary_harvest.csv) through the contract interface.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from noncentra import contract

ROOT = Path(__file__).resolve().parent.parent
VECTORS = [json.loads(l) for l in (ROOT / "oracle" / "public_vectors.jsonl").read_text().splitlines() if l.strip()]
BOUNDARY = list(csv.DictReader((ROOT / "oracle" / "t-paired" / "boundary_harvest.csv").open(encoding="utf-8")))
INT_KEYS = {"n1", "n2", "n_total", "df", "df1", "df2"}
TOL = 1e-6


def cli(*args):
    r = subprocess.run([sys.executable, "-m", "noncentra.contract_cli", *map(str, args)],
                       capture_output=True, text=True, timeout=10)
    lines = r.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be one line, got {r.stdout!r}"
    return json.loads(lines[0]), r.returncode


def args_of(inp):
    return [x for k, v in inp.items() for x in (f"--{k}", v)]


def assert_matches(got, expected):
    for key, want in expected.items():
        assert key in got, f"missing {key}"
        if key in INT_KEYS:
            assert isinstance(got[key], int) and got[key] == want, f"{key}: {got[key]} != {want}"
        else:
            assert abs(got[key] - want) <= TOL or abs(got[key] - want) <= TOL * abs(want), \
                f"{key}: {got[key]} vs G*Power {want}"


# --- §9 public vectors ------------------------------------------------------------

@pytest.mark.parametrize("vec", VECTORS, ids=[v["id"] for v in VECTORS])
def test_public_vector(vec):
    if vec["input"]["test"] in contract.KNOWN_UNIMPLEMENTED:
        out, code = contract.run(vec["input"])
        assert code == 2 and out["code"] == "UNSUPPORTED"
        return
    out, code = contract.run({k: str(v) for k, v in vec["input"].items()})
    assert code == 0, out
    assert_matches(out, vec["expected"])


@pytest.mark.parametrize("vec", [v for v in VECTORS if v["input"]["test"] == "t-paired"],
                         ids=lambda v: v["id"])
def test_public_vector_t_paired_subprocess(vec):
    out, code = cli(*args_of(vec["input"]))
    assert code == 0
    assert_matches(out, vec["expected"])


def test_version():
    out, code = cli("--version")
    assert code == 0 and out["contract_version"] == "1.0.0" and out["name"] and out["engine"]


def test_integers_are_json_integers():
    out, _ = cli("--test", "t-paired", "--mode", "a-priori", "--tails", 2, "--dz", 0.5,
                 "--alpha", 0.05, "--power", 0.95)
    assert out["n_total"] == 54 and out["df"] == 53
    assert isinstance(out["n_total"], int) and isinstance(out["df"], int)


# --- §2.4 errors -------------------------------------------------------------------

BASE = {"test": "t-paired", "mode": "a-priori", "tails": "2", "dz": "0.5", "alpha": "0.05", "power": "0.8"}

ERRORS = [
    ("missing", {k: v for k, v in BASE.items() if k != "power"}, "MISSING_PARAM", "power"),
    ("no default tails", {k: v for k, v in BASE.items() if k != "tails"}, "MISSING_PARAM", "tails"),
    ("unknown field", {**BASE, "foo": "1"}, "UNKNOWN_PARAM", "foo"),
    ("field of another mode", {**BASE, "n_total": "20"}, "UNKNOWN_PARAM", "n_total"),
    ("field of another test", {**BASE, "d": "0.5"}, "UNKNOWN_PARAM", "d"),
    ("not a number", {**BASE, "dz": "abc"}, "INVALID_VALUE", "dz"),
    ("comma decimal", {**BASE, "alpha": "0,05"}, "INVALID_VALUE", "alpha"),
    ("nan", {**BASE, "dz": "nan"}, "INVALID_VALUE", "dz"),
    ("tails 3", {**BASE, "tails": "3"}, "OUT_OF_RANGE", "tails"),
    ("tails 1.0", {**BASE, "tails": "1.0"}, "INVALID_VALUE", "tails"),
    ("dz 0", {**BASE, "dz": "0"}, "OUT_OF_RANGE", "dz"),
    ("dz negative", {**BASE, "dz": "-0.5"}, "OUT_OF_RANGE", "dz"),
    ("dz below G*Power floor", {**BASE, "dz": "0.00001"}, "OUT_OF_RANGE", "dz"),
    ("alpha 0", {**BASE, "alpha": "0"}, "OUT_OF_RANGE", "alpha"),
    ("alpha 1", {**BASE, "alpha": "1"}, "OUT_OF_RANGE", "alpha"),
    ("alpha below 1e-07", {**BASE, "alpha": "5e-08"}, "OUT_OF_RANGE", "alpha"),
    ("power 1", {**BASE, "power": "1"}, "OUT_OF_RANGE", "power"),
    ("power < alpha", {**BASE, "power": "0.04"}, "INCONSISTENT", "power"),
    ("unknown test", {**BASE, "test": "t-nope"}, "UNSUPPORTED", "test"),
    ("unknown mode", {**BASE, "mode": "a_priori"}, "UNSUPPORTED", "mode"),
    ("post-hoc N=2", {"test": "t-paired", "mode": "post-hoc", "tails": "2", "dz": "0.5",
                      "alpha": "0.05", "n_total": "2"}, "OUT_OF_RANGE", "n_total"),
    ("post-hoc N=1", {"test": "t-paired", "mode": "post-hoc", "tails": "2", "dz": "0.5",
                      "alpha": "0.05", "n_total": "1"}, "OUT_OF_RANGE", "n_total"),
    ("fractional N", {"test": "t-paired", "mode": "post-hoc", "tails": "2", "dz": "0.5",
                      "alpha": "0.05", "n_total": "10.5"}, "INVALID_VALUE", "n_total"),
    ("sensitivity power < alpha", {"test": "t-paired", "mode": "sensitivity", "tails": "2",
                                   "alpha": "0.05", "power": "0.04", "n_total": "45"},
     "INCONSISTENT", "power"),
]


@pytest.mark.parametrize("name,fields,code,field", ERRORS, ids=[e[0] for e in ERRORS])
def test_error(name, fields, code, field):
    out, exit_code = contract.run(fields)
    assert exit_code == 2
    assert out["error"] and out["code"] == code and out.get("field") == field


def test_error_through_cli():
    out, code = cli("--test", "t-paired", "--mode", "a-priori", "--tails", 2, "--dz", 0.5,
                    "--alpha", 0.05, "--power", 0.04)
    assert code == 2 and out["code"] == "INCONSISTENT"


def test_malformed_argv():
    out, code = cli("--test", "t-paired", "--mode")
    assert code == 2 and "error" in out


def test_power_equal_alpha_gives_two_pairs():
    # G*Power accepts power == alpha and returns N = 2 (oracle p014, p018).
    out, code = contract.run({**BASE, "power": "0.05"})
    assert code == 0 and out["n_total"] == 2


# --- boundary harvest through the contract -----------------------------------------

def _contract_fields(row):
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


def _expected(row):
    mode = row["analysis"]
    want = {"ncp": row["ncp"], "critical_t": row["critical_t"], "df": row["df"]}
    if mode == "a_priori":
        want.update(n_total=row["n_total"], actual_power=row["power_out"])
    elif mode == "post_hoc":
        want["power"] = row["power_out"]
    elif mode == "compromise":
        want.update(alpha=row["alpha_out"], beta=row["beta_out"], power=row["power_out"])
    elif mode == "criterion":
        want["alpha"] = row["alpha_out"]
    else:
        want["dz"] = row["effect_out"]
    return {k: (int(float(v)) if k in INT_KEYS else float(v)) for k, v in want.items() if v not in ("", "?")}


def _contract_rejects(row):
    """Rows G*Power accepts but CONTRACT.md §5 rules out (dz <= 0, fractional N)."""
    if row["effect_size"] and float(row["effect_size"]) <= 0:
        return "OUT_OF_RANGE"
    if row["n"] and not float(row["n"]).is_integer():
        return "INVALID_VALUE"
    return None


@pytest.mark.regression
@pytest.mark.parametrize("row", BOUNDARY, ids=[r["id"] for r in BOUNDARY])
def test_boundary_through_contract(row):
    out, code = contract.run(_contract_fields(row))
    if row["dialog"]:
        assert code != 0 and "error" in out, f"G*Power refused this: {row['dialog']!r}"
        return
    expected_code = _contract_rejects(row)
    if expected_code:
        assert code == 2 and out["code"] == expected_code
        return
    assert code == 0, out
    assert_matches(out, _expected(row))
