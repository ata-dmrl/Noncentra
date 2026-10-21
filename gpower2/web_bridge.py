"""JSON-in / JSON-out bridge for the browser (Pyodide).

The web page calls `call(name, request_json)` and gets back the same documents and
error codes the HTTP API returns, so the page treats both engines identically.
"""
import json

from .api import analyze, distribution_plot, error_payload, power_curve
from .catalog import describe_tests
from .core.solver import AnalysisError

_FUNCS = {"analyze": analyze, "curve": power_curve, "distribution": distribution_plot,
          "tests": lambda _req: {"tests": describe_tests()}}


def call(name: str, request_json: str) -> str:
    try:
        result = _FUNCS[name](json.loads(request_json or "{}"))
    except AnalysisError as exc:
        result = error_payload(exc.code, str(exc))
    except (ValueError, TypeError, KeyError) as exc:
        result = error_payload("invalid_input", str(exc))
    return json.dumps(result)
