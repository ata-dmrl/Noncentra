"""CONTRACT.md §7: the MCP tool returns exactly the CLI's stdout for every public vector."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from noncentra import mcp_contract  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VECTORS = [json.loads(l) for l in (ROOT / "oracle" / "public_vectors.jsonl").read_text().splitlines() if l.strip()]

EXTRA = [  # errors and two-tailed cases, so equivalence is not only about the happy path
    {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.95},
    {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.04},
    {"test": "t-paired", "mode": "post-hoc", "tails": 2, "dz": 0.5, "alpha": 0.05, "n_total": 2},
    {"test": "t-paired", "mode": "post-hoc", "tails": 2, "dz": 0.5, "alpha": 0.05, "n_total": 10.5},
    {"test": "t-paired", "mode": "post-hoc", "tails": 2, "dz": 0.5, "alpha": 0.05},
]
CASES = [v["input"] for v in VECTORS] + EXTRA


def via_mcp(inp):
    content = asyncio.run(mcp_contract.mcp.call_tool("power_analysis", inp))
    if isinstance(content, tuple):
        content = content[0]
    return content[0].text


def via_cli(inp):
    args = [x for k, v in inp.items() for x in (f"--{k}", str(v))]
    r = subprocess.run([sys.executable, "-m", "noncentra.contract_cli", *args],
                       capture_output=True, text=True, timeout=10)
    return r.stdout.strip()


def test_single_tool():
    tools = asyncio.run(mcp_contract.mcp.list_tools())
    assert [t.name for t in tools] == ["power_analysis"]


@pytest.mark.parametrize("inp", CASES, ids=[f"{c['test']}/{c['mode']}/{i}" for i, c in enumerate(CASES)])
def test_mcp_equals_cli(inp):
    assert json.loads(via_mcp(inp)) == json.loads(via_cli(inp))
