"""Run the CLI and the MCP server for real and keep what they print, for the tour video.

usage: python docs/demo/capture_cli.py <out_dir>
Writes <out_dir>/cli.json: [{"cmd", "stdout", "code", "seconds"}], <out_dir>/mcp.json.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tour_cases import CASES, cli_args  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXE = shutil.which("gpower-clone")

SCRIPT = [
    ["--version"],
    # CONTRACT.md examples, one per family.
    ["--test", "t2-indep", "--mode", "a-priori", "--tails", "2", "--d", "0.5", "--alpha", "0.05",
     "--power", "0.95", "--ratio", "1"],
    ["--test", "t-paired", "--mode", "a-priori", "--tails", "1", "--dz", "0.5", "--alpha", "0.05",
     "--power", "0.95"],
    ["--test", "anova-oneway", "--mode", "a-priori", "--f", "0.25", "--alpha", "0.05", "--power", "0.95",
     "--groups", "5"],
    ["--test", "multireg-r2", "--mode", "a-priori", "--f2", "0.15", "--alpha", "0.05", "--power", "0.95",
     "--predictors", "2"],
    ["--test", "chi2-contingency", "--mode", "a-priori", "--w", "0.3", "--alpha", "0.05", "--power", "0.95",
     "--df", "5"],
    # The other modes.
    *[cli_args(c) for c in CASES[4:8]],
    # Errors, as CONTRACT §2.4 asks.
    ["--test", "t2-indep", "--mode", "a-priori", "--tails", "2", "--d", "0.5", "--alpha", "0.05",
     "--ratio", "1"],
    ["--test", "t2-indep", "--mode", "a-priori", "--tails", "2", "--d", "0.5", "--alpha", "0.05",
     "--power", "0.01", "--ratio", "1"],
    ["--test", "t2-indep", "--mode", "post-hoc", "--tails", "2", "--d", "0.5", "--alpha", "0.05",
     "--power", "0.8", "--n1", "30", "--n2", "30"],
    ["--test", "t-paired", "--mode", "post-hoc", "--tails", "2", "--dz", "0.5", "--alpha", "0.05",
     "--n_total", "45.5"],
    ["--test", "anova-oneway", "--mode", "a-priori", "--f", "0", "--alpha", "0.05", "--power", "0.8",
     "--groups", "3"],
]


def run_cli(args):
    t = time.perf_counter()
    p = subprocess.run([EXE, *args], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    return {"cmd": "gpower-clone " + " ".join(args), "stdout": p.stdout.strip(), "code": p.returncode,
            "seconds": round(time.perf_counter() - t, 2)}


def run_mcp():
    """A real MCP session over stdio: initialize, list the tools, call power_analysis."""
    proc = subprocess.Popen([shutil.which("gpower-clone-mcp")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", cwd=ROOT)
    log = []

    def send(msg, expect=True):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        log.append({"dir": "→", "msg": msg})
        if expect:
            reply = json.loads(proc.stdout.readline())
            log.append({"dir": "←", "msg": reply})
            return reply

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "tour-video", "version": "1"}}})
    send({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect=False)
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
          "params": {"name": "power_analysis",
                     "arguments": {"test": "t-paired", "mode": "a-priori", "tails": 1, "dz": 0.5,
                                   "alpha": 0.05, "power": 0.95}}})
    send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
          "params": {"name": "power_analysis",
                     "arguments": {"test": "anova-oneway", "mode": "a-priori", "f": 0.25, "alpha": 0.05,
                                   "power": 0.95, "groups": 5}}})
    proc.stdin.close()
    proc.wait(timeout=10)
    return log


def main(out_dir):
    out = Path(out_dir)
    runs = []
    for args in SCRIPT:
        runs.append(run_cli(args))
        print(runs[-1]["code"], runs[-1]["seconds"], runs[-1]["stdout"][:110])
    (out / "cli.json").write_text(json.dumps(runs, ensure_ascii=False, indent=1), "utf-8")
    (out / "mcp.json").write_text(json.dumps(run_mcp(), ensure_ascii=False, indent=1), "utf-8")
    pytest = subprocess.run([sys.executable, "-m", "pytest", "tests/contract", "-q", "-p", "no:cacheprovider"],
                            capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    (out / "pytest.txt").write_text(pytest.stdout[-3000:], "utf-8")
    print(pytest.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    main(*sys.argv[1:])
