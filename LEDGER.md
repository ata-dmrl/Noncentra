# LEDGER.md — Kanıt defteri (`t-paired`)

Hedef: G*Power 3.1.9.7, `GPowerNT.exe`, SHA-256
`c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812` (resmi HHU zip'inden; bkz. README).

| Etiket | Anlamı |
|---|---|
| `[DOK]` | Kılavuzda ya da makalede yazıyor. |
| `[REA]` | Binary'den kanıtlandı: dize adresi ve o dizeyi kullanan komutun adresi, ya da PE başlığı/import tablosu. |
| `[AJAN]` | Ajanın çıkarımı; binary'de kanıtı yok. Kâhinle (G*Power ekranı) sınandıysa öyle yazıyor. |

**Adres yöntemi.** ImageBase 0x400000 ve ASLR kapalı olduğu için adresler sabit. "Dize" `.rdata` içindeki sanal
adres, "başvuru" o adresi `push` eden `.text` komutunun adresi. Başvurular 4 baytlık adres eşleşmesiyle bulundu;
kod decompile edilmedi ve repoda decompile çıktısı yok. Aynı mesajın G*Power'da gerçekten göründüğü, ekran
görüntüsüyle ayrıca kanıtlandı (`oracle/t-paired/screenshots/`).

**Kâhin kanıtı.** `pNNN` kimlikleri `oracle/t-paired/boundary_harvest.csv` satırları ve aynı adlı ekran görüntüleri;
`hNNN` kimlikleri `noncentra/reference/t_tests_harvested.csv` satırları.

---

## A. Binary'nin kendisi

| # | Etiket | Bulgu | Kanıt |
|---|---|---|---|
| A1 | [REA] | PE32, x86 32-bit, Windows GUI; linker 14.36 (Visual Studio 2022, MSVC v143); derleme damgası 2023-10-16. | PE başlığı |
| A2 | [REA] | ASLR kapalı, CFG yok: `DllCharacteristics = 0x8100` (NX + Terminal Server aware). ImageBase 0x400000. | PE opsiyonel başlığı |
| A3 | [REA] | Çatı MFC (Unicode): `mfc140u.dll`'den 556 import; ayrıca GDI+, COMCTL32, MSVCP140, UCRT. Ağ API'si importu yok. | Import tablosu |
| A4 | [REA] | Kod 3.0/3.1.7 dalından: PDB yolu dizesi `G:\GPower\GPower30_3.1.7_22\Prog\Release\GPowerNT.pdb` (PDB dağıtılmamış). | Debug dizini dizesi |
| A5 | [REA] | Kendi dağılım kütüphanesi var: `TDist`, `FDist`, `ChiDist`, `NormalDist` … her biri için `-Cdf`, `-Pdf`, `-Quantile` hata dizeleri. | `.rdata` dizeleri |
| A6 | [REA] | Merkezi olmayan t yoğunluğunda yakınsama kontrolü var: `TDist-Pdf: failed to converge`. | `.rdata` dizesi |
| A7 | [AJAN] | A6'dan çıkarım: merkezi olmayan t bir seri açılımıyla, durma koşullu iterasyonla hesaplanıyor. Durma koşulu (tolerans, en fazla adım) bulunamadı. | — |
| A8 | [REA] | Analiz türü metinleri: Post hoc, A priori, Compromise, Criterion, Sensitivity. | Diyalog/string kaynakları |
| A9 | [REA] | Eşleştirilmiş test başlığı dizesi @ `0x005CB56C`, başvuru `0x004DCF4C`. | Dize + başvuru |

## B. Eşleştirilmiş t testi: girdi kabul kuralları (kılavuzda olmayan davranış)

### B1. N girdi olduğunda en küçük N = 3; a priori ise 2 döndürebilir

| Etiket | Satır |
|---|---|
| [REA] | Dize `"Total sample size is outside the admissible range ("` @ `0x005C6524`, başvuru `0x00488A3C`. |
| Kâhin | Post hoc N = 1, 2 → "Input error: Total sample size is outside the admissible range (3, 2147483646)" (p027–p030; `p029_post_hoc_dialog0.png`). Sensitivity N = 2 → aynı (p047). |
| Kâhin | A priori aynı test N = 2 öneriyor: dz = 10 tek kuyruk (p010), dz = 20 (p012, p013), güç = α (p014, p015, p018). |
| [AJAN] | Üst sınır 2147483646 = 2³¹ − 2, yani 32 bit işaretli tam sayı sınırına yakın bir değer. |
| Uygulama | `PairedT.min_n_given = 3`, a priori alt sınırı `min_n = 2`. SPEC §2, test: `test_gpower_clone.py::test_error[post-hoc N=2]`. |

### B2. Güç < α reddedilir; güç = α kabul edilir

| Etiket | Satır |
|---|---|
| [REA] | Dize `"Power must be greater than or equal to alpha."` @ `0x005C6220`, başvuru `0x004880F9`. |
| Kâhin | Güç 0.04, α 0.05 → hata (p016; sensitivity p048). Güç 0.8, α 0.9 → hata (p021). Güç = α = 0.05 → N = 2 (p014, p018). |
| Uygulama | `solver._power_not_below_alpha` → `INCONSISTENT`. |

### B3. Kesirli N en yakın tam sayıya yuvarlanır (.5 yukarı); aralık kontrolü yuvarlamadan sonra

| Etiket | Satır |
|---|---|
| Kâhin | Post hoc dz 0.5, iki kuyruk: 2.5 → 3, 3.4 → 3, 3.5 → 4, 3.6 → 4, 10.2 → 10, 10.5 → 11, 10.7 → 11 (p033–p040). Güç, yuvarlanmış tam sayının gücüyle 7 basamakta aynı. |
| [AJAN] | 2.5 kabul edilip 3'e yuvarlanırken 2 reddediliyor: aralık kontrolü yuvarlanmış değere uygulanıyor. Banker yuvarlaması değil (2.5 → 2 olurdu). Binary'de yuvarlama komutu (ör. `cvtsd2si` / `+0.5` ve `floor`) henüz gösterilmedi. |
| Uygulama | Sözleşme `n_total`'ı tam sayı istediği için `INVALID_VALUE`. Bilinçli fark (tests/T_PAIRED_DIFF_REPORT.md). |

### B4. α ve güç aralığı: mesaj "(1e-07, 1)" diyor ama 1e-07 dahil

| Etiket | Satır |
|---|---|
| [REA] | Dize `"Alpha is outside the admissible range ("` @ `0x005C6100`, başvurular `0x004874EC`, `0x004875B4`. |
| [REA] | Dize `"Power is outside the admissible range ("` @ `0x005C60D8`, başvurular `0x0048809C`, `0x00488194`. |
| Kâhin | α = 0 ve α = 1 → hata (p024, p025); güç = 1 → hata (p026). α = 1e-07 kabul (p041), α = 0.9999999 kabul (p043). |
| Uygulama | `solver.MIN_PROB = 1e-7`, aralık [1e-07, 1). |

### B5. Etki büyüklüğü: a priori'de \|dz\| > 0.00001; negatif dz kabul edilir ve yön değiştirir

| Etiket | Satır |
|---|---|
| [REA] | Dize `"In an a priori analysis, the absolute value of the\n"` @ `0x005CB24C`, altı başvuru; biri `0x004DD1DB`, eşleştirilmiş test başlığının başvurusuna (`0x004DCF4C`, A9) yakın. |
| Kâhin | dz = 0 → "…absolute value of the effect size be greater than 0.00001." (p022, `p022_a_priori_dialog0.png`). |
| [AJAN] | Eşik değerinin kendisi (0.00001) mesajdan okundu; tam 0.00001'de G*Power'ın davranışı denenmedi. Uygulama "≤ 0.00001 ret" kabul ediyor. |
| Kâhin | dz = −0.5 iki kuyrukta N = 34 (dz = 0.5 ile aynı), ama kritik t **negatif** (−2.0345153, p023). Tek kuyrukta sol kuyruk: kritik t = −1.7291328, güç 0.6951493 (p045). |
| Uygulama | Sözleşme dz > 0 istediği için `OUT_OF_RANGE`. |

## C. Hesap

| # | Etiket | Bulgu | Kanıt |
|---|---|---|---|
| C1 | [DOK] | δ = dz·√N, df = N − 1; test, farklar üzerinde tek örneklem t testi. | Faul ve ark. (2007), G*Power 3.1 kılavuzu, "Means: Difference between two dependent means" |
| C2 | [DOK] | dz = \|μx − μy\| / √(σx² + σy² − 2ρσxσy) ("Determine" penceresi; kapsam dışı). | Faul ve ark. (2007); kılavuz |
| C3 | [DOK] | Analiz türleri ve neyin hesaplandığı (a priori N, post hoc güç, compromise β/α, criterion α, sensitivity etki). | Faul ve ark. (2007) |
| C4 | [AJAN] | Çift kuyruklu güç iki kuyruğun katkısını da topluyor: P(T > t_c) + P(T < −t_c). Kâhinle doğrulandı: 48/48 ızgara vektörü 7 basamakta aynı. | tests/T_PAIRED_DIFF_REPORT.md |
| C5 | [AJAN] | A priori N = güç ≥ hedef olan en küçük tam sayı (⌈N*⌉), alt sınır 2. Kâhinle doğrulandı: 53 a priori vektör; statsmodels'ın kesirli N'iyle 180/180. Arama yöntemi (artırma mı, ikiye bölme mi) ve durma koşulu binary'de bulunamadı. | tests/T_PAIRED_DIFF_REPORT.md |
| C6 | [AJAN] | Ekranda 7 ondalık gösteriliyor; iç hesap double. Kâhin: tüm vektörler 1e-6 içinde. | — |
| C7 | [DOK] | Cohen (1988) eşikleri: dz 0.2 / 0.5 / 0.8. | CONTRACT.md §10, Cohen (1988) |

## D. Kâhinin dışındaki referanslar (karşılaştırma için bulunanlar)

| # | Etiket | Bulgu |
|---|---|---|
| D1 | [AJAN] | statsmodels `TTestPower` iki kuyruklu güçte 30 vakada NaN döndürüyor (scipy `nct.cdf` alt kuyruk hatası). Motor yansıma özdeşliğiyle aşıyor (`core/distributions.py`). |
| D2 | [AJAN] | scipy 1.18 `t.isf(1e-300, 11)` → −inf; compromise çözücüsü α'yı çok küçüğe indirince çöküyordu (h134, h137). `t_crit` sonlu olmayan değeri +∞ sayıyor. |

---

## Açık işler: [AJAN] satırlarını [REA]'ya çevirmek

Puan yalnızca [REA] satırlarına verildiği için Ghidra ile şunlara bakılmalı (hepsi bir başvuru adresinden başlıyor):

1. **C5, a priori arama ve durma koşulu:** `0x004880F9` (B2 kontrolü, a priori girişine yakın) çevresindeki fonksiyonun
   çağırdığı döngü; karşılaştırma `power >= target` ve tam sayıya geçiş.
2. **B3, kesirli N yuvarlaması:** `0x00488A3C` (B1 aralık kontrolü) öncesinde N'yi tam sayıya çeviren komut.
3. **A7, seri açılımının durma koşulu:** `TDist-Pdf: failed to converge` dizesinin başvurusu ve önündeki karşılaştırma.
4. **B5 eşiği:** `0x004DD1DB` önündeki karşılaştırmada kullanılan sabit (0.00001 bekleniyor; `.rdata`'da double olarak).
