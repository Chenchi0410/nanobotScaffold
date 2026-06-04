"""
Anthropic Provider 实现 — 展示如何对接另一种 API。

注意：这是简化版，只保留了架构骨架。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from scaffold.providers.base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API Provider（需要安装 anthropic 包）。"""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-sonnet-4-20250514",
    ) -> None:
        super().__init__(api_key=api_key)
        self._default_model = default_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.api_key)

            # Anthropic 的 system 消息是单独的参数
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    chat_messages.append(msg)

            response = await client.messages.create(
                model=model or self._default_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg if system_msg else None,
                messages=chat_messages,
            )

            content = response.content[0].text if response.content else ""
            return LLMResponse(
                content=content,
                finish_reason=response.stop_reason or "stop",
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                },
            )
        except ImportError:
            return LLMResponse(
                content="Error: anthropic package not installed. Run: pip install anthropic",
                finish_reason="error",
            )
        except Exception as e:
            logger.error("Anthropic API error: {}", e)
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def get_default_model(self) -> str:
        return self._default_model
