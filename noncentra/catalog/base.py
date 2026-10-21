"""Shared plumbing for test models.

A model maps (effect size, sample sizes) to a noncentrality parameter and degrees of
freedom, and names the distribution that turns those into power. noncentra.core.solver
does the rest, so adding a test means writing `noncentrality` and `sizes_from_n`.
"""
import math


class TestModel:
    name = ""
    title = ""
    effect_name = "d"
    min_n = 2
    size_keys: tuple[str, ...] = ()

    @classmethod
    def describe(cls) -> dict:
        return {
            "name": cls.name,
            "title": cls.title,
            "effect_size": cls.effect_name,
            "sizes": list(cls.size_keys),
            "options": cls.option_names(),
        }

    @classmethod
    def option_names(cls) -> list[str]:
        return []

    def sizes_from_n(self, n: float) -> dict:
        """Group sizes for a (possibly fractional) base size n, before rounding."""
        raise NotImplementedError

    def round_sizes(self, n: float) -> dict:
        # Observed in G*Power 3.1.9.7 (teardown harvest): every group is rounded up
        # from the continuous solution separately.
        return {k: max(self.min_n, math.ceil(v - 1e-9)) for k, v in self.sizes_from_n(n).items()}

    def noncentrality(self, effect: float, sizes: dict):
        """Return (noncentrality, df); df is a number or a (numerator, denominator) pair."""
        raise NotImplementedError

    def power_terms(self, ncp, df, alpha) -> tuple[float, float, float]:
        """Return (power, beta, critical value)."""
        raise NotImplementedError

    def power_at(self, effect: float, n: float, alpha: float) -> float:
        ncp, df = self.noncentrality(effect, self.sizes_from_n(n))
        return self.power_terms(ncp, df, alpha)[0]

    def check_sizes(self, sizes: dict) -> None:
        missing = [k for k in self.size_keys if k not in sizes]
        if missing:
            raise ValueError(f"{self.name} needs sample sizes {missing}")
        for k in self.size_keys:
            if int(sizes[k]) != sizes[k] or sizes[k] < self.min_n:
                raise ValueError(f"{k} must be an integer >= {self.min_n}")

    def extra_output(self) -> dict:
        return {}

    def evaluate(self, effect: float, sizes: dict, alpha: float) -> dict:
        ncp, df = self.noncentrality(effect, sizes)
        power, beta, crit = self.power_terms(ncp, df, alpha)
        out = {
            "power": power,
            "alpha": alpha,
            "beta": beta,
            "effect_size": effect,
            "sizes": {k: int(v) for k, v in sizes.items()},
            "n_total": int(sum(sizes.values())),
            "noncentrality": ncp,
            "critical_value": crit,
        }
        if isinstance(df, tuple):
            out["df_num"], out["df"] = df
        else:
            out["df"] = df
        out.update(self.extra_output())
        return out
