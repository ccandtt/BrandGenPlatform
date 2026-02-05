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


def _parse_kb_context(rag_context: str) -> Dict[str, list]:
    # 解析 KB 返回的上下文，去掉内部标签，仅保留内容
    buckets = {
        "template": [],
        "rules": [],
        "palette": [],
        "typography": [],
        "elements": [],
        "negatives": [],
    }
    if not rag_context:
        return buckets

    current = None
    for raw in rag_context.splitlines():
        line = raw.strip()
        if not line:
            continue
        # 跳过内部调试标签
        if line.startswith("[KB filters]"):
            continue
        if line.startswith("[模板]"):
            current = "template"
            continue
        if line.startswith("[规则与约束]"):
            current = "rules"
            continue
        if line.startswith("[配色]"):
            current = "palette"
            continue
        if line.startswith("[字体]"):
            current = "typography"
            continue
        if line.startswith("[图形元素]"):
            current = "elements"
            continue
        if line.startswith("[避坑/禁忌]"):
            current = "negatives"
            continue

        # 普通内容行，去掉前缀 "- "
        if line.startswith("- "):
            line = line[2:].strip()
        if current is not None:
            buckets[current].append(line)
    return buckets


def _render_prompt(inp: DesignInput, rag_context: str) -> str:
    # Prompt Formatter / Renderer：输出可直接用于文生图的标准格式
    kb = _parse_kb_context(rag_context)

    # 主体描述
    subject = [
        f"{inp.industry}行业{inp.task}设计",
        f"品牌名称：{inp.brand_name or '未命名'}",
    ]

    # 风格与元素
    style_bits = []
    if inp.style:
        style_bits.append(inp.style)
    if kb["template"]:
        style_bits.extend(kb["template"])

    element_bits = []
    if inp.elements:
        element_bits.append(inp.elements)
    if kb["elements"]:
        element_bits.extend(kb["elements"])

    # 规则与约束
    rule_bits = kb["rules"]

    # 配色与字体
    palette_bits = kb["palette"]
    typography_bits = kb["typography"]

    # 组合输出：稳定结构，便于直接复制使用
    sections = []
    sections.append("Subject: " + "；".join(subject))
    if style_bits:
        sections.append("Style: " + "；".join(style_bits))
    if palette_bits:
        sections.append("Palette: " + "；".join(palette_bits))
    if typography_bits:
        sections.append("Typography: " + "；".join(typography_bits))
    if element_bits:
        sections.append("Elements: " + "；".join(element_bits))
    if rule_bits:
        sections.append("Constraints: " + "；".join(rule_bits))

    return "\n".join(sections)


def assemble_prompt(inp: DesignInput, rag_context: str) -> Dict[str, Any]:
    # 组装中文主 Prompt（可直接用于文生图）
    prompt = _render_prompt(inp, rag_context)

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
