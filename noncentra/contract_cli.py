"""`gpower-clone`: the command line interface fixed by CONTRACT.md.

    gpower-clone --test <TEST_ID> --mode <MODE_ID> [--<field> <value> ...]
    gpower-clone --version

stdout carries exactly one line of JSON; anything else goes to stderr.
Exit codes: 0 success, 2 invalid input, 1 internal error.
"""
import json
import sys

from . import contract


def parse_argv(argv):
    """Turn ['--test', 't-paired', '--dz', '0.5', ...] into a dict. Raises ValueError."""
    fields = {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if not token.startswith("--") or len(token) == 2:
            raise ValueError(f"expected --<field>, got {token!r}")
        name, eq, inline = token[2:].partition("=")
        if eq:
            value = inline
            i += 1
        else:
            if i + 1 >= len(argv):
                raise ValueError(f"--{name} needs a value")
            value = argv[i + 1]
            i += 2
        if name in fields:
            raise ValueError(f"--{name} given twice")
        fields[name] = value
    return fields


def emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--version"]:
        emit(contract.version())
        return contract.EXIT_OK
    try:
        fields = parse_argv(argv)
    except ValueError as exc:
        emit({"error": str(exc), "code": "INVALID_VALUE"})
        return contract.EXIT_INVALID
    payload, code = contract.run(fields)
    emit(payload)
    return code


if __name__ == "__main__":
    sys.exit(main())
