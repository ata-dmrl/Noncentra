"""t-test family. Formulas follow Faul et al. (2007) / Cohen (1988), not G*Power code.

"""
import math

from ..core.distributions import t_power
from .base import TestModel


class _TModel(TestModel):
    def __init__(self, tails: int = 2):
        if tails not in (1, 2):
            raise ValueError("tails must be 1 or 2")
        self.tails = tails

    @classmethod
    def option_names(cls) -> list[str]:
        return ["tails"]

    def power_terms(self, ncp, df, alpha):
        return t_power(ncp, df, alpha, self.tails)

    def extra_output(self):
        return {"tails": self.tails}


class TwoSampleT(_TModel):
    name = "t.two_sample"
    title = "Means: difference between two independent means (two groups)"
    size_keys = ("n1", "n2")

    def __init__(self, tails: int = 2, ratio: float = 1.0):
        super().__init__(tails)
        if ratio <= 0:
            raise ValueError("ratio (n2/n1) must be > 0")
        self.ratio = ratio

    @classmethod
    def option_names(cls) -> list[str]:
        return ["tails", "ratio"]

    def sizes_from_n(self, n):
        return {"n1": n, "n2": n * self.ratio}

    def noncentrality(self, effect, sizes):
        n1, n2 = sizes["n1"], sizes["n2"]
        return effect * math.sqrt(n1 * n2 / (n1 + n2)), n1 + n2 - 2


class OneSampleT(_TModel):
    name = "t.one_sample"
    title = "Means: difference from constant (one sample case)"
    size_keys = ("n",)

    def sizes_from_n(self, n):
        return {"n": n}

    def noncentrality(self, effect, sizes):
        n = sizes["n"]
        return effect * math.sqrt(n), n - 1


class PairedT(OneSampleT):
    """Matched pairs: same math as one sample, with d = d_z on the differences."""

    name = "t.paired"
    title = "Means: difference between two dependent means (matched pairs)"
    effect_name = "dz"

    # G*Power 3.1.9.7 refuses N < 3 whenever N is an input ("Total sample size is
    # outside the admissible range (3, 2147483646)", oracle p027-p030, p047), yet its
    # a priori analysis may return N = 2 (p010, p012-p015). min_n stays 2 for a priori.
    min_n_given = 3
