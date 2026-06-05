# Channels 模块整体流程

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         ChannelManager                          │
│  职责：管理所有渠道的生命周期，调度出站消息                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  __init__(config, bus)                                          │
│      │                                                          │
│      ├─► 保存 config 和 bus 引用                                 │
│      ├─► 初始化 self.channels = {}                              │
│      ├─► 初始化 self._dispatch_task = None                      │
│      └─► _init_channels()                                       │
│              │                                                  │
│              ├─► 从 config 读取 enabled_names 白名单             │
│              │   {"cli_channel", "slack", ...}                  │
│              │                                                  │
│              ├─► discover_enabled()     ← 自动发现所有渠道       │
│              │       │                                          │
│              │       ├─► discover_channel_names()               │
│              │       │   └─► pkgutil.iter_modules(channels/)   │
│              │       │       返回: ["cli_channel", "demo_channel"]│
│              │       │                                          │
│              │       ├─► load_channel_class()  ← 加载内置渠道   │
│              │       │   └─► importlib.import_module()         │
│              │       │       └─► issubclass 过滤               │
│              │       │                                          │
│              │       ├─► discover_plugins()  ← 加载外部插件     │
│              │       │   └─► entry_points(group="scaffold.channels")│
│              │       │                                          │
│              │       └─► 内置优先，外部同名不覆盖                │
│              │           返回: {name: class} 字典               │
│              │                                                  │
│              └─► 实例化每个渠道: cls(section, bus)               │
│                  存入 self.channels 字典                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  start_all()                                                    │
│      │                                                          │
│      ├─► 空检查：channels 为空则直接返回                         │
│      │                                                          │
│      ├─► create_task(_dispatch_outbound())                      │
│      │   启动出站分发器（后台永久循环）                            │
│      │                                                          │
│      └─► 并发启动所有通道：                                      │
│          tasks = [create_task(_start_channel(name, ch)) ...]    │
│          await gather(*tasks, return_exceptions=True)           │
│          单个通道失败不影响其他通道                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  _dispatch_outbound()  ← 后台永久循环协程                        │
│      │                                                          │
│      ├─► await bus.consume_outbound()  ← 阻塞等待出站消息       │
│      │   超时 1 秒，无消息则 continue 继续循环                   │
│      │                                                          │
│      ├─► self.channels.get(msg.channel) ← 按通道名找实例        │
│      │                                                          │
│      └─► _send_with_retry(channel, msg)                        │
│              │                                                  │
│              └─► 指数退避重试 (1s, 2s, 4s)                      │
│                  channel.send(msg)                              │
│                  成功 → return                                  │
│                  全部失败 → 打日志，不抛异常                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  stop_all()                                                     │
│      │                                                          │
│      ├─► 取消 _dispatch_task                                    │
│      │   dispatch_task.cancel() + await                        │
│      │                                                          │
│      └─► 逐个停止通道: channel.stop()                           │
│          单个停止失败不影响其他通道                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 消息流转

```
用户发送消息
  │
  ▼
┌─────────────┐  publish_inbound()   ┌───────────┐
│  渠道层      │ ────────────────────▶│  inbound  │
│  (CLI/TG/..)│                      │   队列    │
└─────────────┘                      └─────┬─────┘
                                           │
                                  consume_inbound()
                                           │
                                           ▼
                                     ┌───────────┐
                                     │  Agent    │
                                     │  处理消息  │
                                     └─────┬─────┘
                                           │
                                 publish_outbound()
                                           │
                                           ▼
┌─────────────┐  consume_outbound()  ┌───────────┐
│  渠道层      │ ◀───────────────────│  outbound │
│  (CLI/TG/..)│                      │   队列    │
└─────────────┘                      └───────────┘
  │
  ▼
用户收到回复
```

## 自动发现机制

```
channels/
├── __init__.py       ← 包初始化
├── base.py           ← ABC 基类（在 _INTERNAL 排除名单中）
├── registry.py       ← 发现引擎（在 _INTERNAL 排除名单中）
├── manager.py        ← 管理器（在 _INTERNAL 排除名单中）
├── channels.md       ← 本文件（非 .py，自动忽略）
├── cli_channel.py    ← ✅ 不在 _INTERNAL 中 → 被发现
└── demo_channel.py   ← ✅ 不在 _INTERNAL 中 → 被发现
```

**排除机制**：`_INTERNAL = frozenset({"base", "manager", "registry"})`，这三个模块是内部基础设施，不作为插件暴露。其余 `.py` 模块自动被发现。

## 核心设计思想

| 概念 | 实现方式 | 作用 |
|------|----------|------|
| 排除名单 | `_INTERNAL = frozenset(...)` | 内部模块不暴露为插件 |
| 动态导入 | `importlib.import_module()` | 运行时按名字加载模块 |
| 类型检查 | `issubclass(cls, BaseChannel)` | 只接受实现了接口的类 |
| 开放扩展 | `entry_points` | 第三方包可插拔接入 |
| 白名单过滤 | `config.channels.*.enabled` | 配置控制启用哪些渠道 |
| 内置优先 | `if name not in result` | 内置和外部同名时，内置优先 |
| 错误隔离 | `try/except` + `return_exceptions=True` | 单个渠道失败不影响其他 |
| 指数退避 | `_SEND_RETRY_DELAYS = (1, 2, 4)` | 发送失败自动重试 3 次 |
| 后台分发 | `create_task(_dispatch_outbound())` | 出站消息在后台永久循环处理 |

## 文件职责

| 文件 | 行数 | 职责 |
|------|------|------|
| `base.py` | ~40 | 定义 BaseChannel ABC（接口契约：start/stop/send） |
| `registry.py` | ~80 | 三层发现：目录扫描 + 动态加载 + entry_points 外部插件 |
| `manager.py` | ~130 | 组装渠道、启动通道、出站消息分发、重试发送、优雅停止 |
| `cli_channel.py` | ~25 | 示例：终端交互渠道 |
| `demo_channel.py` | ~25 | 示例：自动发送演示消息的渠道 |
