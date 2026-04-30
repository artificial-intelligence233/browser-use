import asyncio
import unittest

from job_rag.crawler.browser_use_runner import crawl_page
from job_rag.extraction.job_extractor import extract_job_posting


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


if __name__ == "__main__":
    unittest.main()

