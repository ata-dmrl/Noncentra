# AGENT_COST.md — Ajan maliyet ve süreç günlüğü

> **Ekip için not:** ⚠ ile işaretli hücreler repodan ya da git geçmişinden çıkarılamadı. Teslimden önce, oturumu
> yürüten kişi kendi ajanının kullanım ekranından doldurmalı. Tahmin yazmayın; bilinmiyorsa "ölçülmedi" yazın.

## Oturumlar

| # | Tarih | Kim | Ajan / model | İş | Token (yaklaşık) | Maliyet | İterasyon |
|---|---|---|---|---|---|---|---|
| 1 | 2026-10-16 | ⚠ (ata-dmrl) | ⚠ | Aşama 0–1: statik teardown (PE başlığı, importlar, dizeler), test kataloğu → `docs/teardown-report.md` | ⚠ | ⚠ | ⚠ |
| 2 | 2026-10-16 → 21 | ⚠ (ata-dmrl) | ⚠ | Aşama 2: Win32 otomasyonuyla G*Power'dan 183 + 198 vektör toplama (`teardown/harvest.py`); ilk motor + CLI + MCP + web | ⚠ | ⚠ | ⚠ |
| 3 | 2026-10-21 | ⚠ (Erva Keskin) | ⚠ | Eşleştirilmiş test sınır vektörleri (55 vaka, ekran görüntülü), B1–B6 bulguları, scipy 1.18 düzeltmesi → `docs/t-paired-validation.md` | ⚠ | ⚠ | ⚠ |
| 4 | 2026-10-22 | Safiye Özkan | Claude (claude.ai, Opus 5.5) | Sözleşme katmanı (`gpower-clone`, tek araçlı MCP), G*Power sınır kurallarının motora eklenmesi, t-paired diferansiyel test ve rapor, teslim belgeleri | ⚠ (kullanım ekranından) | ⚠ | aşağıda |

## Oturum 4 süreç kaydı

| Adım | Ne oldu | Tekrar |
|---|---|---|
| Kapsam | Ödev metni + ders dökümü okundu; repo klonlandı, 881 test çalıştırıldı. Eksikler listelendi. | 1 |
| Sözleşme | Bağlantıdan erişilemedi; web özetleyiciyle okunan özet "n_total çift olmalı" diye bir kural uydurdu (HALLUCINATIONS H4). Öğrenci tam metni ekleyince ondan uygulandı. | 2 |
| `gpower-clone` | Adaptör + CLI + MCP yazıldı. 20 açık vektör ilk denemede geçti. | 1 |
| Sınır kuralları | Motor değişince eski 5 xfail "artık eşleşiyor" diye düştü (katı xfail tasarımı amacına uygun çalıştı); listeden çıkarıldı. Eski CLI'nin d = 0 testi yeni davranışa güncellendi. | 2 |
| Diferansiyel test | 780 statsmodels vektörü üretildi. 30 NaN vakası önce "açıklanmış" sayıldı; sonra üst kuyruk gücüyle gerçekten sınanacak şekilde düzeltildi. Rapor metni 3 kez düzeltildi. | 3 |
| Belgeler | SPEC.md örnek tabloları `tests/test_spec.py` ile çalıştırılabilir yapıldı (52 satır). | 1 |

Toplam test: 881 → 1975 civarı (sözleşme, MCP eşdeğerliği, diferansiyel, SPEC testleri).

## Token karşılaştırması (ajan katmanı yapılmadı)

Ödev, MCP üzerinden ve GUI (ekran görüntüsü) üzerinden aynı soruların token/süre/doğruluk karşılaştırmasını yalnızca
+10 ajan katmanı için istiyor. Bu katman yapılmadığı için ölçüm yok. Kaba bir ölçek fikri: bir `gpower-clone`
çağrısı ve yanıtı ~60 + ~40 karakter, yani birkaç düzine token; bir ekran görüntüsü çözünürlüğe göre yüzlerce ile
binlerce token arası. Bu bir **ölçüm değil**, ajan katmanı yapılırsa ölçülmesi gereken şey.

## Neyi farklı yapardık

1. **Sözleşmeyi ilk gün kodlardık.** Motor 5 gün boyunca doğruydu ama hocanın düzeneğinin çağıracağı `gpower-clone`
   arayüzü son güne kaldı. Kapı (gizli vektörlerde %90) arayüz olmadan sıfır demek.
2. **Sınır vektörlerini ızgaradan önce toplardık.** Izgara (48/48) hiçbir hata bulmadı; bütün bulgular (B1–B5) sınır
   vektörlerinden çıktı. Dijkstra'nın sözü burada somut: ızgara hataların yokluğunu göstermedi.
3. **İki oturum ayrımını baştan kayda alırdık.** `prompts/` klasörü sonradan oluşturuldu; ilk prompt'lar o an saklanmalıydı.
4. **Ghidra'yı kurardık.** [REA] puanı fonksiyon adresi istiyor; elimizde dize adresleri var ama a priori arama
   döngüsü ve yuvarlama komutu gibi asıl ilginç davranışların adresi yok (LEDGER "Açık işler").
5. **Özetleyici araçlara spec okutmazdık** (H4).
