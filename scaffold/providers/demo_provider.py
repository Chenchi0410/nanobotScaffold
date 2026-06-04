"""
演示用 Provider — 不需要真实 API Key，用于本地测试。

这就是一个具体的 Provider 实现，继承 LLMProvider，实现 chat() 方法。
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from scaffold.providers.base import LLMProvider, LLMResponse


class DemoProvider(LLMProvider):
    """本地模拟 Provider，返回固定的演示响应。"""

    def __init__(self) -> None:
        super().__init__(api_key="demo", api_base="local")

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        # 模拟网络延迟
        await asyncio.sleep(0.3)

        last_msg = messages[-1]["content"] if messages else ""

        # 模拟偶尔的瞬态错误（用于演示重试机制）
        if random.random() < 0.1:
            return LLMResponse(
                content="Error: 503 Service Unavailable",
                finish_reason="error",
            )

        responses = {
            "hello": "你好！我是 Demo Provider 的模拟响应。这是一个脚手架演示项目。",
            "help": "可用命令：hello, help, tools, quit",
            "tools": "当前可用工具：echo（回显）, add（加法）",
        }

        content = responses.get(
            last_msg.lower().strip(),
            f"Demo 收到：{last_msg[:100]}。这是一个来自 DemoProvider 的模拟回复。",
        )

        return LLMResponse(
            content=content,
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )

    def get_default_model(self) -> str:
        return "demo-model"
