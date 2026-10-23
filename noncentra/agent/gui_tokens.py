"""Token cost of the GUI path, from the real G*Power screenshots in oracle/t-paired/screenshots.

This is a *computed* figure, not a measured agent run: Claude bills an image at about
width × height / 750 tokens (after downscaling to fit 1568 px on the long side). A measured
run needs Windows + G*Power + a computer-use agent; eval/GUI_COMPARISON.md has the protocol
and the table to fill in.

    python -m noncentra.agent.gui_tokens   # rewrites eval/GUI_COMPARISON.md
"""
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "oracle" / "t-paired" / "screenshots"
RESULTS = ROOT / "eval" / "results.jsonl"
OUT = ROOT / "eval" / "GUI_COMPARISON.md"
MAX_EDGE = 1568


def image_tokens(width: int, height: int) -> int:
    scale = min(1.0, MAX_EDGE / max(width, height))
    w, h = width * scale, height * scale
    return math.ceil(w * h / 750)


def screenshot_costs():
    from PIL import Image

    rows = []
    for path in sorted(SHOTS.glob("*.png")):
        with Image.open(path) as im:
            w, h = im.size
        rows.append({"file": path.name, "w": w, "h": h, "tokens": image_tokens(w, h),
                     "kind": "dialog" if "dialog" in path.name else "main"})
    return rows


def mcp_costs():
    """Measured MCP-path tokens per question, if an evaluation run has been made."""
    if not RESULTS.exists():
        return None
    rows = [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("lang") == "tr"]
    return rows or None


def render() -> str:
    shots = screenshot_costs()
    main = [r for r in shots if r["kind"] == "main"]
    dialog = [r for r in shots if r["kind"] == "dialog"]
    t_main = statistics.median(r["tokens"] for r in main)
    t_dialog = statistics.median(r["tokens"] for r in dialog) if dialog else 0
    size_main = max(((r["w"], r["h"]) for r in main), key=lambda s: s[0] * s[1])

    mcp = mcp_costs()
    if mcp:
        n = len(mcp)
        mcp_line = (f"| MCP (ölçüldü, `eval/results.jsonl`) | {sum(r['tokens_in'] for r in mcp) / n:.0f} | "
                    f"{sum(r['tokens_out'] for r in mcp) / n:.0f} | {sum(r['seconds'] for r in mcp) / n:.1f} | "
                    f"{sum(bool(r['ok']) for r in mcp)}/{n} |")
    else:
        mcp_line = "| MCP | ⚠ `noncentra-agent-eval` çalıştırılınca dolar | | | |"

    return "\n".join([
        "# MCP ve GUI yolu: token, süre, doğruluk",
        "",
        "## 1. Ekran görüntüsü başına token (hesaplandı)",
        "",
        f"`oracle/t-paired/screenshots/` içindeki {len(shots)} gerçek G*Power ekran görüntüsünden, Claude'un görüntü",
        "fiyatlandırmasıyla (uzun kenar 1568 px'e küçültme, sonra genişlik × yükseklik / 750):",
        "",
        "| Görüntü | Adet | Boyut | Token (medyan) |",
        "|---|---:|---|---:|",
        f"| Ana pencere | {len(main)} | {size_main[0]}×{size_main[1]} | {t_main:.0f} |",
        f"| Uyarı kutusu | {len(dialog)} | ~430×216 | {t_dialog:.0f} |",
        "",
        "Bir `gpower-clone` çağrısının girdisi ve çıktısı ise toplam ~200 karakterlik JSON, yani birkaç düzine token.",
        "",
        "Bir GUI ajanının tek bir a priori soruyu çözmek için en az şu ekranları görmesi gerekir: test ailesini seçme,",
        "testi seçme, analiz türünü seçme, girdileri kontrol etme, Calculate sonrası sonucu okuma. Her adımda bir ana pencere",
        f"görüntüsü ({t_main:.0f} token) gelir ve her görüntü sonraki her turda bağlamda kalır. Bu yüzden toplam maliyet",
        "adım sayısıyla doğrusal değil, yaklaşık karesel büyür. Bu bir **tahmin**; ölçülmüş değer aşağıdaki tabloya girmeli.",
        "",
        "## 2. Ölçüm (aynı 10 soru)",
        "",
        "| Yol | Ortalama giriş token / soru | Ortalama çıkış token / soru | Ortalama süre (sn) | Doğru |",
        "|---|---:|---:|---:|---:|",
        mcp_line,
        "| GUI (ekran görüntüsüyle) | ⚠ | ⚠ | ⚠ | ⚠ |",
        "",
        "### GUI ölçüm protokolü (Windows + G*Power 3.1.9.7)",
        "",
        "1. G*Power'ı açık bırakın. Aynı modeli (`claude-sonnet-5-5`) bir bilgisayar kullanımı (computer use) aracıyla çalıştırın;",
        "   sistem mesajı: \"G*Power penceresini kullanarak soruyu çöz; sayıyı yalnızca ekrandan oku.\"",
        "2. `eval/questions.jsonl` içindeki 10 Türkçe soruyu sırayla verin. Her soru yeni bir konuşma.",
        "3. Her soru için API yanıtlarındaki `usage.input_tokens` ve `usage.output_tokens` toplamını, ekran görüntüsü sayısını,",
        "   duvar saati süresini ve okunan N'nin doğru olup olmadığını kaydedin (`eval/gui_runs.jsonl`).",
        "4. Tabloyu doldurun. q08 ve q09'da doğru davranış sayı vermemektir; GUI ajanı G*Power'da χ²'yi hesaplayabileceği",
        "   için q08 GUI yolunda sayıyla cevaplanabilir; bunu not edin.",
        "",
        "Sınıflandırılmış veri yok; sorular kurgusaldır (CONTRACT.md §8).",
        "",
    ])


def main():
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
