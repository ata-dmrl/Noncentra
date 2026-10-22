#!/usr/bin/env python3
"""gpower-clone CLI (CONTRACT.md §2). Yalnızca argümanları çevirir ve motoru çağırır."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONTRACT_VERSION = "1.0.0"
TESTS = {"t-paired"}
KNOWN_TESTS = {"t2-indep", "t-paired", "anova-oneway", "chi2-contingency", "multireg-r2"}
FLOAT_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
INT_RE = re.compile(r"^[+-]?\d+$")


def emit(obj, code):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    sys.exit(code)


def fail(code, field, message, exit_code=2):
    emit({"error": message, "code": code, "field": field}, exit_code)


def parse_pairs(argv):
    pairs = []  # sırayı korumak için liste
    i = 0
    while i < len(argv):
        tok = argv[i]
        if not tok.startswith("--") or len(tok) == 2:
            fail("UNKNOWN_PARAM", tok, f"Beklenmeyen argüman: {tok}")
        key = tok[2:]
        if i + 1 >= len(argv):
            fail("INVALID_VALUE", key, f"--{key} için değer verilmedi")
        pairs.append((key, argv[i + 1]))
        i += 2
    return pairs


def main(argv):
    if argv == ["--version"]:
        emit({"contract_version": CONTRACT_VERSION, "name": "cleanroom-session2",
              "engine": f"Python {sys.version.split()[0]} + scipy"}, 0)

    from engine import MODES, MODE_INPUTS, INT_FIELDS, EngineError, compute

    pairs = parse_pairs(argv)
    args = {}
    for k, v in pairs:
        if k in args:
            fail("INVALID_VALUE", k, f"--{k} birden fazla verildi")
        args[k] = v

    # 1) test / mod
    if "test" not in args:
        fail("MISSING_PARAM", "test", "--test verilmedi")
    if args["test"] not in TESTS:
        fail("UNSUPPORTED", "test", f"Desteklenmeyen test: {args['test']}")
    if "mode" not in args:
        fail("MISSING_PARAM", "mode", "--mode verilmedi")
    mode = args["mode"]
    if mode not in MODES:
        fail("UNSUPPORTED", "mode", f"Desteklenmeyen mod: {mode}")
    needed = MODE_INPUTS[mode]
    # 2) tanınmayan / ilgisiz alan (veriliş sırasıyla)
    for k, _ in pairs:
        if k not in ("test", "mode") and k not in needed:
            fail("UNKNOWN_PARAM", k, f"Bu mod için tanınmayan alan: {k}")
    # 3) eksik alan
    for k in needed:
        if k not in args:
            fail("MISSING_PARAM", k, f"Gerekli alan eksik: {k}")
    # 4) tür
    params = {}
    for k in needed:
        raw = args[k].strip()
        if k in INT_FIELDS:
            if not INT_RE.match(raw):
                fail("INVALID_VALUE", k, f"{k} tam sayı olmalı: {args[k]}")
            params[k] = int(raw)
        else:
            if not FLOAT_RE.match(raw):
                fail("INVALID_VALUE", k, f"{k} sayı olmalı (ondalık ayırıcı nokta): {args[k]}")
            params[k] = float(raw)
    # 5-6) aralık + G*Power kuralları + hesap: motor
    try:
        result = compute(mode, params)
    except EngineError as e:
        exit_code = 1 if e.code == "NO_SOLUTION" else 2
        fail(e.code, e.field, e.message, exit_code)
    except Exception as e:  # iç hata
        fail("INTERNAL", None, f"İç hata: {e}", 1)
    emit(result, 0)


if __name__ == "__main__":
    main(sys.argv[1:])
