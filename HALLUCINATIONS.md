# HALLUCINATIONS.md — Ajanın yanlış çıkardıkları

Her madde: ajan ne dedi, gerçek ne, nasıl fark edildi, hangi test yakaladı. "Ajan" burada kodu ve belgeleri yazan
AI oturumları ve araç zincirindeki AI bileşenleri demek.

---

## H1. "En küçük N her analizde 2"

- **Ajanın iddiası:** Eşleştirilmiş t testinde df = N − 1 ≥ 1 olması yeterli, yani en küçük N her analiz türünde 2.
  Kodda `TestModel.min_n = 2` olarak yazıldı ve bütün modlar için kullanıldı.
- **Gerçek:** G*Power N bir girdi olduğunda (post hoc, sensitivity) N < 3'ü reddediyor: "Total sample size is outside
  the admissible range (3, 2147483646)". Ama a priori'de kendisi N = 2 önerebiliyor. Yani tek bir sınır yok, iki sınır var.
- **Nasıl fark edildi:** Sınır vektörü toplanırken N = 1 ve N = 2 bilinçli olarak denendi. G*Power uyarı kutusu çıkardı (ekran görüntüsü
  `oracle/t-paired/screenshots/p029_post_hoc_dialog0.png`). Binary'de mesaj dizesi bulundu (LEDGER B1, `0x005C6524`).
- **Yakalayan test:** `tests/test_paired_boundary.py::test_paired_boundary[p029_post_hoc]` (ve p027, p028, p030, p047).
  Düzeltmeden sonra: `tests/test_gpower_clone.py::test_error[post-hoc N=2]`, SPEC.md "G*Power'ın reddettiği girdiler" tablosu.
- **Ders:** Matematiksel olarak geçerli olan, G*Power'ın kabul ettiğiyle aynı şey değil. Sınırlar kâhinden okunur.

## H2. "Negatif etki büyüklüğü simetriktir, yalnızca mutlak değeri önemli"

- **Ajanın iddiası:** dz'nin işareti sonucu etkilemez; |dz| ile hesaplamak yeterli.
- **Gerçek:** İki kuyrukta doğru (dz = −0.5 de N = 34 veriyor), ama G*Power kritik t'yi negatif gösteriyor (−2.0345153, p023).
  Tek kuyrukta yanlış: dz = −0.5 testi sol kuyruğa çeviriyor; güç 0.6951493 (p045). Motor sağ kuyruğu kullanıp 7.1e-05 buldu.
- **Nasıl fark edildi:** Sınır vektörlerine "geçersiz olması beklenen" girdi olarak dz = −0.5 eklendi; G*Power hata vermedi,
  başka bir sonuç verdi.
- **Yakalayan test:** `tests/test_paired_boundary.py::test_paired_boundary[p045_post_hoc]` (xfail, nedeni yazılı).
  Sözleşme dz > 0 istediği için arayüzde `OUT_OF_RANGE` dönüyor: `tests/test_gpower_clone.py::test_error[dz negative]`.

## H3. "Eşit olmayan oranda her grup ayrı ayrı yukarı yuvarlanır" (t2-indep; aynı motor)

- **Ajanın iddiası:** n1 = ⌈n1*⌉, n2 = ⌈n1*·oran⌉; bu "G*Power'ın kuralı" diye koda yorum olarak yazıldı
  (`catalog/base.py`, `round_sizes`).
- **Gerçek:** Eşit oranda doğru (27/27), oran ≠ 1 olan 23 a priori vakada grup büyüklükleri ±1 farklı. Denenen 6 kuralın
  hiçbiri hepsini açıklamıyor; G*Power'ın önerdiği N, bu vakaların 5'inde istenen gücü sağlamıyor bile.
- **Nasıl fark edildi:** `noncentra/reference/t_tests_ratio_harvested.csv` ile diferansiyel test.
- **Yakalayan test:** `noncentra diff` (difftest.py), satırlar `known_divergence` ile işaretli. Kendi ailemiz (t-paired) tek
  gruplu olduğu için bu kural bizi etkilemiyor, ama aynı motoru paylaşan K1 takımı için önemli.

## H4. Araç özeti sözleşmeye olmayan bir kural ekledi: "n_total çift sayı olmalı"

- **Ajanın iddiası:** CONTRACT.md bağlantısı web özetleyici araçla okunduğunda özet şunu söyledi: *"n_total: integer ≥ 2
  (the spec also describes it as the total pair count, which should be even)"*.
- **Gerçek:** CONTRACT.md'de böyle bir kural yok. "Çift sayısı" (pair count) ifadesi yanlışlıkla "çift (even) sayı"ya
  çevrilmiş. Bu kural uygulansaydı tek N'li bütün vektörler (ör. açık vektör N = 45) reddedilirdi ve kapı kaçardı.
- **Nasıl fark edildi:** Kodlamadan önce sözleşmenin tam metni (öğrencinin eklediği dosya) satır satır okundu; özet ile
  karşılaştırıldı.
- **Yakalayan test:** Hiçbiri; kural koda girmeden yakalandı. Girseydi `tests/test_gpower_clone.py::test_public_vector[t-paired/a-priori]`
  (N = 45) ve `tests/test_spec.py` hemen düşerdi.
- **Ders:** Sözleşmeyi özetten değil, kaynağın kendisinden uygulamak. Özetleyici model kendinden emin cümle kurar.

## H5. "scipy'nin kritik değeri her α için sonludur"

- **Ajanın iddiası:** Compromise çözücüsü α'yı 1e-300'e kadar arayabilir; `scipy.stats.t.isf` her zaman büyük pozitif bir sayı döndürür.
- **Gerçek:** scipy 1.18'de `t.isf(1e-300, 11)` **−inf** döndürüyor. β = 0 çıkıyor, aralık bulunamıyor ve compromise çöküyor
  ("beta/alpha ratio not reachable").
- **Nasıl fark edildi:** scipy güncellenince iki G*Power regresyon satırı (h134, h137) düştü.
- **Yakalayan test:** `tests/test_regression.py` / `noncentra diff` (h134, h137). Düzeltme `core/distributions.py::t_crit`.

## Oturum 1'in (ata-dmrl) ek kayıtları

Aşağıdaki üç kayıt beş aileyi kapsayan inceleme oturumundan gelir; ayrıntılı kanıtlar [docs/ledger_all_families.md](docs/ledger_all_families.md).
H3'e ek: o oturumda kod yorumu bu kuralı *"oran 3 → 43/127 gözlendi"* diye yanlış belgelemişti; kural aynı örnekte 43 + 128 verir.

### H6 · ANOVA a priori N, t testindeki gibi yuvarlanır

- **İddia:** Tek yönlü ANOVA'da gerekli N, kesirli çözümün yukarı yuvarlanmasıdır: f = 0.25, k = 3, güç 0.80 → **158**.
- **Gerçek:** G*Power **159** veriyor. N'yi grup sayısının katına yuvarlıyor, yani gruplar eşit oluyor.
- **Nasıl fark edildi:** Ajan "G*Power'da 159 olduğunu hatırlıyorum" dedi ama hesabı 158'de bıraktı. Canlı
  G*Power çalıştırılınca 159 görüldü ve kural koda eklendi.
- **Yakalayan test:** `tests/test_regression.py::test_reference_row[h028_anova_oneway_a_priori]`,
  `tests/test_http_api.py::test_analyze_matches_core` (`n_total == 159`), açık vektör `anova-oneway/a-priori`
  (N = 305 = 5 × 61).

### H7 · statsmodels `FTestPower` regresyon için doğrudan kullanılabilir

- **İddia:** Bağımsız çapraz kontrolde regresyon gücü `FTestPower.power(effect_size=√f², df_num=p, df_denom=N−p−1)`
  ile hesaplanır.
- **Gerçek:** Bu sınıfın serbestlik derecesi argümanları adlarının tersine çalışıyor. Sonuçlar α'ya yakın
  çıktı (ör. 0.0101 yerine 0.0193). Doğrusu `FTestPowerF2`.
- **Nasıl fark edildi:** Çapraz kontrolde 54 durum birden başarısız oldu. Bu, motorun değil karşılaştırma
  aracının hatasıydı.
- **Yakalayan test:** `tests/test_differential.py::test_matches_statsmodels` (`sm_reg_*` satırları).

### H8 · "G*Power muhtemelen Delphi / C++Builder ile yazılmış"

- **İddia:** İlk planda ajan, çatıyı "büyük ihtimalle Delphi/C++Builder" diye tahmin etti.
- **Gerçek:** Program `mfc140u.dll`'e bağlı bir MFC/C++ uygulaması. Visual Studio 2022 linker 14.36 ile derlenmiş.
- **Nasıl fark edildi:** `objdump -p` import tablosu ve PE kaynakları (LEDGER: PE başlığı ve MFC kayıtları).
  Bu yanlışı bir test değil statik kanıt yakaladı. Tahmin hiçbir koda girmediği için zarar vermedi, ama
  kanıtsız bir cümlenin ne kadar kolay kurulduğunu gösteriyor.
- **Yakalayan:** statik inceleme (test yok).

