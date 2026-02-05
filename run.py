# run.py
# 应用入口：启动 Flask 服务

from __future__ import annotations

import logging
import atexit

from app.config import settings
from app.state import AppState
from app.lifecycle import register_signal_handlers, cleanup
from app.app_factory import create_app


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("brandgen")

    state = AppState()
    # 退出时确保清理资源
    atexit.register(lambda: cleanup(state))
    register_signal_handlers(state)

    app = create_app(state)

    logger.info("BrandGenPlatform 启动: %s:%s", settings.host, settings.port)
    try:
        # 关闭 reloader，避免多进程下 SIGINT 需要按两次
        app.run(host=settings.host, port=settings.port, use_reloader=False)
    except KeyboardInterrupt:
        # 明确捕获 Ctrl+C，确保日志与清理动作一致
        logger.info("收到 KeyboardInterrupt，准备退出...")
        cleanup(state)
