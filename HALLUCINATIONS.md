# Halüsinasyon günlüğü

Ajanın (Claude, inceleme oturumu) kendinden emin biçimde söylediği ama yanlış çıkan şeyler. Her kayıtta
iddianın ne olduğu, nasıl fark edildiği ve onu hangi testin yakaladığı ya da bundan sonra yakalayacağı yazıyor.
Kimlikler [LEDGER.md](LEDGER.md) kayıtlarına bağlıdır.

Ortak ders: Bu yanlışların hiçbiri hesap kodu okunarak bulunmadı. Hepsini G*Power'ın kendisine ya da bağımsız
bir uygulamaya karşı yapılan diferansiyel test buldu. Ödevdeki ipucunu doğruluyor: "Bunun kanıtı hangi
fonksiyonda?" sorusuna cevap verilemeyen her satır sınanana kadar [AJAN] sayılmalı.

## H-01 · Eşit olmayan grup oranında yuvarlama kuralı ve uydurulmuş gözlem (ciddi)

- **İddia:** Kodda şu yorum vardı: *"Observed in G*Power 3.1.9.7 (teardown harvest, ratio 3 -> 43/127): every
  group is rounded up from the continuous solution separately."* Yani "G*Power her grubu ayrı yukarı yuvarlar"
  ve "bu, oran 3 örneğinde gözlendi".
- **Gerçek:** Bu kural aynı örnekte 43 + **128** verir, G*Power ise 43 + **127** veriyor. Yorum, kendi kanıtıyla
  çelişen bir "gözlem" uydurmuştu. 63 eşit olmayan oran vakasından 23'ünde kural tutmuyor ve G*Power'ın gerçek
  kuralı hâlâ belirlenemedi (LEDGER: eşit olmayan oran kaydı).
- **Nasıl fark edildi:** Toplanan G*Power değerleriyle yapılan diferansiyel test, `h146_two_sample_a_priori`
  satırında `n2: got 128, want 127` hatası verdi. Ajan sonradan yorumu düzeltmedi, sadece kuralı "bilinen fark"
  diye işaretledi; bu da ayrıca bir eksiklik.
- **Yakalayan test:** `tests/test_regression.py::test_reference_row[h146_two_sample_a_priori]`, şimdi de
  `tests/contract/test_public_vectors.py::test_gpower_vector` (bu satırlar `note` ile xfail).

## H-02 · ANOVA a priori N, t testindeki gibi yuvarlanır

- **İddia:** Tek yönlü ANOVA'da gerekli N, kesirli çözümün yukarı yuvarlanmasıdır: f = 0.25, k = 3, güç 0.80 → **158**.
- **Gerçek:** G*Power **159** veriyor. N'yi grup sayısının katına yuvarlıyor, yani gruplar eşit oluyor.
- **Nasıl fark edildi:** Ajan "G*Power'da 159 olduğunu hatırlıyorum" dedi ama hesabı 158'de bıraktı. Canlı
  G*Power çalıştırılınca 159 görüldü ve kural koda eklendi.
- **Yakalayan test:** `tests/test_regression.py::test_reference_row[h028_anova_oneway_a_priori]`,
  `tests/test_http_api.py::test_analyze_matches_core` (`n_total == 159`), açık vektör `anova-oneway/a-priori`
  (N = 305 = 5 × 61).

## H-03 · "En küçük N = 2"

- **İddia:** Motordaki `TestModel.min_n = 2` varsayımı: post hoc ve sensitivity N = 2'yi kabul eder.
- **Gerçek:** G*Power bu modlarda N < 3'ü "Total sample size is outside the admissible range (3, 2147483646)"
  hatasıyla reddediyor. A priori ise N = 2 önerebiliyor (`oracle/t-paired/boundary_harvest.csv` p010, p012).
- **Nasıl fark edildi:** erva'nın sınır değer toplaması (p029, p030, p047), ekran görüntüsüyle.
- **Yakalayan test:** `tests/test_paired_boundary.py::test_paired_boundary[p029_post_hoc]` (katı xfail),
  `oracle/gpower_vectors.jsonl` içindeki hata beklenen satırlar.

## H-04 · "Negatif etki büyüklüğü simetriktir"

- **İddia:** Etki büyüklüğünün işareti önemsizdir; dz = −0.5 ile dz = 0.5 aynı gücü verir.
- **Gerçek:** İki kuyrukta doğru. Tek kuyrukta G*Power testi sol kuyruğa çeviriyor: kritik t = −1.7291328,
  güç 0.6951493. Motor sağ kuyruğu kullanıp 7.1e-05 buluyor.
- **Nasıl fark edildi:** erva'nın p045 vakası. CONTRACT.md'de dz > 0 olduğu için sözleşme katmanında bu girdi
  zaten OUT_OF_RANGE olmalı.
- **Yakalayan test:** `tests/test_paired_boundary.py::test_paired_boundary[p045_post_hoc]`.

## H-05 · statsmodels `FTestPower` regresyon için doğrudan kullanılabilir

- **İddia:** Bağımsız çapraz kontrolde regresyon gücü `FTestPower.power(effect_size=√f², df_num=p, df_denom=N−p−1)`
  ile hesaplanır.
- **Gerçek:** Bu sınıfın serbestlik derecesi argümanları adlarının tersine çalışıyor. Sonuçlar α'ya yakın
  çıktı (ör. 0.0101 yerine 0.0193). Doğrusu `FTestPowerF2`.
- **Nasıl fark edildi:** Çapraz kontrolde 54 durum birden başarısız oldu. Bu, motorun değil karşılaştırma
  aracının hatasıydı.
- **Yakalayan test:** `tests/test_differential.py::test_matches_statsmodels` (`sm_reg_*` satırları).

## H-06 · "G*Power muhtemelen Delphi / C++Builder ile yazılmış"

- **İddia:** İlk planda ajan, çatıyı "büyük ihtimalle Delphi/C++Builder" diye tahmin etti.
- **Gerçek:** Program `mfc140u.dll`'e bağlı bir MFC/C++ uygulaması. Visual Studio 2022 linker 14.36 ile derlenmiş.
- **Nasıl fark edildi:** `objdump -p` import tablosu ve PE kaynakları (LEDGER: PE başlığı ve MFC kayıtları).
  Bu yanlışı bir test değil statik kanıt yakaladı. Tahmin hiçbir koda girmediği için zarar vermedi, ama
  kanıtsız bir cümlenin ne kadar kolay kurulduğunu gösteriyor.
- **Yakalayan:** statik inceleme (test yok).

## Açık şüpheler (henüz kanıtlanmadı, [AJAN])

- G*Power'ın a priori çözücüsünün durma koşulu (iterasyon toleransı). Eşit olmayan oranda gözlenen ±1 farklarının
  nedeni bu olabilir; kanıt için Ghidra'da çözücünün bulunması gerekiyor.
- Eşleştirilmiş compromise satırlarında scipy 1.18'in `t.isf` alt taşması (erva). scipy 1.15'te yeniden
  üretilemedi (LEDGER).
