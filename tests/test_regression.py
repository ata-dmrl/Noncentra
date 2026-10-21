"""Golden values: every row in noncentra/reference/*.csv must reproduce."""
import pytest

from noncentra.difftest import check_reference_row, load_reference

ROWS = load_reference()


@pytest.mark.regression
@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_reference_row(row):
    result = check_reference_row(row)
    assert result["ok"], result["detail"]
