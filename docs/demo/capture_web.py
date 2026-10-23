"""Drive the Noncentra web page in headless Chrome (DevTools protocol) and screenshot it.

Needs the API server on http://localhost:8000 (uvicorn noncentra.http_api:app).
usage: python docs/demo/capture_web.py <out_dir>
Writes web_<key>.png per tour case, a few interaction scenes (ui_*.png) and web.json.
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

sys.path.insert(0, str(Path(__file__).parent))
from tour_cases import CASES, web_hash  # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://localhost:8000/web/"
PORT = 9333
W, H = 1440, 1000


class Page:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.seq = 0

    def send(self, method, **params):
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.seq:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr):
        r = self.send("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")

    def wait(self, expr, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            if self.js(expr):
                return
            time.sleep(0.15)
        raise TimeoutError(expr)

    def shot(self, path):
        time.sleep(0.35)  # let charts finish drawing
        data = self.send("Page.captureScreenshot", format="png")["data"]
        Path(path).write_bytes(base64.b64decode(data))

    def type_into(self, field_id, text, frames_dir=None, stem=None):
        """Type character by character, as a person would, optionally keeping a frame per key."""
        self.js(f"(() => {{ const e = document.getElementById('{field_id}'); e.focus(); e.select(); }})()")
        self.send("Input.dispatchKeyEvent", type="keyDown", key="Backspace", code="Backspace",
                  windowsVirtualKeyCode=8)
        self.send("Input.dispatchKeyEvent", type="keyUp", key="Backspace", code="Backspace",
                  windowsVirtualKeyCode=8)
        for i, ch in enumerate(text):
            self.send("Input.insertText", text=ch)
            if frames_dir:
                self.shot(Path(frames_dir) / f"{stem}_{i:02d}.png")

    def click(self, element_id):
        self.js(f"document.getElementById('{element_id}').click()")


def done_expr():
    return "state.last !== null && !document.getElementById('summary').classList.contains('muted')"


def load(page, frag):
    page.js("state.last = null")
    page.send("Page.navigate", url=f"{BASE}?tour=1#{frag}")
    page.wait("typeof state !== 'undefined' && state.engine !== null && !document.getElementById('calc').disabled")
    page.wait(done_expr())


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="tour-chrome-")
    chrome = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                               f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                               f"--window-size={W},{H}", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                break
            except OSError:
                time.sleep(0.2)
        page = Page(next(t for t in targets if t["type"] == "page")["webSocketDebuggerUrl"])
        page.send("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
        page.send("Page.enable")
        page.send("Runtime.enable")

        # Empty start page.
        page.send("Page.navigate", url=BASE)
        page.wait("typeof state !== 'undefined' && state.engine !== null && state.tests.length > 0")
        page.shot(out / "ui_start.png")
        tests = page.js("state.tests.map(t => t.name + ' | ' + (t.title || t.label || ''))")

        results = {}
        for case in CASES:
            load(page, web_hash(case))
            page.shot(out / f"web_{case['key']}.png")
            results[case["key"]] = page.js("state.last")
            print(case["key"], json.dumps(results[case["key"]].get("output", {}))[:120])

        # The power field with a Turkish decimal comma: the bug the user reported, now fixed.
        load(page, web_hash(CASES[0]))
        frames = out / "typing"
        frames.mkdir(exist_ok=True)
        page.js("document.getElementById('f-power').scrollIntoView({block: 'center'})")
        page.type_into("f-power", "0,90", frames, "power")
        page.js("state.last = null")
        page.click("calc")
        page.wait(done_expr())
        page.shot(out / "ui_comma_result.png")
        results["comma"] = page.js("state.last")

        # Invalid input is caught in the form.
        page.type_into("f-power", "abc")
        page.click("calc")
        page.wait("!document.getElementById('error').hidden")
        page.shot(out / "ui_invalid.png")

        # Power below alpha: G*Power refuses it, so does Noncentra.
        page.type_into("f-power", "0,01")
        page.click("calc")
        page.wait("!document.getElementById('error').hidden && document.getElementById('error').textContent.length > 0")
        page.shot(out / "ui_power_below_alpha.png")
        results["below_alpha_error"] = page.js("document.getElementById('error').textContent")

        # Protocol in G*Power's format.
        load(page, web_hash(CASES[2]))
        page.js("document.querySelector('.protocol-box').open = true;"
                "document.querySelector('.protocol-box').scrollIntoView({block: 'start'})")
        page.shot(out / "ui_protocol.png")

        # The downloadable report, rendered as the file the button saves.
        html = page.js("reportHtml()")
        page.send("Page.navigate", url="about:blank")
        time.sleep(0.3)
        frame = page.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
        page.send("Page.setDocumentContent", frameId=frame, html=html)
        time.sleep(0.8)
        page.shot(out / "ui_report.png")

        # Offline engine: the same Python package running in the browser via Pyodide.
        page.send("Page.navigate", url=f"{BASE}?tour=2#{web_hash(CASES[3])}")
        page.wait("typeof state !== 'undefined' && state.engine !== null && !document.getElementById('calc').disabled")
        page.wait(done_expr())
        page.js("const s = document.getElementById('engine'); s.value = 'pyodide'; s.dispatchEvent(new Event('change'))")
        try:
            page.wait("state.engine === engines.pyodide && !document.getElementById('calc').disabled",
                      timeout=180)
            page.js("state.last = null; applyHash()")
            page.click("calc")
            page.wait(done_expr(), timeout=60)
            page.shot(out / "ui_offline.png")
            results["offline"] = page.js("state.last")
        except TimeoutError as exc:
            print("offline engine did not load:", exc, file=sys.stderr)
            page.shot(out / "ui_offline_failed.png")

        (out / "web.json").write_text(json.dumps({"tests": tests, "results": results}, ensure_ascii=False,
                                                 indent=1), "utf-8")
    finally:
        chrome.kill()


if __name__ == "__main__":
    main(*sys.argv[1:])
