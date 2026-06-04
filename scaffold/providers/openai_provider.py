"""
OpenAI Provider 实现 — 展示如何对接真实 API。

注意：这是简化版，只保留了架构骨架。完整版见 nanobot 项目。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from scaffold.providers.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI 兼容 API Provider（需要安装 openai 包）。"""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "gpt-4o-mini",
    ) -> None:
        super().__init__(api_key=api_key, api_base=api_base)
        self._default_model = default_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
            )

            response = await client.chat.completions.create(
                model=model or self._default_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content,
                finish_reason=choice.finish_reason or "stop",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            )
        except ImportError:
            return LLMResponse(
                content="Error: openai package not installed. Run: pip install openai",
                finish_reason="error",
            )
        except Exception as e:
            logger.error("OpenAI API error: {}", e)
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def get_default_model(self) -> str:
        return self._default_model
