"""The five G*Power analysis types, written once for any test model.

post_hoc     power        given effect, alpha, n
a_priori     n            given effect, alpha, power
sensitivity  effect size  given alpha, power, n
criterion    alpha        given effect, power, n
compromise   alpha, power given effect, n, q = beta/alpha
"""
import math

from scipy.optimize import brentq

from .errors import InputError

ANALYSES = ("post_hoc", "a_priori", "sensitivity", "criterion", "compromise")

MAX_N = 10_000_000

# G*Power 3.1.9.7 accepts alpha and power in [1e-07, 1): the message says
# "(1e-07, 1)" but 1e-07 itself is accepted (oracle/t-paired p041, p024-p026).
MIN_PROB = 1e-7
# "In an a priori analysis, the absolute value of the effect size be greater than
# 0.00001." (oracle/t-paired p022)
MIN_ABS_EFFECT_A_PRIORI = 1e-5


class AnalysisError(Exception):
    """Raised for requests that are valid but have no solution."""

    code = "no_solution"


class ConvergenceError(AnalysisError):
    code = "no_convergence"


def _unit(name, value):
    if not (MIN_PROB <= value < 1.0):
        raise InputError(f"{name} must be in [{MIN_PROB:g}, 1), got {value}", "OUT_OF_RANGE", name)


def _power_not_below_alpha(alpha, power):
    # G*Power: "Power must be greater than or equal to alpha." (p016, p021, p048)
    if power < alpha:
        raise InputError("power must be greater than or equal to alpha", "INCONSISTENT", "power")


def post_hoc(model, effect, sizes, alpha):
    _unit("alpha", alpha)
    model.check_sizes(sizes)
    return model.evaluate(effect, sizes, alpha)


def a_priori(model, effect, alpha, power):
    _unit("alpha", alpha)
    _unit("power", power)
    _power_not_below_alpha(alpha, power)
    if abs(effect) <= MIN_ABS_EFFECT_A_PRIORI:
        raise InputError(f"a priori needs |effect size| > {MIN_ABS_EFFECT_A_PRIORI:g}",
                         "OUT_OF_RANGE", "effect_size")

    # Solve for the continuous base size, then round each group up (G*Power's rule).
    def f(n):
        return model.power_at(effect, n, alpha) - power

    lo = hi = float(model.min_n)
    if f(lo) >= 0:
        return model.evaluate(effect, model.round_sizes(lo), alpha)
    while f(hi) < 0:
        lo, hi = hi, hi * 2
        if hi > MAX_N:
            raise AnalysisError(f"target power not reached below n = {MAX_N}")
    try:
        n = brentq(f, lo, hi, xtol=1e-10, rtol=1e-14)
    except (RuntimeError, ValueError) as exc:
        raise ConvergenceError(str(exc)) from exc
    return model.evaluate(effect, model.round_sizes(n), alpha)


def sensitivity(model, sizes, alpha, power):
    _unit("alpha", alpha)
    _unit("power", power)
    _power_not_below_alpha(alpha, power)
    model.check_sizes(sizes)

    def f(e):
        return model.evaluate(e, sizes, alpha)["power"] - power

    lo, hi = 1e-9, 1.0
    if f(lo) >= 0:
        raise AnalysisError("target power is not above alpha; any effect size works")
    while f(hi) < 0:
        hi *= 2
        if hi > 1e4:
            raise AnalysisError("no effect size reaches the target power")
    try:
        effect = brentq(f, lo, hi, xtol=1e-12)
    except (RuntimeError, ValueError) as exc:
        raise ConvergenceError(str(exc)) from exc
    return model.evaluate(effect, sizes, alpha)


def criterion(model, effect, sizes, power):
    _unit("power", power)
    model.check_sizes(sizes)

    def f(a):
        return model.evaluate(effect, sizes, a)["power"] - power

    lo, hi = 1e-12, 1 - 1e-12
    if f(lo) > 0:
        return model.evaluate(effect, sizes, lo)
    if f(hi) < 0:
        raise AnalysisError("target power not reachable for any alpha")
    try:
        alpha = brentq(f, lo, hi, xtol=1e-14)
    except (RuntimeError, ValueError) as exc:
        raise ConvergenceError(str(exc)) from exc
    return model.evaluate(effect, sizes, alpha)


def compromise(model, effect, sizes, q):
    if q <= 0:
        raise ValueError("q (beta/alpha ratio) must be > 0")
    model.check_sizes(sizes)

    # Solve log(beta) = log(q * alpha) on a log-alpha scale: for large effects the
    # answer can be far below 1e-12, and the ratio must hold to relative precision.
    def f(log_a):
        beta = model.evaluate(effect, sizes, math.exp(log_a))["beta"]
        if beta <= 0:
            return -math.inf
        return math.log(beta) - math.log(q) - log_a

    lo, hi = math.log(1e-300), math.log(1 - 1e-12)
    if not (f(lo) > 0 > f(hi)):
        raise AnalysisError("beta/alpha ratio not reachable for this effect and sample size")
    try:
        alpha = math.exp(brentq(f, lo, hi, xtol=1e-13, rtol=1e-14))
    except (RuntimeError, ValueError) as exc:
        raise ConvergenceError(str(exc)) from exc
    result = model.evaluate(effect, sizes, alpha)
    result["beta_alpha_ratio"] = q
    return result
