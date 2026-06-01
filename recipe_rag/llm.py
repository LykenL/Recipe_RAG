from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from .config import LLMConfig


@dataclass
class LLMClient:
    client: Any
    model: str

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
        client = OpenAI(base_url=config.base_url, api_key=config.api_key)
        return cls(client=client, model=config.model)

    def chat(self, prompt: str, *, max_tokens: int = 250) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()

