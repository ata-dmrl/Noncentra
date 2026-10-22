# Noncentra · Spesifikasyon

Noncentra, G*Power 3.1.9.7'nin güç analizlerinin bir kısmını temiz oda kuralıyla yeniden yazar. Bu belge
uygulamanın neyi, hangi doğrulukla yapması gerektiğini tanımlar.

- Davranışla ilgili her gereksinim, [kanıt defterindeki](docs/EVIDENCE.md) bir ya da daha fazla kayda (E-xx) dayanır.
- Her gereksinimi en az bir otomatik test doğrular.
- `tests/test_traceability.py` bu bağları denetler: kanıtsız ya da testsiz bir gereksinim, var olmayan bir kanıta
  ya da teste yapılan atıf testleri kırar.

**Kimlik biçimi:** `R-xx`. Her gereksinimin bir **kabul kriteri** (ölçülebilir), bir **Kanıt** satırı
ve bir **Test** satırı vardır. "Tasarım" etiketli gereksinimlerin G*Power'da karşılığı yoktur; onlar
yalnızca test ister.

**Doğruluk tanımları:**
- **G*Power'a karşı:** Tam sayılar (N, df) birebir eşleşir. Ondalıklar en fazla 1e-6 mutlak farkla eşleşir; G*Power 7 ondalık gösterir.
- **statsmodels'e karşı:** güç en fazla 1e-4 farkla eşleşir.

## 1 · Kapsam

### R-01 · Desteklenen testler
G*Power'daki 49 testten 6'sı desteklenir (`docs/coverage.md`).

| Noncentra | G*Power |
|---|---|
| `t.two_sample` | t tests · Means: difference between two independent means (two groups) |
| `t.one_sample` | t tests · Means: difference from constant (one sample case) |
| `t.paired` | t tests · Means: difference between two dependent means (matched pairs) |
| `f.anova_oneway` | F tests · ANOVA: Fixed effects, omnibus, one-way |
| `f.regression_r2` | F tests · Linear multiple regression: Fixed model, R² deviation from zero |
| `f.regression_r2_increase` | F tests · Linear multiple regression: Fixed model, R² increase |

**Kabul kriteri:** `noncentra tests --json` ve `GET /api/tests` tam olarak bu altı adı listeler.
- **Kanıt:** E-05, E-08
- **Test:** `tests/test_contract.py::test_tests_listing`, `tests/test_http_api.py::test_health_and_tests`

### R-02 · Beş analiz türü
Her test için `a_priori`, `post_hoc`, `sensitivity`, `criterion` ve `compromise` analizleri çalışır.

**Kabul kriteri:** Her analiz türü için geçerli bir istek, `result.schema.json`'a uyan bir sonuç döndürür.
Sensitivity'nin bulduğu etki büyüklüğü post hoc'a verildiğinde istenen gücü 1e-8 içinde geri verir.
- **Kanıt:** E-06
- **Test:** `tests/test_contract.py::test_success_matches_result_schema`, `tests/test_properties.py::test_sensitivity_inverts_post_hoc`

## 2 · Hesaplama

### R-03 · t testlerinin gücü
δ ve df, E-19'daki formüllerle hesaplanır. Güç, merkezi olmayan t dağılımının kritik değeri aşan kısmıdır
(iki yönlü testte iki kuyruğun toplamı).

**Kabul kriteri:**
- `noncentra/reference/t_tests_harvested.csv`'deki `known_divergence` sütunu boş olan her satır, G*Power'a karşı doğruluk tanımı içinde yeniden üretilir: güç, kritik t, N, sensitivity'de etki büyüklüğü, criterion ve compromise'da α.
- Ayrıca statsmodels ızgarasında her post hoc gücü 1e-4 içinde eşleşir.
- **Kanıt:** E-19, E-03, E-10, E-11, E-12, E-26
- **Test:** `tests/test_regression.py::test_reference_row`, `tests/test_differential.py::test_matches_statsmodels`

### R-04 · F testlerinin gücü
λ = f²·N ve df, E-20'deki formüllerle hesaplanır. Güç, merkezi olmayan F dağılımının kritik değeri aşan kısmıdır.

**Kabul kriteri:** `noncentra/reference/f_tests_harvested.csv`'deki 198 satırın tamamı G*Power'a karşı doğruluk
tanımı içinde yeniden üretilir. statsmodels ızgarasındaki ANOVA ve R² durumları 1e-4 içinde eşleşir.
- **Kanıt:** E-20, E-03, E-15, E-17, E-23, E-26
- **Test:** `tests/test_regression.py::test_reference_row`, `tests/test_differential.py::test_matches_statsmodels`

### R-05 · A priori en küçük örneklemi verir
Kesirli çözüm bulunur, sonra her grup ayrı ayrı yukarı yuvarlanır.

**Kabul kriteri:** Dönen N ile güç hedefe eşit ya da hedeften büyüktür. Bir adım küçük N ile (ANOVA'da bir
grup daha az) güç hedefin altında kalır. Grup oranı 1 olan iki örneklemli satırlarda grup büyüklükleri
G*Power ile aynıdır (örnek: d = 0.5, α = 0.05, 1−β = 0.80 → 64 + 64).
- **Kanıt:** E-10, E-11, E-12
- **Test:** `tests/test_properties.py::test_a_priori_returns_smallest_n`, `tests/test_regression.py::test_reference_row`

### R-06 · ANOVA'da N grup sayısının katıdır
Tek yönlü ANOVA a priori'de N, k'nin katına yukarı yuvarlanır; gruplar eşit olur.

**Kabul kriteri:** f = 0.25, k = 3, α = 0.05, 1−β = 0.80 → N = 159, λ = 9.9375, kritik F = 3.0540042,
güç = 0.8048873. Güç eğrisindeki tüm N değerleri k'nin katıdır.
- **Kanıt:** E-16, E-17
- **Test:** `tests/test_http_api.py::test_analyze_matches_core`, `tests/test_http_api.py::test_curve`, `tests/test_regression.py::test_reference_row`

### R-07 · Eşit olmayan grup oranı (bilinen fark)
Grup oranı 1'den farklıyken Noncentra, kesirli n1* çözümünden n1 = ⌈n1*⌉ ve n2 = ⌈n1*·oran⌉ hesaplar.
G*Power'ın bu durumdaki kuralı belirlenemedi (E-13) ve G*Power bazen hedef gücü tutturamıyor (E-14).
Bu yüzden Noncentra G*Power'ı taklit etmez; bunun yerine hedefe ulaşmayı garanti eder.

**Kabul kriteri:** `known_divergence` sütunu dolu 23 satırın her birinde Noncentra'nın gücü hedefe eşit ya da
hedeften büyüktür. Fark raporu (`noncentra diff`) bu satırları başarısız değil "bilinen sapma" olarak sayar.
G*Power'ın hedefi tutturamadığı satır sayısı 5'tir.
- **Kanıt:** E-13, E-14
- **Test:** `tests/test_regression.py::test_reference_row`, `tests/test_traceability.py::test_known_divergence_counts`

### R-08 · Compromise oranı tutar
**Kabul kriteri:** Compromise sonucunda β/α, istenen orana 1e-6 göreli farkla eşittir. G*Power'ın compromise
satırları (t ve F toplamaları, eşleştirilmiş sınır satırları `p051`–`p054`) doğruluk tanımı içinde yeniden üretilir.
- **Kanıt:** E-10, E-15, E-18
- **Test:** `tests/test_properties.py::test_compromise_hits_ratio`, `tests/test_regression.py::test_reference_row`, `tests/test_paired_boundary.py::test_paired_boundary`

### R-09 · Sayısal sağlamlık
scipy ve statsmodels'teki bilinen hatalar sonuçlara sızmaz.

**Kabul kriteri:**
- Hiçbir sonuç NaN değildir.
- Etki büyüklüğü 0 iken güç, α'ya 1e-9 içinde eşittir (t testlerinde ve F testlerinde).
- Güç N, α ve etki büyüklüğüyle azalmaz.
- statsmodels'in NaN döndürdüğü durumlar başarısız değil "referans tanımsız" sayılır.
- Eşleştirilmiş compromise satırları `h134` ve `h137` geçer.
- **Kanıt:** E-21, E-22, E-24, E-25
- **Test:** `tests/test_properties.py::test_zero_effect_gives_alpha`, `tests/test_properties.py::test_power_grows_with_n_alpha_and_effect`, `tests/test_differential.py::test_matches_statsmodels`, `tests/test_regression.py::test_reference_row`

## 3 · Girdi doğrulama ve G*Power ile bilinen farklar

### R-10 · Geçersiz girdi reddedilir
**Kabul kriteri:**
- α ∉ (0, 1), güç ∉ (0, 1), bilinmeyen test, analiz ya da seçenek, eksik parametre ve tam sayı olmayan N → `invalid_input` (CLI çıkış kodu 2, HTTP 400).
- A priori'de etki büyüklüğü 0 → `no_solution` (çıkış kodu 3, HTTP 422).
- G*Power'ın da reddettiği girdiler (α = 0, α = 1, güç = 1, dz = 0) Noncentra'da da reddedilir.
- **Kanıt:** E-09, E-18
- **Test:** `tests/test_contract.py::test_errors_match_error_schema`, `tests/test_http_api.py::test_errors`, `tests/test_paired_boundary.py::test_paired_boundary`

### R-11 · Bilinen farklar kayıt altında tutulur
Aşağıdaki farklar bilinçli bırakılmıştır:
- **B1:** post hoc ve sensitivity'de N = 2.
- **B2:** a priori'de güç < α.
- **B3:** kesirli N.
- **B5:** negatif dz'de tek yönlü testte yön.
- **E-13:** eşit olmayan grup oranı.

**Kabul kriteri:** Her bilinen fark, nedeniyle birlikte bir listede durur (`tests/test_paired_boundary.py` →
`DIVERGENCES`, ya da CSV'deki `known_divergence` sütunu). Bir fark düzelirse ve satır listede kalırsa test kırılır
(katı xfail). Listede olmayan yeni bir fark çıkarsa test yine kırılır.
- **Kanıt:** E-18, E-13
- **Test:** `tests/test_paired_boundary.py::test_paired_boundary`, `tests/test_regression.py::test_reference_row`

## 4 · Arayüzler (ajan çağı)

### R-12 · CLI sözleşmesi (zorunlu)
Komutlar `noncentra tests`, `run`, `request` ve `diff`'tir; ayrıntılar `docs/cli-contract.md`'de.

**Kabul kriteri:**
- `--json` ile stdout'ta tam olarak bir JSON belgesi olur: başarıda `result.schema.json`'a, hatada `error.schema.json`'a uyar.
- Çıkış kodları: 0 başarılı, 2 geçersiz girdi, 3 çözüm yok, 4 yakınsama hatası.
- `request -` ile stdin'den okunan istek aynı sonucu verir.
- **Kanıt:** tasarım (G*Power'ın komut satırı arayüzü yok)
- **Test:** `tests/test_contract.py::test_success_matches_result_schema`, `tests/test_contract.py::test_errors_match_error_schema`, `tests/test_contract.py::test_stdout_is_single_json_document`, `tests/test_contract.py::test_request_from_stdin_round_trips`

### R-13 · MCP sunucusu (bonus)
Araçlar: `list_tests`, `power_analysis`, `explain_result` ve `run_diff_test`.

**Kabul kriteri:**
- Dört araç da kayıtlıdır.
- `power_analysis`, CLI ve API ile aynı belgeyi döndürür.
- Hatalar `error.schema.json` biçiminde döner, istisna olarak fırlatılmaz.
- `explain_result`, sonucu düz dille özetler; özette güç ve örneklem büyüklüğü geçer.
- **Kanıt:** tasarım
- **Test:** `tests/test_mcp.py::test_tools_are_registered`, `tests/test_mcp.py::test_power_analysis_matches_api`, `tests/test_mcp.py::test_power_analysis_reports_errors`, `tests/test_mcp.py::test_explain_result_mentions_power`

### R-14 · HTTP API
Uç noktalar: `/api/health`, `/api/tests`, `/api/analyze`, `/api/curve`, `/api/distribution` ve `/api/schemas/*`.

**Kabul kriteri:**
- `/api/analyze`, çekirdekle aynı belgeyi döndürür.
- Hata kodları HTTP durumlarına şöyle eşlenir: 400, 422, 500.
- `/api/distribution`'da taralı β alanı, β'ya 0.01 içinde eşittir; iki yönlü t testinde α alanlarının toplamı α'ya 0.01 içinde eşittir.
- `/api/curve`, 200'den fazla nokta isteğini reddeder.
- **Kanıt:** tasarım
- **Test:** `tests/test_http_api.py::test_analyze_matches_core`, `tests/test_http_api.py::test_errors`, `tests/test_http_api.py::test_distribution_regions_match_power`, `tests/test_http_api.py::test_distribution_reports_errors`, `tests/test_http_api.py::test_curve_rejects_too_many_points`, `tests/test_http_api.py::test_schema_endpoint`

### R-15 · Web arayüzü ve rapor
İki hesaplama motoru vardır: sunucu (FastAPI) ve tarayıcı (Pyodide). Arayüz G*Power tarzı dağılım grafiği ve
güç eğrisi çizer, indirilebilir bir rapor üretir.

**Kabul kriteri:**
- Tarayıcı köprüsü (`web_bridge.call`), HTTP API ile aynı belgeyi döndürür.
- Web dosyaları `Cache-Control: no-cache` ile sunulur.
- İki motor 6 test × 5 analizde aynı N'yi verir (E-27).
- Rapor şunları içerir: özet, ayarlar, girdiler, tüm sonuç değerleri, iki grafik (SVG) ve protokol. Rapor elle doğrulanır: sayfada "Raporu indir"e basılır ve dosyada bu bölümlerin olduğu kontrol edilir.
- **Kanıt:** E-27
- **Test:** `tests/test_http_api.py::test_bridge_matches_http`, `tests/test_http_api.py::test_web_files_revalidate`

## 5 · Temiz oda

### R-16 · G*Power'a ait hiçbir şey repoda değildir
**Kabul kriteri:**
- Git'in izlediği dosyalar arasında `.exe`, `.dll` ya da `target/` veya `teardown/evidence/` altında dosya yoktur.
- Kaynak kodda G*Power'dan alınmış kod yoktur.
- Formüller yalnızca yayınlanmış kaynaklardan (E-19, E-20) gelir.
- İkili dosyadan yalnızca başlık bilgisi, dizeler ve adresler okunmuştur (E-02, E-04, E-09). Hesap motorunun kodu okunmamıştır (E-28).
- **Kanıt:** E-01, E-02, E-04, E-07, E-19, E-20, E-28
- **Test:** `tests/test_traceability.py::test_no_gpower_artifacts_tracked`

## 6 · İzlenebilirlik

### R-17 · Gereksinim, kanıt ve test bağları tutarlıdır
**Kabul kriteri:**
- Her R'nin bir kabul kriteri ve en az bir testi vardır.
- "Tasarım" olmayan her R en az bir E'ye bağlıdır.
- Atıf yapılan her E, `docs/EVIDENCE.md`'de vardır ve her E en az bir R tarafından kullanılır.
- Atıf yapılan her test dosyası ve fonksiyonu vardır.
- Repoda bulunan her kanıt dosyasının SHA-256'sı defterdekiyle aynıdır.
- **Kanıt:** E-05, E-10, E-15, E-18
- **Test:** `tests/test_traceability.py::test_every_requirement_is_traced`, `tests/test_traceability.py::test_referenced_tests_exist`, `tests/test_traceability.py::test_every_evidence_is_used`, `tests/test_traceability.py::test_evidence_hashes_match`

## Açık işler (bu sürümün kapsamı dışında)

- **E-28 → E-13:** G*Power'ın hesap motorunu Ghidra ile kod düzeyinde bulmak; eşit olmayan grup oranı kuralını kesinleştirmek.
- **Kapsam:** 49 testin 43'ü henüz yok (`docs/coverage.md`). Sırada χ² uyum iyiliği, korelasyon, iki oran (z) ve faktöriyel ANOVA var.
- **R-13 için:** Sonuçları büyük dil modeliyle açıklayan bir yapay zekâ ajanı. Şu an `explain_result` şablon metin üretiyor.
