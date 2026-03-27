"""Truefoundry AI Gateway — OpenAI-compatible LLM client."""

from openai import AsyncOpenAI

from sentinel.config import config

# Truefoundry is an OpenAI-compatible gateway.
# All LLM calls go through here for governance + monitoring.
_client: AsyncOpenAI | None = None


def get_llm_client() -> AsyncOpenAI:
    """Get the Truefoundry-routed LLM client (singleton)."""
    global _client
    if _client is None:
        if config.truefoundry_token:
            _client = AsyncOpenAI(
                api_key=config.truefoundry_token,
                base_url=config.truefoundry_base_url,
            )
        else:
            # Fallback: direct Anthropic via OpenAI-compat endpoint
            _client = AsyncOpenAI(
                api_key=config.anthropic_api_key,
                base_url="https://api.anthropic.com/v1/",
            )
    return _client


async def chat(
    messages: list[dict],
    model: str = "anthropic/claude-sonnet-4-20250514",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Send a chat completion through Truefoundry gateway."""
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
