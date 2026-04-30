import unittest
from unittest.mock import patch

from job_rag.crawler.browser_use_adapter import BrowserUseUnavailable, crawl_with_browser_use


class BrowserUseAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def test_crawl_with_browser_use_requires_opt_in(self) -> None:
        with patch("job_rag.crawler.browser_use_adapter.BROWSER_USE_ENABLED", False):
            with self.assertRaises(BrowserUseUnavailable):
                await crawl_with_browser_use("https://example.com/job")


if __name__ == "__main__":
    unittest.main()
