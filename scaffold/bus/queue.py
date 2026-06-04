"""
模式 2：消息总线 — 模块间解耦的核心

设计要点：
  - 只用两个 asyncio.Queue（inbound + outbound），45 行搞定
  - Channel 往 inbound 放消息，Agent 从 inbound 取消息
  - Agent 往 outbound 放响应，Channel 从 outbound 取响应
  - Channel 和 Agent 互不知道对方存在
"""

import asyncio

from scaffold.bus.events import InboundMessage, OutboundMessage


class EventBus:
    """
    异步消息总线，解耦渠道层和 Agent 层。

    用法：
        bus = EventBus()

        # 渠道端（发布入站消息）
        await bus.publish_inbound(InboundMessage(...))

        # Agent 端（消费入站消息，发布出站响应）
        msg = await bus.consume_inbound()
        # ... 处理 ...
        await bus.publish_outbound(OutboundMessage(...))
    """

    def __init__(self) -> None:
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    # ---- 入站（渠道 → Agent）----

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """渠道调用：发布一条入站消息。"""
        await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """Agent 调用：阻塞等待下一条入站消息。"""
        return await self.inbound.get()

    # ---- 出站（Agent → 渠道）----

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Agent 调用：发布一条出站响应。"""
        await self.outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """渠道调用：阻塞等待下一条出站响应。"""
        return await self.outbound.get()

    @property
    def inbound_size(self) -> int:
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        return self.outbound.qsize()
