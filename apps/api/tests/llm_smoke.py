"""Manual live verification of Gemini structured output."""

import asyncio
import json
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from bridgeline.config import get_settings
from bridgeline.llm.client import GEMINI_MODEL, GeminiGateway
from bridgeline.llm.prompts import PromptRegistry


class Greeting(BaseModel):
    """Trivial strict response used only for live gateway verification."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(description="A friendly greeting containing no more than five words.")


def decimal_default(value: object) -> str:
    """Serialize Decimal accounting values in the smoke-test report."""

    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"cannot JSON serialize {type(value).__name__}")


async def main() -> None:
    """Make one live schema-enforced request and print a non-secret report."""

    settings = get_settings()
    gateway = GeminiGateway.from_settings(settings)
    prompt = PromptRegistry().render("trivial", {"audience": "the Bridgeline team"})
    result = await gateway.generate_structured(
        prompt=prompt,
        response_model=Greeting,
        max_output_tokens=512,
        thinking_level="minimal",
    )
    print(
        json.dumps(
            {
                "model": GEMINI_MODEL,
                "model_version": result.model_version,
                "response": result.data.model_dump(),
                "usage": {
                    "prompt_tokens": result.usage.prompt_tokens,
                    "candidate_tokens": result.usage.candidate_tokens,
                    "thought_tokens": result.usage.thought_tokens,
                    "total_tokens": result.usage.total_tokens,
                    "estimated_standard_cost_usd": result.usage.estimated_cost_usd,
                },
            },
            default=decimal_default,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
