"""Render the 60-second CLI demo (docs/demo/demo.mp4) from real command output.

Every command below is executed; the video shows its actual stdout/stderr. Re-run after changes:

    python docs/demo/make_demo.py            # needs ffmpeg and Pillow
"""
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "demo.mp4"
W, H, FPS = 1280, 720, 15
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SIZE = 17
COLS = 108
BG, FG, PROMPT, NOTE, OK, ERR = (24, 26, 33), (220, 223, 228), (120, 200, 140), (150, 160, 175), (120, 200, 140), (235, 120, 110)

# (caption, command, seconds to hold the result)
STEPS = [
    ("Eşleştirilmiş t testi (önce/sonra tansiyon) için G*Power uyumlu CLI", "gpower-clone --version", 3),
    ("A priori: dz = 0.5, iki kuyruk, α = .05, güç = .95 → kaç hasta?",
     "gpower-clone --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95", 6),
    ("Post hoc: 45 çiftle tek kuyruklu testin gücü (CONTRACT.md §9 açık vektörü)",
     "gpower-clone --test t-paired --mode post-hoc --tails 1 --dz 0.5 --alpha 0.05 --n_total 45", 5),
    ("G*Power gibi: güç < α reddedilir (LEDGER B2)",
     "gpower-clone --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.04", 5),
    ("G*Power gibi: N girdi olduğunda N < 3 reddedilir, a priori ise 2 döndürebilir (B1)",
     "gpower-clone --test t-paired --mode post-hoc --tails 2 --dz 0.5 --alpha 0.05 --n_total 2", 5),
    ("SPEC.md'deki Gherkin örnekleri CLI'den çalıştırılır",
     "python -m pytest -q tests/test_spec.py", 5),
    ("Diferansiyel test: 109 G*Power + 780 statsmodels vektörü",
     "python -m noncentra.difftest_paired | python -c \"import json,sys; s=json.load(sys.stdin); "
     "g=s['gpower']; m=s['statsmodels']['statsmodels']; "
     "print('G*Power:', sum(v['match']+v['explained'] for v in g.values()), '/', sum(v['total'] for v in g.values()), "
     "'| statsmodels:', m['match']+m['explained'], '/', m['total'], '| açıklanmamış fark:', len(s['mismatch']))\"", 6),
    ("MCP aracı CLI ile aynı çıktıyı verir",
     "python -m pytest -q tests/test_mcp_contract.py", 5),
]


def run(cmd):
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=300)
    text = (r.stdout + r.stderr).strip()
    lines = [l for l in text.splitlines() if l.strip()]
    if "pytest" in cmd:
        lines = lines[-1:]  # the summary line
    return lines, r.returncode


def wrap(line):
    return textwrap.wrap(line, COLS, break_long_words=True, break_on_hyphens=False) or [""]


class Screen:
    def __init__(self):
        self.font = ImageFont.truetype(FONT, SIZE)
        self.lines = []  # (text, color)
        self.lh = SIZE + 6

    def add(self, text, color=FG):
        for part in wrap(text):
            self.lines.append((part, color))
        self.lines = self.lines[-((H - 90) // self.lh):]

    def frame(self, caption, cursor=False):
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 44], fill=(36, 39, 48))
        d.text((20, 12), caption, font=self.font, fill=NOTE)
        y = 60
        for i, (t, c) in enumerate(self.lines):
            show = t + ("█" if cursor and i == len(self.lines) - 1 else "")
            d.text((20, y), show, font=self.font, fill=c)
            y += self.lh
        d.text((W - 380, H - 28), "Noncentra · YZM301 Teardown Sprint", font=self.font, fill=(90, 96, 110))
        return im


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg gerekli")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                           "-crf", "28", str(OUT)], stdin=subprocess.PIPE)
    scr = Screen()
    total = 0

    def emit(caption, n, cursor=False):
        nonlocal total
        raw = scr.frame(caption, cursor).tobytes()
        for _ in range(n):
            ff.stdin.write(raw)
        total += n

    for caption, cmd, hold in STEPS:
        output, code = run(cmd)
        shown_cmd = cmd.split(" | ")[0] if "difftest_paired" in cmd else cmd
        scr.add("")
        scr.add("$ ", PROMPT)
        typed = ""
        step = max(1, len(shown_cmd) // 20)  # type each command in ~1.3 s
        for i in range(0, len(shown_cmd), step):
            typed = shown_cmd[: i + step]
            scr.lines.pop()
            for _ in wrap("$ " + typed)[1:]:
                pass
            scr.lines = scr.lines[: len(scr.lines)]
            scr.add("$ " + typed, PROMPT)
            emit(caption, 1, cursor=True)
            scr.lines = scr.lines[: -len(wrap("$ " + typed))]
            scr.add("$ ", PROMPT) if i + step < len(shown_cmd) else None
        scr.add("$ " + shown_cmd, PROMPT)
        emit(caption, FPS // 2)
        color = OK if code == 0 else ERR
        for line in output:
            scr.add(line, color)
        scr.add(f"(çıkış kodu {code})", NOTE)
        emit(caption, hold * FPS)
    ff.stdin.close()
    ff.wait()
    print(f"{OUT} ({total / FPS:.0f} s)")


if __name__ == "__main__":
    main()
