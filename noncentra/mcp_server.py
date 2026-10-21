"""MCP server: exposes the same `analyze` entry point as the CLI to AI clients.

Run with `python -m noncentra.mcp_server` (stdio transport).
"""
from mcp.server.fastmcp import FastMCP

from .api import analyze, error_payload
from .catalog import describe_tests
from .core.solver import AnalysisError

mcp = FastMCP("noncentra")


@mcp.tool()
def list_tests() -> list[dict]:
    """List the statistical tests this server can analyze, with their effect size and sample size keys."""
    return describe_tests()


@mcp.tool()
def power_analysis(test: str, analysis: str, params: dict, options: dict | None = None) -> dict:
    """Run one power analysis.

    analysis: post_hoc | a_priori | sensitivity | criterion | compromise.
    params may hold effect_size, alpha, power, beta_alpha_ratio and sizes ({"n1": 20, "n2": 20} or {"n": 30}).
    options: t tests take tails (1 or 2) and ratio (n2/n1, two-sample); f.anova_oneway takes groups;
    f.regression_r2 takes predictors; f.regression_r2_increase takes predictors and tested.
    Effect size is d/dz for t tests, f for ANOVA and f2 (f squared) for regression.
    Returns the result document from noncentra/schemas/result.schema.json, or an error document.
    """
    try:
        return analyze({"test": test, "analysis": analysis, "params": params, "options": options or {}})
    except AnalysisError as exc:
        return error_payload(exc.code, str(exc))
    except (ValueError, TypeError, KeyError) as exc:
        return error_payload("invalid_input", str(exc))


@mcp.tool()
def explain_result(result: dict, language: str = "tr") -> str:
    """Turn a power_analysis result into a short plain-language summary (language: tr or en)."""
    out = result.get("output")
    if not out:
        return result.get("error", {}).get("message", "No result to explain.")
    sizes = ", ".join(f"{k}={v}" for k, v in out["sizes"].items())
    df = f"{out['df_num']:g}, {out['df']:g}" if "df_num" in out else f"{out['df']:g}"
    if language == "en":
        tails = {1: ", one-tailed", 2: ", two-tailed"}.get(out.get("tails"), "")
        return (f"{result['test']} ({result['analysis']}{tails}): with effect size "
                f"{out['effect_size']:.3f}, alpha {out['alpha']:.4g} and sample sizes {sizes} "
                f"(total {out['n_total']}), power is {out['power']:.4f}. Critical value "
                f"{out['critical_value']:.4f}, df {df}, noncentrality {out['noncentrality']:.4f}.")
    tails = {1: ", tek yönlü", 2: ", iki yönlü"}.get(out.get("tails"), "")
    return (f"{result['test']} ({result['analysis']}{tails}): etki büyüklüğü "
            f"{out['effect_size']:.3f}, alfa {out['alpha']:.4g} ve örneklem {sizes} "
            f"(toplam {out['n_total']}) için güç {out['power']:.4f}. Kritik değer "
            f"{out['critical_value']:.4f}, sd {df}, merkezdışılık parametresi {out['noncentrality']:.4f}.")


@mcp.tool()
def run_diff_test() -> dict:
    """Compare the solver with G*Power reference values and statsmodels; returns pass/fail counts."""
    from .difftest import run_diff

    return run_diff()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
