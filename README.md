# BrandGenPlatform

一个从 0 搭建的 **KB-first + RAG + LLM 推理** 的文生图 Prompt 生成平台。平台不生成图片，仅输出 **LOGO 与门店门头 storefront** 的 **结构化 Prompt 套件**（主 Prompt、负面提示词、推理参数建议）。

## 一、从 0 创建项目的步骤

1. 初始化目录
```
BrandGenPlatform/
  app/            # 应用入口与路由
  core/           # 任务编排器
  rag/            # KB-first RAG 层
  kb/             # 知识库 JSONL
  tests/          # 预留测试
  run.py          # 启动入口
  requirements.txt
```

2. 安装依赖
```bash
cd BrandGenPlatform
pip install -r requirements.txt
```

3. 运行服务
```bash
python run.py
```

## 二、分层结构与职责

1. 应用入口层（App Bootstrap / Lifecycle）
- 负责创建全局状态、加载配置、初始化 RAG、注册路由并启动服务。
- 入口：`run.py` + `app/app_factory.py` + `app/lifecycle.py`。

2. 路由与业务编排层（API Orchestration）
- 对外暴露接口，仅做参数校验与流程编排。
- 路由：`app/routes.py`。
- 核心接口：`/v1/design/prompt`。

3. 设计任务编排器（Design Task Orchestrator）
- 负责输入解析、构造检索 query、调用 RAG、拼装结构化输出。
- 模块：`core/orchestrator.py`。

4. RAG 与检索增强层（KB-first RAG）
- 默认实现：本地 JSONL 检索、简单过滤 + 评分。
- 稳定接口：`RAGService.build_context(query)`。
- 模块：`rag/kb_retriever.py`。

5. 知识库层（kb/ JSONL）
- JSONL 英文 key、中文值；通过 `industry/task/style/tags` 解耦。
- 文件：`kb/entries.jsonl`、`kb/palettes.jsonl`、`kb/typography.jsonl`、`kb/templates.jsonl`。

6. 配置层（Configuration）
- 统一集中管理参数，支持环境变量覆盖。
- 文件：`app/config.py`。

## 三、关键实现代码摘要

- 启动与全局状态
  - `run.py`
  - `app/state.py`
  - `app/lifecycle.py`
- 核心路由
  - `app/routes.py`
- 编排器
  - `core/orchestrator.py`
- RAG 默认实现
  - `rag/kb_retriever.py`
- 配置
  - `app/config.py`
- KB 样例
  - `kb/*.jsonl`

## 四、最小可运行示例

请求：
```bash
curl -X POST http://127.0.0.1:8000/v1/design/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "task": "logo",
    "industry": "餐饮",
    "brand_name": "糖乐",
    "style": "极简、温暖",
    "elements": "甜品、笑脸",
    "avoid": "复杂纹理"
  }'
```

示例响应（节选）：
```json
{
  "task": "logo",
  "prompt": "subject: 餐饮行业 logo 设计，品牌名称：糖乐\nstyle: 极简、温暖；极简扁平风格，强调识别度与品牌温度，图形与文字比例均衡。\npalette: 暖橙、奶油白、浅咖色为主，少量深棕作为对比。\ntypography: 中文采用圆角黑体或手写感字形，保持亲和与可读性。\nelements: 甜品、笑脸；可选用勺子、碗、蒸汽等图形元素表现食物温度感。\nconstraints: 优先使用简洁几何形，确保在小尺寸下仍清晰可辨。",
  "negative_prompt": "写实、复杂背景、杂乱场景、水印、签名、低质量、模糊、噪点、文字变形、错别字、多余物体、过度细节、重渐变、强高光、强阴影，避免：复杂纹理",
  "params": {
    "aspect_ratio": "1:1",
    "steps": 28,
    "cfg": 5.5,
    "num_variants": 4
  },
  "evidence": [
    "tpl-logo-01",
    "rule-food-logo-01",
    "palette-food-01",
    "type-food-01",
    "element-food-01",
    "negative-food-01"
  ]
}
```

case 2:
```bash
curl -X POST http://127.0.0.1:8000/v1/design/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "task": "logo",
    "industry": "餐饮",
    "brand_name": "辣椒先生",
    "style": "市井感、手绘字体、厚重、张力强",
    "elements": 辣椒图形、火焰、红黑高对比",
    "avoid": "几何极简、无衬线冷风格"
  }'
```

## 五、扩展性说明：新增设计任务（如 packaging/menu）

1. 配置层
- 无需修改；如需新增默认参数可在 `app/config.py` 加入配置项。

2. 知识库层
- 在 `kb/entries.jsonl` 与 `kb/templates.jsonl` 追加 `task=packaging` 或 `task=menu` 条目。

3. RAG 层
- 默认实现无需修改，按 task 字段过滤即可。

4. 编排器层
- `core/orchestrator.py` 允许新 task 值，无需修改逻辑。

5. 路由层
- 不需新增接口，仍可使用 `/v1/design/prompt` 统一入口。

## 六、数据流说明（用户输入 → RAG → Prompt）

- 路由接收输入 → 编排器解析
- 构造检索 query → RAG 使用 KB JSONL 检索
- 组装中文主 Prompt + 负面提示词 + params
- 返回结构化 JSON
