# Temiz oda: oturum 2 raporu ve doğrulaması (`t-paired`)

## Düzenek

| | |
|---|---|
| Tarih | 2026-10-22 |
| Oturum | Ayrı, sıfırdan başlayan bir Claude ajan oturumu (oturum 4'ün başlattığı, ama onun bağlamını görmeyen yeni bir alt ajan) |
| Girdiler | Yalnızca bu klasördeki `SPEC.md`, `CONTRACT.md`, `PROMPT.md` (= `prompts/session2_yazim.md`) |
| Girdi hash'leri | `SPEC.md` `28ba05bf…bd3`, `CONTRACT.md` `4cbcc105…f9f`, `PROMPT.md` `373a3149…e8d` (SHA-256) |
| Çalışma klasörü | Repo dışında ayrı bir klasör; repoya erişim yasağı talimatla verildi |
| Başlatan prompt | [prompts/session2_run_2026-10-22.md](../prompts/session2_run_2026-10-22.md) |
| Denetim | [SESSION2_AUDIT.md](SESSION2_AUDIT.md): 17 araç çağrısı, hepsi bu klasörde; repo yoluna değinen çağrı **0** |
| Maliyet | ~106.800 token, 17 araç çağrısı, 8,3 dakika, 2 iterasyon |

**Sınırlama:** İzolasyon dosya sistemi düzeyinde zorlanmadı (alt ajan teknik olarak başka klasörleri okuyabilirdi); talimatla
verildi ve araç çağrısı kaydıyla denetlendi.

## Oturumun kendi raporu (birebir)

> **Sonuç:** SPEC §3 52/52 (31 hesap + 21 hata), SPEC §4 3/3, CONTRACT §9 t-paired 5/5, toplam pytest 60/60. Geçmeyen satır yok.
>
> **İterasyon: 2.** İlk turda 59/60 geçti. a-priori tails 2, dz 20 satırında N=2 yerine 3 çıktı. Neden benim hatam (sayısal):
> scipy `nct.cdf(-12.706, 1, 28.28)` nan döndürüyor. Düzeltme olarak tanımdan sayısal integral alan bir yedek eklendi. İkinci
> turda 60/60 geçti ve 400 rastgele girdilik taramada sorun çıkmadı.
>
> **SPEC'te yok:** (1) aynı aşamada birden çok ihlal varsa önceliği; (2) --test/--mode eksikse MISSING_PARAM; (3) uygulanmayan
> testler için UNSUPPORTED; (4) değersiz ya da tekrarlanan bayrak INVALID_VALUE, `--` ile başlamayan argüman UNKNOWN_PARAM;
> (5) sayı sözdizimi (inf/nan/1_000 reddediliyor, tam sayı alanında 45.0 reddediliyor); (6) NO_SOLUTION ve çıkış kodu (1 seçildi);
> (7) sensitivity'de güç=α için dz=0; (8) beta_alpha_ratio için ek kurallar; (9) criterion çıktısında α<1e-07; (10) --version
> name/engine değerleri; (11) iç hata kodu INTERNAL, CONTRACT tablosunda yok.

(Oturum bu raporu dosyaya yazamadı; içeriği son mesajında verdi ve buraya aynen alındı.)

## Bağımsız doğrulama (oturum 4)

Oturumun kendi testleri yalnızca SPEC'teki 52 satırı ve 5 açık vektörü kapsıyor. SPEC'te **olmayan** vektörlerle de sınadık:
temiz oda CLI'si, ana uygulamanın diferansiyel testindeki bütün kâhin verisinden geçirildi (`tests/test_cleanroom.py`).

| Kâhin | Vaka | Temiz oda uyumu |
|---|---:|---:|
| G*Power ızgara (`t_tests_harvested.csv`, 48) + literatür (1) | 49 | 49/49 |
| G*Power sınır (`boundary_harvest.csv`) | 55 | 55/55 (44 aynı, 11 sözleşmenin reddettiği girdi) |
| CONTRACT.md §9 açık vektörleri | 5 | 5/5 |
| statsmodels `TTestPower` | 780 | 780/780 (30'u NaN yedeğiyle) |

**İki bağımsız uygulama birbirine karşı:** aynı 889 girdide çıkış kodu, hata kodu ve bütün çıktı alanları aynı; ondalıklar
1e-9 göreli fark içinde.

### Ne gösteriyor

- **SPEC yeterli.** Kodu ve binary'yi hiç görmemiş bir oturum, yalnızca SPEC.md ile, SPEC'te bulunmayan 830+ vektörde de G*Power
  ile aynı sonucu üretti. Bu, SPEC kalitesinin (gizli vektörler) en doğrudan ölçüsü.
- **Temiz oda kuralı uygulanabilir.** Oturum 2'nin girdileri, araç çağrıları ve maliyeti kayıtlı.
- **Bağımsız bir hata kanalı buldu.** Oturum, scipy'nin df = 1'de büyük δ ile NaN döndürdüğünü kendi buldu ve ana motordan
  farklı bir yolla (sayısal integral) aştı; ana motor yansıma özdeşliği kullanıyor. İki farklı çözüm aynı sonucu veriyor.
- **SPEC'teki boşluklar:** 11 madde, SPEC.md §6'ya işlendi. Biri iki uygulama arasında **farklı** karar verilmiş bir durum:
  sensitivity'de güç = α için temiz oda dz = 0 döndürüyor, ana motor `NO_SOLUTION` hatası veriyor. G*Power'ın davranışı
  denenmedi; kâhinde sınanması gerekiyor (889 vektörün hiçbiri bu durumu içermiyor).

## Çalıştırma

```bash
python cleanroom/impl/gpower_clone.py --test t-paired --mode a-priori --tails 2 --dz 0.5 --alpha 0.05 --power 0.95
python -m pytest -q cleanroom/impl/tests      # oturumun kendi testleri (60)
python -m pytest -q tests/test_cleanroom.py   # kâhin + ana motorla çapraz doğrulama
```

Teslim edilen CLI ana uygulamadır (`gpower-clone`, `noncentra/`). Temiz oda uygulaması kanıt olarak repoda duruyor.
