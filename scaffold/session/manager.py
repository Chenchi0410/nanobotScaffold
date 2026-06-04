"""
会话管理 — 维护每个会话的对话历史。

设计要点：
  - Session 存储一个会话的完整消息历史
  - SessionManager 管理多个 Session 的创建和查找
  - 消息格式与 OpenAI Chat API 兼容
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Session:
    """一个对话会话。"""

    key: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """添加一条消息到历史。"""
        msg: dict[str, Any] = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        self.messages.append(msg)
        self.updated_at = datetime.now()


class SessionManager:
    """管理多个会话。"""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, key: str) -> Session:
        """获取或创建一个会话。"""
        if key not in self._sessions:
            self._sessions[key] = Session(key=key)
        return self._sessions[key]

    def list_sessions(self) -> list[str]:
        """列出所有会话键。"""
        return list(self._sessions.keys())

    def delete(self, key: str) -> None:
        """删除一个会话。"""
        self._sessions.pop(key, None)
