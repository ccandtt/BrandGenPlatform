# app/config.py
# 配置层：集中管理参数，支持环境变量覆盖

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except Exception:
        return default


@dataclass
class Settings:
    # 服务
    host: str = _env("BGP_HOST", "0.0.0.0")
    port: int = _env_int("BGP_PORT", 8000)
    service_name: str = _env("BGP_SERVICE_NAME", "brandgen_platform")

    # KB 开关与路径
    kb_enabled: bool = _env("BGP_KB_ENABLED", "true").lower() in ("1", "true", "yes")
    kb_root: str = _env("BGP_KB_ROOT", "kb")

    # KB Top-k
    kb_topk_templates: int = _env_int("BGP_KB_TOPK_TEMPLATES", 2)
    kb_topk_rules: int = _env_int("BGP_KB_TOPK_RULES", 6)
    kb_topk_elements: int = _env_int("BGP_KB_TOPK_ELEMENTS", 4)
    kb_topk_palettes: int = _env_int("BGP_KB_TOPK_PALETTES", 2)
    kb_topk_typography: int = _env_int("BGP_KB_TOPK_TYPOGRAPHY", 2)
    kb_topk_negatives: int = _env_int("BGP_KB_TOPK_NEGATIVES", 3)

    # 默认推理参数
    default_aspect: str = _env("BGP_T2I_ASPECT", "1:1")
    default_steps: int = _env_int("BGP_T2I_STEPS", 28)
    default_cfg: float = _env_float("BGP_T2I_CFG", 5.5)
    default_num_variants: int = _env_int("BGP_T2I_NUM_VARIANTS", 4)

    # 默认负面提示词基线
    default_negative_prompt: str = _env(
        "BGP_NEGATIVE_PROMPT",
        "写实、复杂背景、杂乱场景、水印、签名、低质量、模糊、噪点、文字变形、错别字、多余物体、过度细节、重渐变、强高光、强阴影",
    )

    # LLM 客户端（占位，可替换）
    llm_endpoint: str = _env("BGP_LLM_ENDPOINT", "http://127.0.0.1:8008/v1")
    llm_model: str = _env("BGP_LLM_MODEL", "model")
    llm_api_key: str = _env("BGP_LLM_API_KEY", "EMPTY")


settings = Settings()


def as_dict() -> Dict[str, str]:
    # 用于 /health 或调试输出（不返回敏感信息）
    return {
        "service": settings.service_name,
        "kb_enabled": str(settings.kb_enabled),
        "kb_root": settings.kb_root,
        "llm_endpoint": settings.llm_endpoint,
        "llm_model": settings.llm_model,
    }
