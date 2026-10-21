"""CLI contract tests: run the real CLI and validate stdout against the schemas."""
import json
import subprocess
import sys
from importlib import resources
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]


def schema(name):
    return json.loads(resources.files("noncentra.schemas").joinpath(name).read_text("utf-8"))


def cli(*args, stdin=None):
    proc = subprocess.run([sys.executable, "-m", "noncentra", *args], cwd=ROOT, input=stdin,
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


@pytest.mark.parametrize("args", [
    ["run", "t.two_sample", "a_priori", "-d", "0.5", "--alpha", "0.05", "--power", "0.8"],
    ["run", "t.two_sample", "post_hoc", "-d", "0.5", "--alpha", "0.05", "--size", "n1=20", "--size", "n2=30"],
    ["run", "t.one_sample", "sensitivity", "--alpha", "0.05", "--power", "0.8", "--size", "n=40"],
    ["run", "t.paired", "criterion", "-d", "0.5", "--power", "0.8", "--size", "n=30"],
    ["run", "t.two_sample", "compromise", "-d", "0.5", "--q", "1", "--size", "n1=20", "--size", "n2=20"],
    ["run", "t.two_sample", "a_priori", "-d", "0.5", "--alpha", "0.05", "--power", "0.8", "--tails", "1", "--ratio", "2"],
    ["run", "f.anova_oneway", "a_priori", "-d", "0.25", "--alpha", "0.05", "--power", "0.8", "--groups", "3"],
    ["run", "f.regression_r2", "sensitivity", "--alpha", "0.05", "--power", "0.8", "--predictors", "5", "--size", "n=92"],
    ["run", "f.regression_r2_increase", "post_hoc", "-d", "0.15", "--alpha", "0.05", "--predictors", "10",
     "--tested", "4", "--size", "n=85"],
])
def test_success_matches_result_schema(args):
    code, out, _ = cli(*args, "--json")
    assert code == 0
    jsonschema.validate(json.loads(out), schema("result.schema.json"))


@pytest.mark.parametrize("args, exit_code, err", [
    (["run", "t.nope", "post_hoc"], 2, "invalid_input"),
    (["run", "t.two_sample", "a_priori", "-d", "0.5", "--alpha", "1.5", "--power", "0.8"], 2, "invalid_input"),
    (["run", "t.two_sample", "a_priori", "--alpha", "0.05", "--power", "0.8"], 2, "invalid_input"),
    (["run", "t.two_sample", "a_priori", "-d", "0", "--alpha", "0.05", "--power", "0.8"], 3, "no_solution"),
    (["run", "t.two_sample", "bogus"], 2, "invalid_input"),
    (["run", "f.anova_oneway", "a_priori", "-d", "0.25", "--alpha", "0.05", "--power", "0.8", "--tails", "1"],
     2, "invalid_input"),
    (["run", "f.regression_r2_increase", "post_hoc", "-d", "0.15", "--alpha", "0.05", "--predictors", "3",
      "--tested", "5", "--size", "n=40"], 2, "invalid_input"),
])
def test_errors_match_error_schema(args, exit_code, err):
    code, out, _ = cli(*args, "--json")
    assert code == exit_code
    payload = json.loads(out)
    jsonschema.validate(payload, schema("error.schema.json"))
    assert payload["error"]["code"] == err


def test_stdout_is_single_json_document():
    _, out, _ = cli("run", "t.paired", "a_priori", "-d", "0.5", "--alpha", "0.05", "--power", "0.8", "--json")
    assert out.strip().count("\n") == 0


def test_request_from_stdin_round_trips():
    request = {"test": "t.two_sample", "analysis": "a_priori",
               "params": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8}}
    jsonschema.validate(request, schema("request.schema.json"))
    code, out, _ = cli("request", "-", stdin=json.dumps(request))
    assert code == 0
    assert json.loads(out)["output"]["sizes"] == {"n1": 64, "n2": 64}


def test_tests_listing():
    code, out, _ = cli("tests", "--json")
    assert code == 0
    names = {t["name"] for t in json.loads(out)["tests"]}
    assert {"t.two_sample", "t.one_sample", "t.paired", "f.anova_oneway", "f.regression_r2",
            "f.regression_r2_increase"} <= names
