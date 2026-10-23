"""t-paired differential test: G*Power vectors and the statsmodels grid, through gpower-clone.

The same run writes tests/T_PAIRED_DIFF_REPORT.md
(python -m noncentra.difftest_paired --report tests/T_PAIRED_DIFF_REPORT.md).
"""
import pytest

from noncentra import difftest_paired as dp

GPOWER = dp.check_gpower()
STATSMODELS = dp.check_statsmodels()


@pytest.mark.differential
@pytest.mark.parametrize("r", GPOWER, ids=[f"{r['source']}:{r['id']}" for r in GPOWER])
def test_against_gpower(r):
    assert r["status"] != "mismatch", r["detail"]


@pytest.mark.differential
@pytest.mark.parametrize("r", STATSMODELS, ids=[r["id"] for r in STATSMODELS])
def test_against_statsmodels(r):
    assert r["status"] != "mismatch", r["detail"]


def test_scale():
    # Assignment: at least 30 G*Power vectors with screenshots and more than 500 library vectors.
    assert sum(r["source"] == "boundary_harvest.csv" for r in GPOWER) >= 30
    assert len(STATSMODELS) > 500


def test_gpower_a_priori_n_exact():
    # The gate counts exact N on a priori vectors; every a priori row is either an exact
    # match or an input both G*Power and the contract refuse.
    ap = [r for r in GPOWER if r["mode"] == "a-priori"]
    assert all(r["status"] in ("match", "explained") for r in ap)
    assert sum(r["status"] == "match" for r in ap) / len(ap) >= 0.9
