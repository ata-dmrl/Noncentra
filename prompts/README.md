# prompts/ — İki oturumun ilk prompt'ları

Temiz oda kuralı (ödev metni): Oturum 1 REA/Ghidra ile inceler ve yalnızca SPEC.md ile LEDGER.md üretir.
Oturum 2 yeni bir oturumda **yalnızca SPEC.md** (ve arayüz için CONTRACT.md) ile başlar, Ghidra çıktısını görmez.

| Dosya | Oturum |
|---|---|
| [session1_inceleme.md](session1_inceleme.md) | Oturum 1: inceleme |
| [session2_yazim.md](session2_yazim.md) | Oturum 2: temiz oda yazımı (görev metni) |
| [session2_run_2026-10-22.md](session2_run_2026-10-22.md) | Oturum 2'nin 2026-10-22'de gerçekten çalıştırılan ilk prompt'u (birebir); sonuç: [cleanroom/REPORT.md](../cleanroom/REPORT.md) |

**Oturum 2 kayıtlı biçimde çalıştırıldı (2026-10-22):** yeni bir ajan oturumu yalnızca SPEC.md, CONTRACT.md ve
`session2_yazim.md` ile motoru baştan yazdı; araç çağrıları `cleanroom/SESSION2_AUDIT.md`'de, sonuç ve bağımsız doğrulama
`cleanroom/REPORT.md`'de.

> ⚠ **Ekip için not:** Repoyu ilk oluşturan oturumların (motorun ilk yazımı ve teardown) gerçek ilk prompt'ları repoda kayıtlı
> değildi; `session1_inceleme.md` kuralın gerektirdiği prompt'tur. Elinizde gerçek oturum 1 prompt'u varsa onu **değiştirmeden**
> ekleyin.
