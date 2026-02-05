# app/routes.py
# 路由与业务编排层：只做流程编排和参数校验

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Flask, jsonify, request

from app.config import settings, as_dict
from core.orchestrator import run_design_pipeline

logger = logging.getLogger("brandgen")


def _safe_json() -> Dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def register_routes(app: Flask, state) -> None:
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"ok": True, "service": as_dict()})

    @app.route("/v1/design/prompt", methods=["POST"])
    def design_prompt():
        payload = _safe_json()
        try:
            result = run_design_pipeline(payload, state.rag_service)
            return jsonify(result)
        except Exception as exc:
            logger.exception("生成 Prompt 失败")
            return jsonify({"error": str(exc)}), 500

    @app.route("/v1/chat", methods=["POST"])
    def chat_stub():
        # 可选：通用解释接口（当前仅返回占位说明）
        return jsonify({"message": "chat 接口尚未接入 LLM，可用于后续扩展"})
