"""CONTRACT.md §9: the 25 public vectors and the vectors harvested from G*Power.

Red until the clean-room implementation (src/) provides `gpower-clone`.
"""
import pytest

from harness import check_vector, command, load

pytestmark = pytest.mark.contract

PUBLIC = load("public_vectors.jsonl")
GPOWER = load("gpower_vectors.jsonl")


@pytest.fixture(autouse=True)
def _cli_present():
    if command() is None:
        pytest.fail("gpower-clone not found; install src/ (pip install -e .) or set GPOWER_CLONE")


@pytest.mark.parametrize("vector", PUBLIC, ids=[v["id"] for v in PUBLIC])
def test_public_vector(vector):
    ok, detail = check_vector(vector)
    assert ok, detail["problem"]
    assert detail["elapsed"] < 2.0, f"took {detail['elapsed']:.2f}s (limit 2s)"


@pytest.mark.parametrize("vector", GPOWER, ids=[v["id"] for v in GPOWER])
def test_gpower_vector(vector):
    ok, detail = check_vector(vector)
    if not ok and vector.get("note"):
        pytest.xfail(f"known divergence: {vector['note']}")
    assert ok, detail["problem"]
