"""teardown/rea_xrefs.py on a hand-assembled image (no G*Power binary in the repo)."""
import struct
import sys
from pathlib import Path

import pytest

pytest.importorskip("capstone")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "teardown"))
import rea_xrefs as rx  # noqa: E402

TEXT_VA, RDATA_VA = 0x401000, 0x405000


def image():
    # .rdata: 0x405000 = 1e-05 (double), 0x405010 = "msg"
    rdata = struct.pack("<d", 1e-05) + b"\0" * 8 + b"msg\0"
    code = bytearray()
    code += b"\xe8" + struct.pack("<i", 0x401020 - (TEXT_VA + 5))       # 0x401000 call 0x401020
    code += b"\xc3"                                                      # ret
    code += b"\xcc" * (0x20 - len(code))
    # 0x401020: function under test
    code += b"\x55\x8b\xec"                                              # push ebp; mov ebp, esp
    code += b"\xf2\x0f\x10\x45\x08"                                      # movsd xmm0, [ebp+8]
    code += b"\x66\x0f\x2f\x05" + struct.pack("<I", RDATA_VA)            # comisd xmm0, [0x405000]
    code += b"\x83\x7d\x0c\x03"                                          # cmp dword [ebp+0xc], 3
    code += b"\x68" + struct.pack("<I", RDATA_VA + 0x10)                 # push 0x405010
    code += b"\x5d\xc3"                                                  # pop ebp; ret
    return rx.Image({".text": (TEXT_VA, bytes(code)), ".rdata": (RDATA_VA, rdata)})


def test_report_finds_function_and_constants():
    md = rx.report(image(), strings={RDATA_VA + 0x10: "test message"},
                   constants={1e-05: "floor"}, int_constants={3: "min N"})
    assert "fonksiyon `0x00401020`" in md
    assert "comisd" in md and "sabit 1e-05" in md
    assert "`.rdata 0x00405000`; kullanan fonksiyonlar: `0x00401020`" in md
    assert "anlık `3` ile karşılaştırma (min N): `0x00401020`" in md


def test_ledger_addresses_are_listed():
    assert 0x005C6524 in rx.LEDGER_STRINGS and 1e-05 in rx.CONSTANTS
