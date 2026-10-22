# Noncentra — eşleştirilmiş t testi için temiz oda güç analizi

**YZM301 · Teardown Sprint · Test ailesi 2: t testi, eşleştirilmiş ortalama (önce ve sonra tansiyon)**

| Katman | Durum |
|---|---|
| Temel: CLI (`gpower-clone`, CONTRACT.md 1.0.0) | ✅ Yapıldı |
| Bonus +15: MCP sunucusu (`gpower-clone-mcp`, tek araç `power_analysis`) | ✅ Yapıldı |
| Bonus +10: AI ajanı (MCP üzerinden, Türkçe; `noncentra-agent`) | ✅ Yapıldı · ⚠ değerlendirme sonuçları API anahtarıyla `noncentra-agent-eval` çalıştırılınca `eval/RESULTS.md`'ye yazılır |

Noncentra, G*Power 3.1.9.7'nin *Means: Difference between two dependent means (matched pairs)* hesabını
davranışından yeniden yazan, komut satırından ve MCP'den çağrılabilen bir motordur. G*Power değildir ve onun
yerine sunulmaz; G*Power burada yalnızca kâhin (doğru cevabı bilen referans) olarak kullanıldı.

## Sonuç özeti

| | |
|---|---|
| G*Power vektörleri (ızgara 48, sınır 55, açık 5, literatür 1) | **109/109** uyum, 11'i açıklanmış fark ([rapor](tests/T_PAIRED_DIFF_REPORT.md)) |
| statsmodels `TTestPower` vektörleri | **780/780** uyum |
| CONTRACT.md §9 açık vektörleri | t-paired 5/5; motorun desteklediği diğer 3 aile 15/15; χ² → `UNSUPPORTED` |
| SPEC.md çalıştırılabilir örnekleri | 52/52 |
| Temiz oda oturumu (yalnızca SPEC.md ile yazılan ikinci uygulama) | kâhinin tamamında uyum, ana uygulamayla 889/889 aynı |
| MCP = CLI eşdeğerliği | 25 açık vektör + 5 ek vaka, birebir aynı |

## Kurulum ve çalıştırma

Python 3.11+ gerekir.

```bash
pip install -e ".[mcp,test]"
gpower-clone --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95
```
```json
{"ncp": 3.6742346141747673, "critical_t": 2.005745995317869, "df": 53, "n_total": 54, "actual_power": 0.9502120365387465}
```

Diğer modlar (alanların tam listesi CONTRACT.md §4.2'de):

```bash
gpower-clone --test t-paired --mode post-hoc    --tails 1 --dz 0.5 --alpha 0.05 --n_total 45
gpower-clone --test t-paired --mode compromise  --tails 1 --dz 0.5 --beta_alpha_ratio 1 --n_total 45
gpower-clone --test t-paired --mode criterion   --tails 1 --dz 0.5 --power 0.95 --n_total 45
gpower-clone --test t-paired --mode sensitivity --tails 1 --alpha 0.05 --power 0.95 --n_total 45
gpower-clone --version
```

Geçersiz girdi tek satır hata JSON'u ve sıfırdan farklı çıkış kodu verir:

```bash
gpower-clone --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.04
# {"error": "power must be greater than or equal to alpha", "code": "INCONSISTENT", "field": "power"}   (çıkış kodu 2)
```

## Testler

```bash
python -m pytest                                          # hepsi (~2000 test)
python -m pytest tests/test_spec.py                       # SPEC.md'deki Gherkin örnekleri
python -m pytest tests/test_gpower_clone.py tests/test_mcp_contract.py
python -m noncentra.difftest_paired --report tests/T_PAIRED_DIFF_REPORT.md   # diferansiyel test + rapor
python -m noncentra.difftest_paired --regenerate          # statsmodels vektörlerini yeniden üret
```

## MCP sunucusu

```bash
gpower-clone-mcp          # stdio; ya da: python -m noncentra.mcp_contract
```

Claude Code'a eklemek için: `claude mcp add gpower-clone -- gpower-clone-mcp`.

**Araç:** `power_analysis`. Girdi alanları CLI ile aynıdır; `test` ve `mode` zorunlu, diğerleri mod tablosuna göre
zorunlu olur (varsayılan yok). Çıktı, CLI'nin stdout'undaki JSON'un aynısıdır ve metin içerik olarak döner.
Hesap MCP katmanında yapılmaz: araç `noncentra.contract.run()`'ı çağırır, CLI de aynısını.

| Girdi alanı | Tür | t-paired'da hangi modda |
|---|---|---|
| `test` | string, zorunlu | `"t-paired"` (ayrıca `t2-indep`, `anova-oneway`, `multireg-r2`) |
| `mode` | string, zorunlu | `a-priori`, `post-hoc`, `compromise`, `criterion`, `sensitivity` |
| `tails` | integer (1, 2) | hepsi |
| `dz` | number > 0 | sensitivity hariç hepsi |
| `alpha` | number, [1e-07, 1) | a-priori, post-hoc, sensitivity |
| `power` | number, [1e-07, 1), ≥ alpha | a-priori, criterion, sensitivity |
| `beta_alpha_ratio` | number > 0 | compromise |
| `n_total` | integer ≥ 3 (girdi olarak) | post-hoc, compromise, criterion, sensitivity |

JSON şemasında her alan `integer | number | string | null` olarak tanımlıdır; tür denetimi CLI ile aynı ayrıştırıcıda
yapılır, böylece `45.5` gibi bir N iki yolda da aynı `INVALID_VALUE` hatasını verir.

| Çıktı alanı | Mod |
|---|---|
| `ncp`, `critical_t`, `df` | hepsi |
| `n_total`, `actual_power` | a-priori |
| `power` | post-hoc, compromise |
| `alpha` | criterion, compromise |
| `beta` | compromise |
| `dz` | sensitivity |
| `error`, `code`, `field` | hata durumunda (kodlar CONTRACT.md §2.4) |

## Temiz oda kanıtı

Ödevin "iki ayrı ajan oturumu" kuralı kayıt altında uygulandı: yeni ve bağlamsız bir ajan oturumu yalnızca SPEC.md ve
CONTRACT.md ile motoru ve CLI'yi baştan yazdı ([cleanroom/](cleanroom/)). İlk prompt birebir
[prompts/session2_run_2026-10-22.md](prompts/session2_run_2026-10-22.md)'de, 17 araç çağrısının hepsi
[cleanroom/SESSION2_AUDIT.md](cleanroom/SESSION2_AUDIT.md)'de (repoya erişen çağrı: 0).

| | Temiz oda uygulaması |
|---|---|
| SPEC örnekleri + açık vektörler (kendi testleri) | 60/60 |
| SPEC'te **olmayan** G*Power vektörleri (ızgara + sınır) | 104/104 |
| statsmodels vektörleri | 780/780 |
| Ana uygulamayla aynı girdilerde (889) fark | **0** (ondalıklar 1e-9 içinde) |

Kodu ve binary'yi görmemiş bir oturumun SPEC'ten G*Power'la aynı sonuçları üretmesi, SPEC'in doğruluğunun ve
yeterliliğinin en doğrudan kanıtı. Oturumun bulduğu 11 SPEC boşluğu SPEC.md §6'da; biri (sensitivity'de güç = α) G*Power'da
sınanması gereken açık bir soru. Ayrıntı: [cleanroom/REPORT.md](cleanroom/REPORT.md).

## AI ajanı

Hekimin kendi diliyle sorduğu soruyu `power_analysis` MCP aracını çağırarak yanıtlar. **Ajan hesap yapmaz:** dil modeli
yalnızca MCP araç listesini görür; her araç çağrısı ayrı bir süreçte çalışan MCP sunucusuna gider ve sayı oradan döner.

```bash
pip install -e ".[agent]"
export ANTHROPIC_API_KEY=...          # ajanın dil modeli için
noncentra-agent "Aynı hastalarda tedavi öncesi ve sonrası tansiyon ölçeceğiz. dz = 0,5, yalnızca düşüş iddia ediyoruz, α = 0,05, güç %95. Kaç hasta gerekir?"
noncentra-agent --system1 "..."       # önce Sistem 1 sınıflandırıcı
noncentra-agent-eval --lang both --system1   # 10 soru, Türkçe ve İngilizce
```

| Parça | Dosya |
|---|---|
| Ajan döngüsü (Claude + MCP istemcisi, stdio) | `noncentra/agent/agent.py` |
| Sistem kuralları (hesap yapma, "orta etki"yi sessizce varsayma, yön → kuyruk) | `noncentra/agent/prompts.py` |
| Sistem 1 sınıflandırıcı | `noncentra/agent/classifier.py` |
| 10 soruluk değerlendirme seti: beklenen aile, parametreler, N; her birinin İngilizce çevirisi | `eval/questions.jsonl` |
| Değerlendirme çalıştırıcısı → `eval/RESULTS.md`, `eval/results.jsonl` | `noncentra/agent/evaluate.py` |
| Araç çağrı kayıtları (CONTRACT.md §8 alanları) | `logs/agent_calls.jsonl` |
| MCP ve GUI token karşılaştırması | `eval/GUI_COMPARISON.md`, `noncentra/agent/gui_tokens.py` |

- **Varsayılan modeller:** ajan `claude-sonnet-5-5`, Sistem 1 `claude-haiku-5-5` (ortam değişkenleri
  `NONCENTRA_AGENT_MODEL`, `NONCENTRA_CLASSIFIER_MODEL`).
- **Sistem 1 (Jev yerine):** Jev erişimimiz olmadığı için ödevdeki etiket setine (`t2-indep`, `t-paired`, `anova-oneway`,
  `chi2-contingency`, `multireg-r2`, `ambiguous`, `unsupported`) zorunlu araç çağrısıyla kısıtlanmış bir LLM kullanıyoruz.
  Güven 0,75'in altındaysa ya da etiket `ambiguous`/`unsupported` ise soru araştırmacıya geri gider; sınıflandırıcı hiçbir sayı
  üretmez. Kalibrasyon tablosu `eval/RESULTS.md`'de.
- **Değerlendirme setinde iki tuzak soru var:** q08 (χ²; bu sistem desteklemiyor, doğru davranış sayı uydurmamak) ve q09
  ("orta etki"; doğru davranış varsayımı sessizce yapmadan sormak).
- **Test:** `tests/test_agent.py` bütün düzeneği (gerçek MCP sunucu süreci, log, puanlama) senaryolu sahte bir modelle uçtan
  uca çalıştırır; API anahtarı gerektirmez. Gerçek model sonuçları değildir.

## Teslim dosyaları

| Ödevin istediği | Bu repoda |
|---|---|
| SPEC.md (Gherkin) | [SPEC.md](SPEC.md), örnekleri `tests/test_spec.py` çalıştırır |
| LEDGER.md | [LEDGER.md](LEDGER.md) |
| HALLUCINATIONS.md | [HALLUCINATIONS.md](HALLUCINATIONS.md) (5 madde) |
| AGENT_COST.md | [AGENT_COST.md](AGENT_COST.md) |
| prompts/ | [prompts/](prompts/) |
| oracle/ | `oracle/t-paired/boundary_harvest.csv` + 55 ekran görüntüsü, `oracle/t-paired/statsmodels_vectors.csv` (780), `oracle/public_vectors.jsonl`; ızgara vektörleri `noncentra/reference/` |
| src/ | Python paketi olarak `noncentra/` ([src/README.md](src/README.md) yönlendirir) (motor `core/` + `catalog/`; arayüzler `contract.py`, `contract_cli.py`, `mcp_contract.py`) |
| tests/ | `tests/`, uyum raporu [tests/T_PAIRED_DIFF_REPORT.md](tests/T_PAIRED_DIFF_REPORT.md) |

Ayrıntılı bulgular: [docs/t-paired-validation.md](docs/t-paired-validation.md), [docs/teardown-report.md](docs/teardown-report.md).

## Kâhin: sürüm ve bütünlük

| | |
|---|---|
| Kaynak | Yalnızca resmi HHU sayfası (psychologie.hhu.de, G*Power sayfası) → `GPowerWin_3.1.9.7.zip` |
| Zip SHA-256 | `3bb7f1f2478d74ee5ba701ae7f849373cf2b8a11f6b6216c7c6b236db7861199` |
| `GPowerNT.exe` SHA-256 | `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812` |
| Sürüm bilgisi | Franz Faul, "GPower" 3.1.9.7, © 1992–2020; imzasız (Authenticode NotSigned) |
| Repoda mı? | **Hayır.** `*.exe`, `*.dll`, `target/` ve `teardown/evidence/` `.gitignore`'da. |

Motorun ortamı: `gpower-clone --version` (ör. Python 3.13, scipy 1.18). scipy ≥ 1.15 gerekir.

## REA kurulum kontrolü

**Fonksiyon adresleri için betik.** LEDGER.md'deki [REA] satırları şimdilik dize adresine dayanıyor. GPowerNT.exe'si olan
herkes şu komutla, decompile etmeden (yalnızca disassembly), o dizeleri kullanan fonksiyonların adreslerini ve bu
fonksiyonların karşılaştırdığı sabitleri (1e-05, 1e-07, 0.5, 3, 2147483646) çıkarabilir:

```bash
pip install pefile capstone
python teardown/rea_xrefs.py /yol/GPowerNT.exe > teardown/evidence/rea_xrefs.md   # evidence/ git'e girmez
```

Çıktıdaki eşleşmeler LEDGER.md'deki [AJAN] satırlarını (B3 yuvarlama, B5 eşiği, C5 arama) [REA]'ya çevirir; yalnızca
alıntılanan satırları LEDGER'a taşıyın. Betik el ile derlenmiş bir örnek görüntüyle test edildi (`tests/test_rea_xrefs.py`).

## Etik

- Yalnızca G*Power 3.1.9.7 (Windows) incelendi; başka yazılım hedeflenmedi.
- Repoda G*Power binary'si, decompile çıktısı ya da kaynak kod yok. LEDGER.md'de yalnızca kısa dize alıntıları ve adresler var.
- Hesap, yayımlanmış yöntemlerden (Faul ve ark., 2007; Cohen, 1988) ve gözlenen davranıştan yazıldı.
- Yazarlar talep ederse ilgili materyal derhal kaldırılır.

## Atıf

G*Power'ın yazarlarına teşekkür ederiz; bu çalışma onların bilim dünyasına ücretsiz sunduğu araç olmadan yapılamazdı.

- Faul, F., Erdfelder, E., Lang, A.-G., & Buchner, A. (2007). G*Power 3: A flexible statistical power analysis program
  for the social, behavioral, and biomedical sciences. *Behavior Research Methods, 39*(2), 175–191.
- Faul, F., Erdfelder, E., Buchner, A., & Lang, A.-G. (2009). Statistical power analyses using G*Power 3.1: Tests for
  correlation and regression analyses. *Behavior Research Methods, 41*(4), 1149–1160.
- Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.). Lawrence Erlbaum.

## Takım

Atakan Demirel, Erva Keskin, Safiye Özkan.
