# rag/kb_retriever.py
# KB-first 检索实现：本地 JSONL 简单过滤 + 评分

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from app.config import settings


@dataclass
class KBItem:
    id: str
    kind: str
    industry: List[str]
    task: List[str]
    style: List[str]
    tags: List[str]
    text: str
    priority: int


def _safe_read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                rows.append(json.loads(s))
            except Exception:
                # 容忍坏行，避免服务崩溃
                continue
    return rows


def _list_contains_or_star(values: Any, target: str) -> bool:
    if values is None:
        return False
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return False
    vset = set([str(v).strip().lower() for v in values if str(v).strip()])
    if "*" in vset:
        return True
    return target.strip().lower() in vset


def _tag_match_score(tags: List[str], query_text: str) -> int:
    if not tags or not query_text:
        return 0
    q = query_text.lower()
    score = 0
    for t in tags:
        tt = str(t).lower().strip()
        if tt and tt in q:
            score += 1
    return score


def _parse_field(query: str, key: str) -> str:
    m = re.search(rf"{re.escape(key)}\s*:\s*([^|]+)", query, flags=re.IGNORECASE)
    if not m:
        return ""
    return m.group(1).strip()


def parse_filters(query: str) -> Dict[str, str]:
    return {
        "industry": _parse_field(query, "industry"),
        "task": _parse_field(query, "task"),
        "style": _parse_field(query, "style"),
        "elements": _parse_field(query, "elements"),
        "avoid": _parse_field(query, "avoid"),
    }


class KBRetriever:
    def __init__(self, kb_root: str) -> None:
        self.kb_root = kb_root
        self._cache: Dict[str, List[Dict[str, Any]]] | None = None
        self._cache_mtime: float | None = None

    def _kb_files(self) -> Dict[str, str]:
        return {
            "entries": os.path.join(self.kb_root, "entries.jsonl"),
            "palettes": os.path.join(self.kb_root, "palettes.jsonl"),
            "typography": os.path.join(self.kb_root, "typography.jsonl"),
            "templates": os.path.join(self.kb_root, "templates.jsonl"),
        }

    def _load_kb(self) -> Dict[str, List[Dict[str, Any]]]:
        files = self._kb_files()
        mtimes = [os.path.getmtime(p) for p in files.values() if os.path.exists(p)]
        cur_mtime = max(mtimes) if mtimes else None
        if self._cache is not None and self._cache_mtime == cur_mtime:
            return self._cache

        kb = {
            "entries": _safe_read_jsonl(files["entries"]),
            "palettes": _safe_read_jsonl(files["palettes"]),
            "typography": _safe_read_jsonl(files["typography"]),
            "templates": _safe_read_jsonl(files["templates"]),
        }
        self._cache = kb
        self._cache_mtime = cur_mtime
        return kb

    def _filter_rank(self, items: List[Dict[str, Any]], filters: Dict[str, str], kind_whitelist: List[str]) -> List[Dict[str, Any]]:
        industry = (filters.get("industry") or "").strip().lower()
        task = (filters.get("task") or "").strip().lower()
        style = (filters.get("style") or "").strip().lower()

        out = []
        for it in items:
            kind = str(it.get("kind", "")).strip().lower()
            if kind not in [k.lower() for k in kind_whitelist]:
                continue
            if industry and not _list_contains_or_star(it.get("industry", ["*"]), industry):
                continue
            if task and not _list_contains_or_star(it.get("task", ["*"]), task):
                continue
            if style:
                if not _list_contains_or_star(it.get("style", ["*"]), style):
                    continue
            out.append(it)

        def key_fn(x):
            pr = int(x.get("priority", 0) or 0)
            score = _tag_match_score(x.get("tags", []) or [], " ".join(filters.values()))
            return (pr, score)

        out.sort(key=key_fn, reverse=True)
        return out

    def retrieve(self, query: str) -> Tuple[str, List[str]]:
        if not settings.kb_enabled:
            return "", []

        kb = self._load_kb()
        if not any(kb.values()):
            return "", []

        filters = parse_filters(query)

        templates = self._filter_rank(kb["templates"], filters, ["template"])[: settings.kb_topk_templates]
        entries = self._filter_rank(kb["entries"], filters, ["rule", "layout", "material", "element", "negative"])
        palettes = self._filter_rank(kb["palettes"], filters, ["palette"])[: settings.kb_topk_palettes]
        typography = self._filter_rank(kb["typography"], filters, ["typography"])[: settings.kb_topk_typography]

        rules_top = [e for e in entries if e.get("kind") in ("rule", "layout", "material")][: settings.kb_topk_rules]
        elements_top = [e for e in entries if e.get("kind") == "element"][: settings.kb_topk_elements]
        negatives_top = [e for e in entries if e.get("kind") == "negative"][: settings.kb_topk_negatives]

        chosen = templates + rules_top + palettes + typography + elements_top + negatives_top
        hit_ids = [c.get("id", "") for c in chosen if c.get("id")]

        if not chosen:
            return "", []

        parts = []
        parts.append(f"[KB filters] industry={filters.get('industry')}, task={filters.get('task')}, style={filters.get('style') or '*'}")
        if templates:
            parts.append("[模板]")
            for it in templates:
                parts.append(f"- {it.get('text', '')}")
        if rules_top:
            parts.append("[规则与约束]")
            for it in rules_top:
                parts.append(f"- {it.get('text', '')}")
        if palettes:
            parts.append("[配色]")
            for it in palettes:
                parts.append(f"- {it.get('text', '')}")
        if typography:
            parts.append("[字体]")
            for it in typography:
                parts.append(f"- {it.get('text', '')}")
        if elements_top:
            parts.append("[图形元素]")
            for it in elements_top:
                parts.append(f"- {it.get('text', '')}")
        if negatives_top:
            parts.append("[避坑/禁忌]")
            for it in negatives_top:
                parts.append(f"- {it.get('text', '')}")

        return "\n".join(parts), hit_ids


class RAGService:
    # 对外稳定接口
    def __init__(self, kb_root: str) -> None:
        self.retriever = KBRetriever(kb_root)

    def build_context(self, query: str) -> Tuple[str, List[str]]:
        return self.retriever.retrieve(query)
