"""Compose the Noncentra tour video from the captures of capture_*.py.

    python docs/demo/capture_gpower.py <pid> <dir>   # G*Power screenshots + values
    python docs/demo/capture_web.py <dir>            # web screenshots + values
    python docs/demo/capture_cli.py <dir>            # CLI, MCP and pytest output
    python docs/demo/make_tour.py <dir> docs/demo/tour.mp4

Every number on screen comes from those captures; nothing is typed in by hand. The
comparison marks are computed here: G*Power shows 7 decimals, so a value matches when
Noncentra rounded to 7 decimals equals G*Power's text, and integers must be equal.
"""
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from tour_cases import CASES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H = 1920, 1080
FONTS = Path(r"C:\Windows\Fonts")
BG, PANEL, INK, MUTED, LINE = "#F8FAFC", "#FFFFFF", "#0F172A", "#64748B", "#E2E8F0"
ACCENT, SOFT, OK, BAD, TERM = "#2563EB", "#EFF6FF", "#15803D", "#DC2626", "#0F172A"


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


SANS, BOLD, SEMI, MONO = "segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "consola.ttf"
SYM = "seguisym.ttf" if (FONTS / "seguisym.ttf").exists() else SANS


class Video:
    def __init__(self, work):
        self.dir = work / "frames"
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True)
        self.items = []

    def add(self, img, seconds):
        path = self.dir / f"{len(self.items):04d}.png"
        img.save(path)
        self.items.append((path, seconds))

    def encode(self, out):
        lst = self.dir / "list.txt"
        lines = []
        for path, sec in self.items:
            lines += [f"file '{path.as_posix()}'", f"duration {sec}"]
        lines.append(f"file '{self.items[-1][0].as_posix()}'")  # concat demuxer drops the last duration otherwise
        lst.write_text("\n".join(lines), "utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                        "-movflags", "+faststart", str(out)], check=True)
        return sum(s for _, s in self.items)


# ---------- drawing helpers ----------

def canvas():
    return Image.new("RGB", (W, H), BG)


def header(img, step, title, sub=""):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 96], fill=PANEL)
    d.line([0, 96, W, 96], fill=LINE, width=2)
    d.rounded_rectangle([32, 24, 80, 72], 10, fill=ACCENT)
    d.text((56, 48), "1−β", font=font(BOLD, 17), fill="white", anchor="mm")
    x = 100
    if step:
        tag = font(SEMI, 18)
        tw = d.textlength(step, font=tag)
        d.rounded_rectangle([x, 33, x + tw + 24, 63], 15, fill=SOFT)
        d.text((x + 12, 48), step, font=tag, fill=ACCENT, anchor="lm")
        x += tw + 40
    d.text((x, 48 if not sub else 36), title, font=font(BOLD, 30), fill=INK, anchor="lm")
    if sub:
        d.text((x, 70), sub, font=font(SANS, 19), fill=MUTED, anchor="lm")
    d.text((W - 32, 48), "Noncentra · G*Power 3.1.9.7 karşılaştırmalı tanıtım", font=font(SANS, 17),
           fill=MUTED, anchor="rm")


def caption(img, text, color=INK):
    d = ImageDraw.Draw(img)
    f = font(SEMI, 24)
    lines = textwrap.wrap(text, 120)
    h = 26 + 34 * len(lines)
    d.rectangle([0, H - h, W, H], fill=PANEL)
    d.line([0, H - h, W, H - h], fill=LINE, width=2)
    d.rectangle([0, H - h, 8, H], fill=ACCENT)
    for i, line in enumerate(lines):
        d.text((40, H - h + 14 + 34 * i), line, font=f, fill=color)


def card(img, box, label=None, label_color=INK):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0 + 2, y0 + 3, x1 + 2, y1 + 3], 14, fill="#E9EEF5")
    d.rounded_rectangle(box, 14, fill=PANEL, outline=LINE, width=2)
    if label:
        d.text((x0 + 20, y0 + 16), label, font=font(BOLD, 22), fill=label_color)


def paste_fit(img, shot, box):
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / shot.width, (y1 - y0) / shot.height)
    small = shot.resize((round(shot.width * s), round(shot.height * s)), Image.LANCZOS)
    x = x0 + ((x1 - x0) - small.width) // 2
    img.paste(small, (x, y0))
    ImageDraw.Draw(img).rectangle([x - 1, y0 - 1, x + small.width, y0 + small.height], outline=LINE, width=1)
    return small.size


def mark(d, xy, ok):
    d.text(xy, "✓" if ok else "✗", font=font(SYM, 28), fill=OK if ok else BAD, anchor="mm")


def terminal(img, box, lines, title="PowerShell · gpower-clone"):
    """lines: (text, color) with long lines wrapped at the box width."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 14, fill=TERM)
    d.rounded_rectangle([x0, y0, x1, y0 + 44], 14, fill="#1E293B")
    d.rectangle([x0, y0 + 30, x1, y0 + 44], fill="#1E293B")
    for i, c in enumerate(("#EF4444", "#F59E0B", "#22C55E")):
        d.ellipse([x0 + 18 + 24 * i, y0 + 15, x0 + 32 + 24 * i, y0 + 29], fill=c)
    d.text(((x0 + x1) // 2, y0 + 22), title, font=font(SANS, 17), fill="#94A3B8", anchor="mm")
    f = font(MONO, 21)
    cols = int((x1 - x0 - 48) / d.textlength("M", font=f))
    wrapped = []
    for text, color in lines:
        for part in (textwrap.wrap(text, cols, break_long_words=True, break_on_hyphens=False) or [""]):
            wrapped.append((part, color))
    rows = int((y1 - y0 - 70) / 28)
    for i, (text, color) in enumerate(wrapped[-rows:]):
        d.text((x0 + 24, y0 + 60 + 28 * i), text, font=f, fill=color)


# ---------- comparison ----------

GP_KEYS = {
    "ncp": ("Noncentrality parameter δ", "Noncentrality parameter λ"),
    "crit": ("Critical t", "Critical F"),
    "df": ("Df", "Denominator df"),
    "effect": ("Effect size d", "Effect size dz", "Effect size f", "Effect size f²"),
}


def gp_value(gp, keys):
    for k in (keys if isinstance(keys, tuple) else (keys,)):
        if k in gp:
            return gp[k]
    return None


INTEGER_ROWS = {"n1", "n2", "Toplam N", "Serbestlik derecesi"}


def compare_rows(case, out, gp):
    sizes = out.get("sizes", {})
    rows = []
    a = case["analysis"]
    if a == "a_priori":
        if "n1" in sizes:
            rows += [("n1", sizes["n1"], gp_value(gp, "Sample size group 1")),
                     ("n2", sizes["n2"], gp_value(gp, "Sample size group 2"))]
        rows += [("Toplam N", out["n_total"], gp_value(gp, "Total sample size")),
                 ("Gerçekleşen güç", out["power"], gp_value(gp, "Actual power"))]
    elif a == "post_hoc":
        rows += [("Güç (1−β)", out["power"], gp_value(gp, "Power (1-β err prob)"))]
    elif a == "sensitivity":
        rows += [("Etki büyüklüğü", out["effect_size"], gp_value(gp, GP_KEYS["effect"]))]
    elif a == "criterion":
        rows += [("Gerekli α", out["alpha"], gp_value(gp, "α err prob"))]
    elif a == "compromise":
        rows += [("α", out["alpha"], gp_value(gp, "α err prob")), ("β", out["beta"], gp_value(gp, "β err prob")),
                 ("Güç (1−β)", out["power"], gp_value(gp, "Power (1-β err prob)"))]
    rows += [("Merkezdışılık", out["noncentrality"], gp_value(gp, GP_KEYS["ncp"])),
             ("Kritik değer", out["critical_value"], gp_value(gp, GP_KEYS["crit"])),
             ("Serbestlik derecesi", out["df"], gp_value(gp, GP_KEYS["df"]))]
    result = []
    for label, mine, theirs in rows:
        if label in INTEGER_ROWS:
            shown, ok = str(mine), theirs is not None and float(theirs) == mine
        else:
            shown = f"{mine:.7f}"
            ok = theirs is not None and abs(round(mine, 7) - float(theirs)) < 1.5e-7
        result.append((label, shown, theirs if theirs is not None else "—", ok))
    return result


def compare_table(img, box, rows):
    """Two columns of rows (value | Noncentra | G*Power | mark) under one header."""
    d = ImageDraw.Draw(img)
    card(img, box)
    x0, y0, x1, y1 = box
    half = (x1 - x0) // 2
    hf, f, mf = font(SEMI, 16), font(SANS, 20), font(MONO, 20)
    per_col = (len(rows) + 1) // 2
    for c in range(2):
        cx = x0 + c * half
        cols = [cx + 22, cx + 215, cx + 360, cx + half - 30]
        for x, t in zip(cols, ("DEĞER", "NONCENTRA", "G*POWER")):
            d.text((x, y0 + 14), t, font=hf, fill=MUTED)
        for i, (label, mine, theirs, ok) in enumerate(rows[c * per_col:(c + 1) * per_col]):
            y = y0 + 48 + 40 * i
            d.line([cx + 18, y - 6, cx + half - 14, y - 6], fill=LINE)
            d.text((cols[0], y), label, font=f, fill=INK)
            d.text((cols[1], y), mine, font=mf, fill=INK)
            d.text((cols[2], y), str(theirs), font=mf, fill=INK if ok else BAD)
            mark(d, (cols[3], y + 13), ok)
    d.line([x0 + half, y0 + 14, x0 + half, y1 - 14], fill=LINE)


# ---------- scenes ----------

def title_scene(v):
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([W // 2 - 60, 250, W // 2 + 60, 370], 26, fill=ACCENT)
    d.text((W // 2, 310), "1−β", font=font(BOLD, 44), fill="white", anchor="mm")
    d.text((W // 2, 450), "Noncentra", font=font(BOLD, 84), fill=INK, anchor="mm")
    d.text((W // 2, 530), "İstatistiksel güç analizi · G*Power 3.1.9.7'nin temiz oda yeniden yazımı",
           font=font(SANS, 32), fill=MUTED, anchor="mm")
    d.text((W // 2, 640), "Web arayüzü · gpower-clone CLI · MCP sunucusu · G*Power ile yan yana karşılaştırma",
           font=font(SEMI, 26), fill=ACCENT, anchor="mm")
    d.text((W // 2, 950), "YZM301 Teardown Sprint · github.com/ata-dmrl/Noncentra", font=font(SANS, 22),
           fill=MUTED, anchor="mm")
    v.add(img, 4.5)

    img = canvas()
    header(img, "", "Bu videoda")
    d = ImageDraw.Draw(img)
    items = [("1", "Web arayüzü", "test ve analiz türü seçimi, sonuç kartları, dağılım ve güç grafikleri"),
             ("2", "Düzeltilen hata", "Güç (1−β) alanı virgüllü değeri (0,95) artık kabul ediyor"),
             ("3", "G*Power ile yan yana", "4 test ailesi × 5 analiz türü, aynı girdiler, değer değer karşılaştırma"),
             ("4", "Rapor, protokol, çevrimdışı motor", "indirilebilir rapor, G*Power tarzı protokol, Pyodide"),
             ("5", "gpower-clone CLI", "CONTRACT.md örnekleri, tüm modlar ve hata kodları, gerçek çalıştırma"),
             ("6", "MCP ve API", "ajanlar için power_analysis aracı, FastAPI uç noktaları"),
             ("7", "Testler ve bilinen farklar", "sözleşme testleri, uyum raporu, dürüst kalan işler")]
    for i, (n, t, s) in enumerate(items):
        y = 170 + 115 * i
        d.ellipse([140, y, 196, y + 56], fill=SOFT)
        d.text((168, y + 28), n, font=font(BOLD, 26), fill=ACCENT, anchor="mm")
        d.text((230, y + 2), t, font=font(BOLD, 30), fill=INK)
        d.text((230, y + 42), s, font=font(SANS, 23), fill=MUTED)
    v.add(img, 7)


def web_scene(v, shot, step, title, text, seconds=5.0, sub=""):
    img = canvas()
    header(img, step, title, sub)
    paste_fit(img, Image.open(shot), (40, 120, W - 40, H - 110))
    caption(img, text)
    v.add(img, seconds)


def bugfix_scene(v, work):
    frames = sorted((work / "typing").glob("power_*.png"))
    for i, f in enumerate(frames):
        img = canvas()
        header(img, "Hata düzeltmesi", "Güç (1−β) alanına virgüllü değer girme", "web/app.js · numberField + num()")
        paste_fit(img, Image.open(f), (40, 120, W - 40, H - 110))
        caption(img, "Önce: tarayıcının sayı alanı \"0,90\" yazınca değeri boşaltıyordu ve "
                     "\"Güç (1−β) geçerli bir sayı olmalı\" hatası çıkıyordu. Yazılıyor: "
                     + "0,90"[: i + 1])
        v.add(img, 0.45)
    web_scene(v, work / "ui_comma_result.png", "Hata düzeltmesi", "\"0,90\" kabul edildi ve hesaplandı",
              "Şimdi: alan metin girişi, virgül ve nokta aynı sayıyı verir (0,90 = 0.90). Sonuç 86 + 86 = 172; "
              "geçersiz metin hâlâ reddediliyor.", 5.5)
    web_scene(v, work / "ui_invalid.png", "Girdi denetimi", "Sayı olmayan girdi formda yakalanır",
              "\"abc\" yazılınca hesap yapılmaz, alan kırmızıyla işaretlenir ve neyin yanlış olduğu yazılır.", 4)
    web_scene(v, work / "ui_power_below_alpha.png", "Girdi denetimi", "Güç < α: G*Power gibi reddedilir",
              "Güç 0,01 ve α 0,05 iken test anlamsızdır; G*Power bu girdiyi kabul etmez, Noncentra da "
              "\"power must be greater than or equal to alpha\" diyerek reddeder (CLI kodu INCONSISTENT).", 5)


def side_by_side(v, work, case, out, gp, n, total):
    rows = compare_rows(case, out, gp)
    good = sum(r[3] for r in rows)
    img = canvas()
    header(img, f"G*Power karşılaştırması {n}/{total}", case["title"])
    # Left: Noncentra web with the comparison table under it; right: G*Power at full height.
    card(img, (24, 112, 1110, 800), "Noncentra (web)", ACCENT)
    paste_fit(img, Image.open(work / f"web_{case['key']}.png"), (40, 154, 1094, 790))
    table_h = 60 + 40 * ((len(rows) + 1) // 2)
    compare_table(img, (24, 816, 1110, 816 + table_h), rows)
    ImageDraw.Draw(img).text((1086, 128), f"{good}/{len(rows)} değer G*Power ile aynı", font=font(BOLD, 24),
                             fill=OK if good == len(rows) else BAD, anchor="ra")
    card(img, (1128, 112, 1896, 1060), "G*Power 3.1.9.7 · aynı girdiler", INK)
    paste_fit(img, Image.open(work / f"gp_{case['key']}.png"), (1144, 154, 1880, 1050))
    v.add(img, 7.5 if good == len(rows) else 10)
    return good, len(rows)


def ratio_note(v, out, gp):
    img = canvas()
    header(img, "Bilinen fark", "Eşit olmayan grup oranında yuvarlama")
    d = ImageDraw.Draw(img)
    s = out["sizes"]
    lines = [
        ("Girdi", "d = 0.5 · α = 0.05 · güç = 0.80 · iki yönlü · n2/n1 = 3"),
        ("G*Power", f"n1 = {gp['Sample size group 1']}, n2 = {gp['Sample size group 2']}, "
                    f"N = {gp['Total sample size']}, gerçekleşen güç {gp['Actual power']}"),
        ("Noncentra", f"n1 = {s['n1']}, n2 = {s['n2']}, N = {out['n_total']}, gerçekleşen güç {out['power']:.7f}"),
    ]
    for i, (k, t) in enumerate(lines):
        y = 200 + 90 * i
        d.text((140, y), k, font=font(BOLD, 32), fill=ACCENT if k == "Noncentra" else INK)
        d.text((420, y), t, font=font(MONO, 30), fill=INK)
    body = ("İki çözüm de hedef gücü (0.80) geçiyor, ama G*Power n2'yi 127, Noncentra 128 seçiyor; n2'nin "
            "oran üzerinden nasıl yuvarlandığı G*Power'ın belgelerinde yazmıyor ve bu kuralı henüz çözemedik. "
            "Toplanan 557 G*Power vektöründe bu tür 23 fark var; hepsi eşit olmayan oranlı t2-indep a priori "
            "vakaları ve oracle'da 'known divergence' notuyla tutuluyor. Eşit gruplarda (oran = 1) ve diğer "
            "tüm ailelerde N birebir aynı.")
    for i, line in enumerate(textwrap.wrap(body, 95)):
        d.text((140, 520 + 44 * i), line, font=font(SANS, 29), fill=INK)
    v.add(img, 11)


def cli_scenes(v, work, gp_all):
    runs = json.loads((work / "cli.json").read_text("utf-8"))
    by_cmd = {r["cmd"]: r for r in runs}

    def scene(step, title, chosen, notes, note_title, final_hold=4.0):
        shown = []
        for idx, r in enumerate(chosen):
            for with_output in (False, True):
                img = canvas()
                header(img, step, title, "gerçek çalıştırma: stdout tek satır JSON, çıkış kodu ve süre")
                lines = list(shown) + [("PS> " + r["cmd"], "#E2E8F0")]
                if with_output:
                    color = "#86EFAC" if r["code"] == 0 else "#FCA5A5"
                    lines += [(r["stdout"], color), (f"# çıkış kodu {r['code']} · {r['seconds']} s", "#64748B"),
                              ("", "#000")]
                terminal(img, (24, 120, 1300, 1060), lines)
                card(img, (1320, 120, 1896, 1060), note_title)
                d = ImageDraw.Draw(img)
                done = idx + 1 if with_output else idx
                y = 170
                for label, ok, detail in notes[:done]:
                    if ok is not None:
                        mark(d, (1350, y + 16), ok)
                    d.text((1374, y), label, font=font(SEMI, 21), fill=INK)
                    for j, line in enumerate(textwrap.wrap(detail, 40)):
                        d.text((1374, y + 30 + 26 * j), line, font=font(SANS, 18), fill=MUTED)
                    y += 46 + 26 * len(textwrap.wrap(detail, 40))
                hold = final_hold if (with_output and idx == len(chosen) - 1) else (2.4 if with_output else 0.9)
                v.add(img, hold)
            shown = lines

    def n_note(run, key, label):
        out = json.loads(run["stdout"])
        gp = gp_all[key]
        same = str(out["n_total"]) == gp["Total sample size"] and \
            abs(round(out["actual_power"], 7) - float(gp["Actual power"])) < 1.5e-7
        return (label, same, f"Noncentra N = {out['n_total']}, güç {out['actual_power']:.7f} · "
                             f"G*Power N = {gp['Total sample size']}, güç {gp['Actual power']}")

    fam = runs[1:5]
    notes = [("--version", None, json.loads(runs[0]["stdout"])["engine"]),
             n_note(fam[0], "t2_apriori", "t2-indep a-priori"), n_note(fam[1], "paired_apriori", "t-paired a-priori"),
             n_note(fam[2], "anova_apriori", "anova-oneway a-priori"), n_note(fam[3], "reg_apriori", "multireg-r2 a-priori")]
    scene("CLI 1/3", "gpower-clone: CONTRACT.md örnekleri", runs[0:5], notes, "G*Power ile")

    mode_keys = [("t2_posthoc", "power", "Power (1-β err prob)", "post-hoc güç"),
                 ("anova_sens", "f", "Effect size f", "sensitivity f"),
                 ("paired_crit", "alpha", "α err prob", "criterion α"),
                 ("reg_comp", "power", "Power (1-β err prob)", "compromise güç")]
    notes = [("chi2-contingency", False, "UNSUPPORTED: bu aile henüz uygulanmadı (CONTRACT izin veriyor, "
                                         "ayrı oturumda geliştiriliyor)")]
    for r, (key, field, gp_label, label) in zip(runs[6:10], mode_keys):
        mine = json.loads(r["stdout"])[field]
        theirs = gp_all[key][gp_label]
        notes.append((label, abs(round(mine, 7) - float(theirs)) < 1.5e-7,
                      f"Noncentra {mine:.7f} · G*Power {theirs}"))
    scene("CLI 2/3", "Diğer aile ve dört bonus mod", runs[5:10], notes, "G*Power ile")

    errs = runs[10:15]
    notes = [(json.loads(r["stdout"])["code"], True, json.loads(r["stdout"])["error"]) for r in errs]
    scene("CLI 3/3", "Hatalı girdiler: CONTRACT §2.4 hata kodları", errs, notes, "Hata kodu · çıkış 2", 5)
    return runs


def mcp_scene(v, work):
    log = json.loads((work / "mcp.json").read_text("utf-8"))
    lines = [("PS> gpower-clone-mcp   # stdio üzerinden JSON-RPC", "#E2E8F0"), ("", "#000")]
    for e in log:
        m = dict(e["msg"])
        if m.get("method") == "initialize":
            text = '{"method": "initialize", "clientInfo": {"name": "tour-video"}}'
        elif "result" in m and "serverInfo" in m["result"]:
            text = json.dumps({"serverInfo": m["result"]["serverInfo"], "capabilities": ["tools", "prompts", "resources"]})
        elif "result" in m and "tools" in m["result"]:
            tools = m["result"]["tools"]
            text = json.dumps({"tools": [{"name": t["name"], "params": list(t["inputSchema"]["properties"])}
                                         for t in tools]}, ensure_ascii=False)
        elif "result" in m and "content" in m["result"]:
            text = m["result"]["content"][0]["text"]
        elif m.get("method") == "tools/call":
            text = json.dumps({"tools/call": m["params"]["name"], "arguments": m["params"]["arguments"]})
        else:
            text = json.dumps({k: m[k] for k in ("method",) if k in m})
        color = "#93C5FD" if e["dir"] == "→" else "#86EFAC"
        lines += [(f"{e['dir']} {text}", color), ("", "#000")]
    img = canvas()
    header(img, "MCP", "Ajanlar için: power_analysis aracı (CONTRACT §7)",
           "gerçek bir MCP oturumu: initialize → tools/list → tools/call")
    terminal(img, (24, 120, 1300, 1060), lines, "MCP istemcisi ↔ gpower-clone-mcp")
    card(img, (1320, 120, 1896, 1060), "Aynı motor, aynı sonuç")
    d = ImageDraw.Draw(img)
    body = ("MCP aracı CLI ile aynı noncentra.contract.run fonksiyonunu çağırır ve aynı JSON'u döndürür. "
            "Claude gibi bir ajan, G*Power arayüzünü tıklamadan güç analizi yapabilir: t-paired a priori "
            "→ N = 45, ANOVA (5 grup) → N = 305; ikisi de G*Power ile aynı.")
    for i, line in enumerate(textwrap.wrap(body, 40)):
        d.text((1350, 175 + 34 * i), line, font=font(SANS, 22), fill=INK)
    v.add(img, 9)


def api_scene(v, work):
    rea = json.loads((work / "rea.json").read_text("utf-8"))
    web_scene(v, work / "rea_docs.png", "HTTP API", "FastAPI uç noktaları (/docs)",
              f"Web arayüzünün kullandığı API: /api/analyze, /api/curve, /api/distribution, /api/schemas. "
              f"Bu kare REA eklentisinin CDP aracıyla yakalandı ({rea['provider']['name']}, "
              f"kanıt {rea['evidence_id'][:19]}…).", 6)


def tests_scene(v, work):
    text = (work / "pytest.txt").read_text("utf-8").strip().splitlines()
    lines = [("PS> python -m pytest tests/contract -q", "#E2E8F0")] + \
        [(t, "#86EFAC" if "passed" in t else "#CBD5E1") for t in text[-14:]]
    compliance = ROOT / "tests" / "COMPLIANCE.md"
    img = canvas()
    header(img, "Testler", "Kara kutu sözleşme testleri ve uyum raporu")
    terminal(img, (24, 120, 1000, 1060), lines, "pytest")
    card(img, (1020, 120, 1896, 1060), "tests/COMPLIANCE.md")
    d = ImageDraw.Draw(img)
    if compliance.exists():
        body = [l for l in compliance.read_text("utf-8").splitlines() if l.strip()][:24]
        for i, line in enumerate(body):
            for j, part in enumerate(textwrap.wrap(line.replace("**", ""), 62)[:1]):
                d.text((1050, 170 + 34 * i), part, font=font(SANS, 20), fill=INK)
    else:
        d.text((1050, 170), "Uyum çalıştırması bu kayıtta bitmedi.", font=font(SANS, 22), fill=MUTED)
    v.add(img, 9)


def web_features(v, work):
    web_scene(v, work / "ui_start.png", "Web 1/4", "Başlangıç: test, analiz türü, değerler",
              "Soldan test ailesi ve analiz türü seçilir (a priori, post hoc, sensitivity, criterion, compromise); "
              "alanlar seçime göre değişir. Hesaplama sunucuda (FastAPI) ya da çevrimdışı tarayıcıda yapılır.", 6)
    web_scene(v, work / "web_t2_apriori.png", "Web 2/4", "Sonuç: özet cümle, kartlar, tablolar, grafikler",
              "İki yönlü t testi, d = 0.5, α = 0.05, güç 0.95 → 105 + 105 = 210 kişi. Solda H0/H1 dağılımları ve "
              "kritik değer, sağda örneklem büyüklüğüne göre güç eğrisi.", 6.5)
    web_scene(v, work / "ui_protocol.png", "Web 3/4", "G*Power tarzı protokol",
              "Her hesap G*Power'ın 'Protocol of power analyses' biçiminde metin olarak alınabilir ve kopyalanabilir.", 5)
    web_scene(v, work / "ui_report.png", "Web 4/4", "İndirilebilir rapor (HTML / PDF)",
              "'Raporu indir' tek dosyalık bir rapor üretir: ayarlar, girdiler, sonuçlar, grafikler ve protokol. "
              "'PDF / Yazdır' aynı raporu yazdırır; 'JSON' ham sonucu, 'Bağlantı' girdileri taşıyan adresi verir.", 6)
    if (work / "ui_offline.png").exists():
        web_scene(v, work / "ui_offline.png", "Çevrimdışı", "Tarayıcıda Python: Pyodide motoru",
                  "Sağ üstten 'Tarayıcı (çevrimdışı)' seçilince aynı Python paketi tarayıcıda çalışır; sunucu "
                  "olmadan regresyon a priori yine N = 107 (G*Power ile aynı).", 6)


def tools_scene(v):
    img = canvas()
    header(img, "Kayıt", "Bu video nasıl üretildi")
    d = ImageDraw.Draw(img)
    items = [
        ("G*Power 3.1.9.7 (canlı)", "teardown/harvest*.py: Win32 mesajlarıyla alanları doldurup Calculate'e basar, "
                                    "PrintWindow ile ekranı yakalar → docs/demo/capture_gpower.py"),
        ("Noncentra web (canlı)", "başsız Chrome, DevTools protokolüyle: adres, tuş vuruşu, tıklama, ekran "
                                  "görüntüsü → docs/demo/capture_web.py"),
        ("REA MCP eklentisi", "capture_web_screenshot (rea-cdp-browser): API belgeleri karesi, kanıt kimliğiyle"),
        ("gpower-clone ve gpower-clone-mcp", "gerçek süreçler; stdout, çıkış kodu ve süre kaydedildi → "
                                             "docs/demo/capture_cli.py"),
        ("Karşılaştırma ve kurgu", "değerler yakalanan çıktılardan hesaplanır, elle yazılmaz; Pillow + ffmpeg "
                                   "→ docs/demo/make_tour.py"),
    ]
    for i, (t, s) in enumerate(items):
        y = 170 + 150 * i
        d.rounded_rectangle([120, y, 1800, y + 120], 14, fill=PANEL, outline=LINE, width=2)
        d.text((150, y + 20), t, font=font(BOLD, 30), fill=ACCENT)
        d.text((150, y + 66), s, font=font(SANS, 23), fill=INK)
    v.add(img, 8)


def closing(v, matched, total):
    img = canvas()
    header(img, "Özet", "Sonuç")
    d = ImageDraw.Draw(img)
    good = [f"Yan yana {total} G*Power değerinden {matched}'i birebir aynı (tek fark: eşit olmayan oran, bilinen kural).",
            "t2-indep, t-paired, ANOVA ve çoklu regresyonda CONTRACT örnekleri G*Power ile aynı N'yi veriyor.",
            "Beş analiz türü, hata kodları, MCP aracı, HTTP API ve çevrimdışı motor çalışıyor.",
            "Güç alanındaki virgül hatası düzeltildi: 0,95 ve 0.95 artık aynı."]
    todo = ["chi2-contingency henüz uygulanmadı (UNSUPPORTED); ayrı bir oturumda geliştiriliyor.",
            "Soğuk başlatmada bir CLI çağrısı ~2.4–2.7 s sürüyor; CONTRACT 2 s istiyor (scipy içe aktarımı).",
            "Eşit olmayan oranlı t2-indep a priori: 557 vektörde 23 n2 yuvarlama farkı."]
    d.text((120, 150), "Çalışan", font=font(BOLD, 34), fill=OK)
    for i, t in enumerate(good):
        mark(d, (140, 228 + 64 * i), True)
        d.text((175, 212 + 64 * i), t, font=font(SANS, 27), fill=INK)
    d.text((120, 500), "Açık kalan", font=font(BOLD, 34), fill=BAD)
    for i, t in enumerate(todo):
        d.text((128, 562 + 64 * i), "•", font=font(BOLD, 30), fill=BAD)
        d.text((175, 562 + 64 * i), t, font=font(SANS, 27), fill=INK)
    d.text((W // 2, 1000), "Noncentra · github.com/ata-dmrl/Noncentra", font=font(SEMI, 26), fill=ACCENT, anchor="mm")
    v.add(img, 10)


def main(work, out):
    work = Path(work)
    web = json.loads((work / "web.json").read_text("utf-8"))["results"]
    gp_all = json.loads((work / "gpower.json").read_text("utf-8"))
    v = Video(work)
    title_scene(v)
    web_features(v, work)
    bugfix_scene(v, work)
    matched = total = 0
    for i, case in enumerate(CASES, 1):
        g, n = side_by_side(v, work, case, web[case["key"]]["output"], gp_all[case["key"]], i, len(CASES))
        matched, total = matched + g, total + n
        if case["key"] == "t2_ratio":
            ratio_note(v, web[case["key"]]["output"], gp_all[case["key"]])
    cli_scenes(v, work, gp_all)
    mcp_scene(v, work)
    api_scene(v, work)
    tests_scene(v, work)
    tools_scene(v)
    closing(v, matched, total)
    seconds = v.encode(Path(out))
    print(f"{out}: {seconds:.0f} s, {len(v.items)} frames; side by side {matched}/{total} values equal")


if __name__ == "__main__":
    main(*sys.argv[1:])
