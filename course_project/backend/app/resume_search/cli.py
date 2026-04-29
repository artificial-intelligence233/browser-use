"""CLI entry point for the resume search pipeline.

Usage (from repo root):
    python -m course_project.backend.app.resume_search.cli \\
        --file course_project/examples/sample_resume.txt \\
        --no-llm

This is a thin argparse wrapper around run_resume_search_pipeline() — all
business logic lives in pipeline.py.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from course_project.backend.app.resume_search.config import settings
from course_project.backend.app.resume_search.pipeline import run_resume_search_pipeline


def _default_output_path(task_id: str) -> Path:
    """Generate a unique default output path for each CLI run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("course_project/outputs") / f"final_result_{timestamp}_{task_id}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="简历信息提取 + 岗位搜索")
    parser.add_argument("--file", required=True, type=str, help="简历文件路径 (.pdf / .docx / .txt)")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出 JSON 路径；不传则自动生成唯一文件名，避免覆盖历史结果",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="不使用 LLM，仅使用规则解析",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=settings.DEFAULT_MAX_QUERIES,
        help="最大搜索 query 数量",
    )
    parser.add_argument(
        "--max-results-per-query",
        type=int,
        default=settings.DEFAULT_MAX_RESULTS_PER_QUERY,
        help="每个 query 的最大搜索结果数",
    )

    args = parser.parse_args()
    file_path = Path(args.file)
    task_id = uuid4().hex[:12]
    output_path = Path(args.output) if args.output else _default_output_path(task_id)

    # Early exit on missing file — clearer than letting the pipeline raise
    if not file_path.exists():
        print(f"[ERROR] 文件不存在: {file_path}")
        return

    use_llm = not args.no_llm

    print("=" * 60)
    print("简历信息提取 + 岗位搜索 Pipeline")
    print("=" * 60)

    result = run_resume_search_pipeline(
        file_path=file_path,
        use_llm=use_llm,
        max_queries=args.max_queries,
        max_results_per_query=args.max_results_per_query,
        output_path=output_path,
        task_id=task_id,
    )

    # Human-readable summary for terminal review
    print(f"\n解析方式: {result.metadata.parser_type}")
    print(f"输入文件: {result.metadata.input_file}")
    print(f"\n搜索 Queries ({result.metadata.total_queries} 个):")
    for i, q in enumerate(result.search_queries, 1):
        print(f"  {i}. {q}")

    print(f"\n岗位链接 ({result.metadata.total_links} 个):")
    if result.job_links:
        for i, link in enumerate(result.job_links, 1):
            print(f"  {i}. {link.title}")
            print(f"     {link.url}")
    else:
        print("  (未找到岗位链接)")

    if result.metadata.warnings:
        print("\nWarnings:")
        for warning in result.metadata.warnings:
            print(f"  - {warning}")

    print(f"\n输出文件: {output_path.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
