# Part 3 修正后任务规划

本文档用于说明当前第 3 部分 **Browser Use + 岗位信息 RAG** 的项目结构、任务节点状态和当前运行环境。

## 1. 模块目标

第 3 部分负责接收前序模块输出的结构化简历和候选岗位 URL，完成岗位页面读取、岗位信息抽取、岗位检索、岗位匹配打分和解释输出。

输入：

```text
resume_profile.json
candidate_urls.json
```

输出：

```text
page_contents.json
job_postings.json
clean_job_postings.json
vector_index.json 或 chroma_index/
retrieved_jobs.json
job_recommendations.json
```

当前主入口：

```bash
python job_rag/examples/run_demo.py
```

## 2. 项目结构设计

当前模块位于统一仓库根目录：

```text
browser-use/
+-- job_rag/
```

完整结构设计如下：

```text
job_rag/
+-- README.md
+-- __init__.py
+-- config.py
+-- schemas.py
+-- crawler/
|   +-- __init__.py
|   +-- browser_use_adapter.py
|   +-- browser_use_runner.py
|   +-- page_extractor.py
|   +-- url_utils.py
+-- extraction/
|   +-- __init__.py
|   +-- job_extractor.py
|   +-- normalizer.py
|   +-- prompts.py
|   +-- validators.py
+-- indexing/
|   +-- __init__.py
|   +-- chunker.py
|   +-- embedder.py
|   +-- interfaces.py
|   +-- vector_store.py
+-- matching/
|   +-- __init__.py
|   +-- reason_generator.py
|   +-- retriever.py
|   +-- scorer.py
+-- api/
|   +-- __init__.py
|   +-- routes.py
+-- examples/
|   +-- run_demo.py
|   +-- sample_candidate_urls.json
|   +-- sample_job_posting.json
|   +-- sample_match_result.json
|   +-- sample_resume_profile.json
|   +-- local_jobs/
|   |   +-- ai_agent_intern.html
|   |   +-- data_platform_intern.html
|   |   +-- frontend_engineer.html
|   |   +-- ml_research_intern.html
|   |   +-- rag_backend_engineer.html
|   +-- outputs/
|       +-- .gitkeep
+-- tests/
|   +-- test_browser_use_adapter.py
|   +-- test_browser_use_runner.py
|   +-- test_extractor.py
|   +-- test_matcher.py
|   +-- test_normalizer.py
|   +-- test_url_utils.py
|   +-- test_vector_store.py
+-- docs/
    +-- evaluation_report.md
    +-- part3_demo_script.md
    +-- part3_ppt_notes.md
    +-- part3_corrected_task_plan.md
```

各目录职责：

| 目录/文件 | 职责 |
|---|---|
| `config.py` | 管理输出目录、Browser Use 开关、embedding provider、vector backend 等配置 |
| `schemas.py` | 定义 `PageContent`、`ResumeProfile`、`JobPosting`、`JobMatchResult` 等核心数据结构 |
| `crawler/` | 读取本地 HTML、HTTP 页面，并预留 Browser Use 页面读取能力 |
| `extraction/` | 从页面文本中抽取岗位标题、公司、地点、薪资、职责、要求、技能等字段 |
| `indexing/` | 构建岗位检索文本、embedding 接口、向量库后端接口和本地 fallback 检索 |
| `matching/` | 根据简历检索岗位、计算匹配分、生成匹配理由和不匹配原因 |
| `api/` | 提供 `/crawl_jobs` 和 `/recommend_jobs` 的后端集成 stub |
| `examples/` | 提供可离线运行的 demo 数据、HTML 样例和输出目录 |
| `tests/` | 覆盖 URL、抽取、归一化、检索、匹配、Browser Use fallback 等核心逻辑 |
| `docs/` | 存放汇报说明、demo 脚本、评估模板和修正后任务规划 |

## 3. 当前处理流程

```text
sample_resume_profile.json
+ sample_candidate_urls.json
→ crawl_pages()
→ page_contents.json
→ extract_job_postings()
→ job_postings.json
→ deduplicate_jobs()
→ clean_job_postings.json
→ index_jobs()
→ vector_index.json
→ retrieve_jobs()
→ retrieved_jobs.json
→ rank_jobs()
→ job_recommendations.json
```

当前检索层已经改为可插拔结构：

```text
index_jobs / search_jobs
→ get_vector_store_backend()
→ VectorStoreBackend
→ EmbeddingProvider
```

当前默认配置：

```text
JOB_RAG_EMBEDDING_PROVIDER=local
JOB_RAG_VECTOR_BACKEND=local
```

后续可扩展为：

```text
JOB_RAG_VECTOR_BACKEND=chroma
JOB_RAG_EMBEDDING_PROVIDER=openai
```

## 4. 修正后任务节点

| 节点 | 任务 | 状态 | 完成标志 |
|---|---|---|---|
| 1 | 克隆统一仓库并创建个人分支 | 已完成 | 远程分支 `part3-browser-use-job-rag` 已 push |
| 2 | 创建 `job_rag/` 基础模块结构 | 已完成 | 包结构、README、配置和 schema 已存在 |
| 3 | 添加 demo 输入和本地岗位 HTML | 已完成 | `examples/` 中有 sample JSON 和本地岗位 HTML |
| 4 | 实现页面读取 fallback | 已完成 | 本地 HTML / HTTP 页面可读取，单个 URL 失败不影响整体流程 |
| 5 | 接入 Browser Use 可选适配器 | 部分完成 | 代码层 adapter 已完成；真实 Chromium 启动仍需本地终端继续验证 |
| 6 | 实现岗位信息抽取 | 已完成 | 能抽取标题、公司、地点、薪资、职责、要求、技能等字段 |
| 7 | 实现校验、归一化和去重 | 已完成 | 支持岗位有效性校验、城市/薪资/技能归一化、重复岗位去重 |
| 8 | 实现本地检索 fallback | 已完成 | `LocalJsonVectorStore` 可索引和检索岗位 |
| 9 | 完善匹配评分公式 | 已完成 | 已输出 `semantic_similarity`、`skill_match`、`project_relevance`、`city_match` 等分项 |
| 10 | 中文化匹配解释 | 已完成 | 匹配理由、不匹配原因、简历修改重点已改为中文模板 |
| 11 | 抽象 embedding 和 vector store 接口 | 已完成 | 已新增 `EmbeddingProvider`、`VectorStoreBackend` 接口 |
| 12 | 实现 Chroma 向量库后端 | 待完成 | 需要新增 `ChromaVectorStoreBackend` 并持久化到 `chroma_index/` |
| 13 | 实现 OpenAI embedding provider | 暂缓 | 暂时不使用 OpenAI embedding；后续读取 `OPENAI_API_KEY` |
| 14 | 与第 6 部分后端 API 对齐 | 待完成 | 需确认 `/crawl_jobs`、`/recommend_jobs` 的请求/响应字段 |
| 15 | Pull Request / 合并 | 暂缓 | 当前只 push 个人分支，不创建 PR，不合并 main |

## 5. 当前项目环境

当前工作区：

```text
E:\R_store\agent_part3
```

完整 GitHub 仓库本地路径：

```text
E:\R_store\agent_part3\browser-use-repo
```

远程仓库：

```text
https://github.com/artificial-intelligence233/browser-use
```

当前分支：

```text
part3-browser-use-job-rag
```

当前已推送的关键提交：

```text
967c34e5 feat: add part3 job rag module
8549e854 feat: add detailed job match scoring
2c19d535 feat: add pluggable retrieval interfaces
```

Python / conda 环境：

```text
D:\Conda\envs\job_rag_browser_use
```

已安装能力：

```text
browser-use 0.12.6
uv 0.11.8
Playwright Chromium 组件
```

Playwright / Chromium 本地缓存根目录：

```text
D:\agent_part3
```

说明：

```text
这里是 Playwright/Browser Use 自动下载后的本地缓存路径，不是网络下载 URL。
Chromium 不在 conda 环境 D:\Conda\envs\job_rag_browser_use 内。
```

当前 Chromium 子目录：

```text
D:\agent_part3\chromium-1217
```

Chromium 目录大小约：

```text
410.19 MB
```

当前已知限制：

```text
browser-use 实际启动 Chromium 时曾遇到 [WinError 5] 拒绝访问。
因此当前 demo 仍默认使用本地 HTML / HTTP fallback。
```

## 6. 当前验证结果

在完整仓库路径下运行：

```bash
python job_rag/examples/run_demo.py
```

结果：

```text
通过，成功生成 outputs 下的 JSON 文件。
```

测试命令：

```bash
python -m pytest -o addopts= job_rag/tests
```

结果：

```text
14 passed
```

说明：

```text
目标仓库 pyproject.toml 中的 pytest addopts 依赖 pytest-xdist。
当前环境未安装该插件，因此测试时使用 -o addopts= 覆盖仓库默认 pytest 参数。
```

## 7. 下一步建议

优先级建议：

```text
1. 实现 ChromaVectorStoreBackend
2. 用 local embedding provider + Chroma 后端验证持久化向量库
3. 后续再接 OpenAIEmbeddingProvider
4. 在普通本地终端继续验证真实 browser-use 页面读取
5. 与第 6 部分后端同学对齐 API 输入输出
```

Chroma 后端目标：

```text
JOB_RAG_VECTOR_BACKEND=chroma
python job_rag/examples/run_demo.py
```

预期新增持久化目录：

```text
job_rag/examples/outputs/chroma_index/
```
