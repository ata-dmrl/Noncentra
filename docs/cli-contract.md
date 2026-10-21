# gpower2 CLI sözleşmesi (contract_version 1.0)

Bu belge ve `gpower2/schemas/*.json` sözleşmenin kendisidir. `tests/test_contract.py`
CLI'yi alt süreç olarak çalıştırır ve her çıktıyı bu şemalara göre doğrular.
Geriye uyumsuz bir değişiklik `contract_version`'ı yükseltmeden yapılamaz.

## Komutlar

| Komut | Ne yapar |
|---|---|
| `gpower2 tests [--json]` | Bilinen testleri listeler |
| `gpower2 run <test> <analysis> [parametreler] [--json]` | Tek analiz |
| `gpower2 request <dosya veya -> ` | `request.schema.json` biçiminde JSON isteği çalıştırır, JSON döner |
| `gpower2 diff [--report yol.html] [--json]` | Referans verisi + statsmodels ile diferansiyel test |

Analiz türleri: `post_hoc`, `a_priori`, `sensitivity`, `criterion`, `compromise`.

Parametreler: `--effect/-d`, `--alpha`, `--power`, `--q` (β/α), `--size n1=20` (tekrarlanabilir),
`--tails 1|2` ve `--ratio` (n2/n1) t-testleri için; `--groups` (ANOVA), `--predictors` ve `--tested` (regresyon).

F testlerinde `output.df_num` pay serbestlik derecesi, `output.df` payda serbestlik derecesidir; `tails` yalnızca t-testlerinde bulunur.

## Çıktı kuralları

- `--json` verildiğinde stdout'ta **tam olarak bir** JSON belgesi olur: başarıda
  `result.schema.json`, hatada `error.schema.json`.
- Loglar ve insan okunur hata mesajları stderr'e gider.
- Alan adları sabittir; yeni alan eklemek uyumlu, alan silmek/yeniden adlandırmak uyumsuz değişikliktir.

## Çıkış kodları

| Kod | Anlam | `error.code` |
|---|---|---|
| 0 | Başarılı | – |
| 2 | Geçersiz girdi | `invalid_input` |
| 3 | Çözüm yok (ör. hedef güce ulaşılamıyor) / `diff`'te tolerans dışı fark | `no_solution` |
| 4 | Sayısal yöntem yakınsamadı | `no_convergence` |

## Örnek

```bash
python -m gpower2 run t.two_sample a_priori -d 0.5 --alpha 0.05 --power 0.8 --json
```
