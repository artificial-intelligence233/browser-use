# 模块 1：简历信息提取 + 搜索候选岗位网页

## 一、模块定位

本模块是 **六人课程项目中的第 1 个模块**，在整个系统中承担"前置输入"角色。

**我们做什么：**
1. 接收用户上传的简历文件（PDF / DOCX / TXT）
2. 提取纯文本并使用 LLM 或规则引擎解析为结构化 JSON（`ResumeProfile`）
3. 根据简历中的技能、城市、岗位意向，生成多个招聘网站的搜索 query
4. 调用 DuckDuckGo 免费搜索 API，获取招聘/岗位候选链接
5. 输出 `FinalResult JSON`，供后续模块使用

**我们不做什么：**
- 不实现 AI Agent 前端界面（由模块 2 负责）
- 不调用 browser-use 抓取岗位详情页，也不实现岗位信息 RAG（由模块 3 负责）
- 不实现简历优化与应用层能力（由模块 4 负责）
- 不制作汇报 PPT 和演示视频（由模块 5 负责）
- 不实现后端总编排、系统集成和评测（由模块 6 负责）
- 不实现用户登录、数据库持久化

**与 browser-use 的关系：**
本模块**不直接依赖 browser-use**。browser-use 框架由模块 3「Browser Use + 岗位信息 RAG」调用，
通过本模块输出的 `job_links[].url` 列表驱动浏览器自动化抓取。

**核心输出：** `FinalResult JSON` 是本模块与其他模块的联调接口。

## 二、整体流程

```
用户上传简历文件 (.pdf / .docx / .txt)
         │
         ▼
   extract_text()
   根据后缀选择 PyMuPDF / python-docx / 直接读取
   输出：清洗后的纯文本
         │
         ▼
   use_llm=True? ──yes──▶ parse_resume_with_llm()
         │                    │ 调用 OpenAI 兼容 API
         │                    │ 输出：ResumeProfile
         │                    │
         │                on error: graceful fallback
         │                    │
         ▼                    ▼
   parse_resume_with_rules() ◀┘
   正则 + 关键词匹配
   输出：ResumeProfile（确保不抛异常）
         │
         ▼
   generate_search_queries()
   根据 position + city + keywords 生成 6 个搜索模板
   覆盖 BOSS直聘 / 猎聘 / 拉勾 / 前程无忧 + 通用搜索
   输出：list[str]（已去重）
         │
         ▼
   search_job_links()
   逐 query 调用 DuckDuckGo，按 URL 去重
   输出：list[JobLink]（title + url + snippet + source）
         │
         ▼
   FinalResult 组装
   metadata 记录 task_id / created_at / input_file / output_file / parser_type / total_queries / total_links / warnings
         │
         ▼
   保存结果 JSON（CLI 默认生成唯一文件名，避免覆盖历史结果）
         │
         ▼
   下游模块消费：
   - job_links[].url  → 模块 3 browser-use 抓取岗位详情并进入 RAG
   - resume_profile   → 模块 2 前端展示、模块 3 RAG 推荐、模块 4 简历优化、模块 6 编排
   - search_queries   → 模块 2 展示搜索过程、模块 6 记录日志
   - metadata         → 模块 6 状态展示、日志和评测统计
```

**LLM → Rule fallback 决策树：**

| 条件 | 行为 |
|------|------|
| `use_llm=True` + API Key 已配置 + 调用成功 | 使用 LLM 解析，`parser_type="llm"` |
| `use_llm=True` + API Key 未配置 | 抛出 RuntimeError → pipeline 自动 fallback，`parser_type="rule"` |
| `use_llm=True` + LLM 返回非 JSON | 抛出 ValueError → pipeline 自动 fallback，`parser_type="rule"` |
| `use_llm=False` | 直接使用规则解析，`parser_type="rule"` |

## 三、目录结构

```
course_project/
├── backend/
│   ├── __init__.py
│   ├── main.py                          # FastAPI 应用入口，4 个 HTTP 接口
│   └── app/
│       └── resume_search/
│           ├── __init__.py
│           ├── schema.py                # 10 个 Pydantic v2 数据模型
│           ├── config.py                # 环境变量 / .env 配置读取
│           ├── extract_text.py          # PDF/DOCX/TXT → 纯文本
│           ├── llm_parser.py            # LLM 简历解析（OpenAI 兼容接口）
│           ├── rule_parser.py           # 规则解析 fallback（正则 + 关键词）
│           ├── query_generator.py       # 岗位搜索 query 模板生成
│           ├── search_api.py            # DuckDuckGo 免费搜索封装
│           ├── pipeline.py              # 主流程编排（6 阶段线性流水线）
│           ├── cli.py                   # 命令行入口（argparse）
│           └── utils.py                 # 纯函数工具（文本清洗、JSON I/O、URL 校验）
├── examples/
│   └── sample_resume.txt               # 中文样例简历（大模型应用工程师方向）
├── outputs/                             # 流水线输出目录
│   └── .gitkeep
├── uploads/                             # FastAPI 上传文件暂存目录
│   └── .gitkeep
├── tests/
│   └── test_resume_search_pipeline.py   # 20 个 pytest 测试用例
├── .env.example                         # 环境变量模板
├── requirements.txt                     # pip 依赖清单
└── README.md                            # 本文档
```

### 各文件职责详解

#### `backend/main.py`
FastAPI 应用入口。提供 4 个 HTTP 接口：
- `GET /` — 模块自描述，返回接口列表
- `POST /upload_resume` — 上传简历 + 完整流水线，返回 `FinalResult`
- `POST /parse_resume` — 仅解析简历，返回 `ResumeProfile`
- `POST /search_jobs` — 接收已解析的 `ResumeProfile`，执行搜索

内部只做参数校验、文件暂存和异常转 HTTP 状态码，不包含业务逻辑。
上传文件保存到 `course_project/uploads/`。

#### `backend/app/resume_search/schema.py`
定义了 10 个 Pydantic v2 模型，是整个项目的**稳定数据合约**：

| 模型 | 用途 |
|------|------|
| `BasicInfo` | 姓名、电话、邮箱、城市、年龄、性别 |
| `Education` | 学校、学位、专业、起止日期、GPA |
| `Skills` | 四类技能：编程语言 / 框架 / 工具 / 专业技能 |
| `Project` | 项目名称、描述、技术栈、职责、成果 |
| `Internship` | 公司、岗位、起止日期、职责、成果 |
| `JobIntention` | 目标岗位、目标城市、期望薪资、行业 |
| `ResumeProfile` | **核心模型**：聚合以上所有信息 + keywords + inferred_fields |
| `JobLink` | 搜索结果：标题、URL、摘要、来源 query、来源域名 |
| `FinalMetadata` | 执行元数据：输入文件、解析方式、统计计数 |
| `FinalResult` | **顶层输出模型**：ResumeProfile + search_queries + job_links + metadata |

所有字段都有默认值（`""` 或 `[]`），即使解析不完整也不会导致下游报错。
使用 `model_config = ConfigDict(extra='forbid')` 防止 LLM 编造未知字段。

#### `backend/app/resume_search/extract_text.py`
文本提取层。根据文件后缀名自动选择提取引擎：
- `.pdf` → PyMuPDF（支持中文，按页提取）
- `.docx` → python-docx（提取段落文本）
- `.txt` → UTF-8 直接读取

所有提取结果经过 `clean_text()` 清洗（合并多余空格、压缩空行、去除首尾空白）。
不支持的文件格式抛出 `ValueError`，文件不存在抛出 `FileNotFoundError`，
提取为空抛出 `ValueError`。FastAPI 层会把这些输入错误转换为 HTTP 错误响应，CLI 运行时会在终端暴露错误信息。

#### `backend/app/resume_search/llm_parser.py`
LLM 简历解析器。使用 OpenAI 兼容接口（支持自定义 `OPENAI_BASE_URL` 以适配代理和第三方模型）。

设计要点：
- `SYSTEM_PROMPT` 严格约束输出格式——要求只输出 JSON，并在 prompt 中给出完整 schema 示例
- `temperature=0.0` 保证确定性输出
- 对 LLM 输出调用 `strip_json_markdown()` 剥离可能的 ```json 包裹
- 先 `json.loads()` 再 `ResumeProfile(**data)` —— 双重校验确保数据有效
- `OPENAI_API_KEY` 缺失时抛出 `RuntimeError`，由 pipeline 捕获并 fallback

#### `backend/app/resume_search/rule_parser.py`
规则解析器——LLM 不可用时的零成本 fallback。

解析策略：
- **邮箱/手机号**：正则匹配（中国手机号格式）
- **城市**：20 个主要城市的封闭集合关键词匹配
- **姓名**：启发式——首个 1-4 个纯中文字符的行
- **学历**：行内关键词匹配（本科/硕士/博士等）
- **学校**：包含"大学/学院/University"等关键词的行
- **技能**：四类封闭集合匹配（编程语言/框架/工具/专业技能各 ~10 个）
- **项目**：以"项目"开头的区块提取
- **实习**：以"实习"开头的区块提取
- **岗位推断**：`SKILL_TO_POSITION` 优先级表——大模型应用工程师 > AI算法工程师 > 后端开发 > 前端开发 > 默认

推断依据写入 `inferred_fields`，下游可审计每个推断的合理性。

#### `backend/app/resume_search/query_generator.py`
从 `ResumeProfile` 生成 6 个搜索 query 模板：
1. `{city} {position} {keywords} 招聘`
2. `{city} {position} {keywords} JD`
3. `site:zhipin.com {city} {position} {keywords}`
4. `site:liepin.com {city} {position} {keywords}`
5. `site:lagou.com {city} {position} {keywords}`
6. `site:jobs.51job.com {city} {position} {keywords}`

`site:` 前缀告诉 DuckDuckGo 只返回特定域名的结果。
city 优先取 `job_intention.target_city` → `basic_info.city` → `"全国"`。
position 优先取 `job_intention.target_position` → `"软件开发工程师"`。
keywords 从四类技能中按优先级取最多 5 个（编程语言 > 框架 > 工具 > 专业技能）。

#### `backend/app/resume_search/search_api.py`
DuckDuckGo 免费搜索封装。不依赖任何 API Key，全局可用。

- `search_jobs_by_query()` — 单 query 搜索，返回最多 `max_results` 条
- `search_job_links()` — 多 query 批量搜索，按 URL（去尾斜杠）去重

异常处理策略：
- 搜索库未安装 → 返回空列表，并把 warning 写入 `metadata.warnings`
- 单次搜索网络错误 → 返回空列表，并把 warning 写入 `metadata.warnings`，不影响其他 query
- 无效 URL（非 http/https）→ 静默跳过

#### `backend/app/resume_search/pipeline.py`
主流程编排器。CLI 和 FastAPI 都通过此函数运行。

```
run_resume_search_pipeline(file_path, use_llm, max_queries, max_results_per_query, output_path)
    │
    ├─ Stage 1: extract_text(file_path)
    ├─ Stage 2: LLM parse (if enabled) → fallback to rules on error
    ├─ Stage 3: generate_search_queries(profile)
    ├─ Stage 4: search_job_links(queries)
    ├─ Stage 5: assemble FinalResult with metadata
    └─ Stage 6: save_json() if output_path is set
```

异常处理策略：
- 文件不存在、格式不支持、内容为空等输入错误会抛出异常。
- LLM 解析失败会在 pipeline 内 fallback 到 rule parser，并将 `parser_type` 记录为 `"rule"`。
- Search API 失败会记录 warning，写入 `metadata.warnings`，并返回空列表，不中断整个流程。
- FastAPI 层会将异常转换为 HTTP 错误响应；CLI 运行时如果遇到未捕获异常，会在终端显示错误。

#### `backend/app/resume_search/cli.py`
命令行入口。通过 `python -m` 运行，将所有命令行参数透传给 `run_resume_search_pipeline()`，
并格式化打印结果摘要。

#### `backend/app/resume_search/config.py`
环境变量配置。从 `course_project/.env` 加载（使用 python-dotenv），暴露 5 个配置项：
`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` / `DEFAULT_MAX_QUERIES` / `DEFAULT_MAX_RESULTS_PER_QUERY`。

#### `backend/app/resume_search/utils.py`
纯函数工具集：`clean_text()` / `strip_json_markdown()` / `save_json()` / `load_json()` / `get_domain()` / `is_valid_http_url()`。
所有函数无副作用（`save_json` 除外），不依赖全局状态。

#### `tests/test_resume_search_pipeline.py`
20 个 pytest 测试用例，覆盖：
- 文本提取（正常读取、不支持的格式、文件不存在）
- 规则解析（邮箱、手机号、城市、技能检测、岗位推断、推断字段）
- Query 生成（数量限制、包含关键词、无重复）
- Pipeline 端到端（rule mode 返回 FinalResult、输出文件写入）
- 工具函数（文本清洗、JSON markdown 剥离、URL 校验）
- Schema 默认值和序列化

#### `examples/sample_resume.txt`
一份完整的中文样例简历，方向为"大模型应用工程师"。
包含：基本信息、教育经历、技能（Python / LangChain / PyTorch 等）、
两个项目经历、一段字节跳动实习经历、明确的求职意向。

#### `outputs/` 和 `uploads/`
- `outputs/` — CLI 和 pipeline 的 JSON 输出目录
- `uploads/` — FastAPI 上传文件的暂存目录。上传文件名会自动加上时间戳和短 UUID，避免同名简历互相覆盖

## 四、安装和启动

本项目使用 Miniforge / conda 管理 Python 虚拟环境。

### 4.1 环境初始化

```bash
cd /Users/assle/dev/pythonProjects/browser-use

# 创建 conda 虚拟环境（Python 3.11）
conda create -n resume-job-agent python=3.11 -y
conda activate resume-job-agent

# 安装依赖
pip install -r course_project/requirements.txt
```

> **关于 browser-use：** 本模块不直接依赖 browser-use。后续模块如需调用本地 browser-use 源码，
> 可在同一 conda 环境中可选执行 `pip install -e .`（从仓库根目录以 editable 模式安装）。

### 4.2 配置环境变量

```bash
cp course_project/.env.example course_project/.env
```

编辑 `course_project/.env`：

```env
# 可选：LLM 解析需要，不配置则自动使用规则解析
OPENAI_API_KEY=sk-xxxxxxxx
# 可选：自定义 API 地址（代理或第三方模型）
OPENAI_BASE_URL=
# 默认模型
OPENAI_MODEL=gpt-4o-mini
# 搜索参数默认值
DEFAULT_MAX_QUERIES=6
DEFAULT_MAX_RESULTS_PER_QUERY=5
```

**未配置 `OPENAI_API_KEY` 不影响使用**——模块会自动降级到规则解析。

### 4.3 CLI 运行

从仓库根目录：

```bash
python -m course_project.backend.app.resume_search.cli \
  --file course_project/examples/sample_resume.txt \
  --no-llm
```

不传 `--output` 时，CLI 会自动生成唯一输出文件名，例如：

```text
course_project/outputs/final_result_20260429_153012_a1b2c3d4e5f6.json
```

如果显式传入 `--output course_project/outputs/final_result.json`，则会写入指定路径；重复使用同一路径会覆盖旧结果，适合只保留最新一次演示结果的场景。

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--file` | 是 | — | 简历文件路径（.pdf / .docx / .txt） |
| `--output` | 否 | 自动生成唯一文件名 | 输出 JSON 路径；显式指定相同路径时会覆盖旧文件 |
| `--no-llm` | 否 | False | 跳过 LLM，仅使用规则解析 |
| `--max-queries` | 否 | 6 | 生成的最大搜索 query 数 |
| `--max-results-per-query` | 否 | 5 | 每个 query 的最大搜索结果数 |

### 4.4 FastAPI 启动

从仓库根目录：

```bash
uvicorn course_project.backend.main:app --reload
```

启动后：
- Swagger 文档：http://127.0.0.1:8000/docs
- 根路径：http://127.0.0.1:8000/

### 4.5 运行测试

```bash
pytest course_project/tests -vx -o "addopts="
```

（`-o "addopts="` 用于覆盖根目录 pyproject.toml 中的 pytest-xdist 配置）

## 五、API 接口说明

### GET /

**功能：** 模块自描述，返回可用接口列表。

**响应示例：**
```json
{
  "module": "简历信息提取 + 搜索候选岗位网页",
  "version": "1.0.0",
  "endpoints": {
    "POST /upload_resume": "上传简历文件，运行完整 pipeline",
    "POST /parse_resume": "仅解析简历，不搜索岗位",
    "POST /search_jobs": "输入 ResumeProfile JSON，生成 queries 并搜索岗位链接"
  }
}
```

### POST /upload_resume

**功能：** 上传简历文件，运行完整流水线（提取 → 解析 → 搜索 → 去重），返回 `FinalResult`。

**请求：** `multipart/form-data`

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | file | 是 | — | 简历文件（.pdf / .docx / .txt） |
| `use_llm` | bool | 否 | true | 是否启用 LLM 解析 |
| `max_queries` | int | 否 | 6 | 最大搜索 query 数 |
| `max_results_per_query` | int | 否 | 5 | 每个 query 最大结果数 |

**响应：** `FinalResult` JSON（格式见下方"输出 JSON 示例"）

**curl 示例：**
```bash
curl -X POST "http://127.0.0.1:8000/upload_resume" \
  -F "file=@course_project/examples/sample_resume.txt" \
  -F "use_llm=false" \
  -F "max_queries=6" \
  -F "max_results_per_query=5"
```

**错误码：**
- `400` — 文件格式不支持
- `500` — 流水线执行异常（如文件内容为空）

### POST /parse_resume

**功能：** 仅上传并解析简历，不执行岗位搜索。适用于只需要结构化简历数据的下游模块（RAG、简历优化）。

**请求：** `multipart/form-data`

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | file | 是 | — | 简历文件 |
| `use_llm` | bool | 否 | true | 是否启用 LLM 解析 |

**响应：** `ResumeProfile` JSON（格式见下方 `resume_profile` 部分）

**curl 示例：**
```bash
curl -X POST "http://127.0.0.1:8000/parse_resume" \
  -F "file=@course_project/examples/sample_resume.txt" \
  -F "use_llm=false"
```

### POST /search_jobs

**功能：** 接收一个已解析的 `ResumeProfile` JSON，生成搜索 queries 并返回岗位链接。
其他模块可以手工构造或修改 `ResumeProfile` 后调用此接口。

**请求：** `application/json`，body 为 `ResumeProfile` 结构

**Query params：** `max_queries` (default 6), `max_results_per_query` (default 5)

**curl 示例：**
```bash
curl -X POST "http://127.0.0.1:8000/search_jobs?max_queries=6&max_results_per_query=5" \
  -H "Content-Type: application/json" \
  -d '{
    "basic_info": {
      "city": "杭州"
    },
    "skills": {
      "programming_languages": ["Python"],
      "frameworks": ["FastAPI", "LangChain"],
      "tools": ["Docker"],
      "professional_skills": ["RAG", "大模型"]
    },
    "job_intention": {
      "target_position": "大模型应用工程师",
      "target_city": "杭州"
    },
    "keywords": ["Python", "FastAPI", "LangChain", "RAG", "杭州"]
  }'
```

**响应：**
```json
{
  "search_queries": ["杭州 大模型应用工程师 Python ...", "site:zhipin.com ..."],
  "job_links": [
    {
      "title": "大模型应用开发实习生-杭州招聘",
      "url": "https://www.zhipin.com/job_detail/xxx.html",
      "snippet": "...",
      "source_query": "site:zhipin.com 杭州 大模型应用工程师 ...",
      "source": "www.zhipin.com"
    }
  ]
}
```

## 六、输出 JSON 格式

### FinalResult（顶层结构）

```json
{
  "resume_profile": {
    "basic_info": {
      "name": "张明远",
      "phone": "13812345678",
      "email": "zhangmingyuan@example.com",
      "city": "杭州",
      "age": "",
      "gender": ""
    },
    "education": [
      {
        "school": "浙江大学",
        "degree": "本科",
        "major": "计算机科学与技术",
        "start_date": "2020-09",
        "end_date": "2024-06",
        "gpa": "3.7/4.0"
      }
    ],
    "skills": {
      "programming_languages": ["Python", "Java", "JavaScript", "TypeScript", "SQL"],
      "frameworks": ["FastAPI", "React", "PyTorch", "LangChain", "LlamaIndex"],
      "tools": ["Git", "Docker", "Linux", "MySQL", "Redis", "Elasticsearch", "Nginx"],
      "professional_skills": ["机器学习", "自然语言处理", "RAG", "LLM", "大模型", "后端开发"]
    },
    "projects": [
      {
        "name": "智能问答RAG系统",
        "description": "设计并实现了基于RAG的企业文档智能问答系统...",
        "technologies": ["Python", "LangChain", "LlamaIndex", "Elasticsearch", "FastAPI"],
        "responsibilities": ["负责后端服务开发", "向量数据库选型", "检索pipeline优化"],
        "achievements": ["检索准确率达92%", "回答响应时间<3s"]
      }
    ],
    "internships": [
      {
        "company": "字节跳动",
        "position": "大模型应用开发实习生",
        "start_date": "2023-07",
        "end_date": "2023-12",
        "responsibilities": ["参与内部AI助手平台开发", "优化RAG检索流程", "开发Agent编排模块"],
        "achievements": ["将检索延迟降低50%", "获得团队优秀实习生"]
      }
    ],
    "job_intention": {
      "target_position": "大模型应用工程师",
      "target_city": "杭州",
      "expected_salary": "15K-25K",
      "industry": "人工智能"
    },
    "keywords": ["Python", "LangChain", "LlamaIndex", "大模型应用工程师", "杭州"],
    "inferred_fields": ["根据技能 {'RAG', 'LangChain', ...} 推断岗位为 大模型应用工程师"]
  },
  "search_queries": [
    "杭州 大模型应用工程师 Python Java JavaScript TypeScript SQL 招聘",
    "杭州 大模型应用工程师 Python Java JavaScript TypeScript SQL JD",
    "site:zhipin.com 杭州 大模型应用工程师 Python Java JavaScript TypeScript SQL",
    "site:liepin.com 杭州 大模型应用工程师 Python Java JavaScript TypeScript SQL",
    "site:lagou.com 杭州 大模型应用工程师 Python Java JavaScript TypeScript SQL",
    "site:jobs.51job.com 杭州 大模型应用工程师 Python Java JavaScript TypeScript SQL"
  ],
  "job_links": [
    {
      "title": "大模型应用开发-杭州招聘-BOSS直聘",
      "url": "https://www.zhipin.com/job_detail/xxx.html",
      "snippet": "岗位职责：负责大模型应用开发...",
      "source_query": "site:zhipin.com 杭州 大模型应用工程师 Python Java ...",
      "source": "www.zhipin.com"
    }
  ],
  "metadata": {
    "task_id": "a1b2c3d4e5f6",
    "created_at": "2026-04-29T15:30:12+08:00",
    "input_file": "/Users/assle/dev/pythonProjects/browser-use/course_project/examples/sample_resume.txt",
    "output_file": "/Users/assle/dev/pythonProjects/browser-use/course_project/outputs/final_result_20260429_153012_a1b2c3d4e5f6.json",
    "parser_type": "rule",
    "total_queries": 6,
    "total_links": 28,
    "warnings": []
  }
}
```

### metadata 字段说明

`metadata` 记录本次流水线执行的辅助信息，主要用于联调、日志展示和后续评测。它不是简历内容本身，但能帮助判断本次结果的来源和质量。

| 字段 | 类型 | 含义 | 下游用途 |
|------|------|------|----------|
| `task_id` | string | 本次 pipeline 运行的唯一任务 ID。 | 区分多次运行、关联日志和输出文件 |
| `created_at` | string | 本次运行创建时间，使用 ISO 8601 格式并包含时区。 | 前端展示、日志排序、排查历史任务 |
| `input_file` | string | 本次处理的简历文件路径，用于定位数据来源。 | 调试、日志、问题追踪 |
| `output_file` | string | 本次结果 JSON 保存路径；API 未落盘保存时为空字符串。 | 文件联调、下载结果、定位输出文件 |
| `parser_type` | string | 本次实际使用的解析方式，可能是 `llm` 或 `rule`。 | 判断解析质量、展示 fallback 状态 |
| `total_queries` | int | 本次根据简历生成的搜索 query 数量，不是岗位数量。 | 展示搜索过程、评测 query 覆盖度 |
| `total_links` | int | 搜索后去重保留下来的岗位候选链接数量，对应 `job_links.length`。 | 展示搜索结果数量、后续抓取任务数 |
| `warnings` | list[string] | 本次运行中发生但未中断流程的警告，例如 LLM fallback 或某条搜索 query 失败。 | 前端提示、调试、判断为什么链接数量为 0 |

特别注意：
- `total_queries` 表示“生成了几条搜索语句”。
- `total_links` 表示“最终保留了几个岗位候选链接”。
- 两者不是同一个概念，`total_links` 不一定等于 `total_queries * max_results_per_query`，因为搜索可能失败、结果可能重复，也可能被 URL 校验过滤。
- 如果 `total_links` 为 0，应优先查看 `metadata.warnings`，里面会列出搜索失败或无有效链接的具体原因。

### 字段稳定性承诺

- 所有字段都有默认值——缺失字段不会被省略，而是填充空字符串 `""` 或空数组 `[]`
- 不会添加未在 schema.py 中定义的字段（使用 `extra='forbid'`）
- 字段类型不会改变——`skills.programming_languages` 始终是 `list[str]`
- 如需新增字段，会在 schema.py 中定义并设默认值，不破坏旧消费者

## 七、与后续模块对接

### 数据流向

```
本模块 (Module 1)
│
├── final_result_时间戳_task_id.json
│   ├── resume_profile  ───▶ Module 2: 前端展示解析结果
│   │                       Module 3: RAG 简历-岗位匹配推荐
│   │                       Module 4: 简历优化建议
│   │                       Module 6: 后端编排和评测
│   │
│   ├── job_links[].url ──▶ Module 3: browser-use 岗位详情抓取
│   │                       （对每个 url 调用 browser-use 提取完整 JD）
│   │
│   └── metadata        ──▶ Module 6: 状态展示、日志、评测统计
│
└── search_queries      ──▶ Module 2: 展示搜索过程
                         Module 6: 记录搜索日志
```

### 对接方式

1. **文件方式：** CLI 默认输出 `course_project/outputs/final_result_时间戳_task_id.json`，下游模块可根据 `metadata.output_file` 读取对应文件
2. **HTTP 方式：** 本模块启动 FastAPI 服务，下游模块通过 `POST /upload_resume` 或 `POST /search_jobs` 调用
3. **Python 导入方式：** 下游模块可直接 `from course_project.backend.app.resume_search.pipeline import run_resume_search_pipeline`

### 取数示例

**1. 从 API response 取数据**

```python
# 假设 response_json 是 POST /upload_resume 返回的数据
resume_profile = response_json["resume_profile"]
job_links = response_json["job_links"]
urls = [item["url"] for item in job_links]
metadata = response_json["metadata"]
```

**2. 从 JSON 文件取数据**

```python
import json

with open("course_project/outputs/final_result_20260429_153012_a1b2c3d4e5f6.json", encoding="utf-8") as f:
    data = json.load(f)

resume_profile = data["resume_profile"]
job_links = data["job_links"]
urls = [item["url"] for item in job_links]
```

**3. 通过 Python 函数直接调用**

```python
from course_project.backend.app.resume_search.pipeline import run_resume_search_pipeline

result = run_resume_search_pipeline(
    file_path="course_project/examples/sample_resume.txt",
    use_llm=False,
)

profile = result.resume_profile
links = result.job_links
urls = [link.url for link in links]
```

### 下游模块需要关注的关键字段

| 下游模块 | 需要读取的字段 | 用途 |
|----------|---------------|------|
| AI Agent 前端界面 (Module 2) | `FinalResult` 全部字段，尤其是 `resume_profile`、`search_queries`、`job_links` | 展示解析结果、搜索过程和候选岗位链接 |
| Browser Use + 岗位信息 RAG (Module 3) | `job_links[].url`、`resume_profile.skills`、`resume_profile.projects`、`resume_profile.job_intention`、`resume_profile.keywords` | 抓取岗位详情，构建用户画像，检索匹配岗位 |
| 简历优化与应用层 (Module 4) | `resume_profile` 全部字段，以及模块 3 输出的推荐岗位/JD | 分析简历薄弱点，生成定向优化建议 |
| 后端编排 + 系统集成 + 评测 (Module 6) | `metadata`、`search_queries`、`job_links`、`resume_profile` | 任务状态展示、日志记录、缓存和评测统计 |

## 八、注意事项

1. **不修改 browser-use 原项目源码：** 所有代码严格限定在 `course_project/` 目录内
2. **不写死 API Key：** 所有密钥通过 `.env` 文件或环境变量注入
3. **不调用 browser-use：** 本模块只输出链接，不抓取页面内容
4. **候选链接不是强校验链接：** 当前版本只做基础 URL 校验和去重，不验证 HTTP 状态码、HTML 类型、是否为岗位详情页或是否被反爬拦截。可访问性检测、招聘站点白名单、岗位详情页识别属于后续优化。
5. **默认避免覆盖：** CLI 不传 `--output` 时会生成唯一结果文件；FastAPI 上传文件会自动加时间戳和短 UUID。只有显式指定相同 `--output` 路径时才会覆盖旧结果。
6. **DuckDuckGo 频率限制：** 短时间内 >30 次搜索可能被暂时限制，生产环境可考虑替换为付费搜索 API
7. **规则解析的局限性：** 规则解析使用封闭关键词集，无法识别集合外的技能。对于正式答辩，建议配置 LLM API Key 以展示更好的解析效果
8. **Windows 兼容性：** 使用 `pathlib.Path` 处理所有路径，不拼接字符串路径；UTF-8 编码读写
9. **Python 版本：** 需要 Python 3.11+（使用了 `str | None` 联合类型语法）
10. **运行环境：** 使用 Miniforge / conda 虚拟环境（Python 3.11）。依赖通过 `pip install -r course_project/requirements.txt` 安装，不依赖 `uv`。
