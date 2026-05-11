"""Tool mocker: generates and caches mock responses for tool calls.

Thread-safe via per-key locking to prevent duplicate generation when
multiple workers request the same uncached key concurrently.
"""
from __future__ import annotations

import json
import threading
from textwrap import dedent
from typing import TYPE_CHECKING

from prompt_eval.evaluator import MODEL_MAP

if TYPE_CHECKING:
    from anthropic import Anthropic


class ToolMocker:
    """Generates and caches mock responses for tool calls.

    Thread-safe: uses per-key locking to prevent race conditions.
    """

    def __init__(
        self,
        client: "Anthropic | None",
        model: str | None = None,
        task_context: str = "",
        cache: dict | None = None,
    ):
        self.client = client
        self.model = model or MODEL_MAP["haiku"]
        self.task_context = task_context
        self.cache: dict[str, dict] = cache.copy() if cache else {}
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _cache_key(self, tool_name: str, arguments: dict) -> str:
        """Format: tool_name::json(sorted_args)"""
        return f"{tool_name}::{json.dumps(arguments, sort_keys=True)}"

    def _get_lock(self, key: str) -> threading.Lock:
        """Get or create a lock for a specific cache key."""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def get_cache(self) -> dict:
        """Return the cache for persistence."""
        return self.cache

    def get_or_generate(
        self,
        tool_name: str,
        arguments: dict,
        case_context: dict | None = None,
    ) -> str:
        """Return cached mock or generate a new one. Thread-safe."""
        key = self._cache_key(tool_name, arguments)

        with self._get_lock(key):
            if key in self.cache:
                return self.cache[key]["content"]

            mock = self._generate_mock(tool_name, arguments, case_context or {})
            self.cache[key] = {"content": mock, "generated_by": "haiku"}
            return mock

    def _generate_mock(self, tool_name: str, arguments: dict, case_context: dict) -> str:
        """Use LLM to generate a realistic mock response."""
        if self.client is None:
            raise ValueError("Cannot generate mock without Anthropic client")

        scenario = case_context.get("scenario", "")
        prompt_inputs = case_context.get("prompt_inputs", {})

        prompt = dedent(f"""
            Generate a realistic mock response for this tool call.

            Task: {self.task_context}
            Test scenario: {scenario}
            Test inputs: {json.dumps(prompt_inputs)}

            Tool: {tool_name}
            Arguments: {json.dumps(arguments, indent=2)}

            Return ONLY the mock response content (as the tool would return it).
            Make it realistic and useful for this specific test case.
            Keep it concise but complete enough to be useful.
        """)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
