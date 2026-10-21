"""Thin wrappers around scipy's (noncentral) distributions.

Every power function returns (power, beta, critical_value). beta is computed from
its own tail rather than as 1 - power, so it stays accurate when power is near 1
(the compromise analysis divides by it).
"""
import math

from scipy import stats


def nct_cdf(x: float, df: float, ncp: float) -> float:
    # scipy 1.15's nct returns NaN for some far tails (e.g. df=173, ncp=15, x=-1.6).
    # The reflection P(T <= x | ncp) = P(T >= -x | -ncp) evaluates the other branch.
    value = stats.nct.cdf(x, df, ncp)
    if math.isnan(value):
        value = stats.nct.sf(-x, df, -ncp)
    if math.isnan(value):
        raise ArithmeticError(f"noncentral t cdf undefined at x={x}, df={df}, ncp={ncp}")
    return float(value)


def nct_sf(x: float, df: float, ncp: float) -> float:
    return nct_cdf(-x, df, -ncp)


def f_power(ncp: float, df_num: float, df_den: float, alpha: float) -> tuple[float, float, float]:
    """Power, beta and critical value of an F test with noncentrality lambda = `ncp`."""
    crit = float(stats.f.isf(alpha, df_num, df_den))
    if ncp == 0:
        # scipy 1.15's ncf.sf returns -cdf (negative) at exactly zero noncentrality.
        power = float(stats.f.sf(crit, df_num, df_den))
        return power, 1.0 - power, crit
    power = float(stats.ncf.sf(crit, df_num, df_den, ncp))
    beta = float(stats.ncf.cdf(crit, df_num, df_den, ncp))
    if math.isnan(power) or math.isnan(beta):
        raise ArithmeticError(f"noncentral F undefined at df=({df_num}, {df_den}), ncp={ncp}")
    return power, beta, crit


def _finite(values):
    return [float(v) if math.isfinite(v) else None for v in values]


def t_densities(xs, df, ncp):
    """(central, noncentral) t densities on xs; non-finite values become None (JSON null)."""
    return _finite(stats.t.pdf(xs, df)), _finite(stats.nct.pdf(xs, df, ncp))


def f_densities(xs, df_num, df_den, ncp):
    """(central, noncentral) F densities on xs; at ncp=0 both are the central F."""
    central = stats.f.pdf(xs, df_num, df_den)
    noncentral = central if ncp == 0 else stats.ncf.pdf(xs, df_num, df_den, ncp)
    return _finite(central), _finite(noncentral)


def f_upper(df_num, df_den, ncp, q=0.995):
    """A plot range end that holds q of the noncentral F mass."""
    try:
        value = float(stats.ncf.ppf(q, df_num, df_den, ncp) if ncp else stats.f.ppf(q, df_num, df_den))
    except (ValueError, OverflowError):
        value = math.nan
    return value if math.isfinite(value) else df_den * (df_num + ncp) / (df_num * max(df_den - 2, 1)) * 3


def t_power(ncp: float, df: float, alpha: float, tails: int) -> tuple[float, float, float]:
    """Power, beta and critical value of a t test with noncentrality `ncp`."""
    if tails == 2:
        crit = float(stats.t.isf(alpha / 2, df))
        lower, upper = nct_cdf(-crit, df, ncp), nct_sf(crit, df, ncp)
        power = lower + upper
        beta = max(0.0, 1.0 - lower - upper) if power < 0.5 else nct_cdf(crit, df, ncp) - lower
    elif tails == 1:
        crit = float(stats.t.isf(alpha, df))
        power = nct_sf(crit, df, ncp)
        beta = nct_cdf(crit, df, ncp)
    else:
        raise ValueError("tails must be 1 or 2")
    return power, beta, crit
