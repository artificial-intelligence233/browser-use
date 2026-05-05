# Part 3 Integration Guide: Browser Use + Job Information RAG

> 面向对象：第 1 部分简历解析与岗位搜索、第 2 部分前端、第 4 部分简历优化、第 6 部分后端集成同学。  
> 当前分支：`part3-browser-use-job-rag`  
> 当前模块目录：`job_rag/`  
> 当前原则：以现有代码为准，默认可离线运行，外部浏览器、LLM、embedding API 和 Chroma 均为可选增强。

---

## 1. 本模块负责什么

本模块对应总项目第 3 部分：**Browser Use + 岗位信息 RAG**。

它接收前置模块给出的：

1. `resume_profile`：结构化简历信息。
2. `candidate_urls`：候选岗位页面链接。

它输出给后续模块使用：

1. 岗位页面读取结果。
2. 结构化岗位信息。
3. 清洗、归一化、去重后的岗位信息。
4. 本地检索或向量库索引。
5. 岗位推荐结果。
6. 匹配理由、不匹配原因、简历修改重点。

一句话理解：

```text
简历结构化信息 + 候选岗位 URL
→ 读取岗位页面
→ 抽取岗位 JD
→ 写入检索/向量索引
→ 根据简历召回岗位
→ 评分排序
→ 输出推荐原因和简历优化方向
```

本模块不负责：

1. 不解析原始简历文件。
2. 不生成搜索 query。
3. 不调用 Search API 获取岗位链接。
4. 不做前端页面。
5. 不直接改写最终简历文件。
6. 不做全局任务编排。

---

## 2. 当前实现状态

当前代码已经实现完整 MVP pipeline。

| 能力 | 当前状态 | 说明 |
| --- | --- | --- |
| 本地 demo HTML 读取 | 已完成 | 无网络、无 API key 时也能跑通 demo。 |
| HTTP 公共页面读取 | 已完成 | 仅用于公开可访问页面，不绕过登录、验证码、反爬或付费墙。 |
| Browser Use 页面读取 | 已完成，可选 | 通过环境变量启用，失败后回退到 HTTP/local 路径。 |
| 规则抽取岗位信息 | 已完成 | 支持常见中英文岗位字段。 |
| LLM 抽取 fallback | 已完成，可选 | 用于 V2EX 等非标准页面；只读取本地运行时环境变量。 |
| 岗位归一化与去重 | 已完成 | 城市、薪资、技能归一化，URL 与 title/company/city 去重。 |
| 本地检索索引 | 已完成 | 默认 JSON-backed local token embedding。 |
| Chroma 向量库后端 | 已完成，可选 | 使用 `JOB_RAG_VECTOR_BACKEND=chroma` 启用。 |
| API embedding provider | 已完成，可选 | OpenAI-compatible embedding 接口，失败可回退本地 embedding。 |
| 岗位推荐评分 | 已完成 | 按语义相似度、技能、项目、城市、学历经验、薪资/类型综合评分。 |
| 匹配解释输出 | 已完成 | 输出 `match_reasons`、`mismatch_reasons`、`resume_edit_focus`。 |
| FastAPI 路由 | 已完成，可选 | 如果环境安装 FastAPI，会暴露 `/crawl_jobs` 和 `/recommend_jobs`。 |
| 测试 | 已完成 | 最近验证结果：`20 passed`。 |

---

## 3. 代码结构

当前核心目录如下：

```text
job_rag/
├── README.md
├── __init__.py
├── config.py
├── schemas.py
│
├── api/
│   ├── __init__.py
│   └── routes.py
│
├── crawler/
│   ├── __init__.py
│   ├── browser_use_adapter.py
│   ├── browser_use_runner.py
│   ├── page_extractor.py
│   └── url_utils.py
│
├── extraction/
│   ├── __init__.py
│   ├── job_extractor.py
│   ├── llm_extractor.py
│   ├── normalizer.py
│   ├── prompts.py
│   └── validators.py
│
├── indexing/
│   ├── __init__.py
│   ├── chunker.py
│   ├── embedder.py
│   ├── interfaces.py
│   └── vector_store.py
│
├── matching/
│   ├── __init__.py
│   ├── reason_generator.py
│   ├── retriever.py
│   └── scorer.py
│
├── examples/
│   ├── demo_html/
│   ├── outputs/
│   ├── sample_candidate_urls.json
│   ├── sample_job_posting.json
│   ├── sample_match_result.json
│   ├── sample_resume_profile.json
│   └── run_demo.py
│
├── tests/
│   ├── test_api_routes.py
│   ├── test_browser_use_adapter.py
│   ├── test_chroma_backend.py
│   ├── test_embedder.py
│   ├── test_extractor.py
│   ├── test_llm_extractor.py
│   ├── test_matcher.py
│   ├── test_normalizer.py
│   ├── test_url_utils.py
│   └── test_vector_store.py
│
└── docs/
    └── part3_integration_guide.md
```

重要文件职责：

| 文件 | 职责 |
| --- | --- |
| `job_rag/schemas.py` | 定义输入输出数据结构：`PageContent`、`JobPosting`、`ResumeProfile`、`JobMatchResult`。 |
| `job_rag/config.py` | 读取环境变量，集中管理可选配置。 |
| `job_rag/crawler/browser_use_runner.py` | 统一页面读取入口，支持 local file、HTTP、Browser Use fallback。 |
| `job_rag/crawler/browser_use_adapter.py` | 可选 Browser Use 适配层。 |
| `job_rag/extraction/job_extractor.py` | 规则抽取 + 可选 LLM fallback。 |
| `job_rag/extraction/llm_extractor.py` | OpenAI-compatible 聊天模型岗位抽取。 |
| `job_rag/extraction/normalizer.py` | 城市、薪资、技能归一化和岗位去重。 |
| `job_rag/indexing/embedder.py` | 本地 token embedding 与 OpenAI-compatible embedding。 |
| `job_rag/indexing/vector_store.py` | Local JSON 检索后端与 Chroma 向量库后端。 |
| `job_rag/matching/retriever.py` | 根据简历构建检索 query 并召回岗位。 |
| `job_rag/matching/scorer.py` | 计算匹配分数和排序。 |
| `job_rag/matching/reason_generator.py` | 生成匹配理由、不匹配原因、简历修改重点。 |
| `job_rag/api/routes.py` | 给后端集成使用的函数式 API 和可选 FastAPI 路由。 |
| `job_rag/examples/run_demo.py` | 端到端 demo。 |

---

## 4. 推荐接入方式

推荐其他模块优先接入 `job_rag.api.routes`，而不是直接调用内部 crawler、extractor、vector store。

原因：

1. `routes.py` 已经封装了页面读取、抽取、去重、索引和推荐。
2. 后续内部实现调整时，对外调用结构更稳定。
3. 可以同时支持普通 Python 调用和 FastAPI 路由调用。

### 4.1 最小 Python 调用方式

```python
from job_rag.api.routes import crawl_and_index_jobs, recommend_jobs


crawl_result = crawl_and_index_jobs(
    {
        "run_id": "demo_001",
        "candidate_urls": [
            {
                "url": "https://example.com/job/123",
                "source": "search_api",
            }
        ],
    }
)

recommend_result = recommend_jobs(
    {
        "run_id": "demo_001",
        "resume_profile": {
            "skills": ["Python", "RAG", "LLM", "FastAPI"],
            "target_roles": ["AI Agent 工程师"],
            "target_cities": ["北京", "上海"],
            "projects": [
                {
                    "name": "智能简历优化系统",
                    "description": "基于 RAG 的岗位匹配与简历优化系统",
                    "tech_stack": ["Python", "RAG", "FastAPI"],
                }
            ],
        },
        "top_k": 5,
    }
)
```

### 4.2 异步调用方式

如果第 6 部分后端本身是异步服务，可以直接调用：

```python
from job_rag.api.routes import crawl_jobs, recommend_jobs
from job_rag.indexing.vector_store import index_jobs
from job_rag.schemas import JobPosting


async def run_part3(payload: dict) -> dict:
    crawl_result = await crawl_jobs(payload)

    jobs = [
        JobPosting.from_dict(item)
        for item in crawl_result.get("jobs", [])
    ]
    if jobs:
        index_jobs(jobs)

    return recommend_jobs(
        {
            "run_id": payload["run_id"],
            "resume_profile": payload["resume_profile"],
            "top_k": payload.get("top_k", 5),
        }
    )
```

### 4.3 FastAPI 路由方式

如果运行环境安装了 FastAPI，`job_rag.api.routes` 会提供：

```text
POST /crawl_jobs
POST /recommend_jobs
```

当前 FastAPI 路由是轻量 stub，适合被第 6 部分后端挂载或改造成统一 API。

---

## 5. 输入数据契约

### 5.1 `resume_profile`

来源：第 1 部分“简历信息提取”模块。

当前字段结构：

```json
{
  "name": "Demo User",
  "education": [
    {
      "school": "某大学",
      "degree": "本科",
      "major": "计算机科学与技术"
    }
  ],
  "skills": ["Python", "RAG", "LLM", "FastAPI", "Vector DB"],
  "projects": [
    {
      "name": "智能简历优化系统",
      "description": "基于 RAG 的岗位匹配与简历优化系统",
      "tech_stack": ["Python", "RAG", "FastAPI", "Vector DB"]
    }
  ],
  "internships": [],
  "target_roles": ["AI Agent 工程师", "算法实习生", "后端实习生"],
  "target_cities": ["北京", "上海", "杭州"],
  "salary_expectation": "面议"
}
```

接入要求：

1. `skills` 建议尽量标准化，例如 `Python`、`RAG`、`LLM`、`FastAPI`。
2. `projects[].description` 和 `projects[].tech_stack` 会参与项目相关性评分。
3. `target_roles` 会参与检索 query 构建。
4. `target_cities` 会参与城市匹配评分。
5. 不要在 `resume_profile` 中编造学历、经历、项目或技能。

### 5.2 `candidate_urls`

来源：第 1 部分“岗位搜索”模块。

当前字段结构：

```json
{
  "run_id": "demo_001",
  "candidate_urls": [
    {
      "url": "https://example.com/job/123",
      "source": "search_api"
    }
  ]
}
```

接入要求：

1. `url` 必须是公开可访问的 `http`、`https` 页面，或 demo 用 `file` / 本地 HTML 路径。
2. 不要传需要登录、验证码、付费墙、强反爬绕过的页面。
3. 不建议一次传大量 URL。当前模块面向 demo 和轻量 pipeline，不做高频爬取。
4. `source` 可选，仅用于后续追踪来源。

---

## 6. 输出数据契约

### 6.1 `/crawl_jobs` 或 `crawl_and_index_jobs` 返回

```json
{
  "run_id": "demo_001",
  "status": "success",
  "jobs": [
    {
      "job_id": "f2a7...",
      "url": "https://example.com/job/123",
      "source": "example.com",
      "title": "AI Agent 工程师",
      "company": "Example Company",
      "location": "北京",
      "city": "北京",
      "salary": "20k-30k",
      "salary_min": 20.0,
      "salary_max": 30.0,
      "salary_unit": "monthly",
      "job_type": "全职",
      "education_required": "本科",
      "experience_required": "1-3 年",
      "responsibilities": [
        "负责 RAG 检索链路开发"
      ],
      "requirements": [
        "熟悉 Python、LLM、FastAPI"
      ],
      "skills": ["Python", "RAG", "LLM", "FastAPI"],
      "raw_text": "...",
      "extraction_confidence": 0.86,
      "crawled_at": "2026-05-05T00:00:00+00:00",
      "is_valid": true,
      "validation_errors": []
    }
  ],
  "failed_urls": []
}
```

注意：

1. 一个 URL 失败不会导致整个 pipeline 崩溃。
2. 失败页面会进入 `failed_urls`。
3. 低置信度或无效岗位会保留错误信息，但默认不会进入干净岗位索引。

### 6.2 `/recommend_jobs` 返回

```json
{
  "run_id": "demo_001",
  "recommendations": [
    {
      "job_id": "f2a7...",
      "rank": 1,
      "title": "AI Agent 工程师",
      "company": "Example Company",
      "url": "https://example.com/job/123",
      "match_score": 87,
      "retrieval_score": 0.72,
      "matched_skills": ["Python", "RAG", "LLM"],
      "missing_skills": ["Docker"],
      "match_reasons": [
        "岗位要求 RAG 和 LLM，简历技能中包含相关关键词。"
      ],
      "mismatch_reasons": [
        "岗位提到 Docker，但该技能未在简历结构化信息中体现。"
      ],
      "resume_edit_focus": [
        "可以在项目经历中突出 RAG 检索流程、向量库使用和接口实现。"
      ],
      "score_detail": {
        "semantic_similarity": 0.72,
        "skill_match_score": 0.75,
        "project_relevance_score": 0.8,
        "city_match_score": 1.0,
        "education_or_experience_score": 0.5,
        "job_type_or_salary_score": 0.5
      }
    }
  ]
}
```

下游使用建议：

1. 第 2 部分前端展示 `rank`、`match_score`、`matched_skills`、`missing_skills` 和理由。
2. 第 4 部分简历优化优先使用 `resume_edit_focus` 和目标岗位的 `requirements`。
3. 第 6 部分后端保存 `run_id`，方便关联一次完整 pipeline。

---

## 7. Pipeline 内部流程

当前调用链如下：

```text
candidate_urls
→ crawl_pages()
→ PageContent[]
→ extract_job_postings()
→ JobPosting[]
→ deduplicate_jobs()
→ clean JobPosting[]
→ index_jobs()
→ vector_index.json 或 Chroma collection
→ build_resume_query()
→ retrieve_jobs()
→ rank_jobs()
→ JobMatchResult[]
```

### 7.1 页面读取策略

优先级：

1. 本地 HTML 文件：用于稳定 demo。
2. Browser Use：仅在 `JOB_RAG_ENABLE_BROWSER_USE=1` 且包可用时启用。
3. HTTP fetch：用于公开页面。
4. 失败记录：返回结构化错误，不中断整体流程。

### 7.2 岗位抽取策略

优先级：

1. 规则抽取：适合规范岗位页面。
2. LLM fallback：适合 V2EX 这类非标准页面。
3. 无效岗位记录：保留 `validation_errors`，便于前端或后端展示失败原因。

LLM 抽取要求：

1. 只从页面文本中抽取。
2. 不推断缺失字段。
3. 不编造岗位信息。
4. 输出严格 JSON。

### 7.3 检索与向量库策略

默认：

```text
JOB_RAG_VECTOR_BACKEND=local
JOB_RAG_EMBEDDING_PROVIDER=local
```

默认实现会生成：

```text
job_rag/examples/outputs/vector_index.json
```

增强方案：

1. `JOB_RAG_VECTOR_BACKEND=chroma`：持久化到本地 Chroma。
2. `JOB_RAG_EMBEDDING_PROVIDER=openai_compatible`：使用 OpenAI-compatible embedding API。
3. API embedding 失败时，如果允许 fallback，会自动回退到 local embedding。

---

## 8. 环境变量配置

所有真实密钥、真实模型名、真实 base URL 都只能放在本地运行时环境变量中。

严禁把真实值写入：

1. Git 仓库。
2. Markdown 文档。
3. Python 脚本。
4. 测试文件。
5. 示例 JSON。
6. commit message。
7. PR 描述。

### 8.1 默认离线配置

不设置任何环境变量即可运行本地 demo。

```powershell
D:\Conda\envs\job_rag_browser_use\python.exe job_rag\examples\run_demo.py
```

### 8.2 Browser Use 配置

```powershell
$env:JOB_RAG_ENABLE_BROWSER_USE = "1"
$env:JOB_RAG_BROWSER_USE_TIMEOUT_SECONDS = "60"
$env:PLAYWRIGHT_BROWSERS_PATH = "D:\agent_part3"
```

说明：

1. Chromium / Playwright 浏览器文件当前建议放在 `D:\agent_part3`。
2. Browser Use 只处理公开 `http` / `https` URL。
3. Browser Use 失败时会回退到 HTTP fetch 或返回结构化错误。

### 8.3 LLM 岗位抽取配置

```powershell
$env:JOB_RAG_ENABLE_LLM_EXTRACTION = "1"
$env:JOB_RAG_LLM_BASE_URL = "<your-openai-compatible-base-url>"
$env:JOB_RAG_LLM_MODEL = "<your-chat-model>"
$env:JOB_RAG_LLM_API_KEY = "<your-api-key>"
```

说明：

1. 该配置用于聊天模型抽取岗位字段，不是 embedding。
2. 当前代码会把 provider root URL 规范化到 OpenAI-compatible `/v1` 地址。
3. 如果未配置或调用失败，模块会保留规则抽取结果和错误信息。

### 8.4 API embedding 配置

```powershell
$env:JOB_RAG_EMBEDDING_PROVIDER = "openai_compatible"
$env:JOB_RAG_EMBEDDING_BASE_URL = "<your-openai-compatible-embedding-base-url>"
$env:JOB_RAG_EMBEDDING_MODEL = "<your-embedding-model>"
$env:JOB_RAG_EMBEDDING_API_KEY = "<your-api-key>"
$env:JOB_RAG_EMBEDDING_ALLOW_FALLBACK = "1"
```

说明：

1. embedding 模型用于把岗位文本和简历 query 转成向量。
2. 聊天模型用于抽取岗位字段，两者不是同一类模型。
3. 当前默认允许 API embedding 失败后回退本地 embedding。

### 8.5 Chroma 配置

```powershell
$env:JOB_RAG_VECTOR_BACKEND = "chroma"
$env:JOB_RAG_CHROMA_DIR = "job_rag\examples\outputs\chroma_index"
$env:JOB_RAG_CHROMA_COLLECTION = "job_postings"
```

说明：

1. Chroma 是本地持久化向量库后端。
2. 若未安装 `chromadb`，使用 Chroma backend 会报依赖错误。
3. 默认 local backend 不需要安装 Chroma。

---

## 9. 与其他部分怎么接入

### 9.1 与第 1 部分：简历解析 + 岗位搜索

第 1 部分需要提供两个数据：

```text
resume_profile
candidate_urls
```

推荐交付给第 3 部分的 payload：

```json
{
  "run_id": "user_001_20260505",
  "resume_profile": {
    "skills": ["Python", "RAG", "LLM"],
    "projects": [],
    "target_roles": ["AI Agent 工程师"],
    "target_cities": ["上海"]
  },
  "candidate_urls": [
    {
      "url": "https://example.com/job/123",
      "source": "search_api"
    }
  ],
  "top_k": 5
}
```

第 1 部分需要注意：

1. `resume_profile` 字段名尽量保持与 `schemas.py` 一致。
2. `candidate_urls` 只传公开可访问岗位页面。
3. 如果搜索结果是列表页，建议先筛出具体岗位详情页。
4. 如果 URL 失败，第 3 部分会返回失败原因，第 1 部分可以换候选 URL。

### 9.2 与第 2 部分：AI Agent 前端

前端推荐展示这些阶段状态：

```text
读取候选岗位
→ 抽取岗位信息
→ 建立岗位索引
→ 根据简历推荐岗位
→ 展示匹配理由和简历修改重点
```

前端可展示字段：

1. 岗位卡片：`title`、`company`、`city`、`salary`、`job_type`。
2. 匹配结果：`match_score`、`matched_skills`、`missing_skills`。
3. 解释区：`match_reasons`、`mismatch_reasons`。
4. 简历建议区：`resume_edit_focus`。
5. 错误区：`failed_urls`、`validation_errors`。

前端不需要直接调用内部 extractor 或 vector store。建议由第 6 部分后端统一调用本模块。

### 9.3 与第 4 部分：简历优化

第 4 部分主要使用：

```text
recommendations[*].job_id
recommendations[*].title
recommendations[*].company
recommendations[*].matched_skills
recommendations[*].missing_skills
recommendations[*].match_reasons
recommendations[*].mismatch_reasons
recommendations[*].resume_edit_focus
recommendations[*].score_detail
```

使用原则：

1. 可以让用户选择某个目标岗位，然后把该岗位推荐结果传给简历优化模块。
2. 简历优化只能强调用户已有经历和技能，不能编造事实。
3. `missing_skills` 表示“简历结构化信息中未体现”，不等于用户一定不会。
4. `resume_edit_focus` 是修改重点，不是可直接照抄的虚构经历。

### 9.4 与第 6 部分：后端编排

第 6 部分建议按这个顺序集成：

```text
/upload_resume
→ /parse_resume
→ /search_jobs
→ job_rag.api.routes.crawl_and_index_jobs
→ job_rag.api.routes.recommend_jobs
→ /optimize_resume
```

后端推荐封装接口：

```python
from job_rag.api.routes import crawl_and_index_jobs, recommend_jobs


def run_job_rag_pipeline(payload: dict) -> dict:
    crawl_result = crawl_and_index_jobs(
        {
            "run_id": payload["run_id"],
            "candidate_urls": payload["candidate_urls"],
        }
    )

    recommend_result = recommend_jobs(
        {
            "run_id": payload["run_id"],
            "resume_profile": payload["resume_profile"],
            "top_k": payload.get("top_k", 5),
        }
    )

    return {
        "run_id": payload["run_id"],
        "crawl_result": crawl_result,
        "recommend_result": recommend_result,
    }
```

后端需要负责：

1. 保存 `run_id`。
2. 管理用户会话和历史记录。
3. 控制 URL 数量和调用频率。
4. 注入本地环境变量。
5. 不把 API key 传给前端。
6. 不把真实密钥写入日志。

---

## 10. 评分逻辑

当前最终分数范围是 `0-100`。

公式：

```text
final_score =
0.35 * semantic_similarity
+ 0.25 * skill_match
+ 0.20 * project_relevance
+ 0.10 * city_match
+ 0.05 * education_or_experience_match
+ 0.05 * job_type_or_salary_match
```

字段解释：

| 字段 | 含义 |
| --- | --- |
| `semantic_similarity` | 简历 query 与岗位文本的检索相似度。 |
| `skill_match` | 简历技能与岗位技能要求重合度。 |
| `project_relevance` | 简历项目描述和岗位要求的相关性。 |
| `city_match` | 目标城市与岗位城市是否匹配。 |
| `education_or_experience_match` | 学历或经验要求是否大致匹配。 |
| `job_type_or_salary_match` | 岗位类型或薪资期望是否有基本匹配。 |

解释生成原则：

1. 只引用简历和岗位中实际出现的信息。
2. 不编造技能、项目、实习、学历或经历。
3. 缺失技能使用“未在简历结构化信息中体现”这类表述。
4. 简历建议只写“强调/补充表达方向”，不写虚构经历。

---

## 11. 错误处理约定

### 11.1 URL 失败

URL 失败时返回：

```json
{
  "failed_urls": [
    {
      "url": "https://example.com/job/blocked",
      "error": "HTTP Error 403: Forbidden"
    }
  ]
}
```

常见原因：

1. 页面不可访问。
2. 页面需要登录。
3. 页面被 CloudFront、WAF 或反爬策略阻断。
4. 页面返回空文本。
5. URL 不是岗位详情页。

### 11.2 抽取低置信度

抽取结果可能包含：

```json
{
  "is_valid": false,
  "validation_errors": [
    "missing title",
    "missing responsibilities and requirements",
    "low confidence extraction"
  ]
}
```

处理建议：

1. 前端可以提示“该岗位页面无法可靠抽取”。
2. 后端可以更换 URL 或启用 LLM fallback。
3. 不建议把低置信度岗位直接用于简历优化。

### 11.3 LLM 或 embedding API 失败

当前策略：

1. LLM 抽取失败：保留规则抽取结果和错误原因。
2. embedding API 失败：默认回退本地 embedding。
3. Chroma 不可用：需要安装 `chromadb` 或改回 local backend。

---

## 12. 本地验证命令

### 12.1 运行完整 demo

```powershell
D:\Conda\envs\job_rag_browser_use\python.exe job_rag\examples\run_demo.py
```

demo 输出目录：

```text
job_rag/examples/outputs/
```

关键输出文件：

```text
page_contents.json
job_postings.json
clean_job_postings.json
retrieved_jobs.json
job_recommendations.json
vector_index.json
```

### 12.2 运行测试

```powershell
D:\Conda\envs\job_rag_browser_use\python.exe -m pytest -o addopts= job_rag\tests
```

最近验证结果：

```text
20 passed
```

### 12.3 敏感信息扫描

提交前建议扫描：

```powershell
Select-String -Path job_rag\* -Pattern "sk-|api-key|base-url|真实模型名" -Recurse
```

如果扫描命中真实密钥、真实 base URL 或真实模型名，必须先删除再提交。

---

## 13. 当前已知限制

1. 当前模块是 MVP，不做高频爬取或大规模商业 scraping。
2. Browser Use 只能提升动态页面读取能力，不能绕过登录、验证码、付费墙或访问限制。
3. 非标准页面如果不开启 LLM fallback，规则抽取可能置信度较低。
4. 默认 local embedding 更适合 demo 和稳定测试，语义效果不如正式 embedding API。
5. Chroma 是本地持久化向量库，不等同于团队级远程向量数据库服务。
6. API route 当前是轻量接入层，生产级鉴权、任务队列、缓存和日志应由第 6 部分后端处理。

---

## 14. 其他成员最小接入清单

第 1 部分需要提供：

```text
resume_profile: dict
candidate_urls: list[dict]
```

第 6 部分需要调用：

```python
from job_rag.api.routes import crawl_and_index_jobs, recommend_jobs
```

第 2 部分前端需要展示：

```text
recommendations
failed_urls
validation_errors
```

第 4 部分简历优化需要使用：

```text
selected recommendation
matched_skills
missing_skills
match_reasons
mismatch_reasons
resume_edit_focus
```

所有模块共同遵守：

1. 不提交真实 API key。
2. 不把真实密钥返回给前端。
3. 不编造简历事实。
4. 不绕过网站访问限制。
5. 出错时保留结构化错误，保证 demo pipeline 不因单个 URL 失败而中断。
