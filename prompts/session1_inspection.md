# Oturum 1 · İnceleme (REA + Ghidra)

**Ajan:** Claude Code (Claude Opus 5.5), Claude masaüstü uygulaması, Windows 11.
**Başlangıç:** 2026-10-16.

## İlk prompt (birebir)

> REA araçları bu oturumda kullanılabilir mi? Kaç araç aktif?

Hemen ardından gelen mesajlar:

> kurulum büyük çoğunlukla tamamsa gerek yok ek uygulama indirmek

> hedef :g*power nasıl geliştirebiliriz

## Bu oturumun ürettikleri

- **Kanıt defteri:** [LEDGER.md](../LEDGER.md) ve [SPEC.md](../SPEC.md).
- **G*Power vektörleri** (`oracle/`):
  - arayüzden toplanan değerler ve ekran görüntüleri,
  - açık vektörler,
  - statsmodels ölçek vektörleri.
- **Kara kutu sözleşme testleri ve uyum raporu düzeneği:** `tests/contract/`, `tests/run_compliance.py`.
- **Toplama araçları** (`teardown/`): yalnızca G*Power'ın arayüzünü süren ve dosyadan dize/kaynak okuyan betikler.
- **Belgeler:** [HALLUCINATIONS.md](../HALLUCINATIONS.md) ve [AGENT_COST.md](../AGENT_COST.md).

## Temiz oda kuralına uyum (dürüst kayıt)

Ödev, inceleme ile yazımın iki ayrı oturumda yapılmasını istiyor. Bu oturum ödev metni ve CONTRACT.md gelmeden
önce başladı. Bu yüzden **aynı oturumda bir ön prototip de yazdı**:

- `noncentra/` paketi,
- web arayüzü,
- HTTP API,
- MCP sunucusu.

Bu prototip, G*Power'ın hesap kodu okunmadan, yayınlanmış formüller ve gözlenen girdi-çıktı davranışıyla yazıldı.
Ghidra o sırada kurulu değildi ve decompile çıktısı hiç üretilmedi. Yine de iki oturum kuralını karşılamaz.

**Düzeltme:** Teslim edilen motor (`src/`), [session2_writer.md](session2_writer.md) prompt'uyla başlayan **yeni ve
ayrı** bir oturumda yazılır. O oturum yalnızca SPEC.md, CONTRACT.md, `oracle/` vektörleri ve `tests/contract/`
kara kutu testlerini görür. Ghidra çıktısını, LEDGER.md'yi ve prototip kodunu görmez.
