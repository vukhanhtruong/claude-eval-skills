"""Shared utilities for prompt_eval."""
from __future__ import annotations


def strip_code_fence(text: str) -> str:
    """Remove markdown code fences if present.

    Tolerate models that wrap JSON in ```json ... ``` even when told not to.
    Handles ```json, ```, and plain text.
    """
    text = text.strip()
    if text.startswith("```"):
        # Remove first line (```json or ```)
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()
