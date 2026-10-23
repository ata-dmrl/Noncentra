"""Run every tour case in a running G*Power and keep a screenshot plus the field values.

usage: python docs/demo/capture_gpower.py <gpower_pid> <out_dir>
Writes <out_dir>/gp_<key>.png and <out_dir>/gpower.json.
"""
import ctypes
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "teardown"), str(Path(__file__).parent)]

import win32ui as w  # noqa: E402
from harvest import GPower  # noqa: E402
from harvest_contract import fill  # noqa: E402
from harvest_paired import calculate  # noqa: E402
from tour_cases import CASES, gp_case  # noqa: E402


def main(pid, out_dir):
    ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gp = GPower(int(pid))
    w.user32.ShowWindow(gp.hwnd, 4)  # SW_SHOWNOACTIVATE: a minimised window has nothing to capture
    results = {}
    for case in CASES:
        fill(gp, case["gp"], gp_case(case))
        out, _ = calculate(gp, str(out_dir / f"gp_{case['key']}"))
        results[case["key"]] = out
        print(case["key"], out.get("Total sample size"), out.get("Actual power") or out.get("Power (1-β err prob)"))
    (out_dir / "gpower.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
