# core/orchestrator.py
# 设计任务编排器：输入解析 -> 检索 -> 组装 Prompt

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from app.config import settings
from core.prompt_logger import save_prompt_result


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

    # 轻量决策：选取单一主风格/配色/字体，元素限制 1-2
    dominant_style = inp.style or (kb["template"][0] if kb["template"] else "")
    dominant_palette = kb["palette"][0] if kb["palette"] else ""
    dominant_typography = kb["typography"][0] if kb["typography"] else ""

    # 元素：用户优先，其次 KB；最多 2 个
    element_bits = []
    if inp.elements:
        element_bits.extend([e.strip() for e in inp.elements.split("、") if e.strip()])
    if not element_bits and kb["elements"]:
        element_bits.extend(kb["elements"])
    element_bits = element_bits[:2]

    # 规则/约束：仅保留最关键前 2 条，避免冗长
    rule_bits = kb["rules"][:2]

    # 主体描述：更偏生成指令，不用抽象营销语言
    subject = f"{inp.industry}行业{inp.task}，品牌名“{inp.brand_name or '未命名'}”"

    # 生成友好格式：短句 + 清晰属性
    sections = []
    sections.append(f"Subject: {subject}")
    if dominant_style:
        sections.append(f"Style: {dominant_style}")
    if dominant_palette:
        sections.append(f"Palette: {dominant_palette}")
    if dominant_typography:
        sections.append(f"Typography: {dominant_typography}")
    if element_bits:
        sections.append(f"Elements: {'、'.join(element_bits)}")
    if rule_bits:
        sections.append(f"Constraints: {'；'.join(rule_bits)}")

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
    # 保存 Prompt 结果到本地文件（可用于日志或追溯）
    save_prompt_result(result, path="prompt_result.txt")
    return result
