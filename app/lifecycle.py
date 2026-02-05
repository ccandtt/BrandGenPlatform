# app/lifecycle.py
# 生命周期管理：信号注册与资源释放

from __future__ import annotations

import logging
import signal
import sys
from typing import Any, Optional, Callable

logger = logging.getLogger("brandgen")


def register_signal_handlers(state: Any, *, stop_server: Optional[Callable[[], None]] = None) -> None:
    # 注册 SIGINT/SIGTERM，确保优雅退出
    def _handle(sig, _frame):
        logger.info("收到信号 %s，准备退出...", sig)
        try:
            state.shutdown_event.set()
        except Exception:
            pass
        # 尝试调用服务器停止回调（如果有）
        if stop_server is not None:
            try:
                stop_server()
            except Exception:
                pass
        cleanup(state)
        # 显式退出，避免卡住
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)


def cleanup(state: Any) -> None:
    # 安全释放资源（线程池等）
    executor = getattr(state, "executor", None)
    if executor is not None:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
