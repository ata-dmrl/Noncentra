# LEDGER · Kanıt defteri

Bu defter, Noncentra'nın G*Power 3.1.9.7 hakkında dayandığı her iddiayı bir kanıta bağlar.
[spec_all_families.md](spec_all_families.md) içindeki her gereksinim buradaki kimliklere (E-xx) atıf yapar.
`tests/test_traceability.py` iki yönü denetler: her atıf burada var mı, ve repodaki her kanıt
dosyasının SHA-256'sı burada yazanla aynı mı. Bir kanıt dosyası değişirse önce bu defter güncellenmeli.

## Kurallar

- **Etiket** (ödevin etiketleri ve iki açıklayıcı etiket):
  - `[REA]` Binary'den kanıtlandı: REA/Ghidra ile fonksiyon adresi, dize adresi ya da dize referansı. Puan yalnızca bu satırlara verilir.
  - `[DOK]` Kılavuzda ya da makalede yazıyor (Faul vd. 2007, 2009; Cohen 1988; G*Power kılavuzu).
  - `[AJAN]` Ajanın çıkarımı; henüz kanıtı yok. Diferansiyel testle sınanmalı.
  - `[GUI]` G*Power arayüzünden gözlem: girdi ve çıktı değerleri `oracle/` altında, ekran görüntüleriyle. Kâhin budur.
  - `[ÖLÇÜM]` Tekrarlanabilir ölçüm: kütüphane davranışı ya da Noncentra'nın kendi ölçümü; yeniden üretme komutu yazılıdır.
- **Durum:**
  - `doğrulandı`: yeniden üretildi.
  - `kısmen`: bir kısmı yeniden üretildi; açıklaması kaydın içinde.
  - `açık`: henüz kanıtlanmadı.
- **Yerel kanıtlar:** `target/` (G*Power'ın kendisi) ve `teardown/evidence/` (ikili dosyadan çıkarılan
  dökümler) telif nedeniyle repoya **konmaz** (`.gitignore`). Bunlar için yalnızca hash ve yeniden
  üretme komutu kaydedilir. Biri aynı resmi zip'i indirip komutu çalıştırınca aynı hash'i almalıdır.
- **Hash:** Metin dosyalarının (`.csv`, `.txt`, `.json`, `.md`) SHA-256'sı satır sonları LF'ye çevrildikten sonra
  alınır. Böylece Windows (CRLF) ve Linux kopyalarında aynı çıkar. İkili dosyaların hash'i değişmeden alınır.
- **Temiz oda:** G*Power kodu decompile edilmedi ve kopyalanmadı. İkili dosyadan yalnızca başlık bilgileri,
  dizeler ve dizelerin adresleri okundu. Hesaplama davranışı girdi ve çıktı gözlemiyle (dinamik) ve
  yayınlanmış formüllerle (literatür) belirlendi.

## A · Edinme ve statik kanıtlar

### E-01 · Hedef ikili dosya ve bütünlüğü
- **Etiket:** [REA] · **Durum:** doğrulandı
- **İddia:** İncelenen program, resmi HHU sayfasındaki `GPowerWin_3.1.9.7.zip` içindeki `GPowerNT.exe`'dir. Dosya Authenticode ile imzalanmamıştır.
- **Dosya (yerel):** `target/download/GPowerWin_3.1.9.7.zip` · SHA-256 `3bb7f1f2478d74ee5ba701ae7f849373cf2b8a11f6b6216c7c6b236db7861199`
- **Dosya (yerel):** `target/extracted/GPower_3.1.9.7_143/GPowerNT.exe` · SHA-256 `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812`
- **Yeniden üretim:** zip'i psychologie.hhu.de'den indir; `sha256sum`; PowerShell `Get-AuthenticodeSignature` → `NotSigned`.

### E-02 · PE başlığı: derleyici, adres ve güvenlik bayrakları
- **Etiket:** [REA] · **Durum:** doğrulandı
- **İddia:** 32-bit PE dosyası. Linker 14.36 (Visual Studio 2022), derleme tarihi 2023-10-16, ImageBase `0x400000`, `DllCharacteristics = 0x8100` (NX var, ASLR yok). Adresler sabit olduğu için E-09'daki adresler tekrarlanabilir.
- **Dosya (yerel):** `teardown/evidence/objdump_p.txt` (satır 9, 11, 12, 19, 33) · SHA-256 `4ee04992960c782bc9aae3570c5135207b494265b2e82e42184b801417711e84`
- **Yeniden üretim:** `objdump -p GPowerNT.exe`

### E-03 · Arayüz çatısı MFC
- **Etiket:** [REA] · **Durum:** doğrulandı
- **İddia:** Program MFC (`mfc140u.dll`, 556 import) ile yazılmış bir Win32 uygulamasıdır. Kontroller standart Win32 mesajlarına yanıt verir; dinamik kanıt toplamada bu özellik kullanıldı.
- **Dosya (yerel):** `teardown/evidence/objdump_p.txt` (satır 174)
- **Dosya (yerel):** `teardown/evidence/pe_resources.json` (144 kaynak, 89 diyalog) · SHA-256 `d440455d444b9bfa8274ef273a469b02d875ea3d1f2528b7bde842b57d9b374c`
- **Yeniden üretim:** `objdump -p`; REA `inspect_pe_resources`

### E-04 · Kod soyu
- **Etiket:** [REA] · **Durum:** doğrulandı
- **İddia:** Dosyada kalan PDB yolu `G:\GPower\GPower30_3.1.7_22\Prog\Release\GPowerNT.pdb`. Kod tabanı 3.0 / 3.1.7 dalından geliyor.
- **Dosya (yerel):** `teardown/evidence/strings_all.txt` (satır 3228) · SHA-256 `17a2c2fd8ac9d885414b2f09e564761480d7b68f750b6c1c3ec0a2b509aca67c`
- **Yeniden üretim:** `strings -a -n 5 GPowerNT.exe; strings -a -n 5 -el GPowerNT.exe`

### E-05 · Test kataloğu: 5 aile, 49 test
- **Etiket:** [REA] · **Durum:** doğrulandı
- **İddia:** Ana menü (kaynak 128) 5 aileye ayrılmış 49 test içerir. Tam liste ve Noncentra karşılıkları `docs/coverage.md` dosyasındadır.
- **Dosya (yerel):** `teardown/evidence/ui_catalog.json` · SHA-256 `2470628daf04f18cd05114b0960b9c9ac7d1e38512e8e4866b3ae70ee9ebe833`
- **Dosya:** `docs/coverage.md` (bu kanıttan üretilir)
- **Yeniden üretim:** `python -I teardown/catalog_extract.py <pe_resources.json> GPowerNT.exe ui_catalog.json` ve `python -I teardown/coverage.py ui_catalog.json docs/coverage.md`

### E-06 · Beş analiz türü
- **Etiket:** [REA] + [GUI] · **Durum:** doğrulandı
- **İddia:** G*Power beş analiz türü sunar: a priori, post hoc, sensitivity, criterion, compromise. Compromise, β/α oranından α ve gücü hesaplar.
- **Dosya (yerel):** `teardown/evidence/strings_all.txt` (satır 2113, 2116, 2117, 2118: compromise, post hoc, criterion, sensitivity)
- **Gözlem:** Canlı arayüzdeki "Type of power analysis" listesi beş seçeneği gösterir. A priori metni de bu listededir (`teardown/harvest.py` → `ANALYSES`).

### E-07 · Kendi dağılım kütüphanesi
- **Etiket:** [REA] · **Durum:** doğrulandı
- **İddia:** G*Power t, F, χ², normal, korelasyon, binom ve diğer dağılımlar için kendi kodunu kullanır. Merkezi olmayan yoğunluklar yakınsama kontrollü seri açılımıyla hesaplanır.
- **Dosya (yerel):** `teardown/evidence/strings_all.txt` (satır 2592 `TDist-Pdf: failed to converge`, satır 2059 `FDist-Pdf: failed to converge`)
- **Sonuç:** Noncentra bu kodu kullanmaz; scipy kullanır. Bu yüzden eşdeğerlik ancak dinamik kanıtla (E-10, E-15) gösterilebilir.

### E-08 · Kapsam dışı: MANOVA ve matris kodu
- **Etiket:** [REA] · **Durum:** doğrulandı
- **İddia:** MANOVA için Muller-Peterson ve O'Brien-Shieh algoritmaları vardır. Ayrıca gömülü LAPACK kodu bulunur (`xerbla` mesajı). Bunlar Noncentra'nın şu anki kapsamında değildir.
- **Dosya (yerel):** `teardown/evidence/strings_all.txt` (satır 2877, 2413, 3056)

### E-09 · Girdi doğrulama mesajları ve adresleri
- **Etiket:** [REA] + [GUI] · **Durum:** doğrulandı
- **İddia:** G*Power şu girdileri reddeder: güç < α, aralık dışındaki α ve güç, N < 3 (post hoc ve sensitivity), a priori'de etki büyüklüğü 0. Mesajların `.rdata` adresleri ve onları kullanan `.text` adresleri erva'nın raporundadır. Adresler yalnızca dize aramasıyla bulundu; kod decompile edilmedi.
- **Dosya (yerel):** `teardown/evidence/strings_all.txt` (satır 2295 `Power must be greater than or equal to alpha.`)
- **Dosya:** `docs/t-paired-validation.md` (B1, B2, B4, B5)
- **Dosya:** `oracle/t-paired/boundary_harvest.csv` (satırlar `p016`, `p021`, `p022`, `p024`–`p030`, `p047`; ekran görüntüleri `oracle/t-paired/screenshots/`)

## B · Dinamik kanıtlar (G*Power çalıştırıldı)

### E-10 · t testi toplaması
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** 3 t testi × 5 analiz türü için 147 durum, eşit olmayan grup oranı için ayrıca 36 durum toplandı. Her satırda G*Power'ın girdileri geri yansıttığı kontrol edildi.
- **Dosya:** `noncentra/reference/t_tests_harvested.csv` · SHA-256 `91ba749aa0e3819fc02213b21e79548bab5099cdbe918b18b68b3df6239eacfe`
- **Dosya:** `noncentra/reference/t_tests_ratio_harvested.csv` · SHA-256 `63d10383c0594e77861ce1ca3632832c033b45fc094d68f02c199956256acdc9`
- **Yeniden üretim:** G*Power açıkken `python teardown/harvest.py <pid> out.csv t`

### E-11 · İki örneklemli t, a priori örneği
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** d = 0.5, α = 0.05, 1−β = 0.80, iki yönlü → n1 = n2 = 64, δ = 2.8284271, kritik t = 1.9789706, gerçekleşen güç 0.8014596.
- **Dosya:** `noncentra/reference/t_tests_harvested.csv` (satır `h013_two_sample_a_priori`)
- **Dosya:** `noncentra/reference/t_tests.csv` · SHA-256 `e1312b8721514ba57825c0eadf645c27e8957bea46e77166ef45e41044156faf` (literatürdeki değerler; toplamayla doğrulandı)

### E-12 · Eşleştirilmiş t, a priori örneği
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** dz = 0.5, α = 0.05, 1−β = 0.80, iki yönlü → N = 34, kritik t = 2.0345153, güç 0.8077775.
- **Dosya:** `noncentra/reference/t_tests_harvested.csv` (satır `h109_paired_a_priori`)

### E-13 · Eşit olmayan grup oranında G*Power'ın yuvarlama kuralı belirlenemedi
- **Etiket:** [GUI] · **Durum:** kısmen
- **İddia:** Grup oranı 1'den farklıyken (a priori) 23 durumda G*Power'ın grup büyüklükleri Noncentra'nınkinden ±1 farklıdır.
  - Denenen tam sayı arama kurallarının (N veya n1 üzerinden × floor/ceil/round) en iyisi 63 durumdan 24'ünü açıklar.
  - 9 durum tek bir kesirli N* çözümüyle tutarlı değildir.
  - Kesin kural ikili dosyayı okumadan belirlenemez; bu iş için Ghidra gerekir ve henüz yapılmadı.
- **Dosya:** `noncentra/reference/t_tests_ratio_harvested.csv` ve `t_tests_harvested.csv` (`known_divergence` sütunu dolu satırlar; ör. `h146_two_sample_a_priori`: G*Power 43+127, Noncentra 43+128)

### E-14 · G*Power bazı a priori sonuçlarda kendi hedef gücünü tutturamıyor
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** 5 durumda G*Power'ın önerdiği N'nin gerçek gücü, istenen gücün altındadır. Örnek: oran 2.5, d = 0.5, hedef 0.90 → 59+149, gerçek güç 0.8989162.
- **Dosya:** `noncentra/reference/t_tests_ratio_harvested.csv` (satırlar `h201`, `h206`, `h207`, `h221`, `h231`)

### E-15 · F testi toplaması
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** Tek yönlü ANOVA, R² sıfırdan sapma ve R² artışı için 198 durum toplandı. Hepsi Noncentra ile 1e-6 içinde aynıdır.
- **Dosya:** `noncentra/reference/f_tests_harvested.csv` · SHA-256 `c943ded86487ef7912a8c42e171e11b83e7ddb5ab1fb365b5a50085693222be9`
- **Örnekler:** `h094_regression_r2_a_priori` (p = 3, f² = 0.15), `h182_regression_r2_increase_a_priori` (p = 10, q = 4, f² = 0.15)
- **Yeniden üretim:** G*Power açıkken `python teardown/harvest.py <pid> out.csv f`

### E-16 · ANOVA a priori'de N grup sayısının katına yuvarlanır
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** f = 0.25, k = 3, α = 0.05, 1−β = 0.80 → N = 159, λ = 9.9375, kritik F = 3.0540042, güç 0.8048873. Kesirli çözüm 158 verir; G*Power bunu eşit gruplar için 3'ün katına (159) yuvarlar.
- **Dosya:** `noncentra/reference/f_tests_harvested.csv` (satır `h028_anova_oneway_a_priori`)

### E-17 · ANOVA'da N grup sayısının katı değilse uyarı verilir ama hesap aynıdır
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** Post hoc, sensitivity ve compromise analizlerinde N, k'nin katı değilse G*Power "analysis was based on the average group size" uyarısını gösterir. Hesap yine λ = f²·N ile yapılır. Aynı N için criterion analizinde uyarı çıkmaz.
- **Dosya:** `noncentra/reference/f_tests_harvested.csv` (satırlar `h035`, `h037`, `h041`, `h043`, `h056`, `h058`, `h060`, `h062`; `raw` sütununda `_dialog`)
- **Dosya (yerel):** `teardown/evidence/strings_all.txt` (satır 2312 `) is not a multiple of`)

### E-18 · Eşleştirilmiş t sınır durumları (erva)
- **Etiket:** [GUI] · **Durum:** doğrulandı
- **İddia:** 55 sınır durumunun 39'u 1e-6 içinde aynıdır. 16'sı bilinen farktır:
  - **B1:** N < 3 reddi.
  - **B2:** güç < α reddi.
  - **B3:** kesirli N yuvarlaması.
  - **B5:** negatif dz'de tek yönlü testte sol kuyruğa geçiş.
- **Dosya:** `oracle/t-paired/boundary_harvest.csv` · SHA-256 `8a57ebf3ec7ed60a1e9ce687c9ffa7ee24934973003c54d1d03260a606b378ce`
- **Dosya:** `docs/t-paired-validation.md`
- **Yeniden üretim:** `python teardown/harvest_paired.py <pid> out.csv <ekran_klasörü>`

## C · Literatür

### E-19 · t testleri için merkezdışılık ve serbestlik derecesi
- **Etiket:** [DOK] · **Durum:** doğrulandı (E-10 ile)
- **İddia:**
  - İki bağımsız grup: δ = d·√(n1·n2/(n1+n2)), df = n1+n2−2.
  - Tek örneklem ve eşleştirilmiş: δ = d·√N, df = N−1.
  - Güç, merkezi olmayan t dağılımının kritik değeri aşan kısmıdır (iki yönlüde iki kuyruk).
- **Kaynak:** Faul, Erdfelder, Lang ve Buchner (2007), *Behavior Research Methods* 39, 175–191; Cohen (1988), *Statistical Power Analysis for the Behavioral Sciences*.

### E-20 · F testleri için merkezdışılık ve serbestlik derecesi
- **Etiket:** [DOK] · **Durum:** doğrulandı (E-15 ile)
- **İddia:** Üç testte de λ = f²·N.
  - Tek yönlü ANOVA: df = (k−1, N−k); burada f etki büyüklüğüdür, λ = f²·N.
  - R² sıfırdan sapma: df = (p, N−p−1); burada etki büyüklüğü f²'dir, λ = f²·N.
  - R² artışı: df = (q, N−p−1).
- **Kaynak:** Faul, Erdfelder, Buchner ve Lang (2009), *Behavior Research Methods* 41, 1149–1160; Cohen (1988).

## D · Kütüphane davranışı

### E-21 · scipy 1.15'te `nct.cdf` bazı uç kuyruklarda NaN döndürüyor
- **Etiket:** [ÖLÇÜM] · **Durum:** doğrulandı
- **İddia:** `scipy.stats.nct.cdf(-1.6, 173, 15)` NaN döndürür. Yansıma özdeşliği P(T ≤ x | δ) = P(T ≥ −x | −δ) aynı noktada değer verir; 6×361×6'lık bir taramada en az bir yol her zaman tanımlıdır.
- **Yeniden üretim:** `python -c "from scipy import stats; print(stats.nct.cdf(-1.6,173,15), stats.nct.sf(1.6,173,-15))"`

### E-22 · scipy 1.15'te `ncf.sf`, merkezdışılık 0 iken negatif değer döndürüyor
- **Etiket:** [ÖLÇÜM] · **Durum:** doğrulandı
- **İddia:** `scipy.stats.ncf.sf(1, 1, 2, 0)` sonucu −0.577'dir (doğrusu 0.42). Merkezdışılık sıfırdan büyükken hata yoktur (24108 noktalık tarama).
- **Yeniden üretim:** `python -c "from scipy import stats; print(stats.ncf.sf(1,1,2,0), stats.f.sf(1,1,2))"`

### E-23 · statsmodels `FTestPower` sd argümanları ters
- **Etiket:** [ÖLÇÜM] · **Durum:** doğrulandı
- **İddia:** `FTestPower` ile regresyon gücü yanlış (α'ya yakın) çıkar. Doğru sonuç `FTestPowerF2` ile alınır. Çapraz kontrolde (E-26) `FTestPowerF2` kullanılır.
- **Yeniden üretim:** `noncentra/difftest.py` → `statsmodels_cases`

### E-24 · `t.isf` çok küçük olasılıklarda −inf döndürebiliyor
- **Etiket:** [ÖLÇÜM] · **Durum:** kısmen
- **İddia:** erva'ya göre scipy 1.18'de `t.isf(1e-300, 11)` −inf döndürüyor ve bu, eşleştirilmiş compromise satırlarını (`h134`, `h137`) bozuyor. scipy 1.15.3'te aynı çağrı 4.86e27 döndürür, yani hata bu sürümde yeniden üretilemedi. Düzeltme (`t_crit`) her iki sürümde de zararsızdır.
- **Dosya:** `docs/t-paired-validation.md` ("Motor düzeltmesi" bölümü)

### E-25 · statsmodels da aynı nct hatasından etkileniyor
- **Etiket:** [ÖLÇÜM] · **Durum:** doğrulandı
- **İddia:** statsmodels çapraz kontrol ızgarasında 2 durumda NaN döndürür (scipy nct hatası, E-21). Fark raporu bunları "referans tanımsız" diye ayrı sayar.
- **Yeniden üretim:** `python -m noncentra diff --json` → `reference_nan: 2`

## E · Bağımsız çapraz kontrol ve kendi ölçümlerimiz

### E-26 · statsmodels ile çapraz kontrol
- **Etiket:** [ÖLÇÜM] · **Durum:** doğrulandı
- **İddia:** Bağımsız bir uygulamayla (statsmodels) 254 post hoc durumunun hepsi 1e-4 içinde uyuşur. Durumlar: iki örneklemli ve tek örneklemli t, tek yönlü ANOVA ve R² testi.
- **Yeniden üretim:** `python -m noncentra diff --json`

### E-27 · Sunucu ve tarayıcı motorları aynı sonucu verir
- **Etiket:** [ÖLÇÜM] · **Durum:** doğrulandı
- **İddia:** 6 test × 5 analiz = 30 istekte örneklem büyüklükleri aynıdır. Kritik değerlerdeki en büyük fark 2.1e-9'dur (Pyodide scipy 1.12, sunucu scipy 1.15).
- **Dosya:** `docs/web-and-api.md` ("Doğrulama" bölümü)

### E-28 · Hesap motorunun ikili kodu okunmadı
- **Etiket:** [REA] · **Durum:** açık
- **İddia:** REA'nın disassembly sağlayıcıları (Ghidra, IDA) bu makinede kurulu değildi. G*Power'ın hesap fonksiyonlarının yeri ve algoritması kod düzeyinde belirlenmedi. Mevcut kanıtlar yalnızca dizeler, adresler ve girdi-çıktı gözlemidir. Bu, E-13'ü çözmek için gereken eksik adımdır.
- **Dosya:** `docs/teardown-report.md` ("Sayısal çekirdek" bölümü)
