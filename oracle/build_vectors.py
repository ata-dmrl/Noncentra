"""Turn every G*Power harvest into CONTRACT.md vectors: python -I oracle/build_vectors.py

Sources (all collected from the running G*Power 3.1.9.7 GUI):
  noncentra/reference/t_tests_harvested.csv, t_tests_ratio_harvested.csv  (t2-indep, t-paired)
  noncentra/reference/f_tests_harvested.csv                               (anova-oneway, multireg-r2)
  oracle/t-paired/boundary_harvest.csv                                    (t-paired edges, erva)
  oracle/<family>/harvest.csv                                             (later harvests, same layout as above)

Output: oracle/gpower_vectors.jsonl, one {"id","source","input","expected"} or
{"id","source","input","expected_error"} per line. Expected values are the 7-digit numbers
G*Power displayed, read from the `raw` column, so nothing here is computed.
"""
import ast
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "oracle" / "gpower_vectors.jsonl"

MODE = {"a_priori": "a-priori", "post_hoc": "post-hoc", "sensitivity": "sensitivity",
        "criterion": "criterion", "compromise": "compromise"}

# CONTRACT.md §4: inputs and outputs per family and mode (G*Power label for each field).
FAMILIES = {
    "t2-indep": {
        "source_test": "t.two_sample", "effect": ("d", "Effect size d"), "crit": ("critical_t", "Critical t"),
        "df": [("df", "Df")], "sizes": [("n1", "Sample size group 1"), ("n2", "Sample size group 2")],
        "extra_in": {"tails": "Tail(s)"}, "ratio": True,
    },
    "t-paired": {
        "source_test": "t.paired", "effect": ("dz", "Effect size dz"), "crit": ("critical_t", "Critical t"),
        "df": [("df", "Df")], "sizes": [("n_total", "Total sample size")], "extra_in": {"tails": "Tail(s)"},
    },
    "anova-oneway": {
        "source_test": "f.anova_oneway", "effect": ("f", "Effect size f"), "crit": ("critical_f", "Critical F"),
        "df": [("df1", "Numerator df"), ("df2", "Denominator df")], "sizes": [("n_total", "Total sample size")],
        "extra_in": {"groups": "Number of groups"},
    },
    "multireg-r2": {
        "source_test": "f.regression_r2", "effect": ("f2", "Effect size f²"), "crit": ("critical_f", "Critical F"),
        "df": [("df1", "Numerator df"), ("df2", "Denominator df")], "sizes": [("n_total", "Total sample size")],
        "extra_in": {"predictors": "Number of predictors"},
    },
    "chi2-contingency": {
        "source_test": "chi2.contingency", "effect": ("w", "Effect size w"), "crit": ("critical_chi2", "Critical χ²"),
        "df": [], "sizes": [("n_total", "Total sample size")], "extra_in": {"df": "Df"},
    },
}
BY_SOURCE = {spec["source_test"]: fam for fam, spec in FAMILIES.items()}


def num(text):
    v = float(text)
    return int(v) if v.is_integer() and abs(v) < 2**53 else v


def tails_value(text):
    return {"One": 1, "Two": 2}[text]


def vector(fam, mode, raw):
    """Build CONTRACT input/expected from the fields G*Power showed after Calculate."""
    spec = FAMILIES[fam]
    eff_key, eff_label = spec["effect"]
    crit_key, crit_label = spec["crit"]
    inp = {"test": fam, "mode": mode}
    for key, label in spec["extra_in"].items():
        inp[key] = tails_value(raw[label]) if key == "tails" else num(raw[label])
    if mode != "sensitivity":
        inp[eff_key] = num(raw[eff_label])
    if mode in ("a-priori", "post-hoc", "sensitivity"):
        inp["alpha"] = num(raw["α err prob"])
    if mode in ("a-priori", "sensitivity", "criterion"):
        inp["power"] = num(raw["Power (1-β err prob)"])
    if mode == "compromise":
        inp["beta_alpha_ratio"] = num(raw["β/α ratio"])
    if mode == "a-priori":
        if spec.get("ratio"):
            inp["ratio"] = num(raw["Allocation ratio N2/N1"])
    else:
        for key, label in spec["sizes"]:
            inp[key] = num(raw[label])

    exp = {"ncp": num(raw[next(k for k in raw if k.startswith("Noncentrality parameter"))]),
           crit_key: num(raw[crit_label])}
    for key, label in spec["df"]:
        exp[key] = num(raw[label])
    if mode == "a-priori":
        for key, label in spec["sizes"]:
            exp[key] = num(raw[label])
        if spec.get("ratio"):
            exp["n_total"] = num(raw["Total sample size"])
        exp["actual_power"] = num(raw["Actual power"])
    elif mode == "post-hoc":
        exp["power"] = num(raw["Power (1-β err prob)"])
    elif mode == "compromise":
        exp.update(alpha=num(raw["α err prob"]), beta=num(raw["β err prob"]), power=num(raw["Power (1-β err prob)"]))
    elif mode == "criterion":
        exp["alpha"] = num(raw["α err prob"])
    else:
        exp[eff_key] = num(raw[eff_label])
    return inp, exp


def case_input(fam, mode, case):
    """CONTRACT input from the case a harvest typed in (used when G*Power refused it)."""
    inp = {"test": fam, "mode": mode}
    for key in ("tails", "groups", "df", "predictors", "alpha", "power", "ratio", "n1", "n2"):
        if key in case:
            inp[key] = case[key]
    if "effect_size" in case:
        inp[FAMILIES[fam]["effect"][0]] = case["effect_size"]
    if "q" in case:
        inp["beta_alpha_ratio"] = case["q"]
    if "n" in case:
        inp["n_total"] = case["n"]
    return inp


def expected_code(inp, dialog):
    """Contract error code for an input G*Power refused: §5 ranges first, then G*Power's own message.

    Values that are each valid but meaningless together are INCONSISTENT (CONTRACT §2.4 uses
    'power below alpha' as its INCONSISTENT example). G*Power's N >= 3 floor for t tests lies
    inside the contract's N >= 2 range; the contract does not say which code fits, so it is left
    open (None: any error with a non-zero exit passes).
    """
    code = contract_level_error(inp)
    if code:
        return code
    text = dialog or ""
    if "Power must be greater than or equal to alpha" in text or "Sample size must be greater than" in text:
        return "INCONSISTENT"
    return None


def refused(raw):
    return any(v == "?" for k, v in raw.items() if not k.startswith("_"))


def from_harvest(path, source):
    vectors = []
    for row in csv.DictReader(path.open(encoding="utf-8")):
        fam = BY_SOURCE.get(row["test"])
        if fam is None:
            continue  # one-sample t and R² increase are outside the contract
        raw = ast.literal_eval(row["raw"])
        if row.get("case") and refused(raw):
            inp = case_input(fam, MODE[row["analysis"]], json.loads(row["case"]))
            vectors.append({"id": f"{path.parent.name}/{row['id']}", "source": source, "input": inp,
                            "expected_error": {"code": expected_code(inp, raw.get("_dialog"))},
                            "gpower_dialog": raw.get("_dialog"), "screenshots": row.get("screenshots")})
            continue
        if "_dialog" in raw and row["analysis"] == "a_priori":
            continue
        try:
            inp, exp = vector(fam, MODE[row["analysis"]], raw)
        except KeyError as exc:
            raise KeyError(f"{path.name} {row['id']}: G*Power field {exc} missing") from None
        vid = f"{path.parent.name}/{row['id']}" if row.get("case") else f"{path.stem}/{row['id']}"
        v = {"id": vid, "source": source, "input": inp, "expected": exp}
        if row.get("screenshots"):
            v["screenshots"] = row["screenshots"]
        if row.get("known_divergence"):
            v["note"] = row["known_divergence"]
        if "_dialog" in raw:
            v["gpower_warning"] = raw["_dialog"]
        vectors.append(v)
    return vectors


# erva's boundary harvest: rows G*Power refused become expected errors. The code is our
# reading of CONTRACT.md §2.4/§5 for that input, not something G*Power reports.
def paired_boundary(path):
    vectors = []
    for row in csv.DictReader(path.open(encoding="utf-8")):
        mode = MODE[row["analysis"]]
        inp = {"test": "t-paired", "mode": mode, "tails": int(row["tails"])}
        for key, col in (("dz", "effect_size"), ("alpha", "alpha"), ("power", "power"),
                         ("beta_alpha_ratio", "beta_alpha_ratio"), ("n_total", "n")):
            if row[col] != "":
                inp[key] = num(row[col])
        vid = f"boundary_harvest/{row['id']}"
        contract_error = contract_level_error(inp)
        if contract_error or row["dialog"]:
            vectors.append({"id": vid, "source": "gpower-gui+screenshot", "input": inp,
                            "expected_error": {"code": expected_code(inp, row["dialog"])},
                            "gpower_dialog": row["dialog"] or None, "screenshots": row["screenshots"]})
            continue
        if row["taken"] != "yes":
            continue  # G*Power changed an input silently (e.g. rounded a fractional N)
        raw = ast.literal_eval(row["raw"])
        try:
            inp2, exp = vector("t-paired", mode, raw)
        except (KeyError, ValueError):
            continue
        vectors.append({"id": vid, "source": "gpower-gui+screenshot", "input": inp2, "expected": exp,
                        "screenshots": row["screenshots"]})
    return vectors


def contract_level_error(inp):
    """CONTRACT.md §5 ranges, independent of G*Power: these must be OUT_OF_RANGE / INVALID_VALUE."""
    for key in ("n_total", "n1", "n2"):
        if key in inp and not float(inp[key]).is_integer():
            return "INVALID_VALUE"
    for key in ("alpha", "power"):
        if key in inp and not 0 < inp[key] < 1:
            return "OUT_OF_RANGE"
    for key in ("d", "dz", "f", "w", "f2", "ratio", "beta_alpha_ratio"):
        if key in inp and inp[key] <= 0:
            return "OUT_OF_RANGE"
    for key in ("n_total", "n1", "n2", "groups"):
        if key in inp and inp[key] < 2:
            return "OUT_OF_RANGE"
    return None


def main():
    ref = ROOT / "noncentra" / "reference"
    vectors = []
    for name in ("t_tests_harvested.csv", "t_tests_ratio_harvested.csv", "f_tests_harvested.csv"):
        vectors += from_harvest(ref / name, "gpower-gui")
    vectors += paired_boundary(ROOT / "oracle" / "t-paired" / "boundary_harvest.csv")
    for extra in sorted((ROOT / "oracle").glob("*/harvest.csv")):
        vectors += from_harvest(extra, "gpower-gui+screenshot")
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for v in vectors:
            fh.write(json.dumps(v, ensure_ascii=False) + "\n")
    by = {}
    for v in vectors:
        key = v["input"]["test"] + ("/error" if "expected_error" in v else "")
        by[key] = by.get(key, 0) + 1
    print(f"{len(vectors)} vectors -> {OUT.relative_to(ROOT)}", by)


if __name__ == "__main__":
    main()
