"""Walk through the Noncentra web interface in headless Chrome, one element at a time.

Each step keeps a screenshot (1920x1080: a 1600x900 viewport at 1.2x) and the screen
rectangles of the elements the narration talks about, so make_interface_tour.py can
highlight them. Needs the API server on http://localhost:8000.

usage: python docs/demo/capture_walkthrough.py <out_dir>
Writes <out_dir>/<step>.png and <out_dir>/steps.json.
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from capture_web import BASE, CHROME, Page, done_expr  # noqa: E402

PORT = 9335
VW, VH, DPR = 1600, 900, 1.2

RECTS_JS = """(sels) => sels.map((s) => {
  const [sel, up] = s.split(' ^ ');
  let el = document.querySelector(sel);
  if (el && up) el = el.closest(up);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {x: r.x, y: r.y, w: r.width, h: r.height};
})"""


class Walk:
    def __init__(self, page, out):
        self.page, self.out, self.steps = page, out, []

    def rects(self, sels):
        return self.page.js(f"({RECTS_JS})({json.dumps(sels)})")

    def options(self, select_id):
        return self.page.js(f"[...document.getElementById('{select_id}').options].map(o => o.text)")

    def shot(self, name, highlight=(), **extra):
        self.page.shot(self.out / f"{name}.png")
        self.steps.append({"name": name, "dpr": DPR, "rects": [r for r in self.rects(list(highlight)) if r],
                           **extra})

    def scroll(self, y_expr):
        self.page.js(f"window.scrollTo(0, {y_expr})")
        time.sleep(0.3)

    def set_select(self, select_id, value):
        self.page.js(f"(() => {{ const s = document.getElementById('{select_id}'); s.value = '{value}';"
                     f" s.dispatchEvent(new Event('change')); }})()")
        time.sleep(0.2)

    def calculate(self):
        self.page.js("state.last = null")
        self.page.click("calc")
        self.page.wait(done_expr())


def load(page, frag):
    page.send("Page.navigate", url=f"{BASE}?walk={time.time()}#{frag}")
    page.wait("typeof state !== 'undefined' && state.engine !== null && !document.getElementById('calc').disabled")
    page.wait(done_expr())


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="walk-chrome-")
    chrome = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                               f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                               f"--window-size={VW},{VH}", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                break
            except OSError:
                time.sleep(0.2)
        page = Page(next(t for t in targets if t["type"] == "page")["webSocketDebuggerUrl"])
        page.send("Emulation.setDeviceMetricsOverride", width=VW, height=VH, deviceScaleFactor=DPR, mobile=False)
        page.send("Page.enable")
        page.send("Runtime.enable")
        w = Walk(page, out)

        # 1. The page and its parts.
        load(page, "test=t.two_sample&analysis=a_priori&tails=2&ratio=1&effect_size=0.5&alpha=0.05&power=0.8")
        w.shot("overview")
        w.shot("parts", ["#form", ".results", ".charts"])
        w.shot("engine", [".engine"], options=w.options("engine"), anchor=".engine")
        w.shot("test", ["#test ^ .field"], options=w.options("test"))
        w.shot("analysis", ["#analysis ^ .field"], options=w.options("analysis"))
        w.shot("settings", ["#settings-fields"])
        w.shot("effect", ["#f-effect_size ^ .field"])

        # 2. Enter the power and calculate.
        page.type_into("f-power", "0.95", out, "typing_power")
        for i in range(4):
            w.steps.append({"name": f"typing_power_{i:02d}", "dpr": DPR,
                            "rects": [r for r in w.rects(["#f-alpha ^ .row2"]) if r]})
        w.shot("calc", ["#calc"])
        w.calculate()
        w.shot("summary", ["#summary"])
        w.shot("headline", ["#headline"])
        w.shot("tables", [".tables"])

        # 3. Charts.
        w.scroll("document.querySelector('.charts').getBoundingClientRect().top + window.scrollY - 16")
        w.shot("dist", ["#dist ^ .card"])
        w.shot("curve", ["#chart ^ .card"])

        # 4. Report, protocol, export.
        w.scroll("0")
        w.shot("actions", [".actions"])
        page.js("document.querySelector('.protocol-box').open = true")
        w.scroll("document.querySelector('.protocol-box').getBoundingClientRect().top + window.scrollY - 120")
        w.shot("protocol", [".protocol-box"])
        html = page.js("reportHtml()")

        # 5. Another analysis type: the form changes with it.
        w.scroll("0")
        w.set_select("analysis", "post_hoc")
        w.shot("posthoc_form", ["#value-fields"])
        w.calculate()
        w.shot("posthoc_result", ["#headline"])

        # 6. Other tests.
        load(page, "test=t.paired&analysis=criterion&tails=2&effect_size=0.5&power=0.95&n=45")
        w.shot("paired", ["#form", "#headline"])
        load(page, "test=f.anova_oneway&analysis=sensitivity&groups=3&alpha=0.05&power=0.8&n=60")
        w.shot("anova", ["#settings-fields", "#headline"])
        load(page, "test=f.regression_r2&analysis=compromise&predictors=5&effect_size=0.15&beta_alpha_ratio=2&n=60")
        w.shot("regression", ["#value-fields", "#headline"])

        # 7. Offline engine.
        load(page, "test=f.regression_r2&analysis=a_priori&predictors=2&effect_size=0.15&alpha=0.05&power=0.95")
        w.set_select("engine", "pyodide")
        page.wait("state.engine === engines.pyodide && !document.getElementById('calc').disabled", timeout=180)
        page.js("applyHash()")
        w.calculate()
        w.shot("offline", [".engine", "#headline"])

        # 8. The downloaded report as a page of its own.
        page.send("Page.navigate", url="about:blank")
        time.sleep(0.3)
        frame = page.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
        page.send("Page.setDocumentContent", frameId=frame, html=html)
        time.sleep(0.8)
        w.shot("report")

        (out / "steps.json").write_text(json.dumps(w.steps, ensure_ascii=False, indent=1), "utf-8")
        print(len(w.steps), "steps")
    finally:
        chrome.kill()


if __name__ == "__main__":
    main(*sys.argv[1:])
