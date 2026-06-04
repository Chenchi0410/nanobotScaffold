"""
模式 4：Provider 抽象基类 — 策略模式 + 重试链

设计要点：
  - ABC 定义 chat() 接口，子类实现具体的 LLM 调用
  - chat_with_retry() 是模板方法：固定重试策略，子类只管调用
  - LLMResponse 统一封装所有 Provider 的返回格式
  - _is_transient_error() 统一错误分类（可重试 vs 不可重试）
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from loguru import logger


@dataclass
class LLMResponse:
    """统一的 LLM 响应格式，所有 Provider 都返回这个。"""

    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.finish_reason != "error"

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    LLM Provider 抽象基类。

    子类只需实现 chat() 方法。重试、错误处理、流式等横切逻辑
    由基类的模板方法提供。
    """

    # 重试配置
    _RETRY_DELAYS = (1, 2, 4)
    _TRANSIENT_MARKERS = (
        "429", "rate limit", "500", "502", "503", "504",
        "overloaded", "timeout", "timed out", "connection",
    )

    def __init__(self, api_key: str | None = None, api_base: str | None = None) -> None:
        self.api_key = api_key
        self.api_base = api_base

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        发送一次 LLM 请求。子类必须实现。

        Args:
            messages: 消息列表 [{"role": "user", "content": "hello"}]
            model: 模型标识
            max_tokens: 最大生成 token 数
            temperature: 温度

        Returns:
            LLMResponse 统一响应
        """
        ...

    # ---- 模板方法：带重试的调用 ----

    async def chat_with_retry(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        模板方法：调用 chat() 并在瞬态错误时自动重试。

        这是基类提供的横切逻辑，子类不需要覆盖。
        """
        kw = dict(messages=messages, model=model, max_tokens=max_tokens, temperature=temperature)

        for attempt, delay in enumerate(self._RETRY_DELAYS):
            try:
                response = await self._safe_chat(**kw)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                response = LLMResponse(content=f"Error: {exc}", finish_reason="error")

            if response.ok:
                return response

            if not self._is_transient_error(response):
                logger.error("Non-transient error: {}", (response.content or "")[:120])
                return response

            logger.warning(
                "Transient error (attempt {}/{}), retrying in {}s: {}",
                attempt + 1, len(self._RETRY_DELAYS), delay,
                (response.content or "")[:120],
            )
            await asyncio.sleep(delay)

        return response

    async def _safe_chat(self, **kwargs: Any) -> LLMResponse:
        """包装 chat()，捕获异常转为 LLMResponse。"""
        return await self.chat(**kwargs)

    @classmethod
    def _is_transient_error(cls, response: LLMResponse) -> bool:
        """判断是否是可重试的瞬态错误。"""
        content = (response.content or "").lower()
        return any(marker in content for marker in cls._TRANSIENT_MARKERS)

    @abstractmethod
    def get_default_model(self) -> str:
        """返回这个 Provider 的默认模型名。"""
        ...
