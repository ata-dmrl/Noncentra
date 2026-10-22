# AGENT_COST.md — Ajan maliyet ve süreç günlüğü

> **Ekip için not:** ⚠ ile işaretli hücreler repodan ya da git geçmişinden çıkarılamadı. Teslimden önce, oturumu
> yürüten kişi kendi ajanının kullanım ekranından doldurmalı. Tahmin yazmayın; bilinmiyorsa "ölçülmedi" yazın.

## Oturumlar

| # | Tarih | Kim | Ajan / model | İş | Token (yaklaşık) | Maliyet | İterasyon |
|---|---|---|---|---|---|---|---|
| 1 | 2026-10-16 | ⚠ (ata-dmrl) | ⚠ | Aşama 0–1: statik teardown (PE başlığı, importlar, dizeler), test kataloğu → `docs/teardown-report.md` | ⚠ | ⚠ | ⚠ |
| 2 | 2026-10-16 → 21 | ⚠ (ata-dmrl) | ⚠ | Aşama 2: Win32 otomasyonuyla G*Power'dan 183 + 198 vektör toplama (`teardown/harvest.py`); ilk motor + CLI + MCP + web | ⚠ | ⚠ | ⚠ |
| 3 | 2026-10-21 | ⚠ (Erva Keskin) | ⚠ | Eşleştirilmiş test sınır vektörleri (55 vaka, ekran görüntülü), B1–B6 bulguları, scipy 1.18 düzeltmesi → `docs/t-paired-validation.md` | ⚠ | ⚠ | ⚠ |
| 4 | 2026-10-22 | Safiye Özkan | Claude (claude.ai, Opus 5.5) | Sözleşme katmanı (`gpower-clone`, tek araçlı MCP), G*Power sınır kurallarının motora eklenmesi, t-paired diferansiyel test ve rapor, teslim belgeleri, AI ajanı ve değerlendirme düzeneği | ⚠ (kullanım ekranından) | ⚠ | aşağıda |
| 5 | 2026-10-22 | Safiye Özkan (oturum 4'ün başlattığı ayrı alt ajan) | Claude alt ajanı, bağlamsız | **Temiz oda oturumu 2:** yalnızca SPEC.md + CONTRACT.md ile motor + CLI baştan yazıldı (`cleanroom/`) | **~106.800** (ölçüldü) | ⚠ | **2** (ilk tur 59/60; scipy NaN düzeltmesi) |

## Oturum 4 süreç kaydı

| Adım | Ne oldu | Tekrar |
|---|---|---|
| Kapsam | Ödev metni + ders dökümü okundu; repo klonlandı, 881 test çalıştırıldı. Eksikler listelendi. | 1 |
| Sözleşme | Bağlantıdan erişilemedi; web özetleyiciyle okunan özet "n_total çift olmalı" diye bir kural uydurdu (HALLUCINATIONS H4). Öğrenci tam metni ekleyince ondan uygulandı. | 2 |
| `gpower-clone` | Adaptör + CLI + MCP yazıldı. 20 açık vektör ilk denemede geçti. | 1 |
| Sınır kuralları | Motor değişince eski 5 xfail "artık eşleşiyor" diye düştü (katı xfail tasarımı amacına uygun çalıştı); listeden çıkarıldı. Eski CLI'nin d = 0 testi yeni davranışa güncellendi. | 2 |
| Diferansiyel test | 780 statsmodels vektörü üretildi. 30 NaN vakası önce "açıklanmış" sayıldı; sonra üst kuyruk gücüyle gerçekten sınanacak şekilde düzeltildi. Rapor metni 3 kez düzeltildi. | 3 |
| Belgeler | SPEC.md örnek tabloları `tests/test_spec.py` ile çalıştırılabilir yapıldı (52 satır). | 1 |
| Ajan | MCP istemcisi + Claude araç döngüsü, Sistem 1 sınıflandırıcı, 10 soruluk set, puanlama. Sahte modelle testte χ² sorusunda MCP şemasında `w`/`df` alanlarının eksik olduğu görüldü; eklendi. | 2 |

Toplam test: 881 → 1975 civarı (sözleşme, MCP eşdeğerliği, diferansiyel, SPEC testleri).

## Token karşılaştırması: MCP ve GUI

Ayrıntı: [eval/GUI_COMPARISON.md](eval/GUI_COMPARISON.md).

- **Hesaplanan (ölçüm değil):** Repodaki gerçek G*Power ekran görüntüleri ana pencere için 708×802 px, yani görüntü başına
  ~758 token; uyarı kutusu ~125 token. Bir `gpower-clone` çağrısı ve yanıtı ~200 karakterlik JSON, birkaç düzine token.
- **MCP yolu, ölçülecek:** ⚠ `noncentra-agent-eval` API anahtarıyla çalıştırılınca soru başına token ve süre
  `eval/results.jsonl` ve `eval/RESULTS.md`'ye yazılır; `python -m noncentra.agent.gui_tokens` tabloyu günceller.
- **GUI yolu, ölçülecek:** ⚠ Windows + G*Power + bilgisayar kullanımı aracıyla, `eval/GUI_COMPARISON.md`'deki protokolle.

Ajan katmanı, ajanın oturum 4'te yazıldığı ortamda API anahtarı olmadığı için yalnızca senaryolu sahte modelle uçtan uca
test edildi (`tests/test_agent.py`).

## Neyi farklı yapardık

1. **Sözleşmeyi ilk gün kodlardık.** Motor 5 gün boyunca doğruydu ama hocanın düzeneğinin çağıracağı `gpower-clone`
   arayüzü son güne kaldı. Kapı (gizli vektörlerde %90) arayüz olmadan sıfır demek.
2. **Sınır vektörlerini ızgaradan önce toplardık.** Izgara (48/48) hiçbir hata bulmadı; bütün bulgular (B1–B5) sınır
   vektörlerinden çıktı. Dijkstra'nın sözü burada somut: ızgara hataların yokluğunu göstermedi.
3. **İki oturum ayrımını baştan kayda alırdık.** `prompts/` klasörü sonradan oluşturuldu; ilk prompt'lar o an saklanmalıydı.
4. **Ghidra'yı kurardık.** [REA] puanı fonksiyon adresi istiyor; elimizde dize adresleri var ama a priori arama
   döngüsü ve yuvarlama komutu gibi asıl ilginç davranışların adresi yok (LEDGER "Açık işler").
5. **Özetleyici araçlara spec okutmazdık** (H4).
