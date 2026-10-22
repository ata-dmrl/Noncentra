# Diferansiyel test raporu: eşleştirilmiş t testi (`t-paired`)

Üretildi: 2026-10-22, `python -m noncentra.difftest_paired --report tests/T_PAIRED_DIFF_REPORT.md`.
Bütün vakalar teslim edilen arayüzden (`contract.run`, yani `gpower-clone`) geçirildi.
Tolerans CONTRACT.md §6: tam sayılar tam eşleşme, ondalıklar 1e-6 mutlak ya da göreli.

## Özet

| Kâhin | Kaynak | Vaka | Eşleşen | Açıklanmış fark | Açıklanmamış fark | Uyum |
|---|---|---:|---:|---:|---:|---:|
| G*Power 3.1.9.7 | `t_tests_harvested.csv` | 48 | 48 | 0 | 0 | 48/48 (100.0%) |
| G*Power 3.1.9.7 | `t_tests.csv` | 1 | 1 | 0 | 0 | 1/1 (100.0%) |
| G*Power 3.1.9.7 | `boundary_harvest.csv` | 55 | 44 | 11 | 0 | 55/55 (100.0%) |
| G*Power 3.1.9.7 | `public_vectors.jsonl` | 5 | 5 | 0 | 0 | 5/5 (100.0%) |
| statsmodels | `statsmodels` | 780 | 750 | 30 | 0 | 780/780 (100.0%) |

- Toplam: 109 G*Power vakası, 780 statsmodels vakası. Açıklanmamış fark: **0**.
- G*Power a priori vakaları: **52/53** eşleşme (N tam aynı ya da G*Power'ın reddettiği girdide bizim de hata vermemiz). Kalan 1 vaka sözleşmenin reddettiği girdi; "Açıklanmış farklar" tablosunda.

## Açıklanmış farklar

G*Power'ın kabul ettiği ama CONTRACT.md §5'in yasakladığı girdiler. Düzenek bizim JSON'umuzu okuduğu için
sözleşme kazanır; beklenen yanıt hatadır. Motor bu davranışları ayrıca belgeliyor
(`docs/t-paired-validation.md`, B3 ve B5).

| Vaka | Girdi | Neden | Bizim yanıt |
|---|---|---|---|
| `p023_a_priori` | mode=a-priori, tails=2, dz=-0.5, alpha=0.05, power=0.8 | G*Power dz < 0'ı kabul ediyor (tek kuyrukta sol kuyruğa geçiyor); CONTRACT.md §5 dz > 0 istiyor | `OUT_OF_RANGE` |
| `p033_post_hoc` | mode=post-hoc, tails=1, dz=0.5, alpha=0.05, n_total=2.5 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p034_post_hoc` | mode=post-hoc, tails=2, dz=0.5, alpha=0.05, n_total=2.5 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p035_post_hoc` | mode=post-hoc, tails=2, dz=0.5, alpha=0.05, n_total=3.4 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p036_post_hoc` | mode=post-hoc, tails=2, dz=0.5, alpha=0.05, n_total=3.5 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p037_post_hoc` | mode=post-hoc, tails=2, dz=0.5, alpha=0.05, n_total=3.6 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p038_post_hoc` | mode=post-hoc, tails=2, dz=0.5, alpha=0.05, n_total=10.2 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p039_post_hoc` | mode=post-hoc, tails=2, dz=0.5, alpha=0.05, n_total=10.5 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p040_post_hoc` | mode=post-hoc, tails=2, dz=0.5, alpha=0.05, n_total=10.7 | G*Power kesirli N'yi en yakın tam sayıya yuvarlıyor (3.4 → 3, 3.5 → 4); CONTRACT.md §5'te n_total tam sayı | `INVALID_VALUE` |
| `p044_post_hoc` | mode=post-hoc, tails=2, dz=-0.5, alpha=0.05, n_total=20 | G*Power dz < 0'ı kabul ediyor (tek kuyrukta sol kuyruğa geçiyor); CONTRACT.md §5 dz > 0 istiyor | `OUT_OF_RANGE` |
| `p045_post_hoc` | mode=post-hoc, tails=1, dz=-0.5, alpha=0.05, n_total=20 | G*Power dz < 0'ı kabul ediyor (tek kuyrukta sol kuyruğa geçiyor); CONTRACT.md §5 dz > 0 istiyor | `OUT_OF_RANGE` |

## G*Power'ın reddettiği girdiler

G*Power bir uyarı kutusu gösterdi; bizim de hata döndürmemiz beklenir.

| Vaka | G*Power mesajı → bizim kod |
|---|---|
| `p016_a_priori` | Power must be greater than or equal to alpha. → bizim: INCONSISTENT |
| `p021_a_priori` | Power must be greater than or equal to alpha. → bizim: INCONSISTENT |
| `p022_a_priori` | In an a priori analysis, the absolute value of the effect size be greater than 0.00001. → bizim: OUT_OF_RANGE |
| `p024_a_priori` | Alpha is outside the admissible range (1e-07, 1). → bizim: OUT_OF_RANGE |
| `p025_a_priori` | Alpha is outside the admissible range (1e-07, 1). → bizim: OUT_OF_RANGE |
| `p026_a_priori` | Power is outside the admissible range (1e-07, 1). → bizim: OUT_OF_RANGE |
| `p027_post_hoc` | Total sample size is outside the admissible range (3, 2147483646) → bizim: OUT_OF_RANGE |
| `p028_post_hoc` | Total sample size is outside the admissible range (3, 2147483646) → bizim: OUT_OF_RANGE |
| `p029_post_hoc` | Total sample size is outside the admissible range (3, 2147483646) → bizim: OUT_OF_RANGE |
| `p030_post_hoc` | Total sample size is outside the admissible range (3, 2147483646) → bizim: OUT_OF_RANGE |
| `p047_sensitivity` | Total sample size is outside the admissible range (3, 2147483646) → bizim: OUT_OF_RANGE |
| `p048_sensitivity` | Power must be greater than or equal to alpha. → bizim: INCONSISTENT |

## Bulgu: kütüphaneler N'yi kesirli verir, G*Power yukarı yuvarlar

statsmodels `solve_power` 180 a priori vakanın hepsinde kesirli N döndürdü. Bizim N (ve G*Power'ın N'i)
hedef güce ulaşan en küçük tam sayıdır, yani ⌈N⌉. G*Power vektörlerinin hepsi bu kuralla tutuyor.
Sıradan yuvarlama (round) 91/180 vakada eksik N verirdi, yani istenen güce ulaşılamazdı. Örnekler:

| Vaka | statsmodels N | round | ⌈N⌉ = bizim |
|---|---:|---:|---:|
| `sm_ap_t1_dz0.1_a0.01_p0.8` | 1006.3106 | 1006 | 1007 |
| `sm_ap_t1_dz0.1_a0.01_p0.9` | 1304.4015 | 1304 | 1305 |
| `sm_ap_t1_dz0.1_a0.1_p0.95` | 857.2072 | 857 | 858 |
| `sm_ap_t1_dz0.2_a0.01_p0.9` | 328.1364 | 328 | 329 |
| `sm_ap_t1_dz0.2_a0.05_p0.9` | 215.4562 | 215 | 216 |
| `sm_ap_t1_dz0.2_a0.1_p0.9` | 165.0649 | 165 | 166 |
| `sm_ap_t1_dz0.3_a0.01_p0.8` | 114.2332 | 114 | 115 |
| `sm_ap_t1_dz0.3_a0.01_p0.9` | 147.3540 | 147 | 148 |

## Bulgu: statsmodels iki kuyruklu güçte NaN döndürüyor

30 post hoc vakada (hepsi iki kuyruklu, güç ≈ 1) statsmodels NaN döndürdü:
scipy'nin `nct.cdf` fonksiyonu alt kuyrukta hesap yapamıyor. Motorumuz aynı hatayı yansıma özdeşliğiyle
aşıyor (`core/distributions.py`, `nct_cdf`). Bu vakalar statsmodels'ın üst kuyruk gücüyle (tek kuyruk, α/2)
yine 1e-6 içinde karşılaştırıldı; alt kuyruğun katkısı burada 1e-6'nın çok altında. Tabloda "açıklanmış" olarak sayılıyorlar.

Post hoc vakalarında statsmodels ile fark 1e-6'nın çok altında, çünkü iki uygulama da merkezi olmayan
t dağılımını aynı tanımla (iki kuyrukta iki kuyruğun da katkısı) hesaplıyor. Ancak statsmodels G*Power değil:
N ≥ 3 sınırı, güç < α reddi ve |dz| > 0.00001 eşiği yalnızca G*Power vektörleriyle sınanabilir.
