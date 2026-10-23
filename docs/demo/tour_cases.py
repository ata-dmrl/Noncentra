"""Cases shown in the tour video: one per family and per analysis mode.

Each case is written once and translated to the three front ends that run it:
the G*Power GUI (teardown/harvest_contract.fill), the Noncentra web page (URL hash)
and the gpower-clone CLI (CONTRACT.md flags).
"""

CASES = [
    {"key": "t2_apriori", "title": "t testi, iki bağımsız grup · a priori",
     "family": "t2-indep", "web": "t.two_sample", "gp": "t.two_sample", "analysis": "a_priori",
     "tails": 2, "effect_size": 0.5, "alpha": 0.05, "power": 0.95, "ratio": 1},
    {"key": "paired_apriori", "title": "t testi, eşleştirilmiş · a priori",
     "family": "t-paired", "web": "t.paired", "gp": "t.paired", "analysis": "a_priori",
     "tails": 1, "effect_size": 0.5, "alpha": 0.05, "power": 0.95},
    {"key": "anova_apriori", "title": "Tek yönlü ANOVA (5 grup) · a priori",
     "family": "anova-oneway", "web": "f.anova_oneway", "gp": "f.anova_oneway", "analysis": "a_priori",
     "groups": 5, "effect_size": 0.25, "alpha": 0.05, "power": 0.95},
    {"key": "reg_apriori", "title": "Çoklu regresyon R² (2 yordayıcı) · a priori",
     "family": "multireg-r2", "web": "f.regression_r2", "gp": "f.regression_r2", "analysis": "a_priori",
     "predictors": 2, "effect_size": 0.15, "alpha": 0.05, "power": 0.95},
    {"key": "t2_posthoc", "title": "t testi, iki bağımsız grup · post hoc (ulaşılan güç)",
     "family": "t2-indep", "web": "t.two_sample", "gp": "t.two_sample", "analysis": "post_hoc",
     "tails": 2, "effect_size": 0.5, "alpha": 0.05, "n1": 30, "n2": 30},
    {"key": "anova_sens", "title": "Tek yönlü ANOVA (3 grup) · sensitivity (etki büyüklüğü)",
     "family": "anova-oneway", "web": "f.anova_oneway", "gp": "f.anova_oneway", "analysis": "sensitivity",
     "groups": 3, "alpha": 0.05, "power": 0.8, "n": 60},
    {"key": "paired_crit", "title": "t testi, eşleştirilmiş · criterion (gerekli α)",
     "family": "t-paired", "web": "t.paired", "gp": "t.paired", "analysis": "criterion",
     "tails": 2, "effect_size": 0.5, "power": 0.95, "n": 45},
    {"key": "reg_comp", "title": "Çoklu regresyon R² (5 yordayıcı) · compromise (β/α = 2)",
     "family": "multireg-r2", "web": "f.regression_r2", "gp": "f.regression_r2", "analysis": "compromise",
     "predictors": 5, "effect_size": 0.15, "q": 2, "n": 60},
    {"key": "t2_ratio", "title": "Eşit olmayan grup oranı (n2/n1 = 3) · bilinen fark",
     "family": "t2-indep", "web": "t.two_sample", "gp": "t.two_sample", "analysis": "a_priori",
     "tails": 2, "effect_size": 0.5, "alpha": 0.05, "power": 0.8, "ratio": 3},
]

CLI_MODE = {"a_priori": "a-priori", "post_hoc": "post-hoc", "sensitivity": "sensitivity",
            "criterion": "criterion", "compromise": "compromise"}
EFFECT_FLAG = {"t2-indep": "d", "t-paired": "dz", "anova-oneway": "f", "multireg-r2": "f2",
               "chi2-contingency": "w"}

# What to compare, as (label, CLI output key, G*Power field label).
COMPARE = {
    "a_priori": [("N toplam", "n_total", "Total sample size"), ("Gerçek güç", "actual_power", "Actual power")],
    "post_hoc": [("Güç", "power", "Power (1-β err prob)")],
    "sensitivity": [("Etki büyüklüğü", None, None)],
    "criterion": [("α", "alpha", "α err prob")],
    "compromise": [("α", "alpha", "α err prob"), ("Güç", "power", "Power (1-β err prob)")],
}
COMMON = [("Merkezdışılık", "ncp", ("Noncentrality parameter δ", "Noncentrality parameter λ")),
          ("Kritik değer", ("critical_t", "critical_f"), ("Critical t", "Critical F"))]


def cli_args(case):
    fam = case["family"]
    args = ["--test", fam, "--mode", CLI_MODE[case["analysis"]]]
    if "tails" in case:
        args += ["--tails", case["tails"]]
    if "effect_size" in case:
        args += [f"--{EFFECT_FLAG[fam]}", case["effect_size"]]
    for key, flag in (("alpha", "alpha"), ("power", "power"), ("q", "beta_alpha_ratio"),
                      ("ratio", "ratio"), ("groups", "groups"), ("predictors", "predictors"),
                      ("n1", "n1"), ("n2", "n2"), ("n", "n_total")):
        if key in case:
            args += [f"--{flag}", case[key]]
    return [str(a) for a in args]


def web_hash(case):
    from urllib.parse import urlencode
    p = {"test": case["web"], "analysis": case["analysis"]}
    for key, name in (("tails", "tails"), ("ratio", "ratio"), ("groups", "groups"),
                      ("predictors", "predictors"), ("effect_size", "effect_size"), ("alpha", "alpha"),
                      ("power", "power"), ("q", "beta_alpha_ratio"), ("n", "n"), ("n1", "n1"), ("n2", "n2")):
        if key in case:
            p[name] = case[key]
    return urlencode(p)


def gp_case(case):
    keys = ("analysis", "tails", "groups", "predictors", "effect_size", "alpha", "power", "q", "ratio",
            "n1", "n2", "n")
    return {k: case[k] for k in keys if k in case}
