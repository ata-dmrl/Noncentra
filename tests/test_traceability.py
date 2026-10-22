"""SPEC.md <-> docs/EVIDENCE.md <-> tests stay consistent (SPEC R-16, R-17, R-07).

The two documents are written for people; these tests read the few structured lines
they share (### R-xx / ### E-xx headings, **Kanıt:** / **Test:** lines, and
`path` · SHA-256 `hex` entries) and fail when a link breaks.
"""
import ast
import hashlib
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "SPEC.md").read_text(encoding="utf-8")
EVIDENCE = (ROOT / "docs" / "EVIDENCE.md").read_text(encoding="utf-8")


def sections(text, prefix):
    """{id: body} for every '### <prefix>-NN · title' heading."""
    parts = re.split(rf"^### ({prefix}-\d+)\b.*$", text, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


REQS = sections(SPEC, "R")
EVIDENCES = sections(EVIDENCE, "E")


def field(body, name):
    m = re.search(rf"^- \*\*{name}:\*\*(.*)$", body, flags=re.M)
    return m.group(1).strip() if m else None


def test_documents_are_not_empty():
    assert len(REQS) >= 17 and len(EVIDENCES) >= 28


@pytest.mark.parametrize("rid", sorted(REQS))
def test_every_requirement_is_traced(rid):
    body = REQS[rid]
    assert "**Kabul kriteri:**" in body, f"{rid} has no acceptance criterion"
    kanit, test = field(body, "Kanıt"), field(body, "Test")
    assert kanit, f"{rid} has no Kanıt line"
    assert test and re.search(r"`tests/[^`]+::\w+`", test), f"{rid} names no test"
    refs = re.findall(r"E-\d+", kanit)
    if not kanit.startswith("tasarım"):
        assert refs, f"{rid} is not a design requirement but cites no evidence"
    unknown = [e for e in refs if e not in EVIDENCES]
    assert not unknown, f"{rid} cites missing evidence {unknown}"


def _test_functions(path):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_referenced_tests_exist():
    missing = []
    for rid, body in REQS.items():
        for path, func in re.findall(r"`(tests/[^`:]+)::(\w+)`", field(body, "Test") or ""):
            if not (ROOT / path).is_file() or func not in _test_functions(path):
                missing.append(f"{rid}: {path}::{func}")
    assert not missing, missing


def test_every_evidence_is_used():
    used = {e for body in REQS.values() for e in re.findall(r"E-\d+", field(body, "Kanıt") or "")}
    # Evidence may also be cited by other evidence (e.g. E-28 explains E-13).
    used |= {e for body in EVIDENCES.values() for e in re.findall(r"E-\d+", body)}
    orphans = sorted(set(EVIDENCES) - used)
    assert not orphans, f"evidence not used by any requirement: {orphans}"


HASHED = re.findall(r"`([^`]+)` (?:\([^)]*\) )?· SHA-256 `([0-9a-f]{64})`", EVIDENCE)


@pytest.mark.parametrize("path, digest", HASHED, ids=[p for p, _ in HASHED])
def test_evidence_hashes_match(path, digest):
    file = ROOT / path
    if not file.exists():
        # Local-only evidence (G*Power itself, dumps from it) is gitignored by design.
        assert path.startswith(("target/", "teardown/evidence/")), f"{path} is missing from the repo"
        pytest.skip(f"{path} is local-only evidence and not present here")
    # Hash as Git stores it, so a Windows checkout with CRLF line endings still matches.
    data = file.read_bytes()
    if file.suffix in (".csv", ".txt", ".json", ".md"):
        data = data.replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == digest, f"{path} changed; update docs/EVIDENCE.md"


def test_no_gpower_artifacts_tracked():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    bad = [p for p in tracked
           if p.startswith(("target/", "teardown/evidence/")) or p.lower().endswith((".exe", ".dll"))]
    assert not bad, f"G*Power material must not be committed: {bad}"


def test_known_divergence_counts():
    """SPEC R-07: 23 known unequal-allocation divergences, 5 where G*Power misses its own target."""
    from noncentra.difftest import run_diff

    summary = run_diff()
    assert summary["failed"] == 0, summary["failures"]
    assert summary["known_divergence"] == 23
    assert summary["gpower_misses_target"] == 5
