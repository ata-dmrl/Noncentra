# CONTRACT.md 1.0.0'da bulunan belirsizlikler (Classroom yorumu taslağı)

CONTRACT.md §11: "Sözleşmede bir belirsizlik bulursanız ödev gönderisine yorum olarak yazın. Belirsizliği ilk bulan takım
artı puan alır." Aşağıdaki metin doğrudan yapıştırılabilir.

---

**Noncentra (K2, t-paired): CONTRACT.md 1.0.0'da iki belirsizlik**

1. **`n_total` alt sınırı (§5).** Sözleşme `n_total ≥ 2` diyor. G*Power 3.1.9.7 ise eşleştirilmiş t testinde N bir girdi
   olduğunda (post hoc, sensitivity) N = 2'yi reddediyor: "Total sample size is outside the admissible range (3, 2147483646)".
   A priori'de ise kendisi N = 2 döndürebiliyor (ör. dz = 10, tek kuyruk; ya da güç = α). Gizli vektörlerde
   `--mode post-hoc --n_total 2` varsa beklenen yanıt hata mı (G*Power gibi), yoksa bir güç değeri mi (§5'e göre geçerli)?
   Biz G*Power'ı izleyip `OUT_OF_RANGE` döndürüyoruz.

2. **`alpha` ve `power` alt sınırı (§5).** Sözleşme `0 < alpha < 1` diyor. G*Power α ya da güç 1e-07'nin altındaysa reddediyor
   (mesaj "(1e-07, 1)" yazıyor ama 1e-07'yi kabul ediyor). `alpha = 5e-08` gibi bir vektörde beklenen yanıt hata mı?
   Biz `OUT_OF_RANGE` döndürüyoruz.

Ekran görüntüleri ve binary adresleri: repomuzda `oracle/t-paired/screenshots/p029_post_hoc_dialog0.png`, `p041_post_hoc.png`
ve LEDGER.md B1, B4.

---

İkisi de §5'in "aralığın içindeki bir değerin kabul edilip edilmeyeceğine G*Power'ın davranışı karar verir" cümlesiyle
çözülebilir; ama ilk maddede sözleşmenin kendi aralığı (≥ 2) G*Power'ın aralığından (≥ 3) geniş olduğu için açıkça sormaya değer.
