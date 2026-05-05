import asyncio
import unittest

from job_rag.crawler.browser_use_runner import crawl_page
from job_rag.extraction.job_extractor import extract_job_posting
from job_rag.extraction.llm_extractor import normalize_llm_job_fields, normalize_openai_compatible_base_url, parse_llm_json
from job_rag.schemas import PageContent


class ExtractorTest(unittest.TestCase):
    def test_extract_local_job_html(self) -> None:
        page = asyncio.run(crawl_page("local_jobs/ai_agent_intern.html"))
        job = extract_job_posting(page)
        self.assertTrue(job.is_valid)
        self.assertEqual(job.company, "Example AI Lab")
        self.assertEqual(job.city, "Beijing")
        self.assertIn("Python", job.skills)
        self.assertTrue(job.responsibilities)
        self.assertTrue(job.requirements)

    def test_failed_page_becomes_invalid_job(self) -> None:
        page = asyncio.run(crawl_page(""))
        job = extract_job_posting(page)
        self.assertFalse(job.is_valid)
        self.assertIn("empty url", job.validation_errors)

    def test_llm_fallback_extracts_non_standard_recruiting_post(self) -> None:
        page = PageContent(
            url="https://www.v2ex.com/t/demo",
            status="success",
            title="[外资社招] 上海 - AI-native 团队招 iOS / Backend 工程师",
            visible_text=(
                "我们是一家做 AI-native 产品的公司，现在正在上海组建 0→1 工程团队，"
                "优先找 iOS Native 和 Backend / Full-stack 工程师。"
                "工程问题包括端到端语音延迟优化和多模型编排：OpenAI / Anthropic / Gemini / DeepSeek / Qwen。"
            ),
        )

        def fake_llm_extractor(_: str) -> dict:
            return {
                "title": "iOS Native / Backend / Full-stack 工程师",
                "company": "AI-native 产品公司",
                "location": "上海",
                "salary": None,
                "experience_required": None,
                "education_required": None,
                "job_type": "社招",
                "responsibilities": ["端到端语音延迟优化", "多模型编排"],
                "requirements": ["适合喜欢 0→1 的工程师"],
                "skills": ["iOS Native", "Backend", "Full-stack", "OpenAI", "Anthropic", "Gemini", "DeepSeek", "Qwen"],
            }

        job = extract_job_posting(page, llm_extractor=fake_llm_extractor)
        self.assertTrue(job.is_valid)
        self.assertEqual(job.company, "AI-native 产品公司")
        self.assertEqual(job.city, "上海")
        self.assertIn("OpenAI", job.skills)
        self.assertTrue(job.responsibilities)
        self.assertGreaterEqual(job.extraction_confidence, 0.7)

    def test_parse_llm_json_normalizes_markdown_response(self) -> None:
        parsed = parse_llm_json(
            """```json
            {
              "title": "Backend Engineer",
              "company": "Example",
              "location": "Shanghai",
              "salary": null,
              "responsibilities": ["Build APIs"],
              "requirements": "Python; FastAPI",
              "skills": ["Python", "FastAPI"]
            }
            ```"""
        )
        self.assertEqual(parsed["title"], "Backend Engineer")
        self.assertEqual(parsed["requirements"], ["Python", "FastAPI"])

    def test_normalize_llm_job_fields_keeps_missing_fields_empty(self) -> None:
        parsed = normalize_llm_job_fields({"title": "Data Scientist", "skills": "Python\nSQL"})
        self.assertEqual(parsed["title"], "Data Scientist")
        self.assertIsNone(parsed["company"])
        self.assertEqual(parsed["skills"], ["Python", "SQL"])

    def test_normalize_openai_compatible_base_url(self) -> None:
        self.assertEqual(normalize_openai_compatible_base_url("https://example.com"), "https://example.com/v1")
        self.assertEqual(normalize_openai_compatible_base_url("https://example.com/v1"), "https://example.com/v1")


if __name__ == "__main__":
    unittest.main()
