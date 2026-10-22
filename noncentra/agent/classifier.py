"""System 1 step: pick the test family fast, never a number.

The assignment suggests Jev; we had no Jev access, so this is an LLM restricted to the same
label set through a forced tool call (README says so). Default model is the small, fast one.
"""
import os

from .prompts import CLASSIFIER_SYSTEM, CLASSIFY_TOOL, LABELS

DEFAULT_CLASSIFIER_MODEL = os.environ.get("NONCENTRA_CLASSIFIER_MODEL", "claude-haiku-5-5")


def classify(client, question: str, model: str | None = None) -> dict:
    resp = client.messages.create(
        model=model or DEFAULT_CLASSIFIER_MODEL, max_tokens=200, system=CLASSIFIER_SYSTEM,
        tools=[CLASSIFY_TOOL], tool_choice={"type": "tool", "name": "classify"},
        messages=[{"role": "user", "content": question}],
    )
    block = next(b for b in resp.content if b.type == "tool_use")
    label = block.input.get("label")
    confidence = float(block.input.get("confidence", 0))
    if label not in LABELS:
        label, confidence = "ambiguous", 0.0
    return {"label": label, "confidence": max(0.0, min(1.0, confidence)),
            "reason": block.input.get("reason", ""),
            "tokens_in": resp.usage.input_tokens, "tokens_out": resp.usage.output_tokens}
