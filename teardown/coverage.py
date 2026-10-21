"""Coverage matrix: G*Power's test menu (from ui_catalog.json) vs what noncentra implements.

usage: python -I teardown/coverage.py teardown/evidence/ui_catalog.json docs/coverage.md
"""
import json
import sys

FAMILIES = ("Correlation and regression", "Means", "Proportions", "Variances", "Generic")

# G*Power menu entry -> (noncentra test name, verified against G*Power output?)
IMPLEMENTED = {
    ("Means", "One group: Difference from constant"): ("t.one_sample", True),
    ("Means", "Two dependent groups (matched pairs)"): ("t.paired", True),
    ("Means", "Two independent groups"): ("t.two_sample", True),
    ("Means", "Many groups: ANOVA: One-way (one independent variable)"): ("f.anova_oneway", True),
    ("Correlation and regression", "Linear multiple regression: Fixed model, R² deviation from zero"):
        ("f.regression_r2", True),
    ("Correlation and regression", "Linear multiple regression: Fixed model, R² increase"):
        ("f.regression_r2_increase", True),
}


def menu_tests(catalog):
    items = next(m["items"] for m in catalog["menus"] if m["id"] == 128)
    start, end = items.index("&Tests") + 1, items.index("&Calculator")
    family, tests = None, []
    for item in items[start:end]:
        if item in FAMILIES:
            family = item
        else:
            tests.append((family, item.replace("�", "²")))
    return tests


def main(catalog_path, out_path):
    catalog = json.load(open(catalog_path, encoding="utf-8"))
    tests = menu_tests(catalog)
    lines = ["# Kapsam matrisi: G*Power 3.1.9.7 → Noncentra", "",
             "Kaynak: `GPowerNT.exe` ana menüsü (kaynak 128), `teardown/catalog_extract.py` ile çıkarıldı.", "",
             "| Aile | G*Power testi | Noncentra | G*Power ile doğrulandı |", "|---|---|---|---|"]
    done = 0
    for family, name in tests:
        impl = IMPLEMENTED.get((family, name))
        done += impl is not None
        lines.append(f"| {family} | {name} | {f'`{impl[0]}`' if impl else '–'} | "
                     f"{('evet' if impl[1] else 'hayır') if impl else '–'} |")
    lines[3:3] = [f"**{done} / {len(tests)}** test uygulandı.", ""]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"{done}/{len(tests)} implemented")


if __name__ == "__main__":
    main(*sys.argv[1:3])
