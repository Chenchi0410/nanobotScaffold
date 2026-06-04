"""
模式 1：渠道抽象基类 — 定义插件契约

设计要点：
  - ABC 定义必须实现的接口（start / stop / send）
  - 提供默认实现的方法（_handle_message），子类可以直接复用
  - is_allowed() 做权限检查，_handle_message() 做消息转发
  - 子类只需关注"如何连接平台"和"如何发送消息"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from scaffold.bus.events import InboundMessage, OutboundMessage
from scaffold.bus.queue import EventBus


class BaseChannel(ABC):
    """
    渠道抽象基类。

    每个渠道（Telegram、Discord、CLI 等）都继承这个类，
    实现 start / stop / send 三个方法即可。
    """

    # 子类必须设置这些类属性
    name: str = "base"
    display_name: str = "Base"

    def __init__(self, config: Any, bus: EventBus) -> None:
        self.config = config
        self.bus = bus
        self.logger = logger.bind(channel=self.name)
        self._running = False

    # ---- 子类必须实现的抽象方法 ----

    @abstractmethod
    async def start(self) -> None:
        """启动渠道，开始监听消息。这是一个长期运行的任务。"""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """停止渠道，清理资源。"""
        ...

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """通过这个渠道发送一条消息。"""
        ...

    # ---- 提供默认实现的方法（子类可覆盖）----

    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        处理收到的原始消息：权限检查 → 构造 InboundMessage → 发布到总线。

        子类在 start() 中监听到消息后，调用这个方法即可。
        """
        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            metadata=metadata or {},
        )
        await self.bus.publish_inbound(msg)

    @property
    def is_running(self) -> bool:
        return self._running
