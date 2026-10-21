"""F-test family. Formulas follow Faul et al. (2007, 2009) / Cohen (1988), not G*Power code.

All three tests use lambda = f^2 * N with a noncentral F distribution.
"""
import math

from ..core.distributions import f_power
from .base import TestModel


class _FModel(TestModel):
    size_keys = ("n",)

    def sizes_from_n(self, n):
        return {"n": n}

    def power_terms(self, ncp, df, alpha):
        return f_power(ncp, df[0], df[1], alpha)


class AnovaOneWay(_FModel):
    name = "f.anova_oneway"
    title = "ANOVA: Fixed effects, omnibus, one-way"
    effect_name = "f"

    def __init__(self, groups: int = 2):
        if int(groups) != groups or groups < 2:
            raise ValueError("groups must be an integer >= 2")
        self.groups = int(groups)
        self.min_n = self.groups + 1

    @classmethod
    def option_names(cls):
        return ["groups"]

    def round_sizes(self, n):
        # Observed in G*Power 3.1.9.7 (f=.25, k=3 -> N=159): a priori N is rounded up
        # to a multiple of the number of groups, i.e. equal group sizes.
        per_group = math.ceil(n / self.groups - 1e-9)
        return {"n": max(self.min_n, per_group * self.groups)}

    def noncentrality(self, effect, sizes):
        n = sizes["n"]
        return effect ** 2 * n, (self.groups - 1, n - self.groups)

    def extra_output(self):
        return {"groups": self.groups}


class RegressionR2(_FModel):
    """Linear multiple regression, fixed model, R^2 deviation from zero (all predictors)."""

    name = "f.regression_r2"
    title = "Linear multiple regression: Fixed model, R² deviation from zero"
    effect_name = "f2"

    def __init__(self, predictors: int = 1):
        if int(predictors) != predictors or predictors < 1:
            raise ValueError("predictors must be an integer >= 1")
        self.predictors = int(predictors)
        self.min_n = self.predictors + 2

    @classmethod
    def option_names(cls):
        return ["predictors"]

    def noncentrality(self, effect, sizes):
        n = sizes["n"]
        return effect * n, (self.predictors, n - self.predictors - 1)

    def extra_output(self):
        return {"predictors": self.predictors}


class RegressionR2Increase(_FModel):
    """Linear multiple regression, fixed model, R^2 increase (q tested of p total predictors)."""

    name = "f.regression_r2_increase"
    title = "Linear multiple regression: Fixed model, R² increase"
    effect_name = "f2"

    def __init__(self, predictors: int = 2, tested: int = 1):
        if int(predictors) != predictors or int(tested) != tested or not 1 <= tested <= predictors:
            raise ValueError("need integers 1 <= tested <= predictors")
        self.predictors, self.tested = int(predictors), int(tested)
        self.min_n = self.predictors + 2

    @classmethod
    def option_names(cls):
        return ["predictors", "tested"]

    def noncentrality(self, effect, sizes):
        n = sizes["n"]
        return effect * n, (self.tested, n - self.predictors - 1)

    def extra_output(self):
        return {"predictors": self.predictors, "tested": self.tested}
