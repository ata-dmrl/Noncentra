"""Command line front end. The contract is in docs/cli-contract.md.

Exit codes: 0 ok, 2 invalid input, 3 no solution, 4 no convergence.
With --json, stdout carries exactly one JSON document (result or error).
"""
import argparse
import json
import sys

from . import __version__
from .api import analyze, error_payload
from .catalog import describe_tests
from .core.solver import ANALYSES, AnalysisError, ConvergenceError

EXIT_OK, EXIT_INVALID, EXIT_NO_SOLUTION, EXIT_NO_CONVERGENCE = 0, 2, 3, 4


class _Parser(argparse.ArgumentParser):
    # argparse exits with 2 on bad usage already; keep the JSON contract too.
    def error(self, message):
        if "--json" in sys.argv:
            print(json.dumps(error_payload("invalid_input", message)))
            sys.exit(EXIT_INVALID)
        super().error(message)


def _sizes(values):
    sizes = {}
    for item in values or []:
        key, _, val = item.partition("=")
        if not val:
            raise ValueError(f"size must look like key=value, got {item!r}")
        sizes[key] = int(val)
    return sizes or None


def build_parser():
    p = _Parser(prog="noncentra", description="Clean-room statistical power analysis.")
    p.add_argument("--version", action="version", version=f"noncentra {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("tests", help="list available tests").add_argument("--json", action="store_true")

    a = sub.add_parser("run", help="run one power analysis")
    a.add_argument("test", help="test name, see `noncentra tests`")
    a.add_argument("analysis", choices=ANALYSES)
    a.add_argument("--effect", "-d", type=float, dest="effect_size")
    a.add_argument("--alpha", type=float)
    a.add_argument("--power", type=float)
    a.add_argument("--q", type=float, dest="beta_alpha_ratio", help="beta/alpha (compromise)")
    a.add_argument("--size", action="append", metavar="KEY=N", help="sample size, e.g. n1=20")
    a.add_argument("--tails", type=int, choices=(1, 2), help="t tests; default 2")
    a.add_argument("--ratio", type=float, help="n2/n1 allocation ratio (two-sample tests)")
    a.add_argument("--groups", type=int, help="number of groups (ANOVA)")
    a.add_argument("--predictors", type=int, help="number of predictors (regression)")
    a.add_argument("--tested", type=int, help="predictors tested (R² increase)")
    a.add_argument("--json", action="store_true")

    r = sub.add_parser("request", help="run a JSON request (file path or - for stdin)")
    r.add_argument("path")
    r.add_argument("--json", action="store_true", default=True)

    d = sub.add_parser("diff", help="differential test against reference data and statsmodels")
    d.add_argument("--report", help="write an HTML report to this path")
    d.add_argument("--json", action="store_true")
    return p


def _request_from_args(args):
    options = {k: getattr(args, k) for k in ("tails", "ratio", "groups", "predictors", "tested")
               if getattr(args, k) is not None}
    params = {
        "effect_size": args.effect_size,
        "alpha": args.alpha,
        "power": args.power,
        "beta_alpha_ratio": args.beta_alpha_ratio,
        "sizes": _sizes(args.size),
    }
    return {
        "test": args.test,
        "analysis": args.analysis,
        "options": options,
        "params": {k: v for k, v in params.items() if v is not None},
    }


def _print_text(result):
    out = result["output"]
    print(f"{result['test']}  [{result['analysis']}]")
    for key in ("effect_size", "alpha", "power", "beta_alpha_ratio", "noncentrality",
                "critical_value", "df_num", "df", "n_total", "tails", "groups", "predictors", "tested"):
        if key in out:
            val = out[key]
            # 7 decimals, like G*Power's protocol, so the two can be compared by eye.
            print(f"  {key:<18} {val:.7f}" if isinstance(val, float) else f"  {key:<18} {val}")
    for k, v in out["sizes"].items():
        print(f"  {k:<18} {v}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    as_json = getattr(args, "json", False)

    def fail(code, exit_code, message):
        if as_json:
            print(json.dumps(error_payload(code, message)))
        else:
            print(f"error: {message}", file=sys.stderr)
        return exit_code

    try:
        if args.command == "tests":
            tests = describe_tests()
            if as_json:
                print(json.dumps({"tests": tests}))
            else:
                for t in tests:
                    print(f"{t['name']:<16} {t['title']}")
            return EXIT_OK

        if args.command == "diff":
            from .difftest import run_diff

            summary = run_diff(report_path=args.report)
            print(json.dumps(summary) if as_json else
                  f"{summary['checked']} cases, {summary['failed']} outside tolerance")
            return EXIT_OK if summary["failed"] == 0 else EXIT_NO_SOLUTION

        if args.command == "request":
            text = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()
            request = json.loads(text)
        else:
            request = _request_from_args(args)

        result = analyze(request)
    except ConvergenceError as exc:
        return fail(exc.code, EXIT_NO_CONVERGENCE, str(exc))
    except AnalysisError as exc:
        return fail(exc.code, EXIT_NO_SOLUTION, str(exc))
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OSError) as exc:
        return fail("invalid_input", EXIT_INVALID, str(exc))

    if as_json:
        print(json.dumps(result))
    else:
        _print_text(result)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
