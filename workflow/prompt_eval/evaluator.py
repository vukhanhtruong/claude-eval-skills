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
