# app/app_factory.py
# 应用工厂：初始化状态、RAG 服务与路由

from __future__ import annotations

import logging
from flask import Flask

from app.state import AppState
from app.config import settings
from app.routes import register_routes
from rag.kb_retriever import RAGService

logger = logging.getLogger("brandgen")


def create_app(state: AppState) -> Flask:
    app = Flask(__name__)

    # 初始化 RAG 服务
    if state.rag_service is None:
        state.rag_service = RAGService(settings.kb_root)

    register_routes(app, state)
    return app
