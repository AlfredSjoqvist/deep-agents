"""LLM client — Truefoundry AI Gateway with Anthropic fallback."""

import anthropic
from openai import AsyncOpenAI

from sentinel.config import config

# Try Truefoundry first, fall back to direct Anthropic API.
_openai_client: AsyncOpenAI | None = None
_anthropic_client: anthropic.AsyncAnthropic | None = None
_use_anthropic_direct = False


def _init_clients():
    """Initialize LLM clients. Truefoundry preferred, Anthropic fallback."""
    global _openai_client, _anthropic_client, _use_anthropic_direct

    if config.truefoundry_token:
        _openai_client = AsyncOpenAI(
            api_key=config.truefoundry_token,
            base_url=config.truefoundry_base_url,
        )

    if config.anthropic_api_key:
        _anthropic_client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)


async def chat(
    messages: list[dict],
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Send a chat completion. Tries Truefoundry, falls back to Anthropic."""
    global _use_anthropic_direct

    if _openai_client is None and _anthropic_client is None:
        _init_clients()

    # Try Truefoundry first (if not already failed)
    if _openai_client and not _use_anthropic_direct:
        try:
            response = await _openai_client.chat.completions.create(
                model=f"anthropic/{model}" if not model.startswith("anthropic/") else model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception:
            # Truefoundry failed — switch to direct Anthropic for rest of session
            _use_anthropic_direct = True

    # Anthropic direct
    if _anthropic_client:
        # Convert messages: extract system message if present
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        response = await _anthropic_client.messages.create(
            model=model if not model.startswith("anthropic/") else model.removeprefix("anthropic/"),
            system=system_msg,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content[0].text

    raise RuntimeError("No LLM client available — set TRUEFOUNDRY_ACCESS_TOKEN or ANTHROPIC_API_KEY")
