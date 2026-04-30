import unittest
from unittest.mock import patch

from job_rag.crawler.browser_use_adapter import BrowserUseUnavailable
from job_rag.crawler.browser_use_runner import crawl_page


class BrowserUseRunnerTest(unittest.IsolatedAsyncioTestCase):
    async def test_browser_use_failure_falls_back_to_http_fetch(self) -> None:
        html = """
        <html>
          <head><title>Demo Job</title></head>
          <body><main><h1>AI Agent Intern</h1><p>Python RAG LLM</p></main></body>
        </html>
        """
        with patch("job_rag.crawler.browser_use_runner.should_try_browser_use", return_value=True), patch(
            "job_rag.crawler.browser_use_runner.crawl_with_browser_use",
            side_effect=BrowserUseUnavailable("browser denied"),
        ), patch("job_rag.crawler.browser_use_runner._fetch_http_html", return_value=html):
            page = await crawl_page("https://example.com/job")

        self.assertEqual(page.status, "success")
        self.assertIn("AI Agent Intern", page.visible_text or "")


if __name__ == "__main__":
    unittest.main()
