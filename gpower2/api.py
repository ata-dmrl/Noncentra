"""Single entry point shared by the CLI, the MCP server and the HTTP API.

`analyze(request)` takes and returns plain dicts that follow the JSON schemas in
gpower2/schemas/. Keeping one function means the three front ends cannot drift.
"""
from . import CONTRACT_VERSION
from .catalog import get_test
from .core import solver


def analyze(request: dict) -> dict:
    test = request.get("test")
    analysis = request.get("analysis")
    options = dict(request.get("options") or {})
    params = dict(request.get("params") or {})
    if analysis not in solver.ANALYSES:
        raise ValueError(f"analysis must be one of {list(solver.ANALYSES)}")

    model = get_test(test, **options)

    def need(*keys):
        missing = [k for k in keys if params.get(k) is None]
        if missing:
            raise ValueError(f"{analysis} needs params {missing}")
        return [params[k] for k in keys]

    if analysis == "post_hoc":
        effect, sizes, alpha = need("effect_size", "sizes", "alpha")
        out = solver.post_hoc(model, effect, sizes, alpha)
    elif analysis == "a_priori":
        effect, alpha, power = need("effect_size", "alpha", "power")
        out = solver.a_priori(model, effect, alpha, power)
    elif analysis == "sensitivity":
        sizes, alpha, power = need("sizes", "alpha", "power")
        out = solver.sensitivity(model, sizes, alpha, power)
    elif analysis == "criterion":
        effect, sizes, power = need("effect_size", "sizes", "power")
        out = solver.criterion(model, effect, sizes, power)
    else:
        effect, sizes, q = need("effect_size", "sizes", "beta_alpha_ratio")
        out = solver.compromise(model, effect, sizes, q)

    return {
        "contract_version": CONTRACT_VERSION,
        "test": test,
        "analysis": analysis,
        "input": {"options": options, "params": params},
        "output": out,
    }


MAX_CURVE_POINTS = 200


def power_curve(request: dict) -> dict:
    """Power as a function of total sample size, one series per effect size (G*Power's X-Y plot).

    request: {test, options, effect_sizes: [..], alpha, n_from, n_to, points}
    n_from / n_to are base sizes (n1 for two-sample tests, N otherwise); every point is
    rounded the way a priori rounds, so ANOVA steps in whole groups.
    """
    test = request.get("test")
    model = get_test(test, **dict(request.get("options") or {}))
    effects = request.get("effect_sizes") or []
    alpha = request.get("alpha")
    n_from, n_to = request.get("n_from"), request.get("n_to")
    points = int(request.get("points") or 50)
    if not effects or alpha is None or n_from is None or n_to is None:
        raise ValueError("power_curve needs effect_sizes, alpha, n_from and n_to")
    if not 2 <= points <= MAX_CURVE_POINTS:
        raise ValueError(f"points must be in [2, {MAX_CURVE_POINTS}]")
    if not model.min_n <= n_from < n_to:
        raise ValueError(f"need {model.min_n} <= n_from < n_to")

    step = (n_to - n_from) / (points - 1)
    seen, grid = set(), []
    for i in range(points):
        sizes = model.round_sizes(n_from + i * step)
        key = tuple(sorted(sizes.items()))
        if key not in seen:
            seen.add(key)
            grid.append(sizes)

    series = []
    for effect in effects:
        pts = []
        for sizes in grid:
            out = solver.post_hoc(model, effect, sizes, alpha)
            pts.append({"n_total": out["n_total"], "sizes": out["sizes"], "power": out["power"]})
        series.append({"effect_size": effect, "points": pts})
    return {"contract_version": CONTRACT_VERSION, "test": test, "x": "n_total", "alpha": alpha,
            "series": series}


DIST_POINTS = 301


def distribution_plot(request: dict) -> dict:
    """Central (H0) and noncentral (H1) densities of the test statistic for one analysis,
    with the rejection (alpha) and beta regions: G*Power's "Central and noncentral
    distributions" view. Takes the same request as `analyze` and includes its result.
    """
    from .core import distributions as dist

    result = analyze(request)
    out = result["output"]
    ncp, crit = out["noncentrality"], out["critical_value"]
    if "df_num" in out:
        family, statistic = "F", "F"
        lo, hi = 0.0, max(crit * 2.0, dist.f_upper(out["df_num"], out["df"], ncp))
        xs = [lo + (hi - lo) * i / (DIST_POINTS - 1) for i in range(DIST_POINTS)]
        xs[0] = 1e-6 * hi  # the F density can be infinite at 0
        central, noncentral = dist.f_densities(xs, out["df_num"], out["df"], ncp)
        criticals = [crit]
        alpha_regions = [[crit, hi]]
        beta_region = [lo, crit]
    else:
        family, statistic = "t", "t"
        two = out["tails"] == 2
        lo = min(-3.0, -crit - 1.0 if two else -3.0, ncp - 3.5)
        hi = max(3.0, crit + 1.5, ncp + 3.5)
        xs = [lo + (hi - lo) * i / (DIST_POINTS - 1) for i in range(DIST_POINTS)]
        central, noncentral = dist.t_densities(xs, out["df"], ncp)
        criticals = [-crit, crit] if two else [crit]
        alpha_regions = [[lo, -crit], [crit, hi]] if two else [[crit, hi]]
        beta_region = [-crit, crit] if two else [lo, crit]
    return {
        "contract_version": CONTRACT_VERSION, "family": family, "statistic": statistic,
        "x": xs, "central": central, "noncentral": noncentral,
        "critical": criticals, "alpha_regions": alpha_regions, "beta_region": beta_region,
        "tails": out.get("tails"), "result": result,
    }


def error_payload(code: str, message: str) -> dict:
    return {"contract_version": CONTRACT_VERSION, "error": {"code": code, "message": message}}
