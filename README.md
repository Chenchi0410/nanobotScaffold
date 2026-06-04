# 脚手架演示项目

从 [nanobot](https://github.com/HKUDS/nanobot) 提取的 **6 个通用架构模式**，可直接复用到你自己的项目中。

## 项目结构

```
scaffold/
├── __init__.py              # 包入口
├── __main__.py              # python -m scaffold
├── cli.py                   # CLI 入口（3 种运行模式）
├── facade.py                # 模式 6：Facade 门面
│
├── bus/                     # 模式 2：消息总线
│   ├── events.py            #   事件定义
│   └── queue.py             #   异步队列（45 行）
│
├── channels/                # 模式 1：插件自动发现
│   ├── base.py              #   抽象基类
│   ├── registry.py          #   自动扫描 + entry_points
│   ├── manager.py           #   渠道管理器
│   ├── cli_channel.py       #   示例：终端渠道
│   └── demo_channel.py      #   示例：演示渠道
│
├── providers/               # 模式 4+5：策略 + 工厂
│   ├── base.py              #   抽象基类 + 重试模板方法
│   ├── registry.py          #   静态元数据注册表
│   ├── factory.py           #   配置驱动工厂
│   ├── demo_provider.py     #   示例：本地模拟
│   ├── openai_provider.py   #   示例：OpenAI API
│   └── anthropic_provider.py#   示例：Anthropic API
│
├── agent/                   # 模式 3：生命周期 Hook
│   ├── hook.py              #   Hook 基类 + CompositeHook
│   ├── loop.py              #   Agent 核心循环
│   └── tools/               # 模式 1（复用）：Tool 自动发现
│       ├── base.py          #   Tool 抽象基类
│       ├── registry.py      #   Tool 注册表
│       ├── loader.py        #   自动扫描
│       ├── echo_tool.py     #   示例：回显工具
│       └── add_tool.py      #   示例：加法工具
│
├── config/                  # 模式 5（补充）：配置
│   ├── schema.py            #   Pydantic 配置模型
│   └── loader.py            #   配置加载器
│
└── session/                 # 会话管理
    └── manager.py           #   Session + SessionManager
```

## 6 个架构模式速查

| # | 模式 | 核心文件 | 一句话 |
|---|------|---------|--------|
| 1 | 插件自动发现 | `channels/registry.py`, `agent/tools/loader.py` | `pkgutil` 扫描目录，新文件即注册 |
| 2 | 消息总线 | `bus/queue.py` | 两个 `asyncio.Queue` 解耦两端 |
| 3 | 生命周期 Hook | `agent/hook.py` | `CompositeHook` 组合 + 错误隔离 |
| 4 | 策略 + 重试 | `providers/base.py` | `chat_with_retry()` 模板方法 |
| 5 | 配置驱动工厂 | `providers/factory.py`, `providers/registry.py` | 元组注册表 → 工厂函数 |
| 6 | Facade 门面 | `facade.py` | `Nanobot.from_config()` 一行创建 |

## 运行

```bash
cd D:\nanobotScaffold

# 安装依赖
pip install -e .

# 自动演示（不需要 API Key）
python -m scaffold demo

# 交互式对话
python -m scaffold chat

# SDK 调用示例
python -m scaffold sdk
```

## 学习路线建议

1. **先跑起来** — `python -m scaffold demo`，看整体效果
2. **读 `bus/queue.py`** — 45 行，理解消息总线如何解耦
3. **读 `channels/registry.py`** — 理解 pkgutil 自动发现机制
4. **读 `agent/hook.py`** — 理解 CompositeHook 的错误隔离
5. **读 `providers/base.py`** — 理解模板方法和重试链
6. **读 `facade.py`** — 理解如何把复杂系统包装成简单接口
7. **尝试新增一个 Tool** — 在 `agent/tools/` 下新建文件，继承 `Tool`
8. **尝试新增一个 Provider** — 在 `providers/` 下新建文件，注册到 `registry.py`
