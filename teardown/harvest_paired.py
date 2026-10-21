"""Harvest boundary cases for the matched-pairs t test from a running G*Power.

harvest.py covers the ordinary grid; this script goes after the edges the manual does
not describe: tiny and huge dz, the smallest N, power at or below alpha, and inputs
G*Power should refuse. Unlike harvest.py it keeps rows whose inputs G*Power did not
take back, because that refusal is the finding. Every case also gets a screenshot of
the main window, and of any warning box before it is closed.

usage: python teardown/harvest_paired.py <gpower_pid> <out.csv> <screenshot_dir>
"""
import csv
import ctypes
import os
import sys
from ctypes import wintypes

from PIL import Image

import win32ui as w
from harvest import ID_CALCULATE, GPower, SPECS

TEST = "t.paired"
gdi32 = ctypes.WinDLL("gdi32")
PW_RENDERFULLCONTENT = 2


def cases():
    base = {"test": TEST, "alpha": 0.05}
    # Very small and very large effects: huge N, and where the N floor sits.
    for dz in (0.01, 0.05, 2, 3, 5, 10, 20):
        for tails in (1, 2):
            yield {**base, "analysis": "a_priori", "tails": tails, "effect_size": dz, "power": 0.8}
    # Power at, just above and below alpha; power close to 1.
    for power in (0.05, 0.051, 0.04, 0.999):
        yield {**base, "analysis": "a_priori", "tails": 2, "effect_size": 0.5, "power": power}
    yield {**base, "analysis": "a_priori", "tails": 1, "effect_size": 0.5, "power": 0.05}
    # Extreme alpha.
    for alpha in (0.001, 0.5, 0.9):
        yield {**base, "analysis": "a_priori", "tails": 2, "effect_size": 0.5, "power": 0.8, "alpha": alpha}
    # Inputs a careful implementation should refuse.
    for dz in (0, -0.5):
        yield {**base, "analysis": "a_priori", "tails": 2, "effect_size": dz, "power": 0.8}
    for alpha, power in ((0, 0.8), (1, 0.8), (0.05, 1)):
        yield {**base, "analysis": "a_priori", "tails": 2, "effect_size": 0.5, "power": power, "alpha": alpha}
    # Post hoc at the smallest sizes, a fractional size and a negative effect.
    for n in (1, 2, 3, 2.5):
        for tails in (1, 2):
            yield {**base, "analysis": "post_hoc", "tails": tails, "effect_size": 0.5, "n": n}
    # Fractional N is accepted: which integer does G*Power use?
    for n in (3.4, 3.5, 3.6, 10.2, 10.5, 10.7):
        yield {**base, "analysis": "post_hoc", "tails": 2, "effect_size": 0.5, "n": n}
    # Edges of the admissible alpha range (1e-07, 1) that G*Power reports.
    for alpha in (1e-07, 2e-07, 0.9999999):
        yield {**base, "analysis": "post_hoc", "tails": 2, "effect_size": 0.5, "n": 20, "alpha": alpha}
    yield {**base, "analysis": "post_hoc", "tails": 2, "effect_size": -0.5, "n": 20}
    yield {**base, "analysis": "post_hoc", "tails": 1, "effect_size": -0.5, "n": 20}
    # The other modes, two-tailed and with a beta/alpha ratio other than 1.
    yield {**base, "analysis": "sensitivity", "tails": 2, "power": 0.95, "n": 45}
    yield {**base, "analysis": "sensitivity", "tails": 1, "power": 0.95, "n": 2}
    yield {**base, "analysis": "sensitivity", "tails": 2, "power": 0.04, "n": 45}
    yield {"test": TEST, "analysis": "criterion", "tails": 2, "effect_size": 0.5, "power": 0.95, "n": 45}
    yield {"test": TEST, "analysis": "criterion", "tails": 1, "effect_size": 0.5, "power": 0.9999, "n": 45}
    for q in (4, 0.25):
        for tails in (1, 2):
            yield {"test": TEST, "analysis": "compromise", "tails": tails, "effect_size": 0.5, "q": q, "n": 45}


def screenshot(hwnd, path):
    rect = wintypes.RECT()
    w.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    screen = w.user32.GetDC(None)
    dc = gdi32.CreateCompatibleDC(screen)
    bmp = gdi32.CreateCompatibleBitmap(screen, width, height)
    gdi32.SelectObject(dc, bmp)
    w.user32.PrintWindow(hwnd, dc, PW_RENDERFULLCONTENT)
    header = (ctypes.c_uint32 * 10)(40, width, -height, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(dc, bmp, 0, height, buf, header, 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(dc)
    w.user32.ReleaseDC(None, screen)
    Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)


def fill(gp, case):
    spec = SPECS[TEST]
    gp.select(TEST, case["analysis"])
    gp.set("Tail(s)", "Two" if case["tails"] == 2 else "One")
    if "effect_size" in case:
        gp.set(spec["effect"], case["effect_size"], exact=True)
    if "alpha" in case:
        gp.set("α err prob", case["alpha"])
    if "power" in case:
        gp.set("Power", case["power"])
    if "q" in case:
        gp.set("β/α ratio", case["q"])
    if "n" in case:
        gp.set("Total sample size", case["n"])


def calculate(gp, stem):
    w.user32.PostMessageW(gp._by_id(ID_CALCULATE), w.BM_CLICK, 0, 0)
    w.wait(0.8)
    shots = []
    for i, h in enumerate(h for h in w.top_windows(gp.pid) if w.class_name(h) == "#32770"):
        shots.append(f"{stem}_dialog{i}.png")
        screenshot(h, shots[-1])
    notes = w.dismiss_dialogs(gp.pid)
    w.wait(0.3)
    screenshot(gp.hwnd, f"{stem}.png")
    out = {k: w.get_text(v["hwnd"]) for k, v in gp.fields().items()}
    if notes:
        out["_dialog"] = " | ".join(notes)
    return out, [f"{stem}.png", *shots]


COLUMNS = ["id", "analysis", "tails", "effect_size", "alpha", "power", "beta_alpha_ratio", "n",
           "taken", "dialog", "ncp", "critical_t", "df", "n_total", "power_out", "alpha_out", "beta_out",
           "effect_out", "screenshots", "raw"]

LABELS = {"ncp": "Noncentrality parameter δ", "critical_t": "Critical t", "df": "Df",
          "n_total": "Total sample size", "effect_out": "Effect size dz", "alpha_out": "α err prob",
          "beta_out": "β err prob"}


def to_row(i, case, out, shots, shot_dir):
    row = {"id": f"p{i:03d}_{case['analysis']}", "analysis": case["analysis"], "tails": case["tails"],
           "effect_size": case.get("effect_size", ""), "alpha": case.get("alpha", ""),
           "power": case.get("power", ""), "beta_alpha_ratio": case.get("q", ""), "n": case.get("n", ""),
           "dialog": out.get("_dialog", ""), "raw": repr(out),
           "screenshots": " ".join(os.path.relpath(s, shot_dir).replace("\\", "/") for s in shots)}
    for key, label in LABELS.items():
        row[key] = out.get(label, "")
    power_key = "Actual power" if case["analysis"] == "a_priori" else "Power (1-β err prob)"
    row["power_out"] = out.get(power_key, "")
    bad = not_taken(case, out)
    row["taken"] = f"no: {bad}" if bad else "yes"
    return row


def not_taken(case, out):
    """Inputs G*Power did not keep as typed; a refusal shows up as a reset field."""
    want = {"Effect size dz": case.get("effect_size"), "α err prob": case.get("alpha"),
            "Power (1-β err prob)": case.get("power"), "Total sample size": case.get("n")}
    if case["analysis"] == "sensitivity":
        del want["Effect size dz"]
    bad = {}
    for label, value in want.items():
        if value is None:
            continue
        try:
            got = float(out.get(label))
        except (TypeError, ValueError):
            got = None
        if got != float(value):
            bad[label] = (value, out.get(label))
    return bad


def main(pid, out_path, shot_dir):
    # Per-monitor DPI aware, so window rectangles are in physical pixels and the
    # screenshots are not cropped on a scaled display.
    ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    os.makedirs(shot_dir, exist_ok=True)
    gp = GPower(int(pid))
    rows = []
    for i, case in enumerate(cases()):
        stem = os.path.join(shot_dir, f"p{i:03d}_{case['analysis']}")
        try:
            fill(gp, case)
            out, shots = calculate(gp, stem)
        except Exception as exc:  # keep going; one stuck case should not lose the rest
            print(f"case {i} {case}: {exc!r}", file=sys.stderr)
            w.dismiss_dialogs(gp.pid)
            continue
        rows.append(to_row(i, case, out, shots, shot_dir))
        print(rows[-1]["id"], rows[-1]["n_total"], rows[-1]["power_out"], rows[-1]["dialog"][:80])
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
