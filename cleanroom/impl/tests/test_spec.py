"""SPEC.md §3 Örnekler tabloları + CONTRACT.md §9 t-paired açık vektörleri.

Beklenen değerler burada hesaplanmaz: SPEC.md ve CONTRACT.md çalışma anında okunur,
her tablo satırı bir test olur. CLI alt süreç olarak çağrılır (sözleşme CLI'dir).
"""
import json
import pathlib
import re
import subprocess
import sys
import time

import pytest

IMPL = pathlib.Path(__file__).resolve().parents[1]
ROOT = IMPL.parent
CLI = [sys.executable, str(IMPL / "gpower_clone.py")]
SPEC = (ROOT / "SPEC.md").read_text(encoding="utf-8")
CONTRACT = (ROOT / "CONTRACT.md").read_text(encoding="utf-8")

INT_FIELDS = {"n_total", "df"}
# CONTRACT.md §4.2: her modun girdi alanları
MODE_INPUTS = {
    "a-priori": ["tails", "dz", "alpha", "power"],
    "post-hoc": ["tails", "dz", "alpha", "n_total"],
    "compromise": ["tails", "dz", "beta_alpha_ratio", "n_total"],
    "criterion": ["tails", "dz", "power", "n_total"],
    "sensitivity": ["tails", "alpha", "power", "n_total"],
}


def run(args):
    p = subprocess.run(CLI + args, capture_output=True, text=True)
    return p


def close(got, exp):
    d = abs(got - exp)
    return d <= 1e-6 or (exp != 0 and d / abs(exp) <= 1e-6)


# ---------------------------------------------------------------- tablo okuma
def parse_tables():
    """Gherkin bloğundaki her 'Örnekler:' tablosunu (senaryo adı, satır sözlükleri) olarak döndürür."""
    block = SPEC.split("```gherkin", 1)[1].split("```", 1)[0]
    tables, scenario, header, rows = [], None, None, None
    for line in block.splitlines() + [""]:
        s = line.strip()
        if s.startswith("Senaryo Taslağı:"):
            scenario = s.split(":", 1)[1].strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if header is None:
                header, rows = cells, []
            else:
                rows.append(dict(zip(header, cells)))
        elif header is not None:
            tables.append((scenario, rows))
            header = None
    return tables


TABLES = parse_tables()
SUCCESS, ERRORS = [], []
for scen, rows in TABLES:
    for i, r in enumerate(rows):
        tid = f"{scen}#{i + 1}:" + ",".join(f"{k}={v}" for k, v in r.items() if v)
        (ERRORS if "error_code" in r else SUCCESS).append(pytest.param(r, id=tid))


def args_for(row, keys):
    a = ["--test", "t-paired"]
    for k in keys:
        a += [f"--{k}", row[k]]
    return a


@pytest.mark.parametrize("row", SUCCESS)
def test_spec_success(row):
    mode = row["mode"]
    inputs = [k for k in MODE_INPUTS[mode] if row.get(k, "")]
    p = run(args_for(row, ["mode"] + inputs))
    assert p.returncode == 0, p.stdout + p.stderr
    lines = p.stdout.splitlines()
    assert len(lines) == 1
    out = json.loads(lines[0])
    for col, val in row.items():
        if col == "mode" or col in inputs or val == "":
            continue
        key = col[4:] if col.startswith("out_") else col
        assert key in out, f"{key} çıktıda yok: {out}"
        if key in INT_FIELDS:
            assert type(out[key]) is int and out[key] == int(val), (key, out[key], val)
        else:
            assert close(out[key], float(val)), (key, out[key], val)


@pytest.mark.parametrize("row", ERRORS)
def test_spec_errors(row):
    a = []
    for k, v in row.items():
        if k in ("error_code", "error_field") or v == "":
            continue
        if k == "extra":
            name, val = v.split("=", 1)
            a += [f"--{name}", val]
        else:
            a += [f"--{k}", v]
    p = run(["--test", "t-paired"] + a)
    lines = p.stdout.splitlines()
    assert len(lines) == 1, p.stdout + p.stderr
    out = json.loads(lines[0])
    assert "error" in out
    assert p.returncode == 2
    assert out["code"] == row["error_code"]
    assert out["field"] == row["error_field"]


# ---------------------------------------------------------- CONTRACT.md §9
def public_vectors():
    block = CONTRACT.split("```jsonl", 1)[1].split("```", 1)[0]
    vecs = [json.loads(l) for l in block.splitlines() if l.strip()]
    return [pytest.param(v, id=v["id"]) for v in vecs if v["input"]["test"] == "t-paired"]


@pytest.mark.parametrize("vec", public_vectors())
def test_public_vector(vec):
    a = []
    for k, v in vec["input"].items():
        a += [f"--{k}", str(v)]
    p = run(a)
    assert p.returncode == 0, p.stdout
    out = json.loads(p.stdout)
    for k, v in vec["expected"].items():
        if k in INT_FIELDS:
            assert type(out[k]) is int and out[k] == v
        else:
            assert close(out[k], v), (k, out[k], v)


# ---------------------------------------------------------------- SPEC.md §4
def test_output_format_integers():
    p = run("--test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95".split())
    assert p.returncode == 0
    assert len(p.stdout.splitlines()) == 1
    line = p.stdout.strip()
    for k in ("ncp", "critical_t", "df", "n_total", "actual_power"):
        assert f'"{k}"' in line
    assert re.search(r'"n_total": ?54[,}]', line) and re.search(r'"df": ?53[,}]', line)


def test_version():
    p = run(["--version"])
    assert p.returncode == 0
    assert json.loads(p.stdout)["contract_version"] == "1.0.0"


def test_timing_largest_n():
    t0 = time.perf_counter()
    p = run("--test t-paired --mode a-priori --tails 2 --dz 0.01 --alpha 0.05 --power 0.8".split())
    assert p.returncode == 0
    assert time.perf_counter() - t0 < 2.0
