"""Zip the gpower2 package for the browser and stamp the build: python web/build_bundle.py

Pyodide unpacks web/gpower2.zip into its file system. Server-only modules (CLI,
MCP, HTTP, diff tooling and reference data) are left out to keep the download small.

The build stamp (a hash of the zip, app.js and style.css) is written into index.html
as ?v=<stamp> on every asset URL, so a browser that cached an older app.js cannot mix
it with a newer page.
"""
import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent
PKG = ROOT / "gpower2"
OUT = WEB / "gpower2.zip"
SKIP = {"cli.py", "__main__.py", "mcp_server.py", "http_api.py", "difftest.py"}
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # stable zip bytes -> stable stamp


def build_zip():
    files = [p for p in PKG.rglob("*")
             if p.is_file() and p.suffix in (".py", ".json")
             and p.name not in SKIP and "__pycache__" not in p.parts and "reference" not in p.parts]
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(files):
            info = zipfile.ZipInfo(p.relative_to(ROOT).as_posix(), FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, p.read_bytes())
    return len(files)


def stamp():
    h = hashlib.sha256()
    for name in ("gpower2.zip", "app.js", "style.css"):
        h.update((WEB / name).read_bytes())
    build = h.hexdigest()[:10]
    index = WEB / "index.html"
    html = index.read_text(encoding="utf-8")
    html = re.sub(r'(<meta name="build" content=")[^"]*(")', rf"\g<1>{build}\g<2>", html)
    html = re.sub(r'((?:app\.js|style\.css)\?v=)[^"]*', rf"\g<1>{build}", html)
    index.write_text(html, encoding="utf-8")
    return build


def main():
    n = build_zip()
    build = stamp()
    print(f"{n} files -> {OUT} ({OUT.stat().st_size} bytes), build {build}")


if __name__ == "__main__":
    main()
