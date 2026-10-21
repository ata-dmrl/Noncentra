# G*Power 3.1.9.7 teardown raporu (Aşama 0 + 1)

Tarih: 2026-10-16. Aşama 1 statik analizdir. Aşama 2'de exe kullanıcı onayıyla çalıştırıldı ve yalnızca girdi/çıktı değerleri okundu.
Ham kanıtlar: `teardown/evidence/`.

## Edinme ve bütünlük

| | |
|---|---|
| Kaynak | Resmi HHU sayfası (psychologie.hhu.de/.../gpower) → `GPowerWin_3.1.9.7.zip` |
| Zip SHA-256 | `3bb7f1f2478d74ee5ba701ae7f849373cf2b8a11f6b6216c7c6b236db7861199` |
| İçerik | `GPowerNT.exe` (2.29 MB), `VC_redist.x86.exe`, iki `.wav`. Yükleyici yok, exe doğrudan çalışıyor |
| `GPowerNT.exe` SHA-256 | `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812` |
| İmza | **İmzasız** (Authenticode `NotSigned`). `VC_redist.x86.exe` geçerli Microsoft imzalı |
| Sürüm bilgisi | Franz Faul, "GPower" 3.1.9.7, © 1992–2020 |

## Yapı

- **Platform:** PE32, x86 (32-bit), Windows GUI. Linker 14.36 → Visual Studio 2022 (MSVC v143). Derleme tarihi 2023-10-16.
- **Çatı:** MFC (Unicode), `mfc140u.dll` dinamik bağlı (556 import). Ayrıca GDI+ (grafikler), COMCTL32, MSVCP140, UCRT.
- **PDB yolu:** `G:\GPower\GPower30_3.1.7_22\Prog\Release\GPowerNT.pdb` (PDB dağıtılmamış). Kod tabanı 3.0 / 3.1.7 dalından geliyor.
- **Güvenlik bayrakları:** `DllCharacteristics = 0x8100` → NX ve Terminal Server aware var; **ASLR (DYNAMIC_BASE) kapalı**, CFG yok. ImageBase 0x400000.
- **Dış iletişim:** Ağ API'si importu yok, güncelleme kontrolü ya da kayıt defteri anahtarı izi yok.
- **Kaynaklar:** 144 kaynak: 89 diyalog, 6 menü, 42 string, 13 DLGINIT, 1 toolbar, manifest (DPI-aware, asInvoker).
- **Grid:** Diyaloglarda `MFCGridCtrl` (Chris Maunder'ın MFC Grid Control'ü) kullanılıyor. Bazı kontrol adları Almanca ("Benutzerdefiniert1").

## Sayısal çekirdek (string izlerinden)

Kendi yazdığı bir dağılım kütüphanesi var; hata mesajlarından çıkan fonksiyon listesi:

`TDist`, `FDist`, `ChiDist`, `NormalDist`, `CorrDist`, `MRCDist` (çoklu korelasyon katsayısı), `BinomialDist`,
`HypergeometricDist`, `Poisson`, `LogNormalDist`, `LaplaceDist`, `Exponential`, `Uniform`. Her birinde `-Cdf`, `-Pdf` ve `-Quantile` bulunuyor.

- `TDist-Pdf` / `FDist-Pdf: failed to converge` → merkezi olmayan yoğunluklar seri açılımıyla, yakınsama kontrollü hesaplanıyor.
- `** On entry to %6s, parameter number %2i had an illegal value` → LAPACK `xerbla` mesajı. MANOVA ve tekrarlı ölçüm matris işlemleri için gömülü LAPACK/BLAS kodu var.
- MANOVA için iki algoritma ailesi açıkça adlandırılmış: **Muller-Peterson** ve **O'Brien-Shieh** (Wilks U, Pillai V, Hotelling-Lawley T1/T2). Yaklaşık değerler için Rao (1951) F dönüşümü kullanılıyor.
- Seçenek diyaloglarında: süreklilik düzeltmesi, arcsin dönüşümü, iki yönlü testte alfa dengeleme, "N < eşik ise exact, değilse büyük örneklem yaklaşımı (Fisher z / z-test)", Wilcoxon testleri için ARE (Asimptotik Göreli Etkinlik).
- Analiz türü metinleri gpower2 ile bire bir örtüşüyor: Post hoc, A priori, Compromise (β/α oranı), Criterion, Sensitivity.

Hesaplama kodunun kendisi okunmadı. Ghidra/IDA kurulu olmadığı için REA disassembly sağlayıcısı devre dışı. Algoritma ayrıntıları bilinçli olarak kopyalanmıyor; yayınlanmış kaynaklardan yazılıyor.

## Test kataloğu

Ana menüde 5 aile ve **49 test** var (+ hesap makinesi). Tam liste ve gpower2 karşılıkları [coverage.md](coverage.md) dosyasında.
Şu an 6 / 49 test uygulanmış durumda (3 t-testi, tek yönlü ANOVA, iki regresyon R² testi); altısı da canlı G*Power çıktısıyla doğrulandı (aşağıya bakın).

## Zayıf noktalar → gpower2 geliştirme listesi

1. **Otomasyon yok:** komut satırı, betik ya da API yok; her hesap elle yapılıyor. → CLI sözleşmesi, MCP ve REST (yapıldı / planda).
2. **Toplu hesaplama yok:** X-Y grafik dışında parametre ızgarası taranamıyor. → `grid` komutu, CSV/JSON çıktı.
3. **Platform:** Yalnızca Windows x86 ve macOS; web sürümü yok. 32-bit, imzasız, ASLR kapalı. → Pyodide web arayüzü.
4. **Çıktı:** "Protocol" düz metin/RTF olarak alınıyor; makine okunur değil. → JSON şemaları, HTML/PDF rapor.
5. **Eksik modern yöntemler:** eşdeğerlik (TOST), karma/çok düzeyli modeller, simülasyonla güç, Bayesçi güç/örneklem büyüklüğü, kümelenmiş tasarımlar. → G*Power'da olmayan testler.
6. **Tekrarlanabilirlik:** Ayarlar ve girdiler bir dosyaya kaydedilip paylaşılamıyor (yalnızca matris diyaloglarında Load/Save var). → paylaşılabilir istek JSON'u / URL.

## Aşama 2: canlı referans toplama (kullanıcı onayıyla exe çalıştırıldı)

- **Yöntem:** `teardown/harvest.py` + `teardown/win32ui.py`. ctypes üzerinden Win32 mesajları kullanılıyor (`WM_SETTEXT`, `BM_CLICK`, `CB_SETCURSEL`); ek paket yok. Etiket ile değer kutusu ekran satırına göre eşleniyor, bu yüzden G*Power'ın test değişince yeniden atadığı kontrol ID'lerinden bağımsız.
  REA'nın UI araçları macOS (AX) içindir; Windows'ta kullanılamadı.
- **Kapsam:** 3 t-testi × 5 analiz türü, toplam 183 durum (`gpower2/reference/t_tests_harvested.csv`, `t_tests_ratio_harvested.csv`). Her satırda G*Power'ın geri yansıttığı girdiler kontrol edildi; 0 hata.
- **Sonuç:** 160 durum G*Power ile **7. ondalığa kadar** aynı (G*Power'ın gösterim hassasiyeti). Bu durumlar: güç, kritik t, sensitivity'de etki büyüklüğü, criterion/compromise'da α ve a priori n.
  Literatürden alınan 4 satır da bu sırada doğrulandı.

### Bulgu: eşit olmayan grup oranında a priori n

- 23 durumda (hepsi `ratio ≠ 1`, a priori) grup büyüklükleri ±1 farklı.
- gpower2 kesirli çözüm n1*'ı bulup her grubu ayrı yukarı yuvarlıyor: n1 = ⌈n1*⌉, n2 = ⌈n1*·oran⌉. Eşit oranda G*Power ile 27/27 aynı.
- G*Power'ın kuralı tek bir yuvarlama kuralıyla açıklanamıyor. Denenen kurallar: N veya n1 üzerinden tam sayı arama × floor/ceil/round. En iyisi 24/63 tuttu. Ayrıca 9 durum tek bir kesirli N* ile bile tutarlı değil; demek ki sonuç sonradan ayrıca düzeltiliyor. Kesin kural için disassembly (Ghidra/IDA) gerekiyor.
- **G*Power'da hata:** Bu 23 durumun 5'inde G*Power'ın önerdiği n, istenen gücü sağlamıyor (ör. oran 2.5, d=0.5, hedef .90 → 59+149, gerçek güç 0.8989). gpower2'nin sonucu 23 durumun hepsinde hedefe ulaşıyor.
- Bu satırlar CSV'de `known_divergence` sütunuyla işaretli. Diferansiyel test bunları "SAPMA" olarak raporluyor ve gpower2'nin hedefe ulaştığını ayrıca doğruluyor.

### Bulgu: scipy / statsmodels

- scipy 1.15 `nct.cdf` bazı uç kuyruklarda NaN döndürüyor; gpower2 yansıma özdeşliğiyle bunu aşıyor.
- statsmodels aynı hata yüzünden 2 grid durumunda NaN döndürüyor.

## Aşama 2b: F testleri (tek yönlü ANOVA, çoklu regresyon R²)

- **Uygulanan testler:**
  - `f.anova_oneway`: λ = f²·N, sd = (k−1, N−k).
  - `f.regression_r2`: λ = f²·N, sd = (p, N−p−1).
  - `f.regression_r2_increase`: λ = f²·N, sd = (q, N−p−1).
- **Toplama:** `harvest.py` artık test ailesinden bağımsız çalışıyor (`SPECS` tablosu). Her satırda girdinin geri yansıdığı kontrol ediliyor. G*Power'ın modal uyarıları okunup kapatılıyor ve metinleri `raw` sütununa yazılıyor.
- **Sonuç:** 198 durumun (`gpower2/reference/f_tests_harvested.csv`) tamamı G*Power ile 7. ondalığa kadar aynı; sapma yok. Ayrıca statsmodels ile 108 F karşılaştırması da uyuşuyor.
- **G*Power kuralı (gözlem):** ANOVA a priori N, grup sayısının katına yukarı yuvarlanıyor (f=.25, k=3 → 159, kesirli çözüm 158'i veriyordu). gpower2 bunu `AnovaOneWay.round_sizes` ile uyguluyor.
- **G*Power uyarısı:** N grup sayısının katı değilse post hoc, sensitivity ve compromise analizlerinde "analysis was based on the average group size" uyarısı çıkıyor; hesap yine λ = f²·N ile yapılıyor. Aynı N için criterion analizinde uyarı çıkmıyor (tutarsızlık).
- **scipy hatası:** `ncf.sf`, merkezdışılık tam 0 iken negatif değer döndürüyor (ör. d1=1, d2=2, x=1 → −0.577). gpower2 bu durumda merkezi F'ye geçiyor (`f_power`).
- **statsmodels tuzağı:** `FTestPower` sınıfının sd argümanları ters; doğrusu `FTestPowerF2`.

## Sonraki adımlar

- Katalogda sıradaki öncelik: χ² uyum iyiliği, korelasyon (bivariate normal), iki oran (z-test), faktöriyel ANOVA.
- İsteğe bağlı: eşit olmayan oran kuralını kesinleştirmek için Ghidra kurulumu. Kurulum gerektirdiği için şimdilik yapılmadı.
