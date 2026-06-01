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
        hydrate_config_from_streamlit_secrets()
        return
    load_dotenv(dotenv_path=Path(dotenv_path))
    hydrate_config_from_streamlit_secrets()


def _streamlit_secret(*keys: str) -> str:
    """Read top-level or nested Streamlit Cloud secrets (st.secrets)."""
    try:
        import streamlit as st
    except ImportError:
        return ""

    try:
        secrets = st.secrets
    except Exception:
        return ""

    for key in keys:
        try:
            if key in secrets:
                return str(secrets[key]).strip()
        except Exception:
            pass

    for section in ("openai", "nvidia", "llm", "api"):
        try:
            if section not in secrets:
                continue
            block = secrets[section]
            for key in keys:
                if key in block:
                    return str(block[key]).strip()
            if "OPENAI_API" in keys or "OPENAI_API_KEY" in keys:
                for alt in ("OPENAI_API", "OPENAI_API_KEY", "api_key", "api"):
                    if alt in block:
                        return str(block[alt]).strip()
            if "OPENAI_BASE_URL" in keys:
                for alt in ("OPENAI_BASE_URL", "base_url"):
                    if alt in block:
                        return str(block[alt]).strip()
            if "OPENAI_MODEL" in keys:
                for alt in ("OPENAI_MODEL", "model"):
                    if alt in block:
                        return str(block[alt]).strip()
        except Exception:
            continue
    return ""


def hydrate_config_from_streamlit_secrets() -> None:
    """Copy Streamlit Cloud secrets into os.environ for the rest of the app."""
    pairs = (
        ("OPENAI_API", ("OPENAI_API", "OPENAI_API_KEY")),
        ("OPENAI_API_KEY", ("OPENAI_API_KEY", "OPENAI_API")),
        ("OPENAI_BASE_URL", ("OPENAI_BASE_URL",)),
        ("OPENAI_MODEL", ("OPENAI_MODEL",)),
    )
    for env_name, secret_keys in pairs:
        if os.getenv(env_name, "").strip():
            continue
        value = _streamlit_secret(*secret_keys)
        if value:
            os.environ[env_name] = value


def _config_value(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    value = _streamlit_secret(*keys)
    if value:
        return value
    return default


def load_llm_config() -> LLMConfig:
    hydrate_config_from_streamlit_secrets()
    api_key = _config_value("OPENAI_API", "OPENAI_API_KEY")
    base_url = _config_value("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = _config_value("OPENAI_MODEL") or "gpt-4o-mini"
    if "embed" in model.lower():
        raise ValueError(
            f"OPENAI_MODEL={model!r} looks like an embedding model. "
            "Use a chat/instruct model (e.g. meta/llama-3.1-70b-instruct or gpt-4o-mini)."
        )
    if not api_key:
        raise ValueError(
            "Missing OPENAI_API. "
            "Streamlit Cloud: open the app → Manage app (⋮) → Settings → Secrets, "
            "add OPENAI_API (and OPENAI_BASE_URL / OPENAI_MODEL if needed), then Reboot app. "
            "Locally: create a .env file (see .env.example)."
        )
    return LLMConfig(api_key=api_key, base_url=base_url, model=model)
