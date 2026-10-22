# prompts/ — İki oturumun ilk prompt'ları

Temiz oda kuralı (ödev metni): Oturum 1 REA/Ghidra ile inceler ve yalnızca SPEC.md ile LEDGER.md üretir.
Oturum 2 yeni bir oturumda **yalnızca SPEC.md** (ve arayüz için CONTRACT.md) ile başlar, Ghidra çıktısını görmez.

| Dosya | Oturum |
|---|---|
| [session1_inceleme.md](session1_inceleme.md) | Oturum 1: inceleme |
| [session2_yazim.md](session2_yazim.md) | Oturum 2: temiz oda yazımı |

> ⚠ **Ekip için not:** Repoyu ilk oluşturan oturumların gerçek ilk prompt'ları repoda kayıtlı değildi. Bu iki dosya,
> kuralın gerektirdiği prompt'lardır ve SPEC.md'nin bugünkü hâliyle uyumludur. Elinizde gerçek ilk prompt'lar
> varsa bunları **değiştirmeden** bu dosyaların yerine koyun. Yoksa, oturum 2'yi bu prompt'la yeniden çalıştırıp
> çıkan kodu `tests/test_spec.py` ve `tests/test_gpower_clone.py` ile sınamak, temiz oda iddiasını kanıtlamanın en
> dürüst yoludur.
