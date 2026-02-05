# app/state.py
# 全局状态对象：集中保存运行时依赖与缓存

from __future__ import annotations

from dataclasses import dataclass, field
import threading
from typing import Any, Optional


@dataclass
class AppState:
    # 线程池或异步执行器（当前为占位）
    executor: Any | None = None

    # RAG 检索器实例
    rag_service: Any | None = None

    # LLM 客户端实例
    llm_client: Any | None = None

    # 生命周期控制
    shutdown_event: threading.Event = field(default_factory=threading.Event)
