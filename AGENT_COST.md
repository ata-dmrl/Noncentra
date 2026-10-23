# Ajan maliyet ve süreç günlüğü

## Hangi ajan

| Oturum | Ajan | Model | Ortam |
|---|---|---|---|
| 1 · İnceleme | Claude Code (Claude masaüstü uygulaması) | Claude Opus 5.5 | Windows 11, REA 6.5.0 (`rea-agents`, npm), Ghidra 12.1.4 + Temurin JDK 21.0.12.1 |
| 2 · Yazım | Claude Code (yeni oturum) | Claude Opus 5.5 | aynı makine; yalnızca SPEC.md, CONTRACT.md, `oracle/`, `tests/contract/` |

Destek: Claude Pro planı. API anahtarı kullanılmadı, faturalama plan limitleri üzerinden.

## Token ve süre (ölçülen)

Uygulamanın kendi sayacından (`get_usage`) okunan değerler:

| An | Oturum 1 bağlam penceresi | Plan kullanımı |
|---|---|---|
| 2026-10-22, inceleme oturumunun 6. günü | 739 146 token (%74 / 1 M), bunun 644 732'si mesajlar | 5 saatlik pencere %65, haftalık %56 |

- **Maliyet:** Pro aboneliği sabit ücretli olduğu için oturumun doğrudan bir API faturası yok. API fiyatıyla yaklaşık karşılığı,
  oturum bitince toplam giriş ve çıkış token'larından hesaplanıp buraya eklenecek.
- **Oturum 2:** başlatılınca kendi raporunu `prompts/session2_report.md` dosyasına yazacak; sayıları buraya aktarılacak.

## İterasyonlar (oturum 1)

| # | Aşama | Ne oldu |
|---|---|---|
| 1 | Statik inceleme | PE başlığı, kaynaklar, dizeler (REA + objdump). Ghidra yoktu; hesap kodu okunmadı. |
| 2 | İlk prototip | t testleri, CLI, MCP. Literatürden hatırlanan 4 referans değeri (doğrulanmamış). |
| 3 | Canlı G*Power toplama | t testleri, 183 vaka. Eşit olmayan oranda 23 fark bulundu (H-01). |
| 4 | F testleri | 198 vaka. ANOVA'nın N yuvarlama kuralı bulundu (H-02). |
| 5 | Web, API, rapor | Çekirdeğe dokunmadı. |
| 6 | erva'nın PR'ı | Eşleştirilmiş t sınır değerleri (H-03, H-04). |
| 7 | Ödev metni ve CONTRACT.md | Sözleşme uyumsuzluğu fark edildi. Kara kutu testler, `gpower-clone` vektörleri, Ghidra kurulumu. |

## Neyi farklı yapardık

1. **Önce sözleşme ve ödev metni.** Oturum, ödev metni ve CONTRACT.md'den önce başladı. Bu yüzden arayüz iki kez
   tasarlandı (`noncentra run …`, sonra `gpower-clone …`) ve temiz oda ayrımı baştan kurulamadı.
2. **İki oturumu ilk günden ayırmak.** İnceleme ve prototip aynı oturumda yapıldı (bkz. `prompts/session1_inspection.md`).
3. **Ghidra'yı ilk gün kurmak.** "Ek kurulum yok" kararı yüzünden 6 gün boyunca hesap motoru kod düzeyinde okunamadı.
   Eşit olmayan oran kuralı (H-01) bu yüzden açık kaldı.
4. **Her toplamada ekran görüntüsü.** İlk 381 G*Power vakası görüntüsüz toplandı. erva'nın betiği görüntü eklediğinde
   bu kanıt standardı geriye dönük olarak kurulmuş oldu.
5. **Bağlam bütçesi.** Tek bir uzun oturum bağlamın %74'ünü doldurdu. İnceleme, toplama ve belge yazımı ayrı
   kısa oturumlara bölünseydi hem daha ucuz olurdu hem de oturumlar arasında bilgi sızıntısı riski azalırdı.
