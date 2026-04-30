import unittest

from job_rag.crawler.url_utils import is_valid_url, make_job_id, normalize_url


class UrlUtilsTest(unittest.TestCase):
    def test_normalize_url_removes_fragment_and_sorts_query(self) -> None:
        url = "HTTPS://Example.COM/jobs/123/?b=2&a=1#section"
        self.assertEqual(normalize_url(url), "https://example.com/jobs/123?a=1&b=2")

    def test_is_valid_url_accepts_http_only(self) -> None:
        self.assertTrue(is_valid_url("https://example.com/job"))
        self.assertFalse(is_valid_url("local_jobs/job.html"))

    def test_make_job_id_is_stable(self) -> None:
        first = make_job_id("https://example.com/job", "AI Agent Intern", "Example")
        second = make_job_id("https://example.com/job", "AI Agent Intern", "Example")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("job_"))


if __name__ == "__main__":
    unittest.main()

