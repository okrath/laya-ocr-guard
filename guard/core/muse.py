"""
Backward compatibility layer for Muse Reviewer.
Re-exports LLMReviewerEngine from guard.core.llm_reviewer.
The final gatekeeper is the user-configured LLM (Claude, GPT, DeepSeek, Ollama, etc.).
"""

from guard.core.llm_reviewer import (
    LLMReviewVerdict,
    LLMReviewerEngine,
    MuseEngine,
    MuseReviewVerdict,
    MuseVerdict,
    ReviewVerdict,
)

__all__ = [
    "MuseEngine",
    "MuseVerdict",
    "MuseReviewVerdict",
    "LLMReviewerEngine",
    "ReviewVerdict",
    "LLMReviewVerdict",
]
