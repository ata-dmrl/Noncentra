"""CONTRACT.md §2 and §5: command-line rules that do not depend on G*Power's numbers."""
import json

import pytest

from harness import command, run

pytestmark = pytest.mark.contract

BASE = ["--test", "t2-indep", "--mode", "a-priori", "--tails", "2", "--d", "0.5", "--alpha", "0.05",
        "--power", "0.95", "--ratio", "1"]


@pytest.fixture(autouse=True)
def _cli_present():
    if command() is None:
        pytest.fail("gpower-clone not found; install src/ (pip install -e .) or set GPOWER_CLONE")


def one_json(out):
    lines = out.strip().splitlines()
    assert len(lines) == 1, f"stdout must be one line: {out!r}"
    return json.loads(lines[0])


def test_version():
    code, out, _, _ = run(["--version"])
    doc = one_json(out)
    assert code == 0
    assert doc["contract_version"] == "1.0.0" and doc["name"] and doc["engine"]


def test_task_example_two_tailed():
    """The example in the assignment text: d=0.5, alpha=0.05, power=0.95, two-tailed."""
    code, out, _, _ = run(BASE)
    doc = one_json(out)
    assert code == 0
    assert (doc["n1"], doc["n2"], doc["n_total"], doc["df"]) == (105, 105, 210, 208)
    assert abs(doc["actual_power"] - 0.9501287) < 1e-6
    assert abs(doc["critical_t"] - 1.9714347) < 1e-6


def test_integer_fields_are_json_integers():
    _, out, _, _ = run(BASE)
    raw = out.strip()
    for key in ("n1", "n2", "n_total", "df"):
        assert f'"{key}": 105.0' not in raw and f'"{key}":105.0' not in raw
        assert isinstance(json.loads(raw)[key], int)


def test_deterministic():
    assert run(BASE)[1] == run(BASE)[1]


@pytest.mark.parametrize("args, code", [
    (["--test", "t2-indep", "--mode", "a-priori", "--tails", "2", "--d", "0.5", "--alpha", "0.05", "--ratio", "1"],
     "MISSING_PARAM"),
    (BASE + ["--colour", "red"], "UNKNOWN_PARAM"),
    (["--test", "t2-indep", "--mode", "post-hoc", "--tails", "2", "--d", "0.5", "--alpha", "0.05",
      "--n1", "20", "--n2", "20", "--power", "0.8"], "UNKNOWN_PARAM"),
    (["--test", "t2-indep", "--mode", "post-hoc", "--tails", "2", "--d", "abc", "--alpha", "0.05",
      "--n1", "20", "--n2", "20"], "INVALID_VALUE"),
    (["--test", "t2-indep", "--mode", "post-hoc", "--tails", "2", "--d", "0.5", "--alpha", "0.05",
      "--n1", "20.5", "--n2", "20"], "INVALID_VALUE"),
    (["--test", "t2-indep", "--mode", "a-priori", "--tails", "2", "--d", "0.5", "--alpha", "0",
      "--power", "0.95", "--ratio", "1"], "OUT_OF_RANGE"),
    (["--test", "t2-indep", "--mode", "a-priori", "--tails", "3", "--d", "0.5", "--alpha", "0.05",
      "--power", "0.95", "--ratio", "1"], "OUT_OF_RANGE"),
    (["--test", "anova-oneway", "--mode", "a-priori", "--f", "0.25", "--alpha", "0.05", "--power", "0.95",
      "--groups", "1"], "OUT_OF_RANGE"),
    (["--test", "t3-magic", "--mode", "a-priori"], "UNSUPPORTED"),
    (["--test", "t2-indep", "--mode", "guess"], "UNSUPPORTED"),
])
def test_invalid_input(args, code):
    exit_code, out, _, _ = run(args)
    doc = one_json(out)
    assert "error" in doc, doc
    assert exit_code == 2, f"exit {exit_code}"
    assert doc.get("code") == code, doc


def test_power_below_alpha_is_rejected():
    """G*Power: 'Power must be greater than or equal to alpha.' (LEDGER, docs/t-paired-validation.md B2)."""
    exit_code, out, _, _ = run(["--test", "t-paired", "--mode", "a-priori", "--tails", "2", "--dz", "0.5",
                                "--alpha", "0.05", "--power", "0.04"])
    doc = one_json(out)
    assert "error" in doc and exit_code != 0
