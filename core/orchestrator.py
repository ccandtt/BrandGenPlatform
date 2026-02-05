# core/orchestrator.py
# 设计任务编排器：输入解析 -> 检索 -> 组装 Prompt

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from app.config import settings


@dataclass
class DesignInput:
    # 统一输入字段
    task: str
    industry: str
    brand_name: str
    style: str
    elements: str
    avoid: str


def parse_design_input(payload: Dict[str, Any]) -> DesignInput:
    # 输入解析与默认值处理
    def _get(key: str, default: str = "") -> str:
        value = payload.get(key)
        return str(value).strip() if value is not None else default

    task = _get("task", "logo")
    industry = _get("industry", "餐饮")
    brand_name = _get("brand_name", _get("brand", _get("name", "")))
    style = _get("style", "")
    elements = _get("elements", _get("keywords", ""))
    avoid = _get("avoid", "")

    return DesignInput(
        task=task or "logo",
        industry=industry or "餐饮",
        brand_name=brand_name,
        style=style,
        elements=elements,
        avoid=avoid,
    )


def build_retrieval_query(inp: DesignInput) -> str:
    # 统一构造检索 query，便于 KB-first 检索解析
    return (
        f"industry: {inp.industry} | "
        f"task: {inp.task} | "
        f"brand_name: {inp.brand_name or '未命名'} | "
        f"style: {inp.style or '未指定'} | "
        f"elements: {inp.elements or '无'} | "
        f"avoid: {inp.avoid or '无'}"
    )


def assemble_prompt(inp: DesignInput, rag_context: str) -> Dict[str, Any]:
    # 组装中文主 Prompt
    prompt_lines = [
        f"为{inp.industry}行业设计{inp.task}的中文文生图提示词。",
        f"品牌名称：{inp.brand_name or '未命名'}。",
    ]
    if inp.style:
        prompt_lines.append(f"风格：{inp.style}。")
    if inp.elements:
        prompt_lines.append(f"元素/关键词：{inp.elements}。")
    if rag_context:
        prompt_lines.append("结合以下知识增强：")
        prompt_lines.append(rag_context)

    prompt = "\n".join(prompt_lines)

    # 负面提示词：基线 + 用户 avoid
    negative = settings.default_negative_prompt
    if inp.avoid:
        negative = f"{negative}，避免：{inp.avoid}"

    params = {
        "aspect_ratio": settings.default_aspect,
        "steps": settings.default_steps,
        "cfg": settings.default_cfg,
        "num_variants": settings.default_num_variants,
    }

    return {
        "task": inp.task,
        "prompt": prompt,
        "negative_prompt": negative,
        "params": params,
    }


def run_design_pipeline(payload: Dict[str, Any], rag_service) -> Dict[str, Any]:
    # 编排主流程
    inp = parse_design_input(payload)
    query = build_retrieval_query(inp)

    rag_context, evidence = rag_service.build_context(query)

    result = assemble_prompt(inp, rag_context)
    if evidence:
        result["evidence"] = evidence
    return result
