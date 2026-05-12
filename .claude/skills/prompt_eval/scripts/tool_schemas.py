"""Built-in tool schemas and schema drafting utilities."""
from __future__ import annotations

import json
from textwrap import dedent
from typing import TYPE_CHECKING

from anthropic import Anthropic
from prompt_eval._utils import strip_code_fence
from prompt_eval.evaluator import MODEL_MAP

if TYPE_CHECKING:
    from anthropic import Anthropic as AnthropicType


SAFE_BUILTIN_TOOLS: set[str] = {"web_fetch", "web_search"}
RISKY_BUILTIN_TOOLS: set[str] = {"read_file", "bash"}

BUILTIN_TOOLS: dict[str, dict] = {
    "web_fetch": {
        "name": "web_fetch",
        "description": "Fetch content from a URL and return the page content",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch content from"}
            },
            "required": ["url"],
        },
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web and return relevant results",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
    "read_file": {
        "name": "read_file",
        "description": "Read the contents of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to read"}
            },
            "required": ["path"],
        },
    },
    "bash": {
        "name": "bash",
        "description": "Execute a bash command and return the output",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute"}
            },
            "required": ["command"],
        },
    },
}


def get_builtin_schema(tool_name: str) -> dict | None:
    """Return schema if tool_name matches a built-in, else None."""
    return BUILTIN_TOOLS.get(tool_name)


def is_builtin_tool(tool_name: str) -> bool:
    """Check if tool_name is a built-in tool."""
    return tool_name in BUILTIN_TOOLS


def is_safe_builtin(tool_name: str) -> bool:
    """Check if tool_name is a safe built-in (auto-enable without confirmation)."""
    return tool_name in SAFE_BUILTIN_TOOLS


def is_risky_builtin(tool_name: str) -> bool:
    """Check if tool_name is a risky built-in (should warn user)."""
    return tool_name in RISKY_BUILTIN_TOOLS


def draft_custom_schema(
    tool_name: str,
    context: str,
    client: Anthropic | None = None,
) -> dict:
    """Use LLM to draft a schema for an unknown tool based on task context."""
    if client is None:
        client = Anthropic()

    prompt = dedent(f"""
        Generate a tool schema for the following tool name, based on the task context.

        Tool name: {tool_name}
        Task context: {context}

        Infer what this tool likely does based on its name and the task.
        Generate a JSON schema in this exact format:
        {{
            "name": "{tool_name}",
            "description": "What this tool does",
            "input_schema": {{
                "type": "object",
                "properties": {{
                    "param_name": {{"type": "string", "description": "..."}}
                }},
                "required": ["param_name"]
            }}
        }}

        Return ONLY the JSON object. No prose, no markdown fences.
    """)

    response = client.messages.create(
        model=MODEL_MAP["haiku"],
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    return json.loads(strip_code_fence(response.content[0].text))
