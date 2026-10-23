# Eşleştirilmiş t testi doğrulaması (K2 · `t-paired`)

Tarih: 2026-10-21. Kâhin: G*Power 3.1.9.7, `GPowerNT.exe` SHA-256
`c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812` (teardown raporundaki hash ile aynı).

G*Power test adı: *t tests – Means: Difference between two dependent means (matched pairs)*.
Motorda `t.paired`; δ = dz·√N, df = N − 1 (tek örneklem t testinin farklar üzerindeki hâli).

## Ne doğrulandı

| Kaynak | Vektör | Sonuç |
|---|---|---|
| `noncentra/reference/t_tests_harvested.csv` (`t.paired` satırları, ızgara) | 48 | 48 / 48 aynı |
| `oracle/t-paired/boundary_harvest.csv` (sınır değerler, bu çalışma) | 55 | 39 aynı, 16 bilinen fark |
| CONTRACT.md §9 açık vektörleri (`t-paired/*`) | 5 | a priori elle kontrol edildi: N = 45, δ = 3.3541020, kritik t = 1.6802300 |

Sınır vektörleri `teardown/harvest_paired.py` ile toplandı. Betik, açık G*Power penceresine Win32 mesajlarıyla
değer giriyor. Her vakanın ve her uyarı kutusunun ekran görüntüsü `oracle/t-paired/screenshots/` klasöründe,
dosya adları CSV'deki `screenshots` sütununda. Testler: `tests/test_paired_boundary.py`. Farklı çıkan
satırlar orada `DIVERGENCES` listesinde, nedenleriyle birlikte; katı xfail olarak işaretli.

Karşılaştırma kuralı CONTRACT.md §6 ile aynı: tam sayılar tam eşleşme, ondalıklar 1e-6 mutlak ya da göreli.

## Bulgular (kanıt defteri için)

`[REA]` satırlarında dize adresi `.rdata` içindeki sanal adres, "başvuru" ise bu adresi `push` eden
`.text` komutunun adresidir (ImageBase 0x400000, ASLR kapalı, yani adresler sabittir). Bu adresler yalnızca
dize araması ve 4 baytlık adres eşleşmesiyle bulundu; kod decompile edilmedi. Sayısal sınırlar
(ör. "3") ikili dosyadan değil, G*Power'ın çalışırken gösterdiği mesajdan alındı. Bu yüzden ayrıca
ekran görüntüsüyle kanıtlandı.

### B1. Post hoc ve sensitivity N < 3'ü reddediyor, a priori ise N = 2 öneriyor

- `[REA]` Dize `"Total sample size is outside the admissible range ("` @ `0x005C6524`, başvuru `0x00488A3C`.
- Gözlem: post hoc ve sensitivity modlarında N = 1 ve N = 2 için "Input error: Total sample size is outside the
  admissible range (3, 2147483646)" çıkıyor (p027–p030, p047; `p029_post_hoc_dialog0.png`).
- Gözlem: aynı test a priori modda N = 2 öneriyor: dz = 10 tek kuyruk (p010), dz = 20 (p012, p013),
  güç = α (p014, p015). Yani G*Power, a priori'de kendi post hoc modunun kabul etmediği bir N veriyor.
- Motor: `min_n = 2`. A priori sonuçları G*Power ile aynı. Post hoc ve sensitivity'de N = 2 kabul ediliyor → **fark**.

### B2. Güç < α reddediliyor; güç = α kabul ediliyor

- `[REA]` Dize `"Power must be greater than or equal to alpha."` @ `0x005C6220`, başvuru `0x004880F9`.
- Gözlem: güç 0.04, α 0.05 → hata (p016, p048); güç 0.8, α 0.9 → aynı hata (p021). Güç 0.05 = α ise kabul
  ediliyor ve N = 2 çıkıyor (p014, p018).
- Motor: a priori'de güç < α için hata vermiyor, N = 2 döndürüyor → **fark**. Sensitivity'de motor da reddediyor.

### B3. Kesirli N en yakın tam sayıya yuvarlanıyor (.5 yukarı); aralık kontrolü yuvarlamadan sonra

- Gözlem (post hoc, iki kuyruk, dz 0.5): 2.5 → 3, 3.4 → 3, 3.5 → 4, 3.6 → 4, 10.2 → 10, 10.5 → 11, 10.7 → 11
  (p033–p040). Güç, yuvarlanmış tam sayının gücüyle 7 basamakta aynı. 2.5 reddedilmiyor, 2 reddediliyor.
  Demek ki aralık kontrolü yuvarlanmış değere uygulanıyor. Banker yuvarlaması değil (2.5 → 2 olurdu).
- Motor: kesirli N'yi reddediyor → **fark**. CONTRACT.md'de `n_total` tam sayı türünde, yani sözleşme
  katmanında `INVALID_VALUE` doğru yanıt. Bu fark bilinçli bırakılabilir.

### B4. α aralığı `(1e-07, 1)` yazıyor ama alt sınır dahil

- `[REA]` Dize `"Alpha is outside the admissible range ("` @ `0x005C6100`, başvurular `0x004874EC`, `0x004875B4`.
  `"Power is outside the admissible range ("` @ `0x005C60D8`, başvurular `0x0048809C`, `0x00488194`.
- Gözlem: α = 0 ve α = 1 → hata (p024, p025); güç = 1 → hata (p026). α = 1e-07 kabul ediliyor (p041), yani
  mesaj açık aralık yazsa da alt sınır dahil. α = 0.9999999 de kabul ediliyor (p043).
- Motor: α ∈ (0, 1). 1e-07 altını reddetmiyor. Sözleşmenin aralığı da (0, 1) olduğu için bu bir fark değil,
  ama `alpha = 5e-08` gibi bir gizli vektör G*Power'da hata verir.

### B5. dz = 0 reddediliyor, negatif dz kabul ediliyor ve yön değişiyor

- `[REA]` Dize `"In an a priori analysis, the absolute value of the\n"` @ `0x005CB24C`, altı başvuru. Biri
  `0x004DD1DB`, eşleştirilmiş test başlığının başvurusuna (`0x004DCF4C`, dize @ `0x005CB56C`) çok yakın.
- Gözlem: dz = 0 → "…absolute value of the effect size be greater than 0" (p022). dz = −0.5 iki kuyrukta N = 34
  veriyor, dz = 0.5 ile aynı, ama kritik t **negatif** gösteriliyor (−2.0345153, p023). Tek kuyrukta
  dz = −0.5 testi sol kuyruğa çeviriyor: kritik t = −1.7291328, güç 0.6951493 (p045,
  `p045_post_hoc.png`). Motor aynı girdide sağ kuyruğu kullanıp 7.1e-05 buluyor → **fark**.
- CONTRACT.md'de dz > 0 olduğu için negatif dz sözleşme katmanında `OUT_OF_RANGE`; motor farkı CLI'den görünmez.

### B6. Uçlarda motor G*Power ile aynı

- dz = 0.01 → N = 61827 (tek kuyruk) / 78491 (iki kuyruk); dz = 0.05 → 2475 / 3142; güç 0.999 → N = 104;
  α 0.001 / 0.5; compromise β/α = 4 ve 0.25; criterion güç 0.9999. Bunların hepsi 7 basamakta aynı.

## Motor düzeltmesi: scipy 1.18'de compromise çöküyordu

- `t_tests_harvested.csv` satırları `h134` ve `h137` (paired compromise, N = 12) scipy 1.18 ile düşüyordu.
  Hata: "beta/alpha ratio not reachable".
- Neden: `scipy.stats.t.isf(1e-300, 11)` **−inf** döndürüyor (doğru değer çok büyük pozitif bir sayı). Compromise
  çözücüsü α'yı 1e-300'e kadar indirdiği için alt uçta β = 0 çıkıyor ve aralık bulunamıyor.
- Düzeltme: `noncentra/core/distributions.py` → `t_crit`. Sonlu olmayan kritik değer +∞ sayılıyor (güç 0, β 1).
  1e-200 ve üstündeki α'larda `isf` değişmeden kullanılıyor.
- `pyproject.toml` scipy sürümünü sabitlemiyor. Bu düzeltme olmadan sonuç, kurulumdaki scipy sürümüne bağlı.

## Halüsinasyon günlüğü için adaylar

1. Repodaki varsayım "en küçük N = 2" (`TestModel.min_n = 2`). G*Power post hoc ve sensitivity'de 3'ü istiyor
   (B1). Bunu sınır vektörü p029 yakaladı.
2. "Negatif etki büyüklüğü simetriktir, yalnızca mutlak değer önemli" varsayımı iki kuyrukta doğru, tek kuyrukta
   yanlış (B5). Bunu p045 yakaladı.

## Sözleşme katmanı ve motor düzeltmeleri (2026-10-22)

- `gpower-clone` (CONTRACT.md 1.0.0) eklendi: `noncentra/contract.py` (ince adaptör) + `noncentra/contract_cli.py`.
  MCP: `noncentra/mcp_contract.py`, tek araç `power_analysis`; ikisi de `contract.run()` çağırır.
- Motor artık G*Power gibi davranıyor:
  - B2: a priori ve sensitivity'de güç < α → `INCONSISTENT` (p016, p021, p048).
  - B1: eşleştirilmiş testte N girdi olduğunda N < 3 → `OUT_OF_RANGE` (p027–p030, p047). A priori hâlâ N = 2 döndürebiliyor (p010, p014).
  - B4: α ya da güç < 1e-07 → `OUT_OF_RANGE`; 1e-07 kabul.
  - B5: a priori'de |dz| ≤ 0.00001 → `OUT_OF_RANGE` (p022 mesajındaki eşik).
- Bilinçli bırakılan farklar (sözleşme bunları zaten reddediyor): kesirli N → `INVALID_VALUE` (B3), dz ≤ 0 → `OUT_OF_RANGE` (B5).
  `tests/test_paired_boundary.py` motor seviyesinde bunları xfail tutuyor; `tests/test_gpower_clone.py` aynı 55 satırı sözleşme
  arayüzünden geçirip hepsinin beklenen hata ya da G*Power değeriyle sonuçlandığını doğruluyor.
- Açık vektörler: `oracle/public_vectors.jsonl` (CONTRACT.md §9). Uygulanan 4 ailenin 20 vektörü geçiyor; `chi2-contingency` → `UNSUPPORTED`.
- `tests/test_mcp_contract.py`: 25 açık vektör + 5 ek vakada MCP çıktısı CLI stdout'uyla aynı.

## Açık işler

- SPEC.md (Gherkin), LEDGER.md, HALLUCINATIONS.md, AGENT_COST.md, prompts/, README.md.
- Ghidra ile [REA] kanıtlarını güçlendirmek: a priori N araması ve durma koşulu, N ≥ 3 kontrolünün fonksiyonu.
