"""Our solver vs statsmodels, an independent implementation, over a grid."""
import pytest

pytest.importorskip("statsmodels")

from gpower2.difftest import check_statsmodels  # noqa: E402

RESULTS = check_statsmodels()


@pytest.mark.differential
@pytest.mark.parametrize("result", RESULTS, ids=[r["id"] for r in RESULTS])
def test_matches_statsmodels(result):
    assert result["ok"], result["detail"]
