"""Turn LEDGER string addresses into function addresses and the constants those functions compare.

Static disassembly only (pefile + capstone, linear sweep of .text). Nothing is decompiled and the
output holds addresses, mnemonics and constant values, which is what LEDGER.md [REA] lines may quote.

    pip install pefile capstone
    python teardown/rea_xrefs.py path/to/GPowerNT.exe > teardown/evidence/rea_xrefs.md

teardown/evidence/ is git-ignored; copy only the lines you cite into LEDGER.md.

What it reports
1. For every string address in LEDGER.md: each instruction that references it, the function that
   contains it (nearest preceding call target), and the comparisons in that function with the value
   of any .rdata constant they read (e.g. `comisd xmm0, [0x5c8f10]` -> 1e-05).
2. For every constant we expect from the oracle (1e-05 dz floor, 1e-07 alpha floor, 0.5 rounding,
   3 minimum N, 2147483646 maximum N): where it lives in .rdata / as an immediate, and which
   functions use it. A hit inside the function of the matching message turns an [AJAN] line into [REA].
"""
import argparse
import bisect
import hashlib
import struct
import sys

EXPECTED_SHA256 = "c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812"

# From LEDGER.md (string VA, label).
LEDGER_STRINGS = {
    0x005C6524: "B1 Total sample size is outside the admissible range",
    0x005C6220: "B2 Power must be greater than or equal to alpha",
    0x005C6100: "B4 Alpha is outside the admissible range",
    0x005C60D8: "B4 Power is outside the admissible range",
    0x005CB24C: "B5 In an a priori analysis, the absolute value of the",
    0x005CB56C: "A9 matched pairs test title",
}
CONSTANTS = {1e-05: "B5 |dz| floor", 1e-07: "B4 alpha/power floor", 0.5: "B3 round half up",
             3.0: "B1 minimum N (as double)", 2147483646.0: "B1 maximum N (as double)"}
INT_CONSTANTS = {3: "B1 minimum N (immediate)", 2147483646: "B1 maximum N (immediate)"}
COMPARE = {"comisd", "ucomisd", "comiss", "ucomiss", "fcom", "fcomp", "fcompp", "fcomi", "fcomip",
           "fucomi", "fucomip", "cmp", "cmpsd", "test"}
WINDOW = 400  # bytes after a function start scanned when the next start is unknown


class Image:
    """A loaded PE: sections as (va, bytes) pairs plus a few lookups."""

    def __init__(self, sections, text_name=".text"):
        self.sections = sections            # {name: (va, data)}
        self.text_va, self.text = sections[text_name]

    @classmethod
    def from_pe(cls, path):
        import pefile

        pe = pefile.PE(path)
        base = pe.OPTIONAL_HEADER.ImageBase
        secs = {s.Name.rstrip(b"\0").decode(errors="replace"): (base + s.VirtualAddress, s.get_data())
                for s in pe.sections}
        return cls(secs)

    def read(self, va, size):
        for sva, data in self.sections.values():
            if sva <= va < sva + len(data) - size + 1:
                off = va - sva
                return data[off:off + size]
        return None

    def section_of(self, va):
        for name, (sva, data) in self.sections.items():
            if sva <= va < sva + len(data):
                return name
        return None


def disassemble(img):
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs
    from capstone.x86 import X86_OP_IMM, X86_OP_MEM

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    insns, call_targets = [], set()
    off = 0
    while off < len(img.text):
        progressed = False
        for ins in md.disasm(img.text[off:], img.text_va + off):
            refs = []
            for op in ins.operands:
                if op.type == X86_OP_IMM:
                    refs.append(("imm", op.imm & 0xFFFFFFFF, op.size))
                elif op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                    refs.append(("mem", op.mem.disp & 0xFFFFFFFF, op.size))
            insns.append((ins.address, ins.mnemonic, ins.op_str, refs))
            if ins.mnemonic == "call" and refs and refs[0][0] == "imm":
                call_targets.add(refs[0][1])
            off = ins.address - img.text_va + ins.size
            progressed = True
        if not progressed or off < len(img.text):
            off += 1  # skip a byte capstone could not decode and resync
    return insns, sorted(call_targets)


def function_of(addr, starts):
    i = bisect.bisect_right(starts, addr) - 1
    return starts[i] if i >= 0 else None


def function_body(start, starts, insns, addrs):
    j = bisect.bisect_right(starts, start)
    end = starts[j] if j < len(starts) else start + WINDOW
    lo = bisect.bisect_left(addrs, start)
    hi = bisect.bisect_left(addrs, end)
    return insns[lo:hi]


def constant_value(img, ref):
    kind, va, size = ref
    if kind != "mem" or img.section_of(va) in (None, ".text"):
        return None
    # capstone reports SSE scalar-double operands as xmmword (16); the low 8 bytes are the double.
    if size in (0, 8, 10, 16):
        raw = img.read(va, 8)
        return struct.unpack("<d", raw)[0] if raw else None
    if size == 4:
        raw = img.read(va, 4)
        return struct.unpack("<f", raw)[0] if raw else None
    return None


def xrefs_to(va, insns):
    return [i for i in insns if any(r[1] == va for r in i[3])]


def find_doubles(img, value, section=".rdata"):
    if section not in img.sections:
        return []
    sva, data = img.sections[section]
    pat = struct.pack("<d", value)
    hits, i = [], data.find(pat)
    while i != -1:
        hits.append(sva + i)
        i = data.find(pat, i + 1)
    return hits


def report(img, strings=LEDGER_STRINGS, constants=CONSTANTS, int_constants=INT_CONSTANTS):
    insns, starts = disassemble(img)
    addrs = [i[0] for i in insns]
    out = ["# REA çapraz başvuru raporu", "",
           f"{len(insns)} komut, {len(starts)} fonksiyon başlangıcı (çağrı hedefleri).", ""]

    out += ["## 1. LEDGER dizeleri → fonksiyonlar ve karşılaştırdıkları sabitler", ""]
    for va, label in strings.items():
        out.append(f"### `0x{va:08X}` — {label}")
        refs = xrefs_to(va, insns)
        if not refs:
            out += ["- başvuru bulunamadı", ""]
            continue
        for addr, mn, ops, _ in refs:
            fn = function_of(addr, starts)
            out.append(f"- başvuru `0x{addr:08X}` (`{mn} {ops}`), fonksiyon `0x{fn:08X}`" if fn else
                       f"- başvuru `0x{addr:08X}` (`{mn} {ops}`), fonksiyon bulunamadı")
            if fn is None:
                continue
            for a, m, o, rr in function_body(fn, starts, insns, addrs):
                if m in COMPARE or m.startswith(("comi", "ucomi", "fcom")):
                    vals = [constant_value(img, r) for r in rr]
                    vals = [v for v in vals if v is not None]
                    imms = [r[1] for r in rr if r[0] == "imm"]
                    extra = (f" → sabit {', '.join(f'{v:.10g}' for v in vals)}" if vals else
                             f" → anlık değer {', '.join(str(x) for x in imms)}" if imms else "")
                    out.append(f"  - `0x{a:08X}` `{m} {o}`{extra}")
        out.append("")

    out += ["## 2. Kâhinden beklenen sabitler", ""]
    for value, label in constants.items():
        locs = find_doubles(img, value)
        out.append(f"### {value:g} — {label}")
        if not locs:
            out += ["- .rdata'da double olarak yok", ""]
            continue
        for loc in locs:
            users = sorted({function_of(a, starts) or 0 for a, *_ in xrefs_to(loc, insns)})
            out.append(f"- `.rdata 0x{loc:08X}`; kullanan fonksiyonlar: "
                       + (", ".join(f"`0x{u:08X}`" for u in users) if users else "yok"))
        out.append("")
    for value, label in int_constants.items():
        users = sorted({function_of(a, starts) or 0 for a, m, o, rr in insns
                        if m in COMPARE and any(r[0] == "imm" and r[1] == value for r in rr)})
        out.append(f"- anlık `{value}` ile karşılaştırma ({label}): "
                   + (", ".join(f"`0x{u:08X}`" for u in users[:20]) if users else "yok"))
    out.append("")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("exe")
    args = p.parse_args(argv)
    digest = hashlib.sha256(open(args.exe, "rb").read()).hexdigest()
    if digest != EXPECTED_SHA256:
        print(f"UYARI: SHA-256 {digest} beklenen sürüm değil; adresler tutmayabilir.", file=sys.stderr)
    print(report(Image.from_pe(args.exe)))


if __name__ == "__main__":
    main()
