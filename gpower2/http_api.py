"""HTTP API (FastAPI) over the same `analyze` entry point as the CLI and MCP server.

Run:  python -m uvicorn gpower2.http_api:app --port 8000
It also serves the web UI from ../web at / when that folder exists, so the page can
call the API instead of loading Pyodide.
"""
import json
from importlib import resources
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import CONTRACT_VERSION, __version__
from .api import analyze, distribution_plot, error_payload, power_curve
from .catalog import describe_tests
from .core.solver import AnalysisError, ConvergenceError

# Same meaning as the CLI exit codes (docs/cli-contract.md), as HTTP statuses.
STATUS = {"invalid_input": 400, "no_solution": 422, "no_convergence": 500}

app = FastAPI(title="gpower2", version=__version__,
              description="Clean-room statistical power analysis, validated against G*Power 3.1.9.7.")


def _run(fn, request):
    try:
        return fn(request)
    except ConvergenceError as exc:
        code, message = exc.code, str(exc)
    except AnalysisError as exc:
        code, message = exc.code, str(exc)
    except (ValueError, TypeError, KeyError) as exc:
        code, message = "invalid_input", str(exc)
    return JSONResponse(error_payload(code, message), status_code=STATUS[code])


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__, "contract_version": CONTRACT_VERSION}


@app.get("/api/tests")
def tests():
    return {"tests": describe_tests()}


@app.post("/api/analyze")
def analyze_endpoint(request: dict = Body(..., examples=[{
        "test": "t.two_sample", "analysis": "a_priori",
        "params": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8}}])):
    """Run one analysis. Body follows request.schema.json; response follows result.schema.json."""
    return _run(analyze, request)


@app.post("/api/curve")
def curve_endpoint(request: dict = Body(..., examples=[{
        "test": "t.two_sample", "effect_sizes": [0.3, 0.5, 0.8], "alpha": 0.05,
        "n_from": 5, "n_to": 100, "points": 40}])):
    """Power versus total sample size, one series per effect size."""
    return _run(power_curve, request)


@app.post("/api/distribution")
def distribution_endpoint(request: dict = Body(..., examples=[{
        "test": "t.two_sample", "analysis": "a_priori",
        "params": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8}}])):
    """Central and noncentral densities with alpha/beta regions (G*Power's distribution plot).
    Body is the same as /api/analyze; the analysis result is included under `result`."""
    return _run(distribution_plot, request)


@app.get("/api/schemas/{name}")
def schema(name: str):
    if name not in ("request", "result", "error"):
        raise HTTPException(404, "unknown schema")
    return json.loads(resources.files("gpower2.schemas").joinpath(f"{name}.schema.json").read_text("utf-8"))


class _RevalidatingStatic(StaticFiles):
    # The UI and gpower2.zip change together; make browsers revalidate (ETag) every load
    # instead of mixing a cached app.js with a new index.html.
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


WEB = Path(__file__).resolve().parent.parent / "web"
if WEB.is_dir():
    app.mount("/web", _RevalidatingStatic(directory=WEB, html=True), name="web")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/web/")
