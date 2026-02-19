"""Prompt loading helpers for Ollama/Bay Tides AI."""

from __future__ import annotations

import os
from pathlib import Path


def load_prompt(
    *,
    path_env: str,
    inline_env: str,
    fallback: str,
) -> str:
    """Load a prompt from env path or inline env, else fallback."""
    path_value = os.getenv(path_env)
    if path_value:
        prompt_path = Path(path_value)
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()

    inline_value = os.getenv(inline_env)
    if inline_value:
        return inline_value.strip()

    return fallback
