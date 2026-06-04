"""
模式 5（补充）：配置 Schema — 用 Pydantic 定义配置结构

设计要点：
  - Pydantic BaseSettings 自动从环境变量读取配置
  - 支持 camelCase 别名（JSON 配置文件通常用 camelCase）
  - 默认值让最小配置也能跑
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """单个 Provider 的配置。"""

    api_key: str = ""
    api_base: str = ""
    model: str = ""


class AgentConfig(BaseModel):
    """Agent 配置。"""

    provider: str = "demo"
    model: str = "demo-model"
    max_iterations: int = 10
    max_tokens: int = 4096
    temperature: float = 0.7


class AppConfig(BaseModel):
    """应用总配置。"""

    agents: AgentConfig = Field(default_factory=AgentConfig)
    channels: dict[str, Any] = Field(default_factory=dict)
    providers: dict[str, Any] = Field(default_factory=dict)
