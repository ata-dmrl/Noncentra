# Web arayüzü ve HTTP API

Üç ön yüz aynı Python fonksiyonlarını kullanır (`noncentra/api.py`: `analyze`, `power_curve`). Bu yüzden CLI, MCP, HTTP ve tarayıcı aynı sonucu ve aynı hata kodlarını verir.

## Çalıştırma

```bash
python web/build_bundle.py
```

```bash
python -m uvicorn noncentra.http_api:app --port 8000
```

- Arayüz: http://localhost:8000/ (→ `/web/`). API belgeleri (OpenAPI): http://localhost:8000/docs
- Sunucu olmadan, yalnızca tarayıcıda çalıştırmak için `web/` klasörünü herhangi bir statik sunucuyla yayınlamak yeterli (ör. `python -m http.server 8001 --directory web`). Sayfa API'yi bulamazsa otomatik olarak Pyodide'e geçer.
- `noncentra/` içindeki kod değişince `web/build_bundle.py` yeniden çalıştırılmalı. Paket ~10 KB; CLI, MCP, HTTP ve referans verisi pakete dahil edilmez.

## HTTP API

| Yöntem | Yol | Gövde / yanıt |
|---|---|---|
| GET | `/api/health` | `{status, version, contract_version}` |
| GET | `/api/tests` | Test kataloğu (`noncentra tests --json` ile aynı) |
| POST | `/api/analyze` | `request.schema.json` → `result.schema.json` |
| POST | `/api/distribution` | `analyze` ile aynı gövde → merkezi/merkezi olmayan yoğunluklar, kritik değer(ler), α ve β bölgeleri, `result` |
| POST | `/api/curve` | `{test, options, effect_sizes[], alpha, n_from, n_to, points≤200}` → güç eğrisi serileri |
| GET | `/api/schemas/{request\|result\|error}` | JSON şemaları |

Hata yanıtları `error.schema.json` biçimindedir. HTTP durum kodları CLI çıkış kodlarıyla aynı anlamı taşır:

| `error.code` | HTTP | CLI çıkış kodu |
|---|---|---|
| `invalid_input` | 400 | 2 |
| `no_solution` | 422 | 3 |
| `no_convergence` | 500 | 4 |

## Web arayüzü

- **Motor seçimi:** "Sunucu (FastAPI)" ya da "Tarayıcı (Pyodide 0.26.4 + scipy)". Pyodide ilk açılışta numpy/scipy indirir (~birkaç saniye); sonra her şey çevrimdışı hesaplanır.
- **Dağılım grafiği:** G*Power'ın "Central and noncentral distributions" görünümünün karşılığı: H0 kırmızı düz, H1 mavi kesikli, kritik değerler yeşil, β ve α (α/2) alanları taralı, başlıkta `critical t/F`. Yoğunluklar Python'da hesaplanır, iki motor aynı veriyi çizer. df_num = 1 olan F testlerinde 0'daki sonsuz tepe kırpılır.
- **Özellikler:** 6 test × 5 analiz türü, Cohen etki büyüklüğü kısayolları, G*Power tarzı protokol (kopyala), JSON indirme, paylaşılabilir bağlantı (tüm girdiler URL hash'inde) ve güç–N eğrisi (seçilen etki büyüklüğü + iki konvansiyonel değer, hedef güç çizgisi).
- **Güvenlik:** `pyodide.js` SRI hash'iyle yükleniyor. Motordan gelen hata mesajları, kullanıcı girdisini (ör. URL'deki test adı) içerebileceği için HTML olarak değil düz metin olarak gösteriliyor.

## Doğrulama (2026-10-16)

- `tests/test_http_api.py`: 8 test. Sonuçlar çekirdekle aynı, şemalar geçerli, HTTP durumları doğru, eğri ANOVA'da grup sayısının katlarında ilerliyor.
- Tarayıcıda (uygulama içi tarayıcı) iki motor, 6 test × 5 analiz = 30 istekte karşılaştırıldı:
  - Örneklem büyüklükleri aynı.
  - Kritik değerlerde en fazla 2.1×10⁻⁹ fark var (Pyodide scipy 1.12, sunucu scipy 1.15). Bu fark G*Power'ın 10⁻⁷ gösterim hassasiyetinin altında.
- ANOVA f=.25, k=3 arayüzde G*Power ile bire bir: N=159, λ=9.9375, F_krit=3.0540042, güç=0.8048873.
- 375 px mobil genişlikte yatay taşma yok. URL'ye konan HTML/JS içerikli test adı çalıştırılmadı.
