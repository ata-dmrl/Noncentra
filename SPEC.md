# SPEC.md — Eşleştirilmiş t testi (`t-paired`) güç analizi

**Kapsam:** G*Power 3.1.9.7'deki *t tests – Means: Difference between two dependent means (matched pairs)*
hesabının davranışı. Klinik örnek: aynı hastalarda tedavi öncesi ve sonrası tansiyon.
**Arayüz:** [CONTRACT.md](CONTRACT.md) 1.0.0 (`gpower-clone`). Bu belge arayüzü tekrar etmez, davranışı tanımlar.
**Kaynak:** Her kural bir kanıta bağlıdır; etiketler [LEDGER.md](LEDGER.md) ile aynıdır.
Beklenen değerlerin hepsi G*Power 3.1.9.7 ekranından alınmıştır (`oracle/`, `noncentra/reference/`).

> Temiz oda notu: Bu belge yazım oturumunun **tek** girdisidir. Kod, decompile çıktısı ya da adres içermez.
> Yazım oturumu ayrıca CONTRACT.md'yi okuyabilir.

---

## 1. Model

| Sembol | Anlamı | Kaynak |
|---|---|---|
| `N` | Çift sayısı (`n_total`) | [DOK] |
| `dz` | Farkların standartlaştırılmış ortalaması: μ_fark / σ_fark | [DOK] |
| `df` | N − 1 | [DOK] |
| `δ` (`ncp`) | dz · √N | [DOK] |
| `T` | Serbestlik derecesi df, merkezdışılık δ olan merkezi olmayan t değişkeni | [DOK] |

Hesap, farklar üzerinde tek örneklem t testidir. Etki büyüklüğünü ortalamalardan ve SD'lerden hesaplama
("Determine" penceresi) kapsam dışıdır (CONTRACT.md §1).

### 1.1 Kritik değer ve güç

- Tek kuyruk: `critical_t = t⁻¹(1 − α; df)` (merkezi t'nin üst α niceliği).
  `power = P(T > critical_t)`.
- Çift kuyruk: `critical_t = t⁻¹(1 − α/2; df)`.
  `power = P(T > critical_t) + P(T < −critical_t)`. **İki kuyruğun katkısı da toplanır.** [DOK] [AJAN-doğrulandı: 48/48 ızgara vektörü]
- `beta = 1 − power`. Güç 1'e çok yakınken β, 1 − güç farkından değil kendi kuyruğundan hesaplanmalıdır
  (compromise analizi β'ya böler).

### 1.2 Analiz türleri

| `mode` | Verilen | Hesaplanan |
|---|---|---|
| `a-priori` | tails, dz, α, güç | N (+ gerçek güç) |
| `post-hoc` | tails, dz, α, N | güç |
| `compromise` | tails, dz, β/α oranı, N | α, β, güç (β = oran · α) |
| `criterion` | tails, dz, güç, N | α |
| `sensitivity` | tails, α, güç, N | dz (pozitif yön) |

### 1.3 A priori N kuralı

N, `power(N) ≥ hedef güç` koşulunu sağlayan **en küçük tam sayıdır**. Çözüm sürekli N* için bulunup
**yukarı** yuvarlanır (⌈N*⌉); sıradan yuvarlama değildir. Arama alt sınırı **2**'dir: N = 2 bile hedefi
aşıyorsa sonuç 2'dir. [AJAN-doğrulandı: 53 G*Power a priori vektörü; statsmodels'ın kesirli N'i ile 180/180]

`actual_power`, bulunan tam sayı N'deki güçtür.

---

## 2. Girdi kabul kuralları (G*Power'ın davranışı)

CONTRACT.md §5'teki aralıklar önce uygulanır. Aralığın içinde G*Power'ın ayrıca reddettikleri:

| Kural | Kod | Kanıt |
|---|---|---|
| α ve güç **[1e-07, 1)** aralığında olmalı. 1e-07 kabul edilir; mesaj "(1e-07, 1)" yazsa da alt sınır dahildir. | `OUT_OF_RANGE` | [REA] B4 |
| Güç < α ise reddedilir (a priori ve sensitivity). Güç = α kabul edilir. | `INCONSISTENT` | [REA] B2 |
| A priori'de \|dz\| ≤ 0.00001 reddedilir. | `OUT_OF_RANGE` | [REA] B5 |
| N bir **girdi** ise (post-hoc, compromise, criterion, sensitivity) N ≥ 3 olmalı. A priori ise N = 2 **döndürebilir**. | `OUT_OF_RANGE` | [REA] B1 |
| Kesirli N: G*Power en yakın tam sayıya yuvarlar (.5 yukarı). Sözleşmede `n_total` tam sayı olduğu için reddedilir. | `INVALID_VALUE` | [REA] B3 |
| dz ≤ 0: G*Power negatif dz'yi kabul eder, tek kuyrukta sol kuyruğa geçer. Sözleşme dz > 0 istediği için reddedilir. | `OUT_OF_RANGE` | [REA] B5 |

Doğrulama sırası: test/mod → tanınmayan alan → eksik alan → tür → CONTRACT.md §5 aralığı → bu tablo.

---

## 3. Kabul kriterleri (Gherkin)

Tablolardaki ondalıklar G*Power'ın gösterdiği 7 basamaktır. Karşılaştırma CONTRACT.md §6'ya göre yapılır:
tam sayılar (`n_total`, `df`) tam eşleşir; ondalıklar 1e-6 mutlak ya da göreli fark içinde kalır.
`tests/test_spec.py` bu dosyadaki her `Examples` tablosunu okuyup `gpower-clone` ile çalıştırır.

```gherkin
Özellik: Eşleştirilmiş t testi güç analizi
  Bir klinik araştırmacı olarak
  önce-sonra tasarımında kaç hasta gerektiğini ve elimdeki örneklemin gücünü
  G*Power ile aynı sonuçla, bir komutla hesaplamak istiyorum.

  Geçmiş:
    Diyelim ki test "t-paired"

  Senaryo Taslağı: A priori gerekli çift sayısı
    Eğer mode "<mode>", tails <tails>, dz <dz>, alpha <alpha>, power <power> verirsem
    O zaman çıkış kodu 0 olur
    Ve n_total <n_total>, df <df>, ncp <ncp>, critical_t <critical_t>, actual_power <actual_power> olur

    Örnekler:
      | mode     | tails | dz  | alpha | power | n_total | df  | ncp       | critical_t | actual_power |
      | a-priori | 1     | 0.5 | 0.05  | 0.95  | 45      | 44  | 3.3541020 | 1.6802300  | 0.9512400    |
      | a-priori | 2     | 0.5 | 0.05  | 0.95  | 54      | 53  | 3.6742346 | 2.0057460  | 0.9502120    |
      | a-priori | 2     | 0.5 | 0.05  | 0.8   | 34      | 33  | 2.9154759 | 2.0345153  | 0.8077775    |
      | a-priori | 1     | 0.2 | 0.01  | 0.8   | 254     | 253 | 3.1874755 | 2.3411771  | 0.8006816    |
      | a-priori | 2     | 0.2 | 0.01  | 0.95  | 449     | 448 | 4.2379240 | 2.5868479  | 0.9501572    |
      | a-priori | 2     | 0.2 | 0.05  | 0.8   | 199     | 198 | 2.8213472 | 1.9720175  | 0.8016910    |
      | a-priori | 1     | 0.8 | 0.05  | 0.8   | 12      | 11  | 2.7712813 | 1.7958848  | 0.8289809    |
      | a-priori | 2     | 0.8 | 0.01  | 0.95  | 32      | 31  | 4.5254834 | 2.7440419  | 0.9556539    |

  Senaryo Taslağı: A priori uç değerler
    Eğer mode "<mode>", tails <tails>, dz <dz>, alpha <alpha>, power <power> verirsem
    O zaman n_total <n_total>, df <df>, critical_t <critical_t>, actual_power <actual_power> olur

    Örnekler:
      | mode     | tails | dz   | alpha | power | n_total | df    | critical_t | actual_power |
      | a-priori | 1     | 0.01 | 0.05  | 0.8   | 61827   | 61826 | 1.6448783  | 0.8000004    |
      | a-priori | 2     | 0.01 | 0.05  | 0.8   | 78491   | 78490 | 1.9599942  | 0.8000024    |
      | a-priori | 2     | 0.05 | 0.05  | 0.8   | 3142    | 3141  | 1.9607195  | 0.8000668    |
      | a-priori | 2     | 0.5  | 0.05  | 0.999 | 104     | 103   | 1.9832641  |              |
      | a-priori | 2     | 0.5  | 0.001 | 0.8   | 74      | 73    | 3.4288542  |              |

  Senaryo Taslağı: Arama alt sınırı N = 2
    # dz çok büyükse ya da güç = alpha ise N = 2 bile yeter; G*Power 2 döndürür.
    Eğer mode "<mode>", tails <tails>, dz <dz>, alpha <alpha>, power <power> verirsem
    O zaman n_total <n_total> ve df <df> olur

    Örnekler:
      | mode     | tails | dz  | alpha | power | n_total | df |
      | a-priori | 1     | 10  | 0.05  | 0.8   | 2       | 1  |
      | a-priori | 2     | 20  | 0.05  | 0.8   | 2       | 1  |
      | a-priori | 2     | 0.5 | 0.05  | 0.05  | 2       | 1  |
      | a-priori | 1     | 0.5 | 0.05  | 0.05  | 2       | 1  |

  Senaryo Taslağı: Post hoc ulaşılan güç
    Eğer mode "<mode>", tails <tails>, dz <dz>, alpha <alpha>, n_total <n_total> verirsem
    O zaman df <df>, ncp <ncp>, critical_t <critical_t>, power <power> olur

    Örnekler:
      | mode     | tails | dz  | alpha | n_total | df | ncp       | critical_t | power     |
      | post-hoc | 1     | 0.5 | 0.05  | 45      | 44 | 3.3541020 | 1.6802300  | 0.9512400 |
      | post-hoc | 1     | 0.3 | 0.05  | 10      | 9  | 0.9486833 | 1.8331129  | 0.2216581 |
      | post-hoc | 2     | 0.3 | 0.05  | 10      | 9  | 0.9486833 | 2.2621572  | 0.1361363 |
      | post-hoc | 2     | 0.7 | 0.05  | 25      | 24 | 3.5000000 | 2.0638986  | 0.9187763 |
      | post-hoc | 2     | 0.7 | 0.05  | 60      | 59 | 5.4221767 | 2.0009954  | 0.9996271 |
      | post-hoc | 2     | 0.5 | 0.05  | 3       | 2  | 0.8660254 | 4.3026527  |           |
      | post-hoc | 2     | 0.5 | 1e-07 | 20      | 19 | 2.2360680 | 8.2809230  |           |

  Senaryo Taslağı: Compromise, criterion ve sensitivity
    Eğer verilen alanlarla "<mode>" çalıştırırsam
    O zaman tablodaki çıktılar G*Power ile eşleşir

    Örnekler:
      | mode        | tails | dz  | alpha | power | beta_alpha_ratio | n_total | df | ncp       | critical_t | out_alpha | out_beta  | out_power | out_dz    |
      | compromise  | 1     | 0.5 |       |       | 1                | 45      | 44 | 3.3541020 | 1.6864315  | 0.0493959 | 0.0493959 | 0.9506041 |           |
      | compromise  | 2     | 0.5 |       |       | 1                | 12      | 11 | 1.7320508 | 1.1500354  | 0.2745180 | 0.2745180 | 0.7254820 |           |
      | compromise  | 1     | 0.5 |       |       | 4                | 45      | 44 | 3.3541020 | 2.0325864  | 0.0240783 | 0.0963131 | 0.9036869 |           |
      | criterion   | 1     | 0.5 |       | 0.95  |                  | 45      | 44 | 3.3541020 | 1.6922637  | 0.0488334 |           |           |           |
      | criterion   | 2     | 0.5 |       | 0.8   |                  | 40      | 39 | 3.1622777 | 2.3074217  | 0.0264263 |           |           |           |
      | sensitivity | 1     |     | 0.05  | 0.95  |                  | 45      | 44 | 3.3417616 | 1.6802300  |           |           |           | 0.4981604 |
      | sensitivity | 2     |     | 0.05  | 0.8   |                  | 40      | 39 | 2.8729731 | 2.0226909  |           |           |           | 0.4542569 |

  Senaryo Taslağı: G*Power'ın reddettiği girdiler hata döndürür
    Eğer tablodaki alanlarla çalıştırırsam
    O zaman stdout tek satır JSON olur ve "error" alanı bulunur
    Ve çıkış kodu 2 olur
    Ve code "<error_code>", field "<error_field>" olur

    Örnekler:
      | mode        | tails | dz      | alpha | power | n_total | error_code   | error_field |
      | a-priori    | 2     | 0.5     | 0.05  | 0.04  |         | INCONSISTENT | power       |
      | a-priori    | 2     | 0.5     | 0.9   | 0.8   |         | INCONSISTENT | power       |
      | sensitivity | 2     |         | 0.05  | 0.04  | 45      | INCONSISTENT | power       |
      | a-priori    | 2     | 0.00001 | 0.05  | 0.8   |         | OUT_OF_RANGE | dz          |
      | a-priori    | 2     | 0.5     | 5e-08 | 0.8   |         | OUT_OF_RANGE | alpha       |
      | a-priori    | 2     | 0.5     | 0.05  | 1     |         | OUT_OF_RANGE | power       |
      | post-hoc    | 1     | 0.5     | 0.05  |       | 2       | OUT_OF_RANGE | n_total     |
      | post-hoc    | 2     | 0.5     | 0.05  |       | 1       | OUT_OF_RANGE | n_total     |
      | sensitivity | 1     |         | 0.05  | 0.95  | 2       | OUT_OF_RANGE | n_total     |

  Senaryo Taslağı: G*Power'ın kabul ettiği ama sözleşmenin reddettiği girdiler
    # G*Power: dz = -0.5 tek kuyrukta sol kuyruğa geçer; n_total = 10.5 → 11'e yuvarlanır.
    Eğer tablodaki alanlarla çalıştırırsam
    O zaman çıkış kodu 2 olur ve code "<error_code>" olur

    Örnekler:
      | mode     | tails | dz   | alpha | power | n_total | error_code    | error_field |
      | a-priori | 2     | -0.5 | 0.05  | 0.8   |         | OUT_OF_RANGE  | dz          |
      | post-hoc | 1     | -0.5 | 0.05  |       | 20      | OUT_OF_RANGE  | dz          |
      | post-hoc | 2     | 0.5  | 0.05  |       | 10.5    | INVALID_VALUE | n_total     |
      | post-hoc | 2     | 0.5  | 0.05  |       | 3.4     | INVALID_VALUE | n_total     |

  Senaryo Taslağı: Arayüz hataları
    Eğer tablodaki alanlarla çalıştırırsam
    O zaman code "<error_code>" ve field "<error_field>" olur

    Örnekler:
      | mode     | tails | dz  | alpha | power | n_total | extra   | error_code    | error_field |
      | a-priori | 2     | 0.5 | 0.05  |       |         |         | MISSING_PARAM | power       |
      | a-priori |       | 0.5 | 0.05  | 0.8   |         |         | MISSING_PARAM | tails       |
      | a-priori | 2     | 0.5 | 0.05  | 0.8   | 20      |         | UNKNOWN_PARAM | n_total     |
      | a-priori | 2     | 0.5 | 0.05  | 0.8   |         | foo=1   | UNKNOWN_PARAM | foo         |
      | a-priori | 3     | 0.5 | 0.05  | 0.8   |         |         | OUT_OF_RANGE  | tails       |
      | a-priori | 2     | abc | 0.05  | 0.8   |         |         | INVALID_VALUE | dz          |
      | a-priori | 2     | 0.5 | 0,05  | 0.8   |         |         | INVALID_VALUE | alpha       |
      | a_priori | 2     | 0.5 | 0.05  | 0.8   |         |         | UNSUPPORTED   | mode        |
```

---

## 4. Çıktı biçimi

```gherkin
  Senaryo: Başarılı çıktı tek satır JSON'dur ve tam sayılar tam sayıdır
    Eğer "gpower-clone --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95" çalıştırırsam
    O zaman stdout tam olarak bir satırdır
    Ve satır ncp, critical_t, df, n_total, actual_power alanlarını içerir
    Ve n_total 54 ve df 53 JSON tam sayısıdır (54.0 değil)
    Ve sayılar yuvarlanmadan tam double hassasiyetle yazılır

  Senaryo: Sürüm sorgusu
    Eğer "gpower-clone --version" çalıştırırsam
    O zaman contract_version "1.0.0" olur ve çıkış kodu 0 olur

  Senaryo: Süre
    Eğer en büyük N'li vakayı (tails 2, dz 0.01, alpha 0.05, power 0.8) çalıştırırsam
    O zaman sonuç 2 saniyeden kısa sürede gelir
```

---

## 5. Bilinen ama kapsam dışı bırakılan davranışlar

- G*Power, sensitivity'de yalnızca pozitif dz yönünü hesaplar; sözleşmede yön parametresi yoktur.
- Negatif dz ile G*Power negatif `critical_t` gösterir (p023: −2.0345153). Sözleşme dz > 0 istediği için bu davranış
  arayüzden görünmez.
- "Determine" penceresi (dz'yi ortalama, SD ve korelasyondan hesaplama) kapsam dışıdır:
  dz = |μx − μy| / √(σx² + σy² − 2ρσxσy) [DOK].

---

## 6. Temiz oda oturumunun bulduğu boşluklar (2026-10-22)

Oturum 2 yalnızca bu belgeyle (sürüm SHA-256 `28ba05bf…bd3`, `cleanroom/SPEC.md`) bütün örnekleri geçti ve SPEC'te olmayan
889 kâhin vektöründe de G*Power ile aynı sonucu verdi ([cleanroom/REPORT.md](cleanroom/REPORT.md)). Kendisinin "SPEC'te yok"
diye not ettiği noktalar ve şimdiki karar:

| # | Boşluk | Karar | Kaynak |
|---|---|---|---|
| 1 | Aynı aşamada birden çok ihlal | Tanınmayan alanlar verildiği sırayla; eksik/tür/aralık CONTRACT.md §4.2 alan sırasıyla; §2 kuralları tablo sırasıyla | İki uygulama aynı |
| 2 | `--test` ya da `--mode` eksik | `MISSING_PARAM`, `field` = `test` / `mode` | İki uygulama aynı |
| 3 | Uygulanmayan test kimliği | `UNSUPPORTED`, `field` = `test` | CONTRACT.md §2.4 |
| 4 | Değersiz ya da tekrarlanan bayrak | `INVALID_VALUE` | İki uygulama aynı |
| 5 | Sayı sözdizimi | Ondalık ve e-gösterimi kabul; `inf`, `nan`, `1_000`, virgül ret. Tam sayı alanında `45.0` ret (`INVALID_VALUE`) | İki uygulama aynı |
| 6 | Sayısal çözüm bulunamazsa (ör. criterion'da α double ile gösterilemeyecek kadar küçük) | `NO_SOLUTION`. Çıkış kodu: ana uygulama 2, temiz oda 1 | ⚠ G*Power'da denenmedi |
| 7 | **Sensitivity'de güç = α** | **İki uygulama farklı:** ana uygulama `NO_SOLUTION` (çıkış 2), temiz oda dz = 0 (çıkış 0) | ⚠ **Açık soru:** G*Power'da denenmeli; sonuç bu tabloya ve §3'e örnek olarak eklenmeli |
| 8 | `beta_alpha_ratio` için ek kural | Yalnızca CONTRACT.md'deki > 0 | Kâhinde β/α = 0.25 ve 4 denendi (p051–p054) |
| 9 | Criterion çıktısında α < 1e-07 | Olduğu gibi döndürülür; 1e-07 sınırı yalnızca girdi için | ⚠ G*Power'da denenmedi |
| 10 | `--version` alanları | Serbest (takım adı, motor sürümü) | CONTRACT.md §2.2 |
| 11 | Beklenmeyen iç hata | Ana uygulama `INTERNAL` kodu, çıkış 1; CONTRACT.md tablosunda yok | CONTRACT.md §2.4 yalnızca 1 = iç hata diyor |
