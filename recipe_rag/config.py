from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str


def load_env(dotenv_path: str | os.PathLike[str] | None = None) -> None:
    if dotenv_path is None:
        load_dotenv()
        return
    load_dotenv(dotenv_path=Path(dotenv_path))


def load_llm_config() -> LLMConfig:
    api_key = (
        os.getenv("OPENAI_API", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1"
    model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
    if "embed" in model.lower():
        raise ValueError(
            f"OPENAI_MODEL={model!r} looks like an embedding model. "
            "Use a chat/instruct model (e.g. meta/llama-3.1-70b-instruct or gpt-4o-mini)."
        )
    if not api_key:
        raise ValueError(
            "Missing OPENAI_API. Set it in your environment or in a .env file."
        )
    return LLMConfig(api_key=api_key, base_url=base_url, model=model)

