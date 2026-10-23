"""MCP server fixed by CONTRACT.md §7: one tool, `power_analysis`, same fields as the CLI.

Run with `gpower-clone-mcp` or `python -m noncentra.mcp_contract` (stdio transport).
The tool forwards to `noncentra.contract.run`, the same function `gpower-clone` calls,
and returns the CLI's stdout JSON as text. No calculation happens here.
"""
import json

from mcp.server.fastmcp import FastMCP

from . import contract

mcp = FastMCP("gpower-clone")

Value = int | float | str | None


def call(arguments: dict) -> str:
    """Shared by the tool and the tests: JSON text, exactly what the CLI prints."""
    # Values are JSON-encoded so they pass through the CLI's string parser: 45 and
    # "45" are the same input, 45.5 is refused for n_total exactly as on the CLI.
    fields = {k: (v if k in ("test", "mode") or isinstance(v, str) else json.dumps(v))
              for k, v in arguments.items() if v is not None}
    payload, _ = contract.run(fields)
    return json.dumps(payload, ensure_ascii=False, allow_nan=False)


@mcp.tool()
def power_analysis(test: str, mode: str, tails: Value = None, dz: Value = None, d: Value = None,
                   f: Value = None, f2: Value = None, alpha: Value = None, power: Value = None,
                   beta_alpha_ratio: Value = None, n_total: Value = None, n1: Value = None,
                   n2: Value = None, ratio: Value = None, groups: Value = None,
                   predictors: Value = None, w: Value = None, df: Value = None) -> str:
    """Statistical power analysis (G*Power-compatible, clean-room engine).

    test: t-paired (matched pairs, e.g. blood pressure before/after in the same patients),
          t2-indep, anova-oneway, multireg-r2. chi2-contingency (w, df) is part of the
          contract but not implemented here: it returns code UNSUPPORTED.
    mode: a-priori (needs power, returns n_total) | post-hoc (needs n_total, returns power)
          | compromise | criterion | sensitivity.
    t-paired fields: a-priori tails, dz, alpha, power; post-hoc tails, dz, alpha, n_total;
          compromise tails, dz, beta_alpha_ratio, n_total; criterion tails, dz, power, n_total;
          sensitivity tails, alpha, power, n_total.
    Give exactly the fields of the mode; there are no defaults. Returns one JSON object,
    or {"error", "code", "field"} for invalid input.
    """
    return call({k: v for k, v in locals().items()})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
