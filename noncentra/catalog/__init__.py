"""Registry of the statistical tests the solver knows about."""
from .f_tests import AnovaOneWay, RegressionR2, RegressionR2Increase
from .t_tests import OneSampleT, PairedT, TwoSampleT

TESTS = {
    cls.name: cls
    for cls in (TwoSampleT, OneSampleT, PairedT, AnovaOneWay, RegressionR2, RegressionR2Increase)
}


def get_test(name: str, **options):
    try:
        cls = TESTS[name]
    except KeyError:
        raise ValueError(f"unknown test {name!r}; known: {sorted(TESTS)}") from None
    unknown = set(options) - set(cls.option_names())
    if unknown:
        raise ValueError(f"{name} does not take options {sorted(unknown)}; it takes {cls.option_names()}")
    return cls(**options)


def describe_tests() -> list[dict]:
    return [cls.describe() for cls in TESTS.values()]
