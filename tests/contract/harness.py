"""Black-box harness for the gpower-clone CLI (CONTRACT.md).

The implementation is not imported: every check runs the executable the way the
course's grader will. Set GPOWER_CLONE to the command (default: `gpower-clone`), e.g.
GPOWER_CLONE="python -m src.gpower_clone".
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / "oracle"
INT_FIELDS = {"n1", "n2", "n_total", "df", "df1", "df2"}
TOL = 1e-6


def command():
    raw = os.environ.get("GPOWER_CLONE", "gpower-clone")
    parts = shlex.split(raw, posix=(os.name != "nt"))
    if len(parts) == 1 and shutil.which(parts[0]) is None:
        # Not installed (pip install -e .): run the same entry point as a module, still as a subprocess.
        if "GPOWER_CLONE" not in os.environ and (ROOT / "noncentra" / "contract_cli.py").exists():
            return [sys.executable, "-m", "noncentra.contract_cli"]
        return None
    if parts[0] == "python":
        parts[0] = sys.executable
    return parts


def argv(inp):
    args = []
    for key, value in inp.items():
        if key in ("test", "mode"):
            continue
        args += [f"--{key}", repr(value) if isinstance(value, float) else str(value)]
    return ["--test", inp["test"], "--mode", inp["mode"], *args]


def run(args, timeout=10):
    cmd = command()
    if cmd is None:
        raise FileNotFoundError("gpower-clone not found; install it or set GPOWER_CLONE")
    start = time.perf_counter()
    proc = subprocess.run([*cmd, *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT,
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    elapsed = time.perf_counter() - start
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def load(name):
    path = ORACLE / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compare(expected, actual):
    """CONTRACT.md §6. Returns a list of mismatch descriptions (empty when the vector passes)."""
    problems = []
    for key, want in expected.items():
        if key not in actual:
            problems.append(f"{key}: missing")
            continue
        got = actual[key]
        if key in INT_FIELDS:
            if not (isinstance(got, int) and not isinstance(got, bool)) or got != want:
                problems.append(f"{key}: got {got!r}, want {want}")
        else:
            if not isinstance(got, (int, float)) or isinstance(got, bool):
                problems.append(f"{key}: not a number ({got!r})")
            elif abs(got - want) > TOL and abs(got - want) > TOL * abs(want):
                problems.append(f"{key}: got {got}, want {want}")
    return problems


def check_vector(vector):
    """Run one vector; return (ok, details dict)."""
    code, out, err, elapsed = run(argv(vector["input"]))
    lines = out.strip().splitlines()
    detail = {"exit": code, "stdout": out.strip(), "elapsed": elapsed}
    if len(lines) != 1:
        return False, {**detail, "problem": f"stdout must be exactly one line, got {len(lines)}"}
    try:
        doc = json.loads(lines[0])
    except json.JSONDecodeError:
        return False, {**detail, "problem": "stdout is not JSON"}
    if "expected_error" in vector:
        want = vector["expected_error"].get("code")
        ok = "error" in doc and code != 0
        detail["code_match"] = want is None or doc.get("code") == want
        return ok, {**detail, "problem": None if ok else "expected an error with non-zero exit"}
    if code != 0 or "error" in doc:
        return False, {**detail, "problem": f"unexpected error: {doc}"}
    problems = compare(vector["expected"], doc)
    return not problems, {**detail, "problem": "; ".join(problems) or None}
