"""Thin adapter between CONTRACT.md (the course's `gpower-clone` interface) and the engine.

This module only translates names and checks the *shape* of the input (which fields,
which types, the ranges in CONTRACT.md §5). Every number comes from `noncentra.api.analyze`.
G*Power-specific refusals inside those ranges (power < alpha, N < 3 for matched pairs,
alpha < 1e-07, ...) live in the engine, so the old CLI, the HTTP API and this contract
front end all behave alike. Both `gpower-clone` (CLI) and the contract MCP server call
`run()`, so they cannot drift apart.
"""
import math
import platform
import re

import scipy

from .api import analyze
from .core.errors import InputError
from .core.solver import AnalysisError, ConvergenceError

CONTRACT_VERSION = "1.0.0"
TEAM_NAME = "Noncentra"

EXIT_OK, EXIT_INTERNAL, EXIT_INVALID = 0, 1, 2

MODES = {
    "a-priori": "a_priori",
    "post-hoc": "post_hoc",
    "compromise": "compromise",
    "criterion": "criterion",
    "sensitivity": "sensitivity",
}

INT_FIELDS = {"tails", "n_total", "n1", "n2", "groups", "predictors", "df"}

# Per test: engine name, effect-size field, sample-size fields -> engine size keys,
# structural options, extra a-priori-only options, critical-value key, F (df1/df2) or t (df).
TESTS = {
    "t-paired": {
        "engine": "t.paired", "effect": "dz", "sizes": {"n_total": "n"},
        "options": ["tails"], "a_priori_options": [], "critical": "critical_t", "f": False,
    },
    "t2-indep": {
        "engine": "t.two_sample", "effect": "d", "sizes": {"n1": "n1", "n2": "n2"},
        "options": ["tails"], "a_priori_options": ["ratio"], "critical": "critical_t", "f": False,
    },
    "anova-oneway": {
        "engine": "f.anova_oneway", "effect": "f", "sizes": {"n_total": "n"},
        "options": ["groups"], "a_priori_options": [], "critical": "critical_f", "f": True,
    },
    "multireg-r2": {
        "engine": "f.regression_r2", "effect": "f2", "sizes": {"n_total": "n"},
        "options": ["predictors"], "a_priori_options": [], "critical": "critical_f", "f": True,
    },
}
# Listed in CONTRACT.md but not implemented by this team (K4 is another team's family).
KNOWN_UNIMPLEMENTED = {"chi2-contingency"}


def version() -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "name": TEAM_NAME,
        "engine": f"Python {platform.python_version()}, scipy {scipy.__version__}",
    }


def input_fields(test: str, mode: str) -> list[str]:
    """The exact input fields CONTRACT.md §4 requires for (test, mode), in table order."""
    spec = TESTS[test]
    fields = []
    if "tails" in spec["options"]:
        fields.append("tails")
    if mode != "sensitivity":
        fields.append(spec["effect"])
    if mode in ("a-priori", "post-hoc", "sensitivity"):
        fields.append("alpha")
    if mode in ("a-priori", "criterion", "sensitivity"):
        fields.append("power")
    if mode == "compromise":
        fields.append("beta_alpha_ratio")
    if mode == "a-priori":
        fields += spec["a_priori_options"]
    else:
        fields += list(spec["sizes"])
    fields += [o for o in spec["options"] if o != "tails"]
    return fields


def _fail(message, code, field=None, exit_code=EXIT_INVALID):
    payload = {"error": message, "code": code}
    if field is not None:
        payload["field"] = field
    return payload, exit_code


_INT_RE = re.compile(r"[+-]?\d+")


def _parse(field, raw):
    """Parse one value. CLI values arrive as strings; MCP values are JSON-encoded first."""
    text = str(raw).strip()
    if field in INT_FIELDS:
        if not _INT_RE.fullmatch(text):
            raise InputError(f"{field} must be an integer, got {text!r}", "INVALID_VALUE", field)
        return int(text)
    try:
        value = float(text)
    except ValueError:
        raise InputError(f"{field} must be a number, got {text!r}", "INVALID_VALUE", field) from None
    if not math.isfinite(value):
        raise InputError(f"{field} must be finite, got {text!r}", "INVALID_VALUE", field)
    return value


def _check_range(field, value):
    """CONTRACT.md §5."""
    ok = {
        "tails": lambda v: v in (1, 2),
        "alpha": lambda v: 0 < v < 1,
        "power": lambda v: 0 < v < 1,
        "n1": lambda v: v >= 2, "n2": lambda v: v >= 2, "n_total": lambda v: v >= 2,
        "groups": lambda v: v >= 2,
        "df": lambda v: v >= 1,
        "predictors": lambda v: v >= 1,
    }.get(field, lambda v: v > 0)  # beta_alpha_ratio, ratio, d, dz, f, w, f2
    if not ok(value):
        raise InputError(f"{field} is out of range: {value}", "OUT_OF_RANGE", field)


def _as_int(x):
    return int(x) if float(x).is_integer() else x


def _output(spec, mode, out) -> dict:
    res = {"ncp": out["noncentrality"], spec["critical"]: out["critical_value"]}
    if spec["f"]:
        res["df1"], res["df2"] = _as_int(out["df_num"]), _as_int(out["df"])
    else:
        res["df"] = _as_int(out["df"])
    if mode == "a-priori":
        if list(spec["sizes"]) == ["n1", "n2"]:
            res["n1"], res["n2"] = out["sizes"]["n1"], out["sizes"]["n2"]
        res["n_total"] = out["n_total"]
        res["actual_power"] = out["power"]
    elif mode == "post-hoc":
        res["power"] = out["power"]
    elif mode == "compromise":
        res["alpha"], res["beta"], res["power"] = out["alpha"], out["beta"], out["power"]
    elif mode == "criterion":
        res["alpha"] = out["alpha"]
    else:
        res[spec["effect"]] = out["effect_size"]
    for k, v in res.items():
        if isinstance(v, float) and not math.isfinite(v):
            raise ArithmeticError(f"{k} is not finite")
    return res


def run(fields: dict) -> tuple[dict, int]:
    """Run one contract request. `fields` maps contract field names to raw values.

    Returns (payload, exit_code); payload is the success JSON or the error JSON of §2.
    """
    fields = dict(fields)
    test, mode = fields.pop("test", None), fields.pop("mode", None)
    if test is None:
        return _fail("--test is required", "MISSING_PARAM", "test")
    if mode is None:
        return _fail("--mode is required", "MISSING_PARAM", "mode")
    if test not in TESTS:
        why = "not implemented by this team" if test in KNOWN_UNIMPLEMENTED else "unknown test"
        return _fail(f"{why}: {test}", "UNSUPPORTED", "test")
    if mode not in MODES:
        return _fail(f"unknown mode: {mode}", "UNSUPPORTED", "mode")

    spec = TESTS[test]
    wanted = input_fields(test, mode)
    for name in fields:
        if name not in wanted:
            return _fail(f"{name} is not a field of {test} {mode}", "UNKNOWN_PARAM", name)
    for name in wanted:
        if name not in fields:
            return _fail(f"{test} {mode} needs --{name}", "MISSING_PARAM", name)

    try:
        values = {k: _parse(k, fields[k]) for k in wanted}
        for k, v in values.items():
            _check_range(k, v)

        options = {o: values[o] for o in spec["options"]}
        options.update({o: values[o] for o in spec["a_priori_options"] if o in values})
        params = {k: values[k] for k in ("alpha", "power", "beta_alpha_ratio") if k in values}
        if spec["effect"] in values:
            params["effect_size"] = values[spec["effect"]]
        if mode != "a-priori":
            params["sizes"] = {eng: values[c] for c, eng in spec["sizes"].items()}

        result = analyze({"test": spec["engine"], "analysis": MODES[mode],
                          "options": options, "params": params})
        return _output(spec, mode, result["output"]), EXIT_OK
    except InputError as exc:
        field, message = exc.field, str(exc)
        if field == "effect_size":
            field = spec["effect"]
        elif field in ("n", "n1", "n2"):
            field = next(c for c, eng in spec["sizes"].items() if eng == field)
        if field != exc.field and message.startswith(f"{exc.field} "):
            # Engine messages name engine keys; show the contract field instead.
            message = field + message[len(exc.field):]
        return _fail(message, exc.code, field)
    except ConvergenceError as exc:
        return _fail(str(exc), "NO_SOLUTION", exit_code=EXIT_INTERNAL)
    except AnalysisError as exc:
        return _fail(str(exc), "NO_SOLUTION")
    except ValueError as exc:
        return _fail(str(exc), "INVALID_VALUE")
    except Exception as exc:  # noqa: BLE001 - the contract wants JSON, never a traceback
        return _fail(f"internal error: {exc}", "INTERNAL", exit_code=EXIT_INTERNAL)
