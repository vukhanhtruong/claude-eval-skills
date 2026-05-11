"""Tool discovery: analyze outputs to detect tool needs.

Note: These functions are implemented but not wired into CLI commands
in this release. They are exposed for future SKILL.md orchestration.
"""
from __future__ import annotations

import json
from textwrap import dedent

from anthropic import Anthropic

from prompt_eval._utils import strip_code_fence
from prompt_eval.evaluator import MODEL_MAP
from prompt_eval.tool_schemas import is_builtin_tool, is_safe_builtin, RISKY_BUILTIN_TOOLS


def detect_tool_needs(
    output: str,
    task_description: str,
    client: Anthropic | None = None,
) -> list[str]:
    """Analyze Claude's output to detect if it mentions needing tools."""
    if client is None:
        client = Anthropic()

    prompt = dedent(f"""
        Analyze this LLM output. Did it:
        1. Explicitly say it cannot access external data/tools?
        2. Hallucinate plausible-looking content it couldn't actually have?
        3. Ask the user for content it would need a tool to fetch?

        Task: {task_description}

        Output:
        {output}

        If any of the above apply, list the tools that would be needed:
        - Fetch URLs/web pages → "web_fetch"
        - Search the web → "web_search"
        - Read files → "read_file"
        - Run commands → "bash"
        - MCP or custom tools → return the tool name as mentioned

        Return a JSON array of tool names needed, or [] if none.
        Example: ["web_fetch", "mcp__slack__post"]

        Return ONLY the JSON array.
    """)

    response = client.messages.create(
        model=MODEL_MAP["haiku"],
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return json.loads(strip_code_fence(response.content[0].text))


def classify_detected_tools(detected: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Separate detected tools into safe builtins, risky builtins, and custom."""
    safe = [t for t in detected if is_safe_builtin(t)]
    risky = [t for t in detected if t in RISKY_BUILTIN_TOOLS]
    custom = [t for t in detected if not is_builtin_tool(t)]
    return safe, risky, custom


def detect_tool_needs_batch(
    outputs: list[str],
    task_description: str,
    client: Anthropic | None = None,
) -> dict[int, list[str]]:
    """Batch version of detect_tool_needs."""
    if client is None:
        client = Anthropic()
    result = {}
    for i, output in enumerate(outputs):
        result[i] = detect_tool_needs(output, task_description, client)
    return result
