"""Tests for the resume search pipeline.

Run from repo root:
    pytest course_project/tests
"""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE = (
    Path(__file__).resolve().parent.parent / "examples" / "sample_resume.txt"
)


class TestExtractText:
    def test_read_sample_txt_and_not_empty(self):
        from course_project.backend.app.resume_search.extract_text import extract_text

        text = extract_text(SAMPLE)
        assert len(text) > 0
        assert "张明远" in text

    def test_unsupported_format_raises(self, tmp_path):
        from course_project.backend.app.resume_search.extract_text import extract_text

        bad = tmp_path / "test.xyz"
        bad.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported"):
            extract_text(bad)

    def test_missing_file_raises(self):
        from course_project.backend.app.resume_search.extract_text import extract_text

        with pytest.raises(FileNotFoundError):
            extract_text("nonexistent_file_999.txt")


class TestRuleParser:
    def test_extracts_email(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        assert profile.basic_info.email == "zhangmingyuan@example.com"

    def test_extracts_phone(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        assert "13812345678" in profile.basic_info.phone

    def test_extracts_city(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        assert profile.basic_info.city == "杭州"

    def test_infers_position(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        # Should infer 大模型应用工程师 from RAG/LLM/LangChain skills
        assert "大模型应用工程师" in profile.job_intention.target_position

    def test_detects_skills(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        assert "Python" in profile.skills.programming_languages
        assert "FastAPI" in profile.skills.frameworks
        assert "Docker" in profile.skills.tools
        assert "LLM" in profile.skills.professional_skills

    def test_has_inferred_fields(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        assert len(profile.inferred_fields) > 0


class TestQueryGenerator:
    def test_generates_queries(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules
        from course_project.backend.app.resume_search.query_generator import generate_search_queries

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        queries = generate_search_queries(profile, max_queries=6)
        assert len(queries) >= 1
        assert len(queries) <= 6
        assert all(isinstance(q, str) for q in queries)

    def test_queries_contain_position_and_city(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules
        from course_project.backend.app.resume_search.query_generator import generate_search_queries

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        queries = generate_search_queries(profile, max_queries=6)
        for q in queries:
            assert "杭州" in q or "大模型" in q or "工程师" in q

    def test_no_duplicate_queries(self):
        from course_project.backend.app.resume_search.extract_text import extract_text
        from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules
        from course_project.backend.app.resume_search.query_generator import generate_search_queries

        text = extract_text(SAMPLE)
        profile = parse_resume_with_rules(text)
        queries = generate_search_queries(profile, max_queries=10)
        assert len(queries) == len(set(queries))


class TestPipeline:
    def test_rule_pipeline_returns_final_result(self, monkeypatch):
        from course_project.backend.app.resume_search.schema import JobLink
        from course_project.backend.app.resume_search import pipeline
        from course_project.backend.app.resume_search.pipeline import run_resume_search_pipeline

        monkeypatch.setattr(
            pipeline,
            "search_job_links_with_warnings",
            lambda queries, max_results_per_query=5: (
                [JobLink(title="测试岗位", url="https://example.com/job", source_query=queries[0], source="example.com")],
                [],
            ),
        )

        result = run_resume_search_pipeline(
            file_path=SAMPLE,
            use_llm=False,
            output_path=None,
        )
        assert result.metadata.parser_type == "rule"
        assert result.metadata.input_file.endswith("sample_resume.txt")
        assert result.metadata.task_id
        assert result.metadata.created_at
        assert result.metadata.output_file == ""
        assert result.metadata.warnings == []
        assert len(result.search_queries) >= 1
        assert result.metadata.total_links == 1
        assert result.resume_profile.basic_info.email == "zhangmingyuan@example.com"

    def test_pipeline_with_output_file(self, tmp_path, monkeypatch):
        from course_project.backend.app.resume_search import pipeline
        from course_project.backend.app.resume_search.pipeline import run_resume_search_pipeline

        monkeypatch.setattr(
            pipeline,
            "search_job_links_with_warnings",
            lambda queries, max_results_per_query=5: ([], ["search failed in test"]),
        )

        out = tmp_path / "result.json"
        result = run_resume_search_pipeline(
            file_path=SAMPLE,
            use_llm=False,
            output_path=out,
            task_id="test-task-001",
        )
        assert out.exists()
        data = __import__("json").loads(out.read_text(encoding="utf-8"))
        assert result.metadata.task_id == "test-task-001"
        assert data["metadata"]["parser_type"] == "rule"
        assert data["metadata"]["task_id"] == "test-task-001"
        assert data["metadata"]["output_file"] == str(out.resolve())
        assert data["metadata"]["warnings"] == ["search failed in test"]


class TestUtils:
    def test_clean_text(self):
        from course_project.backend.app.resume_search.utils import clean_text

        assert clean_text("hello  \tworld") == "hello world"
        assert clean_text("\n\n\na\n\n\nb\n\n\n") == "a\n\nb"

    def test_strip_json_markdown(self):
        from course_project.backend.app.resume_search.utils import strip_json_markdown

        raw = '```json\n{"a":1}\n```'
        assert strip_json_markdown(raw) == '{"a":1}'

    def test_is_valid_http_url(self):
        from course_project.backend.app.resume_search.utils import is_valid_http_url

        assert is_valid_http_url("https://example.com")
        assert not is_valid_http_url("ftp://example.com")
        assert not is_valid_http_url("")


class TestSchema:
    def test_resume_profile_defaults(self):
        from course_project.backend.app.resume_search.schema import ResumeProfile

        p = ResumeProfile()
        assert p.basic_info.name == ""
        assert p.skills.programming_languages == []
        assert p.education == []

    def test_job_link_model(self):
        from course_project.backend.app.resume_search.schema import JobLink

        link = JobLink(title="Test", url="https://example.com")
        assert link.title == "Test"

    def test_final_result_model_dump(self):
        from course_project.backend.app.resume_search.schema import FinalResult

        r = FinalResult()
        d = r.model_dump()
        assert "resume_profile" in d
        assert "search_queries" in d
        assert "job_links" in d
        assert "metadata" in d
