"""Core evaluator: dataset generation + GEval-based grading."""
import os
import re

# Opt out of DeepEval telemetry before any deepeval import
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")


MODEL_MAP = {
    "haiku":  "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-7",
}


def render_prompt(template: str, variables: dict) -> str:
    """Substitute {var} placeholders. Unknown vars stay literal. {{ }} escapes."""
    placeholders = re.findall(r"{([^{}]+)}", template)
    result = template
    for ph in placeholders:
        if ph in variables:
            result = result.replace("{" + ph + "}", str(variables[ph]))
    return result.replace("{{", "{").replace("}}", "}")


import concurrent.futures
import json
import time
from textwrap import dedent
from typing import Callable, Optional
from anthropic import Anthropic
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from prompt_eval.anthropic_llm import AnthropicLLM


def _chat(client, model, messages, system=None, temperature=1.0, stop_sequences=None):
    params = {
        "model": model,
        "max_tokens": 8192,
        "messages": messages,
        "temperature": temperature,
        "stop_sequences": stop_sequences or [],
    }
    if system:
        params["system"] = system
    return client.messages.create(**params).content[0].text


def _strip_code_fence(text: str) -> str:
    """Tolerate models that wrap JSON in ```json ... ``` even when told not to."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


class DatasetGenerator:
    """Generate diverse test cases for a prompt-evaluation task using Claude."""

    def __init__(self, model: str = "claude-haiku-4-5", max_concurrent_tasks: int = 3):
        self.model = model
        self.max_concurrent_tasks = max_concurrent_tasks
        self.client = Anthropic()

    def generate_unique_ideas(self, task_description, prompt_inputs_spec, num_cases):
        example_inputs = ",".join(
            f'"{k}": str # {v}' for k, v in prompt_inputs_spec.items()
        )
        prompt = dedent(f"""
            Generate {num_cases} unique, diverse ideas for testing a prompt that accomplishes this task:

            <task_description>
            {task_description}
            </task_description>

            The prompt will receive the following inputs:
            <prompt_inputs>
            {example_inputs}
            </prompt_inputs>

            Each idea should represent a distinct scenario testing different aspects of the task.

            Output Format:
            Provide a JSON array where each item is a brief description of the idea.

            Ensure each idea is:
            - Distinct from the others
            - Relevant to the task
            - Specific enough to guide a full test case
            - Solvable with no more than 400 tokens

            Generate exactly {num_cases} ideas.

            Respond with ONLY the JSON array. No prose, no markdown fences.
        """)
        text = _chat(
            self.client,
            self.model,
            [{"role": "user", "content": prompt}],
            system="You are a test scenario designer.",
        )
        return json.loads(_strip_code_fence(text))

    def generate_test_case(self, task_description, idea, prompt_inputs_spec):
        allowed_keys = ", ".join(f'"{k}"' for k in prompt_inputs_spec.keys())
        example_inputs = "\n".join(
            f'    "{k}": "EXAMPLE_VALUE", // {v}' for k, v in prompt_inputs_spec.items()
        )
        prompt = dedent(f"""
            Generate a single detailed test case for prompt evaluation based on:

            <task_description>
            {task_description}
            </task_description>

            <specific_idea>
            {idea}
            </specific_idea>

            <allowed_input_keys>
            {allowed_keys}
            </allowed_input_keys>

            Output Format:
            ```json
            {{
                "prompt_inputs": {{
            {example_inputs}
                }},
                "solution_criteria": ["criterion 1", "criterion 2"]
            }}
            ```

            REQUIREMENTS:
            - Use ONLY these input keys: {allowed_keys}
            - Include all required keys
            - Solution criteria: 1-4 concise items, tied to the core task
            - Solvable with no more than 400 tokens

            Respond with ONLY the JSON object. No prose, no markdown fences.
        """)
        text = _chat(
            self.client,
            self.model,
            [{"role": "user", "content": prompt}],
            system="You are a test case creator.",
            temperature=0.7,
        )
        case = json.loads(_strip_code_fence(text))
        case["task_description"] = task_description
        case["scenario"] = idea
        return case

    def generate_dataset(
        self, task_description, prompt_inputs_spec, num_cases, output_file
    ):
        ideas = self.generate_unique_ideas(
            task_description, prompt_inputs_spec, num_cases
        )
        dataset = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_tasks
        ) as ex:
            futures = [
                ex.submit(self.generate_test_case, task_description, idea, prompt_inputs_spec)
                for idea in ideas
            ]
            for f in concurrent.futures.as_completed(futures):
                try:
                    dataset.append(f.result())
                except Exception as e:
                    print(f"Error generating test case: {e}")

        with open(output_file, "w") as f:
            json.dump(dataset, f, indent=2)
        return dataset


class Evaluator:
    """Run test cases through a prompt and grade the outputs with GEval."""

    def __init__(
        self,
        test_model: str = "claude-haiku-4-5",
        judge_model: str = "claude-sonnet-4-6",
        max_concurrent_tasks: int = 3,
        tools: list[dict] | None = None,
        max_tool_turns: int = 5,
    ):
        self.test_model = test_model
        self.judge_model = judge_model
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tools = tools
        self.max_tool_turns = max_tool_turns
        self.client = Anthropic()

    def run_test_case(self, test_case: dict, prompt_template: str) -> str:
        """Render the template with test_case inputs and call the test model."""
        rendered = render_prompt(prompt_template, test_case["prompt_inputs"])
        return _chat(
            self.client,
            self.test_model,
            [{"role": "user", "content": rendered}],
        )

    def run_test_case_with_tools(
        self,
        test_case: dict,
        prompt_template: str,
        task_context: str,
        mock_cache: dict,
    ) -> tuple[str, list[dict], dict]:
        """Run a test case with tools enabled.
        Note: mock_cache is mutated in place by ToolMocker.
        """
        from prompt_eval.tool_mocker import ToolMocker
        from prompt_eval.agentic_runner import AgenticRunner

        rendered = render_prompt(prompt_template, test_case["prompt_inputs"])
        mocker = ToolMocker(
            client=self.client,
            task_context=task_context,
            cache=mock_cache,
        )
        runner = AgenticRunner(
            client=self.client,
            model=self.test_model,
            tools=self.tools,
            mocker=mocker,
            max_turns=self.max_tool_turns,
        )
        output, tool_log = runner.run(rendered, case_context=test_case)
        mock_cache.update(mocker.cache)
        return output, tool_log, mock_cache

    def grade_with_geval(
        self,
        test_case: dict,
        output: str,
        extra_criteria: str | None = None,
    ) -> dict:
        """Score one (test_case, output) pair using GEval with Claude as judge."""
        criteria_lines = "\n".join(f"- {c}" for c in test_case["solution_criteria"])
        if extra_criteria:
            criteria_lines += f"\n\nMandatory:\n{extra_criteria}"

        metric = GEval(
            name="Task Quality",
            evaluation_steps=[
                f"Evaluate the output against these criteria:\n{criteria_lines}",
                "Score 1-10 where 10 = fully meets all criteria.",
            ],
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=AnthropicLLM(self.judge_model),
        )
        tc = LLMTestCase(
            input=str(test_case["prompt_inputs"]),
            actual_output=output,
        )
        metric.measure(tc)
        return {
            "score": round(metric.score * 10),
            "reasoning": metric.reason,
        }

    def run_evaluation(
        self,
        dataset: list,
        prompt_template: str,
        output_file: str,
        extra_criteria: str | None = None,
        on_case_complete: Optional[
            Callable[[int, dict, str, str, int, str, int], None]
        ] = None,
        task_context: str = "",
        mock_cache: dict | None = None,
    ) -> list:
        """Run + grade every case in the dataset; write JSON to output_file.

        If ``on_case_complete`` is provided, it's called once per case with
        ``(index, case, rendered_prompt, output, score, reasoning, latency_ms)``.
        ``index`` is the case's position in the input dataset (captured at
        submit time, stable under parallel execution). The callback may run
        from worker threads; callees must be thread-safe.
        """
        shared_cache: dict = mock_cache if mock_cache is not None else {}

        def _process(indexed_case):
            index, case = indexed_case
            t0 = time.monotonic()
            rendered = render_prompt(prompt_template, case["prompt_inputs"])
            if self.tools:
                output, tool_log, _ = self.run_test_case_with_tools(
                    case, prompt_template, task_context, shared_cache
                )
            else:
                output = self.run_test_case(case, prompt_template)
                tool_log = None
            grade = self.grade_with_geval(case, output, extra_criteria)
            latency_ms = int((time.monotonic() - t0) * 1000)
            if on_case_complete is not None:
                on_case_complete(
                    index, case, rendered, output,
                    grade["score"], grade["reasoning"], latency_ms,
                )
            result = {
                "test_case": case,
                "output": output,
                "score": grade["score"],
                "reasoning": grade["reasoning"],
            }
            if tool_log is not None:
                result["tool_log"] = tool_log
            return result

        results = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_tasks
        ) as ex:
            for fut in concurrent.futures.as_completed(
                [ex.submit(_process, ic) for ic in enumerate(dataset)]
            ):
                results.append(fut.result())

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        return results
