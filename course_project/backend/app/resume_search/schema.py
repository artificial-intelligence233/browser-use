"""Pydantic models for resume parsing and job search results.

These models serve as the stable wire format between the six course-project
modules.  Every field has a default (empty string or empty list) so that
partial parses never break downstream consumers.

Key models:
- ResumeProfile: the core structured resume (output of parse step)
- JobLink: a single search result pointing to a job listing
- FinalResult: the top-level output written to final_result.json
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BasicInfo(BaseModel):
    """Candidate identity and contact details."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", description="候选人姓名")
    phone: str = Field(default="", description="候选人联系电话")
    email: str = Field(default="", description="候选人邮箱地址")
    city: str = Field(default="", description="候选人当前所在城市")
    age: str = Field(default="", description="候选人年龄")
    gender: str = Field(default="", description="候选人性别")


class Education(BaseModel):
    """A single education entry (school → degree → date range)."""

    model_config = ConfigDict(extra="forbid")

    school: str = Field(default="", description="学校或教育机构名称")
    degree: str = Field(default="", description="学历或学位，例如本科、硕士、博士")
    major: str = Field(default="", description="专业名称")
    start_date: str = Field(default="", description="教育经历开始时间")
    end_date: str = Field(default="", description="教育经历结束时间")
    gpa: str = Field(default="", description="GPA 或成绩信息")


class Skills(BaseModel):
    """Four-category skill taxonomy used by both LLM and rule parsers.

    The split into programming_languages / frameworks / tools / professional_skills
    lets the query generator pick representative keywords per category.
    """

    model_config = ConfigDict(extra="forbid")

    programming_languages: list[str] = Field(default_factory=list, description="编程语言技能列表")
    frameworks: list[str] = Field(default_factory=list, description="框架或库技能列表")
    tools: list[str] = Field(default_factory=list, description="开发工具、中间件或平台技能列表")
    professional_skills: list[str] = Field(default_factory=list, description="专业技能或领域能力列表")


class Project(BaseModel):
    """A project entry from the resume — name, tech stack, and contributions."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", description="项目名称")
    description: str = Field(default="", description="项目简介或背景说明")
    technologies: list[str] = Field(default_factory=list, description="项目使用的技术栈")
    responsibilities: list[str] = Field(default_factory=list, description="候选人在项目中的职责列表")
    achievements: list[str] = Field(default_factory=list, description="项目成果、指标或亮点列表")


class Internship(BaseModel):
    """An internship / work-experience entry."""

    model_config = ConfigDict(extra="forbid")

    company: str = Field(default="", description="实习或工作单位名称")
    position: str = Field(default="", description="实习或工作岗位名称")
    start_date: str = Field(default="", description="实习或工作开始时间")
    end_date: str = Field(default="", description="实习或工作结束时间")
    responsibilities: list[str] = Field(default_factory=list, description="实习或工作职责列表")
    achievements: list[str] = Field(default_factory=list, description="实习或工作成果列表")


class JobIntention(BaseModel):
    """Candidate's stated or inferred job preference.

    target_position and target_city drive search-query generation; if absent
    they are inferred from skills / basic_info by the parser.
    """

    model_config = ConfigDict(extra="forbid")

    target_position: str = Field(default="", description="候选人的目标岗位")
    target_city: str = Field(default="", description="候选人的目标工作城市")
    expected_salary: str = Field(default="", description="候选人的期望薪资")
    industry: str = Field(default="", description="候选人的目标行业")


class ResumeProfile(BaseModel):
    """Stable structured resume — the single source of truth for downstream modules.

    Every downstream consumer (RAG, resume optimiser, browser-use scraper) reads
    this structure.  Field stability is critical: renaming or removing a field
    breaks the pipeline for other team members.
    """

    model_config = ConfigDict(extra="forbid")

    basic_info: BasicInfo = Field(default_factory=BasicInfo, description="候选人基本信息")
    education: list[Education] = Field(default_factory=list, description="候选人教育经历列表")
    skills: Skills = Field(default_factory=Skills, description="候选人技能信息")
    projects: list[Project] = Field(default_factory=list, description="候选人项目经历列表")
    internships: list[Internship] = Field(default_factory=list, description="候选人实习或工作经历列表")
    job_intention: JobIntention = Field(default_factory=JobIntention, description="候选人求职意向")
    keywords: list[str] = Field(default_factory=list, description="用于岗位搜索和推荐的关键词列表")
    inferred_fields: list[str] = Field(default_factory=list, description="由解析器推断出的字段及推断依据列表")


class JobLink(BaseModel):
    """A single search-result entry pointing to a job listing HTML page.

    url is the payload — the browser-use module will later scrape these pages.
    source_query records which search query produced this result (for debugging).
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", description="搜索结果标题")
    url: str = Field(default="", description="岗位或招聘页面 URL")
    snippet: str = Field(default="", description="搜索结果摘要")
    source_query: str = Field(default="", description="产生该搜索结果的原始搜索 query")
    source: str = Field(default="", description="搜索结果来源域名")


class FinalMetadata(BaseModel):
    """Execution metadata — records how the pipeline ran so results are auditable.

    parser_type is either 'llm' or 'rule' — downstream consumers can decide
    whether to trust LLM-extracted fields or treat them as best-effort.
    task_id / created_at / output_file make repeated runs traceable and avoid
    confusing one run's output with another.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default="", description="本次流水线任务的唯一标识")
    created_at: str = Field(default="", description="本次流水线任务创建时间")
    input_file: str = Field(default="", description="输入简历文件的绝对路径")
    output_file: str = Field(default="", description="输出 JSON 文件的绝对路径")
    parser_type: str = Field(default="rule", description="实际使用的解析方式，可选值为 llm 或 rule")
    total_queries: int = Field(default=0, description="本次生成的搜索 query 总数")
    total_links: int = Field(default=0, description="本次搜索得到的岗位链接总数")
    warnings: list[str] = Field(default_factory=list, description="流水线执行过程中的警告信息列表")


class FinalResult(BaseModel):
    """Top-level output written to final_result.json.

    Contains everything downstream modules need:
    - resume_profile → RAG / resume optimiser
    - job_links      → browser-use page scraper
    - metadata       → audit trail
    """

    model_config = ConfigDict(extra="forbid")

    resume_profile: ResumeProfile = Field(default_factory=ResumeProfile, description="解析后的结构化简历信息")
    search_queries: list[str] = Field(default_factory=list, description="根据简历生成的岗位搜索 query 列表")
    job_links: list[JobLink] = Field(default_factory=list, description="搜索得到的候选岗位链接列表")
    metadata: FinalMetadata = Field(default_factory=FinalMetadata, description="本次流水线运行的元数据信息")


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Convenience wrapper — delegates to Pydantic's model_dump()."""
    return model.model_dump()
