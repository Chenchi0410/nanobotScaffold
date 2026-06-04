"""
示例渠道：CLI — 终端交互。

展示如何实现一个 Channel：继承 BaseChannel，实现 start/stop/send。
这个渠道可以直接运行，不需要任何外部服务。
"""

from __future__ import annotations

import asyncio
from typing import Any

from scaffold.bus.events import OutboundMessage
from scaffold.bus.queue import EventBus
from scaffold.channels.base import BaseChannel


class CliChannel(BaseChannel):
    """终端交互渠道 — 在命令行直接与 Agent 对话。"""

    name = "cli"
    display_name = "CLI"

    def __init__(self, config: Any, bus: EventBus) -> None:
        super().__init__(config, bus)
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动 CLI 输入循环。"""
        self._running = True
        self.logger.info("CLI channel started. Type 'quit' to exit.")

        while self._running:
            try:
                # 用 asyncio 兼容的方式读取 stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("\nYou: ")
                )
                line = line.strip()
                if not line:
                    continue
                if line.lower() in ("quit", "exit", "q"):
                    self._running = False
                    break

                await self._handle_message(
                    sender_id="cli-user",
                    chat_id="cli-session",
                    content=line,
                )
            except (EOFError, KeyboardInterrupt):
                self._running = False
                break
            except asyncio.CancelledError:
                break

    async def stop(self) -> None:
        self._running = False
        self.logger.info("CLI channel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        """打印 Agent 响应到终端。"""
        print(f"\n🤖 Agent: {msg.content}")
