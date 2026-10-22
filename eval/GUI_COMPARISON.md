# MCP ve GUI yolu: token, süre, doğruluk

## 1. Ekran görüntüsü başına token (hesaplandı)

`oracle/t-paired/screenshots/` içindeki 67 gerçek G*Power ekran görüntüsünden, Claude'un görüntü
fiyatlandırmasıyla (uzun kenar 1568 px'e küçültme, sonra genişlik × yükseklik / 750):

| Görüntü | Adet | Boyut | Token (medyan) |
|---|---:|---|---:|
| Ana pencere | 55 | 708×802 | 758 |
| Uyarı kutusu | 12 | ~430×216 | 125 |

Bir `gpower-clone` çağrısının girdisi ve çıktısı ise toplam ~200 karakterlik JSON, yani birkaç düzine token.

Bir GUI ajanının tek bir a priori soruyu çözmek için en az şu ekranları görmesi gerekir: test ailesini seçme,
testi seçme, analiz türünü seçme, girdileri kontrol etme, Calculate sonrası sonucu okuma. Her adımda bir ana pencere
görüntüsü (758 token) gelir ve her görüntü sonraki her turda bağlamda kalır. Bu yüzden toplam maliyet
adım sayısıyla doğrusal değil, yaklaşık karesel büyür. Bu bir **tahmin**; ölçülmüş değer aşağıdaki tabloya girmeli.

## 2. Ölçüm (aynı 10 soru)

| Yol | Ortalama giriş token / soru | Ortalama çıkış token / soru | Ortalama süre (sn) | Doğru |
|---|---:|---:|---:|---:|
| MCP | ⚠ `noncentra-agent-eval` çalıştırılınca dolar | | | |
| GUI (ekran görüntüsüyle) | ⚠ | ⚠ | ⚠ | ⚠ |

### GUI ölçüm protokolü (Windows + G*Power 3.1.9.7)

1. G*Power'ı açık bırakın. Aynı modeli (`claude-sonnet-5-5`) bir bilgisayar kullanımı (computer use) aracıyla çalıştırın;
   sistem mesajı: "G*Power penceresini kullanarak soruyu çöz; sayıyı yalnızca ekrandan oku."
2. `eval/questions.jsonl` içindeki 10 Türkçe soruyu sırayla verin. Her soru yeni bir konuşma.
3. Her soru için API yanıtlarındaki `usage.input_tokens` ve `usage.output_tokens` toplamını, ekran görüntüsü sayısını,
   duvar saati süresini ve okunan N'nin doğru olup olmadığını kaydedin (`eval/gui_runs.jsonl`).
4. Tabloyu doldurun. q08 ve q09'da doğru davranış sayı vermemektir; GUI ajanı G*Power'da χ²'yi hesaplayabileceği
   için q08 GUI yolunda sayıyla cevaplanabilir; bunu not edin.

Sınıflandırılmış veri yok; sorular kurgusaldır (CONTRACT.md §8).
