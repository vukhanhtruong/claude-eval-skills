"""DeepEval adapter so GEval uses Claude instead of GPT-4."""
from anthropic import Anthropic
from deepeval.models import DeepEvalBaseLLM


class AnthropicLLM(DeepEvalBaseLLM):
    def __init__(self, model: str = "claude-haiku-4-5"):
        self.model = model
        self.client = Anthropic()

    def load_model(self):
        return self.client

    def generate(self, prompt: str, schema=None) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    async def a_generate(self, prompt: str, schema=None) -> str:
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return self.model
