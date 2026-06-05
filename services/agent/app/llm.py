"""Single point of LLM construction so configuration stays consistent."""
from __future__ import annotations

import os
from functools import lru_cache

from langchain_ollama import ChatOllama


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    return ChatOllama(
        model=os.environ["OLLAMA_MODEL"],
        base_url=os.environ["OLLAMA_HOST"],
        temperature=0.1,
        num_ctx=8192,
    )
