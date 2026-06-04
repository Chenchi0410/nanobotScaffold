"""
模式 1（复用）：Tool 抽象基类 — 与 Channel/Provider 同样的插件模式

设计要点：
  - ABC 定义 name / description / parameters / execute 四个契约
  - parameters 用 JSON Schema 描述，框架自动做参数验证
  - _discoverable / _scopes 控制自动发现行为
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    工具抽象基类。

    每个工具继承这个类，实现 4 个属性/方法即可被自动发现和注册。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称，用于 LLM 函数调用。"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述，告诉 LLM 这个工具做什么。"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema 格式的参数定义。"""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """执行工具，返回结果字符串。"""
        ...

    # ---- 插件元数据 ----

    _discoverable: bool = True   # 是否参与自动发现
    _scopes: set[str] = {"core"} # 作用域

    def to_schema(self) -> dict[str, Any]:
        """导出为 OpenAI 函数调用格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """基本的参数验证，返回错误列表（空 = 通过）。"""
        errors = []
        schema = self.parameters or {}
        required = schema.get("required", [])
        for key in required:
            if key not in params:
                errors.append(f"Missing required parameter: {key}")
        return errors
