"""The clean-room rewrite (cleanroom/impl, written by a separate agent session from SPEC.md and
CONTRACT.md only) against the oracle and against the main engine.

Two independent implementations that agree with G*Power and with each other on every vector are
the strongest answer we have to "how do you prove the teardown is right?".
"""
import contextlib
import io
import json
import sys
from pathlib import Path

import pytest

from noncentra import contract
from noncentra import difftest_paired as dp

CR = Path(__file__).resolve().parent.parent / "cleanroom" / "impl"
sys.path.insert(0, str(CR))
import gpower_clone as cleanroom  # noqa: E402

sys.path.remove(str(CR))


def run_cleanroom(fields):
    argv = [x for k, v in fields.items() for x in (f"--{k}", str(v))]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            code = cleanroom.main(argv)
        except SystemExit as exc:
            code = exc.code
    lines = buf.getvalue().strip().splitlines()
    assert len(lines) == 1, lines
    return json.loads(lines[0]), code or 0


@pytest.fixture(scope="module")
def results(monkeypatch_module):
    monkeypatch_module.setattr(dp.contract, "run", run_cleanroom)
    gp, sm = dp.check_gpower(), dp.check_statsmodels()
    monkeypatch_module.undo()
    return gp, sm


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_cleanroom_matches_gpower(results):
    gp, _ = results
    bad = [(r["id"], r["detail"]) for r in gp if r["status"] == "mismatch"]
    assert not bad and len(gp) == 109


def test_cleanroom_matches_statsmodels(results):
    _, sm = results
    bad = [(r["id"], r["detail"]) for r in sm if r["status"] == "mismatch"]
    assert not bad and len(sm) == 780


def test_cleanroom_equals_main_engine(results):
    gp, sm = results
    for r in gp + sm:
        a, ca = contract.run(r["input"])
        b, cb = run_cleanroom(r["input"])
        assert ca == cb, (r["id"], a, b)
        if "error" in a:
            assert a["code"] == b["code"], (r["id"], a, b)
            continue
        for key, value in a.items():
            if isinstance(value, int):
                assert b[key] == value, (r["id"], key)
            else:
                assert abs(b[key] - value) <= 1e-9 * max(1.0, abs(value)), (r["id"], key, value, b[key])
