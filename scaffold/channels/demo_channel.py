"""
示例渠道：Demo — 自动发送演示消息。

展示渠道如何与消息总线交互，不需要用户输入。
"""

from __future__ import annotations

import asyncio
from typing import Any

from scaffold.bus.events import OutboundMessage
from scaffold.bus.queue import EventBus
from scaffold.channels.base import BaseChannel


class DemoChannel(BaseChannel):
    """演示渠道 — 自动发送几条消息然后停止。"""

    name = "demo"
    display_name = "Demo"

    def __init__(self, config: Any, bus: EventBus) -> None:
        super().__init__(config, bus)

    async def start(self) -> None:
        self._running = True
        self.logger.info("Demo channel started, sending test messages...")

        messages = ["hello", "help", "what tools do you have?"]
        for msg_text in messages:
            if not self._running:
                break
            await self._handle_message(
                sender_id="demo-user",
                chat_id="demo-session",
                content=msg_text,
            )
            await asyncio.sleep(0.5)

        # 等待一段时间让 Agent 处理完
        await asyncio.sleep(5)
        self._running = False

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        print(f"[DemoChannel] Response: {msg.content}")
