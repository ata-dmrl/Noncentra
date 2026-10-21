"""Drive a running G*Power main window and harvest reference values.

The input and output panels are rows of (Static label, Edit/ComboBox) pairs; we pair
them by screen row, so the script does not depend on control IDs, which G*Power
reassigns when the test changes.

usage: python teardown/harvest.py <gpower_pid> <out.csv> [family ...]
       family: t (t tests), f (F tests); default all
"""
import csv
import itertools
import sys

import win32ui as w

ID_FAMILY, ID_TEST, ID_ANALYSIS, ID_CALCULATE = 1000, 1001, 1002, 1009

ANALYSES = {"a_priori": "A priori", "post_hoc": "Post hoc", "sensitivity": "Sensitivity",
            "criterion": "Criterion", "compromise": "Compromise"}

# noncentra test -> how G*Power names it and labels its fields.
SPECS = {
    "t.two_sample": {"family": "t tests", "title": "Means: Difference between two independent means (two groups)",
                     "effect": "Effect size d", "critical": "Critical t"},
    "t.one_sample": {"family": "t tests", "title": "Means: Difference from constant (one sample case)",
                     "effect": "Effect size d", "critical": "Critical t"},
    "t.paired": {"family": "t tests", "title": "Means: Difference between two dependent means (matched pairs)",
                 "effect": "Effect size dz", "critical": "Critical t"},
    "f.anova_oneway": {"family": "F tests", "title": "ANOVA: Fixed effects, omnibus, one-way",
                       "effect": "Effect size f", "critical": "Critical F",
                       "options": {"groups": "Number of groups"}},
    "f.regression_r2": {"family": "F tests",
                        "title": "Linear multiple regression: Fixed model, R² deviation from zero",
                        "effect": "Effect size f²", "critical": "Critical F",
                        "options": {"predictors": "Number of predictors"}},
    "f.regression_r2_increase": {"family": "F tests",
                                 "title": "Linear multiple regression: Fixed model, R² increase",
                                 "effect": "Effect size f²", "critical": "Critical F",
                                 "options": {"tested": "Number of tested predictors",
                                             "predictors": "Total number of predictors"}},
}


class GPower:
    def __init__(self, pid):
        self.pid = pid
        self.hwnd = w.main_window(pid)
        w.dismiss_dialogs(pid)

    def _controls(self):
        return [c for c in w.children(self.hwnd) if c["visible"]]

    def _by_id(self, cid):
        return next(c["hwnd"] for c in self._controls() if c["id"] == cid)

    def fields(self):
        """label -> control for every visible parameter row."""
        ctrls = self._controls()
        labels = [c for c in ctrls if c["cls"] == "Static" and c["text"]]
        values = [c for c in ctrls if c["cls"] in ("Edit", "ComboBox")
                  and c["id"] not in (ID_FAMILY, ID_TEST, ID_ANALYSIS)]
        out = {}
        for lab in labels:
            row = [v for v in values if abs(v["rect"][1] - lab["rect"][1]) <= 3
                   and v["rect"][0] > lab["rect"][0] and v["parent"] == lab["parent"]]
            if row:
                out[lab["text"].strip()] = min(row, key=lambda v: v["rect"][0])
        return out

    def select(self, test, analysis):
        spec = SPECS[test]
        w.combo_select(self._by_id(ID_FAMILY), spec["family"])
        w.wait(0.3)
        w.combo_select(self._by_id(ID_TEST), spec["title"])
        w.wait(0.3)
        w.combo_select(self._by_id(ID_ANALYSIS), ANALYSES[analysis])
        w.wait(0.3)

    def set(self, label, value, exact=False):
        fields = self.fields()
        matches = {k: v for k, v in fields.items() if (k == label if exact else k.startswith(label))}
        if len(matches) != 1:
            raise KeyError(f"{label!r} matched {list(matches)} among {list(fields)}")
        ctrl = next(iter(matches.values()))
        if ctrl["cls"] == "ComboBox":
            w.combo_select(ctrl["hwnd"], str(value))
        else:
            w.set_text(ctrl["hwnd"], str(value))

    def calculate(self):
        # BM_CLICK is posted, not sent: a modal warning would otherwise block the call.
        w.user32.PostMessageW(self._by_id(ID_CALCULATE), w.BM_CLICK, 0, 0)
        w.wait(0.5)
        notes = w.dismiss_dialogs(self.pid)
        out = {k: w.get_text(v["hwnd"]) for k, v in self.fields().items()}
        if notes:
            out["_dialog"] = " | ".join(notes)
        return out


def _num(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def t_cases():
    effects, alphas, powers, tails = (0.2, 0.5, 0.8), (0.01, 0.05), (0.8, 0.95), (1, 2)
    for test in ("t.two_sample", "t.one_sample", "t.paired"):
        for d, a, p, t in itertools.product(effects, alphas, powers, tails):
            yield {"test": test, "analysis": "a_priori", "tails": t, "effect_size": d, "alpha": a, "power": p}
        for n, d, a, t in itertools.product((10, 25, 60), (0.3, 0.7), (0.05,), tails):
            yield {"test": test, "analysis": "post_hoc", "tails": t, "effect_size": d, "alpha": a, "n": n}
        for n, t in itertools.product((12, 40), tails):
            yield {"test": test, "analysis": "sensitivity", "tails": t, "alpha": 0.05, "power": 0.8, "n": n}
            yield {"test": test, "analysis": "criterion", "tails": t, "effect_size": 0.5, "power": 0.8, "n": n}
            yield {"test": test, "analysis": "compromise", "tails": t, "effect_size": 0.5, "q": 1, "n": n}
    for ratio in (0.5, 2, 3):
        yield {"test": "t.two_sample", "analysis": "a_priori", "tails": 2, "effect_size": 0.5,
               "alpha": 0.05, "power": 0.8, "ratio": ratio}


def f_cases():
    designs = ([("f.anova_oneway", {"groups": k}, (0.1, 0.25, 0.4)) for k in (2, 3, 5)]
               + [("f.regression_r2", {"predictors": p}, (0.02, 0.15, 0.35)) for p in (1, 3, 8)]
               + [("f.regression_r2_increase", {"predictors": p, "tested": q}, (0.02, 0.15, 0.35))
                  for p, q in ((3, 1), (6, 2), (10, 4))])
    for test, opts, effects in designs:
        n_small, n_big = sum(opts.values()) + 12, sum(opts.values()) + 80
        for e, a, p in itertools.product(effects, (0.01, 0.05), (0.8, 0.95)):
            yield {"test": test, "analysis": "a_priori", **opts, "effect_size": e, "alpha": a, "power": p}
        for e, n in itertools.product(effects[1:], (n_small, n_big)):
            yield {"test": test, "analysis": "post_hoc", **opts, "effect_size": e, "alpha": 0.05, "n": n}
        for n in (n_small, n_big):
            yield {"test": test, "analysis": "sensitivity", **opts, "alpha": 0.05, "power": 0.8, "n": n}
            yield {"test": test, "analysis": "criterion", **opts, "effect_size": effects[1], "power": 0.8, "n": n}
            yield {"test": test, "analysis": "compromise", **opts, "effect_size": effects[1], "q": 1, "n": n}


FAMILIES = {"t": t_cases, "f": f_cases}


def run_case(gp, case):
    spec = SPECS[case["test"]]
    gp.select(case["test"], case["analysis"])
    if "tails" in case:
        gp.set("Tail(s)", "Two" if case["tails"] == 2 else "One")
    for opt, label in spec.get("options", {}).items():
        gp.set(label, case[opt], exact=True)
    if "effect_size" in case:
        gp.set(spec["effect"], case["effect_size"], exact=True)
    if "alpha" in case:
        gp.set("α err prob", case["alpha"])
    if "power" in case:
        gp.set("Power", case["power"])
    if "q" in case:
        gp.set("β/α ratio", case["q"])
    if case["test"] == "t.two_sample":
        if "n" in case:
            gp.set("Sample size group 1", case["n"])
            gp.set("Sample size group 2", case["n"])
        else:
            gp.set("Allocation ratio", case.get("ratio", 1))
    elif "n" in case:
        gp.set("Total sample size", case["n"])
    return gp.calculate()


COLUMNS = ["id", "test", "analysis", "tails", "ratio", "groups", "predictors", "tested", "effect_size",
           "alpha", "power", "beta_alpha_ratio", "n1", "n2", "n", "exp_n1", "exp_n2", "exp_n", "exp_power",
           "exp_critical", "exp_effect", "exp_alpha", "known_divergence", "source", "raw"]


def to_row(i, case, out):
    spec = SPECS[case["test"]]
    two = case["test"] == "t.two_sample"
    row = {"id": f"h{i:03d}_{case['test'].split('.')[1]}_{case['analysis']}", "test": case["test"],
           "analysis": case["analysis"], "tails": case.get("tails", ""),
           "ratio": case.get("ratio", 1) if two else "",
           "effect_size": case.get("effect_size", ""), "alpha": case.get("alpha", ""),
           "power": case.get("power", ""), "beta_alpha_ratio": case.get("q", ""),
           "source": "gpower-3.1.9.7-harvest", "raw": repr(out)}
    for opt in spec.get("options", {}):
        row[opt] = case[opt]
    if "n" in case:
        row.update({"n1": case["n"], "n2": case["n"]} if two else {"n": case["n"]})
    if case["analysis"] == "a_priori":
        if two:
            row["exp_n1"] = int(_num(out.get("Sample size group 1")))
            row["exp_n2"] = int(_num(out.get("Sample size group 2")))
        else:
            row["exp_n"] = int(_num(out.get("Total sample size")))
    power_key = "Actual power" if case["analysis"] == "a_priori" else "Power (1-β err prob)"
    row["exp_power"] = out.get(power_key, "")
    row["exp_critical"] = out.get(spec["critical"], "")
    if case["analysis"] == "sensitivity":
        row["exp_effect"] = out.get(spec["effect"], "")
    if case["analysis"] in ("criterion", "compromise"):
        row["exp_alpha"] = out.get("α err prob", "")
    return row


def check_echo(case, out):
    """G*Power must show back the inputs we typed; otherwise the row is not trustworthy."""
    spec = SPECS[case["test"]]
    want = {label: case[opt] for opt, label in spec.get("options", {}).items()}
    if "effect_size" in case and case["analysis"] != "sensitivity":
        want[spec["effect"]] = case["effect_size"]
    if "alpha" in case:
        want["α err prob"] = case["alpha"]
    if "n" in case and case["test"] != "t.two_sample":
        want["Total sample size"] = case["n"]
    bad = {k: (v, out.get(k)) for k, v in want.items() if _num(out.get(k)) != float(v)}
    if bad:
        raise ValueError(f"G*Power did not take inputs: {bad}")


def main(pid, out_path, *families):
    gp = GPower(int(pid))
    rows, failures = [], 0
    for fam in families or tuple(FAMILIES):
        for case in FAMILIES[fam]():
            i = len(rows) + failures
            try:
                out = run_case(gp, case)
                check_echo(case, out)
                rows.append(to_row(i, case, out))
            except Exception as exc:  # keep harvesting; record the failure
                failures += 1
                print(f"case {i} {case}: {exc!r}", file=sys.stderr)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows -> {out_path}, {failures} failed")


if __name__ == "__main__":
    main(*sys.argv[1:])
