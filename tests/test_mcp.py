"""MCP tools return the same documents as the CLI/API."""
import asyncio
import json

import pytest

pytest.importorskip("mcp")

from noncentra import mcp_server  # noqa: E402
from noncentra.api import analyze  # noqa: E402

REQUEST = {"test": "t.two_sample", "analysis": "a_priori",
           "params": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8}}


def call(name, args):
    # Exercise the full MCP path: the client sees the tool result as JSON text content.
    content = asyncio.run(mcp_server.mcp.call_tool(name, args))
    if isinstance(content, tuple):  # newer SDKs return (content, structured)
        content = content[0]
    return json.loads(content[0].text)


def test_tools_are_registered():
    tools = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert {"list_tests", "power_analysis", "explain_result", "run_diff_test"} <= tools


def test_power_analysis_matches_api():
    got = call("power_analysis", REQUEST)
    want = analyze(REQUEST)
    want["input"]["options"] = {}
    assert got == json.loads(json.dumps(want))


def test_power_analysis_reports_errors():
    got = call("power_analysis", {**REQUEST, "test": "t.nope"})
    assert got["error"]["code"] == "invalid_input"


def test_explain_result_mentions_power():
    text = mcp_server.explain_result(analyze(REQUEST))
    assert "0.8015" in text and "n1=64" in text
