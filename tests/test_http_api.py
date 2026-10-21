"""HTTP API returns the same documents as the CLI, with statuses mapped from error codes."""
import json
from importlib import resources

import jsonschema
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from gpower2.api import analyze  # noqa: E402
from gpower2.http_api import app  # noqa: E402

client = TestClient(app)
REQUEST = {"test": "f.anova_oneway", "analysis": "a_priori", "options": {"groups": 3},
           "params": {"effect_size": 0.25, "alpha": 0.05, "power": 0.8}}


def schema(name):
    return json.loads(resources.files("gpower2.schemas").joinpath(name).read_text("utf-8"))


def test_health_and_tests():
    assert client.get("/api/health").json()["status"] == "ok"
    names = {t["name"] for t in client.get("/api/tests").json()["tests"]}
    assert "f.regression_r2_increase" in names


def test_analyze_matches_core():
    r = client.post("/api/analyze", json=REQUEST)
    assert r.status_code == 200
    jsonschema.validate(r.json(), schema("result.schema.json"))
    assert r.json() == json.loads(json.dumps(analyze(REQUEST)))
    assert r.json()["output"]["n_total"] == 159  # G*Power: multiple of groups


@pytest.mark.parametrize("body, status, code", [
    ({**REQUEST, "test": "nope"}, 400, "invalid_input"),
    ({**REQUEST, "params": {"effect_size": 0, "alpha": 0.05, "power": 0.8}}, 422, "no_solution"),
    ({"test": "t.paired"}, 400, "invalid_input"),
])
def test_errors(body, status, code):
    r = client.post("/api/analyze", json=body)
    assert r.status_code == status
    jsonschema.validate(r.json(), schema("error.schema.json"))
    assert r.json()["error"]["code"] == code


def test_curve():
    r = client.post("/api/curve", json={"test": "f.anova_oneway", "options": {"groups": 3},
                                        "effect_sizes": [0.25, 0.4], "alpha": 0.05,
                                        "n_from": 6, "n_to": 90, "points": 30})
    assert r.status_code == 200
    series = r.json()["series"]
    assert len(series) == 2
    ns = [p["n_total"] for p in series[0]["points"]]
    assert all(n % 3 == 0 for n in ns) and ns == sorted(set(ns))
    powers = [p["power"] for p in series[0]["points"]]
    assert powers == sorted(powers)
    assert all(a["power"] <= b["power"] for a, b in zip(series[0]["points"], series[1]["points"]))


def test_curve_rejects_too_many_points():
    r = client.post("/api/curve", json={"test": "t.one_sample", "effect_sizes": [0.5], "alpha": 0.05,
                                        "n_from": 5, "n_to": 50, "points": 5000})
    assert r.status_code == 400


def _area(xs, ys, lo, hi):
    pts = [(x, y or 0.0) for x, y in zip(xs, ys) if lo <= x <= hi]
    return sum((b[0] - a[0]) * (a[1] + b[1]) / 2 for a, b in zip(pts, pts[1:]))


@pytest.mark.parametrize("body", [
    {"test": "t.two_sample", "analysis": "a_priori", "params": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8}},
    {"test": "t.one_sample", "analysis": "post_hoc", "options": {"tails": 1},
     "params": {"effect_size": 0.4, "alpha": 0.05, "sizes": {"n": 25}}},
    REQUEST,
    {"test": "f.regression_r2_increase", "analysis": "post_hoc", "options": {"predictors": 10, "tested": 4},
     "params": {"effect_size": 0.15, "alpha": 0.05, "sizes": {"n": 85}}},
])
def test_distribution_regions_match_power(body):
    r = client.post("/api/distribution", json=body)
    assert r.status_code == 200
    d = r.json()
    out = d["result"]["output"]
    assert d["result"] == json.loads(json.dumps(analyze(body)))
    assert len(d["x"]) == len(d["central"]) == len(d["noncentral"])
    assert max(d["critical"]) == pytest.approx(out["critical_value"])
    # The shaded beta area under H1 is beta; the alpha regions under H0 add up to alpha.
    assert _area(d["x"], d["noncentral"], *d["beta_region"]) == pytest.approx(out["beta"], abs=0.01)
    if d["family"] == "t":
        alpha = sum(_area(d["x"], d["central"], *reg) for reg in d["alpha_regions"])
        assert alpha == pytest.approx(out["alpha"], abs=0.01)


def test_distribution_reports_errors():
    r = client.post("/api/distribution", json={**REQUEST, "test": "nope"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_input"


def test_web_files_revalidate():
    r = client.get("/web/app.js")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"


def test_bridge_matches_http():
    from gpower2.web_bridge import call

    body = {"test": "t.paired", "analysis": "a_priori", "params": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8}}
    assert json.loads(call("distribution", json.dumps(body))) == client.post("/api/distribution", json=body).json()


def test_schema_endpoint():
    assert client.get("/api/schemas/result").json()["title"] == "Power analysis result"
    assert client.get("/api/schemas/nope").status_code == 404
