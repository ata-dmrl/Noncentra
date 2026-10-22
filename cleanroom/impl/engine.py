"""t-paired güç analizi motoru (SPEC.md §1-§2). Tüm hesap mantığı burada.

Dış arayüz: compute(mode, params) -> dict  ya da EngineError fırlatır.
params, tür dönüşümü yapılmış değerlerdir (tails/n_total int, diğerleri float).
"""
import math

from scipy import optimize
from scipy.stats import nct, t as tdist

MODES = ("a-priori", "post-hoc", "compromise", "criterion", "sensitivity")
MODE_INPUTS = {
    "a-priori": ("tails", "dz", "alpha", "power"),
    "post-hoc": ("tails", "dz", "alpha", "n_total"),
    "compromise": ("tails", "dz", "beta_alpha_ratio", "n_total"),
    "criterion": ("tails", "dz", "power", "n_total"),
    "sensitivity": ("tails", "alpha", "power", "n_total"),
}
INT_FIELDS = ("tails", "n_total")


class EngineError(Exception):
    def __init__(self, code, field, message):
        super().__init__(message)
        self.code, self.field, self.message = code, field, message


# ------------------------------------------------------------------ çekirdek
def _nct_quad(x, df, ncp, upper):
    """Yedek: P(T<=x) ya da P(T>x), T=(Z+δ)/sqrt(V/df) tanımından sayısal integral."""
    from scipy import integrate
    from scipy.stats import chi2, norm
    g = (lambda v: chi2.pdf(v, df) * norm.sf(x * math.sqrt(v / df) - ncp)) if upper else \
        (lambda v: chi2.pdf(v, df) * norm.cdf(x * math.sqrt(v / df) - ncp))
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return float(integrate.quad(g, 0, math.inf, limit=500, epsabs=0, epsrel=1e-12)[0])


def nct_cdf(x, df, ncp):
    v = float(nct.cdf(x, df, ncp))
    return v if math.isfinite(v) else _nct_quad(x, df, ncp, upper=False)


def nct_sf(x, df, ncp):
    v = float(nct.sf(x, df, ncp))
    return v if math.isfinite(v) else _nct_quad(x, df, ncp, upper=True)


def critical_t(alpha, df, tails):
    """SPEC §1.1: merkezi t'nin üst α (tek) ya da α/2 (çift) niceliği."""
    a = alpha if tails == 1 else alpha / 2.0
    return float(tdist.isf(a, df))


def alpha_from_crit(c, df, tails):
    a = float(tdist.sf(c, df))
    return a if tails == 1 else 2.0 * a


def power_beta(c, df, ncp, tails):
    """(power, beta). β kendi kuyruğundan hesaplanır (SPEC §1.1)."""
    upper = nct_sf(c, df, ncp)
    if tails == 1:
        return upper, nct_cdf(c, df, ncp)
    lower = nct_cdf(-c, df, ncp)
    power = upper + lower
    beta = nct_cdf(c, df, ncp) - lower
    return power, beta


def power_at(n, dz, alpha, tails):
    df = n - 1
    return power_beta(critical_t(alpha, df, tails), df, dz * math.sqrt(n), tails)[0]


def _base(n, dz, crit):
    return {"ncp": dz * math.sqrt(n), "critical_t": crit, "df": int(n - 1)}


# ------------------------------------------------------------------ modlar
def a_priori(tails, dz, alpha, power):
    """SPEC §1.3: power(N) >= hedef sağlayan en küçük tam sayı N, alt sınır 2.
    Güç N'de monoton arttığından tam sayı ikili araması ⌈N*⌉ ile aynı sonucu verir."""
    lo = 2
    if power_at(lo, dz, alpha, tails) >= power:
        n = lo
    else:
        hi = 4
        while power_at(hi, dz, alpha, tails) < power:
            lo, hi = hi, hi * 2
            if hi > 10**9:
                raise EngineError("NO_SOLUTION", None, "N bulunamadı")
        while hi - lo > 1:  # değişmez: power(lo) < hedef <= power(hi)
            mid = (lo + hi) // 2
            if power_at(mid, dz, alpha, tails) >= power:
                hi = mid
            else:
                lo = mid
        n = hi
    df = n - 1
    crit = critical_t(alpha, df, tails)
    out = _base(n, dz, crit)
    out["n_total"] = int(n)
    out["actual_power"] = power_beta(crit, df, dz * math.sqrt(n), tails)[0]
    return out


def post_hoc(tails, dz, alpha, n_total):
    df = n_total - 1
    crit = critical_t(alpha, df, tails)
    out = _base(n_total, dz, crit)
    out["power"] = power_beta(crit, df, out["ncp"], tails)[0]
    return out


def _root(f, lo, hi):
    return optimize.brentq(f, lo, hi, xtol=1e-15, rtol=4 * 2.220446049250313e-16, maxiter=500)


def _bracket(f, lo, hi, grow_lo=True):
    """f(lo)<0<f(hi) olacak şekilde aralığı genişletir."""
    for _ in range(200):
        flo, fhi = f(lo), f(hi)
        if flo < 0 < fhi:
            return lo, hi
        if fhi <= 0:
            hi = hi * 2 + 1
        if flo >= 0:
            if not grow_lo:
                break
            lo = lo * 2 - 1
    raise EngineError("NO_SOLUTION", None, "Çözüm aralığı bulunamadı")


def compromise(tails, dz, beta_alpha_ratio, n_total):
    """β = oran · α koşulunu sağlayan kritik değer (SPEC §1.2)."""
    df = n_total - 1
    ncp = dz * math.sqrt(n_total)
    r = beta_alpha_ratio

    def f(c):
        a = alpha_from_crit(c, df, tails)
        b = power_beta(c, df, ncp, tails)[1]
        if a <= 0 or b <= 0:
            return -1.0 if b <= 0 else 1.0
        return math.log(b) - math.log(r) - math.log(a)

    lo, hi = (0.0, 10.0) if tails == 2 else (-1.0, 10.0)
    if tails == 2:
        lo = 1e-12
    lo, hi = _bracket(f, lo, hi, grow_lo=(tails == 1))
    c = _root(f, lo, hi)
    alpha = alpha_from_crit(c, df, tails)
    power, beta = power_beta(c, df, ncp, tails)
    out = _base(n_total, dz, c)
    out.update(alpha=alpha, beta=beta, power=power)
    return out


def criterion(tails, dz, power, n_total):
    """Hedef gücü veren α (SPEC §1.2)."""
    df = n_total - 1
    ncp = dz * math.sqrt(n_total)
    if tails == 1:
        c = float(nct.isf(power, df, ncp))
        if not math.isfinite(c):
            c = _root(lambda x: nct_sf(x, df, ncp) - power, *_bracket(lambda x: power - nct_sf(x, df, ncp), -10.0, 10.0))
    else:
        f = lambda c: power - power_beta(c, df, ncp, 2)[0]  # c'de artan
        lo, hi = 0.0, 10.0
        if f(lo) >= 0:
            raise EngineError("NO_SOLUTION", "power", "Bu güç hiçbir α ile sağlanamıyor")
        lo, hi = _bracket(f, lo, hi, grow_lo=False)
        c = _root(f, lo, hi)
    alpha = alpha_from_crit(c, df, tails)
    if not (0.0 < alpha < 1.0):
        raise EngineError("NO_SOLUTION", "power", "Geçerli α bulunamadı")
    out = _base(n_total, dz, c)
    out["alpha"] = alpha
    return out


def sensitivity(tails, alpha, power, n_total):
    """Hedef gücü veren pozitif dz (SPEC §1.2, §5)."""
    df = n_total - 1
    crit = critical_t(alpha, df, tails)
    sq = math.sqrt(n_total)
    f = lambda d: power_beta(crit, df, d * sq, tails)[0] - power  # d'de artan
    if f(0.0) >= 0:
        dz = 0.0  # güç = α sınırı (SPEC'te yok: dz = 0 döndürülür)
    else:
        lo, hi = _bracket(f, 0.0, 1.0, grow_lo=False)
        dz = _root(f, lo, hi)
    out = _base(n_total, dz, crit)
    out["dz"] = dz
    return out


# ------------------------------------------------------------- doğrulama
def validate(mode, p):
    """CONTRACT §5 aralıkları, ardından SPEC §2 tablosu (sırasıyla)."""
    order = MODE_INPUTS[mode]
    # CONTRACT §5
    for k in order:
        v = p[k]
        bad = {
            "tails": v not in (1, 2),
            "alpha": not (0.0 < v < 1.0),
            "power": not (0.0 < v < 1.0),
            "beta_alpha_ratio": not (v > 0.0),
            "dz": not (v > 0.0),
            "n_total": v < 2,
        }[k]
        if bad:
            raise EngineError("OUT_OF_RANGE", k, f"{k} izin verilen aralığın dışında")
    # SPEC §2 (tablo sırası)
    for k in ("alpha", "power"):
        if k in p and p[k] < 1e-07:
            raise EngineError("OUT_OF_RANGE", k, f"{k} [1e-07, 1) aralığında olmalı")
    if mode in ("a-priori", "sensitivity") and p["power"] < p["alpha"]:
        raise EngineError("INCONSISTENT", "power", "Power, alpha değerinden küçük olamaz")
    if mode == "a-priori" and abs(p["dz"]) <= 0.00001:
        raise EngineError("OUT_OF_RANGE", "dz", "|dz| 0.00001'den büyük olmalı")
    if mode != "a-priori" and p["n_total"] < 3:
        raise EngineError("OUT_OF_RANGE", "n_total", "n_total en az 3 olmalı")


def compute(mode, params):
    if mode not in MODES:
        raise EngineError("UNSUPPORTED", "mode", f"Bilinmeyen mod: {mode}")
    validate(mode, params)
    fn = {"a-priori": a_priori, "post-hoc": post_hoc, "compromise": compromise,
          "criterion": criterion, "sensitivity": sensitivity}[mode]
    return fn(**{k: params[k] for k in MODE_INPUTS[mode]})
