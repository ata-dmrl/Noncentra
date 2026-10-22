"""Executable SPEC.md: every Gherkin `Örnekler` table row runs through gpower-clone.

Column rules
- `mode` and the contract input fields of that mode are inputs; `extra` holds k=v inputs.
- In a-priori rows `n_total` is an expected output, otherwise an input.
- `out_<key>` is an expected output named <key>; other filled columns are expected outputs.
- Rows with `error_code` expect exit code 2 with that code (and `error_field` if given);
  every filled input-like column is sent as is.
"""
import json
import re
from pathlib import Path

import pytest

from noncentra import contract, contract_cli

SPEC = Path(__file__).resolve().parent.parent / "SPEC.md"
INPUT_LIKE = ["tails", "dz", "alpha", "power", "beta_alpha_ratio", "n_total"]
INT_KEYS = {"n_total", "df"}
TOL = 1e-6


def spec_rows():
    rows, header, scenario = [], None, ""
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("Senaryo Taslağı:"):
            scenario, header = s.split(":", 1)[1].strip(), None
        elif s.startswith("Örnekler:"):
            header = []
        elif header is not None and s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not header:
                header.extend(cells)
            else:
                rows.append((scenario, dict(zip(header, cells))))
        elif header is not None and s and not s.startswith("|"):
            header = None
    return rows


ROWS = spec_rows()


def run_cli(fields, capsys):
    argv = []
    for k, v in fields.items():
        argv += [f"--{k}", v]
    code = contract_cli.main(argv)
    out = capsys.readouterr().out
    assert out.count("\n") == 1, f"stdout must be one line: {out!r}"
    return json.loads(out), code


def test_spec_has_examples():
    assert len(ROWS) >= 40
    assert {r["mode"] for _, r in ROWS} >= set(contract.MODES)


@pytest.mark.parametrize("scenario,row", ROWS, ids=[f"{s[:28]}|{i}" for i, (s, _) in enumerate(ROWS)])
def test_spec_example(scenario, row, capsys):
    mode = row["mode"]
    fields = {"test": "t-paired", "mode": mode}

    if row.get("error_code"):
        for k in INPUT_LIKE:
            if row.get(k):
                fields[k] = row[k]
        if row.get("extra"):
            k, _, v = row["extra"].partition("=")
            fields[k] = v
        out, code = run_cli(fields, capsys)
        assert code == 2 and "error" in out, out
        assert out["code"] == row["error_code"], out
        if row.get("error_field"):
            assert out.get("field") == row["error_field"], out
        return

    wanted = contract.input_fields("t-paired", mode)
    expected = {}
    for k, v in row.items():
        if k == "mode" or not v:
            continue
        if k in wanted:
            fields[k] = v
        else:
            expected[re.sub(r"^out_", "", k)] = v
    out, code = run_cli(fields, capsys)
    assert code == 0, out
    for key, text in expected.items():
        assert key in out, f"{key} missing from {out}"
        if key in INT_KEYS:
            assert out[key] == int(text) and isinstance(out[key], int), f"{key}: {out[key]} != {text}"
        else:
            want = float(text)
            got = out[key]
            assert abs(got - want) <= TOL or abs(got - want) <= TOL * abs(want), f"{key}: {got} vs {want}"
