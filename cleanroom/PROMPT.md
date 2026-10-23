# Oturum 2 — Temiz oda yazımı

```text
Yeni bir oturumsun. Elinde yalnızca iki belge var: SPEC.md (davranış) ve CONTRACT.md (arayüz).
Başka kaynak YOK: G*Power binary'sine, Ghidra/REA çıktısına, LEDGER.md'ye ya da önceki bir oturumun
koduna bakma. Bir şey SPEC'te yazmıyorsa uydurma; "SPEC'te yok" diye not düş.

Görev: eşleştirilmiş t testi (t-paired) için güç analizi motoru ve onu çağıran `gpower-clone` CLI'si.
- Dil: Python 3.11+. Dağılım fonksiyonları için scipy serbest (merkezi ve merkezi olmayan t).
- Hesap mantığı tek bir motor modülündedir. CLI (ve varsa MCP) yalnızca alan adlarını çevirir ve motoru çağırır.
- CLI ve JSON biçimi CONTRACT.md §2 ve §4.2'deki gibi: tek satır JSON, tam sayılar JSON tam sayısı,
  hata JSON'u {"error","code","field"}, çıkış kodları 0 / 2 / 1.
- Beş mod: a-priori, post-hoc, compromise, criterion, sensitivity.

Önce testler: SPEC.md §3'teki her Örnekler tablosunu bir test olarak yaz (beklenen değer tablodadır,
sen hesaplamazsın), sonra motoru yaz. Tolerans CONTRACT.md §6: N ve df tam eşleşme, ondalıklar 1e-6.

Bitirince: bütün SPEC örnekleri ve CONTRACT.md §9'daki t-paired açık vektörleri geçiyor mu, raporla.
Geçmeyen her satır için nedenini yaz (senin hatan mı, SPEC'teki bir eksik mi).
```
