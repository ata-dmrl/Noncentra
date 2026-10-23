"""Narrated tour of the Noncentra interfaces: web, gpower-clone CLI, MCP and HTTP API.

    python docs/demo/capture_walkthrough.py <walk_dir>   # web steps + element rectangles
    python docs/demo/make_interface_tour.py <walk_dir> <capture_dir> docs/demo/interface_tour.mp4 [--voice]

<capture_dir> holds the G*Power, CLI and MCP captures of capture_gpower.py and
capture_cli.py. The narration is spoken by the Windows Turkish voice (tts.ps1); each
scene lasts as long as its sentence (the video is silent
unless --voice is given), and the element being described is highlighted.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import make_tour  # noqa: E402
from make_tour import (ACCENT, BOLD, INK, MUTED, PANEL, SANS, SEMI, SOFT, H, W,  # noqa: E402
                       canvas, card, font, paste_fit, terminal)

HERE = Path(__file__).parent
PAD = 0.7  # silence after each sentence, seconds


def header(img, step, title, sub=""):
    make_tour.header(img, step, title, sub, right="Noncentra · arayüz tanıtımı")


def spoken(text):
    """What the voice should say for text written for the eye."""
    for a, b in (("G*Power", "Ci Pavır"), ("gpower-clone", "ci pavır klon"), ("JSON", "ceysın"),
                 ("MCP", "em si pi"), ("API", "a pi ay"), ("PDF", "pe de ef"), ("HTTP", "ha te te pe"),
                 ("1−β", "bir eksi beta"), ("α", "alfa"), ("β", "beta")):
        text = text.replace(a, b)
    return text


# ---------- overlays ----------

def highlight(img, rects, dpr, pad=10):
    """Dim everything except the rectangles and outline them."""
    if not rects:
        return img
    shade = Image.new("L", img.size, 120)
    d = ImageDraw.Draw(shade)
    boxes = []
    for r in rects:
        box = [r["x"] * dpr - pad, r["y"] * dpr - pad, (r["x"] + r["w"]) * dpr + pad, (r["y"] + r["h"]) * dpr + pad]
        boxes.append(box)
        d.rounded_rectangle(box, 16, fill=0)
    dark = Image.new("RGB", img.size, "#0F172A")
    out = Image.composite(dark, img, shade.point(lambda v: v))
    d2 = ImageDraw.Draw(out)
    for box in boxes:
        d2.rounded_rectangle(box, 16, outline=ACCENT, width=5)
    return out


def dropdown(img, rect, dpr, options, current=0):
    """Draw the options of a select under it, as the open menu would look."""
    d = ImageDraw.Draw(img)
    f = font(SANS, 24)
    x = rect["x"] * dpr
    y = (rect["y"] + rect["h"]) * dpr + 14
    width = max(max(d.textlength(o, font=f) for o in options) + 48, rect["w"] * dpr)
    if x + width > W - 20:
        x = W - 20 - width
    height = 18 + 46 * len(options)
    d.rounded_rectangle([x + 4, y + 6, x + width + 4, y + height + 6], 12, fill="#94A3B8")
    d.rounded_rectangle([x, y, x + width, y + height], 12, fill=PANEL, outline=ACCENT, width=3)
    for i, o in enumerate(options):
        top = y + 9 + 46 * i
        if i == current:
            d.rounded_rectangle([x + 8, top, x + width - 8, top + 42], 8, fill=SOFT)
        d.text((x + 24, top + 21), o, font=f, fill=ACCENT if i == current else INK, anchor="lm")
    return img


def subtitle(img, text, chip):
    band = Image.new("RGBA", (W, 150), (15, 23, 42, 215))
    img.paste(band, (0, H - 150), band)
    d = ImageDraw.Draw(img)
    f = font(SEMI, 30)
    words, lines, cur = text.split(), [], ""
    for wd in words:
        if d.textlength(cur + " " + wd, font=f) > W - 160:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    top = H - 75 - 22 * len(lines)
    for i, line in enumerate(lines[:3]):
        d.text((W // 2, top + 44 * i + 22), line, font=f, fill="white", anchor="mm")
    if chip:
        cf = font(SEMI, 20)
        tw = d.textlength(chip, font=cf)
        # Just above the subtitle band, left: clear of the page's own header controls.
        d.rounded_rectangle([24, H - 200, 24 + tw + 36, H - 162], 19, fill=ACCENT)
        d.text((42 + tw / 2, H - 181), chip, font=cf, fill="white", anchor="mm")
    return img


# ---------- scenes ----------

class Scene:
    def __init__(self, sid, text, frames, chip=""):
        """frames: list of (PIL image, share) - share of the scene time, None for an even split."""
        self.id, self.text, self.frames, self.chip = sid, text, frames, chip


def web_scenes(walk):
    steps = {s["name"]: s for s in json.loads((walk / "steps.json").read_text("utf-8"))}

    def shot(name, options_for=None, current=0):
        s = steps[name]
        img = Image.open(walk / f"{name}.png").convert("RGB")
        img = highlight(img, s["rects"], s["dpr"])
        if options_for:
            img = dropdown(img, s["rects"][0], s["dpr"], s["options"], current)
        return img

    chip = "Web arayüzü"
    S = []
    S.append(Scene("overview", "Web arayüzü açıldığında örnek bir hesap hazır gelir. Ekran üç bölümden oluşur.",
                   [(shot("overview"), None)], chip))
    S.append(Scene("parts", "Solda test ayarları ve değerler, sağda sonuçlar, altta ise grafikler yer alır.",
                   [(shot("parts"), None)], chip))
    S.append(Scene("engine", "Sağ üstteki menüden hesabın nerede yapılacağı seçilir: sunucuda ya da internet "
                             "gerekmeden doğrudan tarayıcıda.", [(shot("engine", True), None)], chip))
    S.append(Scene("test", "Test menüsünden istatistiksel test seçilir: iki bağımsız grup t testi, eşleştirilmiş "
                           "t testi, tek yönlü ANOVA ve çoklu regresyon gibi.", [(shot("test", True), None)], chip))
    S.append(Scene("analysis", "Ne hesaplansın menüsü beş analiz türü sunar: gerekli örneklem büyüklüğü, ulaşılan "
                               "güç, saptanabilir etki büyüklüğü, gerekli α ve uzlaşma analizi.",
                   [(shot("analysis", True), None)], chip))
    S.append(Scene("settings", "Teste özgü ayarlar burada görünür. Bağımsız t testinde kuyruk sayısı ve iki grubun "
                               "oranı girilir.", [(shot("settings"), None)], chip))
    S.append(Scene("effect", "Değerler bölümüne etki büyüklüğü yazılır. Küçük, orta ve büyük düğmeleri Cohen'in "
                             "standart değerlerini tek tıkla doldurur.", [(shot("effect"), None)], chip))
    typing = []
    for i in range(4):
        img = Image.open(walk / f"typing_power_{i:02d}.png").convert("RGB")
        typing.append((highlight(img, steps[f"typing_power_{i:02d}"]["rects"], 1.2), 0.12 if i < 3 else 0.64))
    S.append(Scene("typing", "Ardından α hata olasılığı ve istenen güç girilir. Gücü 0.95 yapalım.", typing, chip))
    S.append(Scene("calc", "Hesapla düğmesine basınca sonuç hemen güncellenir.", [(shot("calc"), None)], chip))
    S.append(Scene("summary", "Sonuç önce sade bir cümleyle özetlenir: bu etkiyi yüzde doksan beş güçle bulmak "
                              "için toplam 210 katılımcı gerekir.", [(shot("summary"), None)], chip))
    S.append(Scene("headline", "En önemli değerler büyük kartlarda gösterilir: toplam örneklem ve gerçekleşen güç.",
                   [(shot("headline"), None)], chip))
    S.append(Scene("tables", "Tablolarda girdiler ve tüm çıktılar yer alır: merkezdışılık parametresi, kritik t "
                             "değeri, serbestlik derecesi ve grup büyüklükleri.", [(shot("tables"), None)], chip))
    S.append(Scene("dist", "Bu grafik, sıfır hipotezindeki merkezi dağılımı kırmızıyla, alternatif hipotezdeki "
                           "merkezi olmayan dağılımı mavi kesikli çizgiyle gösterir. Yeşil çizgi kritik değerdir, "
                           "boyalı alanlar α ve β hatalarıdır.", [(shot("dist"), None)], chip))
    S.append(Scene("curve", "Güç eğrisi, örneklem büyüdükçe gücün nasıl arttığını küçük, orta ve büyük etki için "
                            "gösterir. Turuncu nokta bizim hesabımızdır.", [(shot("curve"), None)], chip))
    S.append(Scene("actions", "Bu düğmelerle sonuç rapor olarak indirilir, PDF olarak yazdırılır, ham veri JSON "
                              "olarak alınır ya da girdileri taşıyan bir bağlantı paylaşılır.",
                   [(shot("actions"), None)], chip))
    S.append(Scene("protocol", "G*Power tarzı protokol, hesabın tüm girdi ve çıktılarını tanıdık bir metin "
                               "biçiminde verir ve tek tıkla kopyalanır.", [(shot("protocol"), None)], chip))
    S.append(Scene("report", "İndirilen rapor tek bir dosyadır: ayarlar, sonuçlar, grafikler ve protokol bir arada.",
                   [(shot("report"), None)], chip))
    S.append(Scene("posthoc_form", "Analiz türü değişince form da değişir. Ulaşılan güç hesabında güç yerine grup "
                                   "büyüklükleri sorulur.", [(shot("posthoc_form"), None)], chip))
    S.append(Scene("posthoc_result", "Otuzar kişilik iki grupla bu etkiyi saptama gücü yaklaşık yüzde kırk sekizdir.",
                   [(shot("posthoc_result"), None)], chip))
    S.append(Scene("paired", "Eşleştirilmiş t testinde aynı kişilerin önce ve sonra ölçümleri karşılaştırılır. "
                             "Burada 45 çift için gereken α hesaplanıyor.", [(shot("paired"), None)], chip))
    S.append(Scene("anova", "Tek yönlü ANOVA'da grup sayısı girilir. Duyarlılık analizi, 60 kişiyle "
                            "saptanabilecek en küçük etki büyüklüğünü verir.", [(shot("anova"), None)], chip))
    S.append(Scene("regression", "Çoklu regresyonda yordayıcı sayısı girilir. Uzlaşma analizi, β bölü α oranına "
                                 "göre α ve gücü birlikte belirler.", [(shot("regression"), None)], chip))
    S.append(Scene("offline", "Çevrimdışı mod seçildiğinde aynı Python hesap motoru tarayıcının içinde çalışır; "
                              "sunucu olmadan da aynı sonuç alınır.", [(shot("offline"), None)], chip))
    return S


def section(title, sub):
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([W // 2 - 50, 330, W // 2 + 50, 430], 22, fill=ACCENT)
    d.text((W // 2, 380), "1−β", font=font(BOLD, 36), fill="white", anchor="mm")
    d.text((W // 2, 520), title, font=font(BOLD, 64), fill=INK, anchor="mm")
    d.text((W // 2, 600), sub, font=font(SANS, 30), fill=MUTED, anchor="mm")
    return img


def gpower_scene(cap, key, title):
    img = canvas()
    header(img, "G*Power ile", title)
    card(img, (24, 112, 1180, 920), "Noncentra", ACCENT)
    paste_fit(img, Image.open(cap / f"web_{key}.png"), (40, 154, 1164, 910))
    card(img, (1200, 112, 1896, 920), "G*Power 3.1.9.7", INK)
    paste_fit(img, Image.open(cap / f"gp_{key}.png"), (1216, 154, 1880, 910))
    return img


def cli_scenes(cap):
    runs = json.loads((cap / "cli.json").read_text("utf-8"))
    picks = [(0, "Sürüm komutu, sözleşme sürümünü ve hesap motorunu gösterir."),
             (1, "Test, analiz modu ve değerler parametre olarak verilir; sonuç tek satır JSON olarak yazılır. "
                 "Burada da 210 katılımcı."),
             (3, "Tek yönlü ANOVA için grup sayısı eklenir: beş grupta 305 katılımcı."),
             (6, "Ulaşılan güç için örneklem büyüklükleri verilir ve güç hesaplanır."),
             (10, "Eksik ya da hatalı bir değer verilirse araç neyin yanlış olduğunu bir hata koduyla söyler.")]
    shown, scenes = [], []
    for idx, text in picks:
        r = runs[idx]
        frames = []
        cmd = "PS> " + r["cmd"]
        for part, share in ((cmd[: len(cmd) // 2], 0.08), (cmd, 0.12)):
            img = canvas()
            header(img, "Komut satırı", "gpower-clone", "her çağrı tek satır JSON yazar; hata olursa açıklama ve kod")
            terminal(img, (24, 120, W - 24, 920), shown + [(part, "#E2E8F0")])
            frames.append((img, share))
        lines = shown + [(cmd, "#E2E8F0"), (r["stdout"], "#86EFAC" if r["code"] == 0 else "#FCA5A5"), ("", "#000")]
        img = canvas()
        header(img, "Komut satırı", "gpower-clone", "her çağrı tek satır JSON yazar; hata olursa açıklama ve kod")
        terminal(img, (24, 120, W - 24, 920), lines)
        frames.append((img, 0.8))
        shown = lines
        scenes.append(Scene(f"cli{idx}", text, frames))
    return scenes


def mcp_scene(cap):
    log = json.loads((cap / "mcp.json").read_text("utf-8"))
    lines = [("PS> gpower-clone-mcp   # stdio üzerinden JSON-RPC", "#E2E8F0"), ("", "#000")]
    for e in log:
        m = e["msg"]
        if m.get("method") == "tools/list":
            text = '{"method": "tools/list"}'
        elif "result" in m and "tools" in m["result"]:
            text = json.dumps({"tools": [t["name"] for t in m["result"]["tools"]]})
        elif m.get("method") == "tools/call":
            text = json.dumps({"tools/call": m["params"]["name"], "arguments": m["params"]["arguments"]})
        elif "result" in m and "content" in m["result"]:
            text = m["result"]["content"][0]["text"]
        else:
            continue
        lines += [(f"{e['dir']} {text}", "#93C5FD" if e["dir"] == "→" else "#86EFAC"), ("", "#000")]
    img = canvas()
    header(img, "MCP", "Yapay zekâ ajanları için power_analysis aracı", "ajan aracı listeler, değerleri gönderir, sonucu alır")
    terminal(img, (24, 120, W - 24, 920), lines, "MCP istemcisi ↔ gpower-clone-mcp")
    return Scene("mcp", "MCP sunucusu, Claude gibi yapay zekâ ajanlarının güç analizini bir araç olarak "
                        "çağırmasını sağlar. Ajan aracı listeler, değerleri gönderir ve aynı sonucu alır.",
                 [(img, None)])


def api_scene(cap):
    img = canvas()
    header(img, "HTTP API", "Belgelenmiş uç noktalar (/docs)")
    paste_fit(img, Image.open(cap / "rea_docs.png"), (40, 120, W - 40, 920))
    return Scene("api", "Web arayüzünün kullandığı HTTP API de belgelenmiştir: analiz, güç eğrisi ve dağılım uç "
                        "noktaları başka uygulamalardan da çağrılabilir.", [(img, None)])


def title_card():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([W // 2 - 60, 250, W // 2 + 60, 370], 26, fill=ACCENT)
    d.text((W // 2, 310), "1−β", font=font(BOLD, 44), fill="white", anchor="mm")
    d.text((W // 2, 450), "Noncentra", font=font(BOLD, 84), fill=INK, anchor="mm")
    d.text((W // 2, 530), "İstatistiksel güç analizi", font=font(SANS, 34), fill=MUTED, anchor="mm")
    d.text((W // 2, 620), "Web arayüzü · Komut satırı · MCP · HTTP API", font=font(SEMI, 28), fill=ACCENT, anchor="mm")
    return img


def outro_card():
    img = title_card()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 680, W, 760], fill="#F8FAFC")
    d.text((W // 2, 720), "github.com/ata-dmrl/Noncentra", font=font(SEMI, 30), fill=INK, anchor="mm")
    return img


def scenes(walk, cap):
    S = [Scene("intro", "Noncentra, istatistiksel güç analizi için geliştirdiğimiz bir uygulamadır. Bu videoda "
                        "web arayüzünü, komut satırı aracını ve yapay zekâ ajanları için MCP sunucusunu tanıtıyoruz.",
               [(title_card(), None)])]
    S.append(Scene("sec_web", "Önce web arayüzü.", [(section("Web arayüzü", "test seç, değerleri gir, sonucu gör"), None)]))
    S += web_scenes(walk)
    S.append(Scene("sec_gp", "Sonuçlar, karşılaştırdığımız G*Power ile aynıdır.",
                   [(section("G*Power ile aynı sonuç", "aynı girdiler, yan yana"), None)]))
    S.append(Scene("gp1", "Solda Noncentra, sağda aynı girdilerle G*Power. İki program da 210 katılımcı ve aynı "
                          "gerçekleşen gücü buluyor.",
                   [(gpower_scene(cap, "t2_apriori", "t testi, iki bağımsız grup · a priori"), None)]))
    S.append(Scene("gp2", "Beş gruplu ANOVA'da da iki program 305 katılımcıda buluşuyor.",
                   [(gpower_scene(cap, "anova_apriori", "Tek yönlü ANOVA, 5 grup · a priori"), None)]))
    S.append(Scene("sec_cli", "Aynı hesaplar komut satırı aracı gpower-clone ile terminalden de yapılır.",
                   [(section("Komut satırı", "gpower-clone"), None)]))
    S += cli_scenes(cap)
    S.append(Scene("sec_agents", "Son olarak ajanlar ve diğer uygulamalar için arayüzler.",
                   [(section("MCP ve HTTP API", "ajanlar ve başka uygulamalar için"), None)]))
    S.append(mcp_scene(cap))
    S.append(api_scene(cap))
    S.append(Scene("outro", "Noncentra: web arayüzü, komut satırı ve MCP ile tek bir hesap motoru. "
                            "İzlediğiniz için teşekkürler.", [(outro_card(), None)]))
    return S


# ---------- audio and encoding ----------

def narrate(S, audio_dir):
    audio_dir.mkdir(parents=True, exist_ok=True)
    lines = audio_dir / "lines.json"
    lines.write_text(json.dumps([{"id": s.id, "say": spoken(s.text)} for s in S], ensure_ascii=False), "utf-8")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "tts.ps1"),
                    str(lines), str(audio_dir)], check=True)
    lengths = {}
    for s in S:
        with wave.open(str(audio_dir / f"{s.id}.wav")) as wf:
            lengths[s.id] = wf.getnframes() / wf.getframerate()
    return lengths


def main(walk, cap, out, *flags):
    # Silent by default: the narration still sets how long each scene stays on screen,
    # and the subtitles carry the text. --voice adds the spoken track.
    voice = "--voice" in flags
    walk, cap, out = Path(walk), Path(cap), Path(out)
    work = walk / "render"
    frames_dir = work / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.png"):
        f.unlink()
    S = scenes(walk, cap)
    lengths = narrate(S, work / "audio")

    items, track, rate = [], [], None
    for s in S:
        total = lengths[s.id] + PAD
        fixed = sum(sh for _, sh in s.frames if sh is not None)
        even = (1 - fixed) / max(1, sum(1 for _, sh in s.frames if sh is None))
        for img, share in s.frames:
            path = frames_dir / f"{len(items):04d}.png"
            subtitle(img.copy(), s.text, s.chip).save(path)
            items.append((path, round(total * (share if share is not None else even), 3)))
        with wave.open(str(work / "audio" / f"{s.id}.wav")) as wf:
            rate, width, ch = wf.getframerate(), wf.getsampwidth(), wf.getnchannels()
            n = wf.getnframes()
            data = wf.readframes(n)
        scene_seconds = sum(sec for _, sec in items[-len(s.frames):])
        track.append(data + b"\0" * (max(0, round(scene_seconds * rate) - n) * width * ch))

    with wave.open(str(work / "narration.wav"), "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(b"".join(track))
    lst = frames_dir / "list.txt"
    body = [x for p, sec in items for x in (f"file '{p.as_posix()}'", f"duration {sec}")]
    lst.write_text("\n".join(body + [f"file '{items[-1][0].as_posix()}'"]), "utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    *(["-i", str(work / "narration.wav")] if voice else []),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    *(["-c:a", "aac", "-b:a", "128k", "-shortest"] if voice else ["-an"]),
                    "-movflags", "+faststart", str(out)], check=True)
    print(f"{out}: {sum(d for _, d in items):.0f} s, {len(S)} scenes, {len(items)} frames")


if __name__ == "__main__":
    main(*sys.argv[1:])
