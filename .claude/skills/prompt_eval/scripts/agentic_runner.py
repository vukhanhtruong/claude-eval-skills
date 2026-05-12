"""Agentic runner: handles multi-turn tool loops."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import Anthropic
    from prompt_eval.tool_mocker import ToolMocker


class AgenticRunner:
    """Executes a prompt with tool support, handling the multi-turn loop."""

    def __init__(
        self,
        client: "Anthropic",
        model: str,
        tools: list[dict],
        mocker: "ToolMocker",
        max_turns: int = 5,
    ):
        self.client = client
        self.model = model
        self.tools = tools
        self.mocker = mocker
        self.max_turns = max_turns

    def run(self, prompt: str, case_context: dict) -> tuple[str, list[dict]]:
        """Execute prompt, handling tool calls until completion.
        Returns (final_text, tool_call_log)
        """
        messages: list[dict] = [{"role": "user", "content": prompt}]
        tool_call_log: list[dict] = []
        response = None

        for _ in range(self.max_turns):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=messages,
                tools=self.tools,
            )

            if response.stop_reason == "end_turn":
                return self._extract_text(response), tool_call_log

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        mock_output = self.mocker.get_or_generate(
                            tool_name=block.name,
                            arguments=block.input,
                            case_context=case_context,
                        )
                        tool_call_log.append({
                            "tool": block.name,
                            "input": block.input,
                            "output": mock_output,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": mock_output,
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        return self._extract_text(response) if response else "", tool_call_log

    def _extract_text(self, response) -> str:
        """Extract text content from response."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
