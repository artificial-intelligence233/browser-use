import unittest

from job_rag.extraction.normalizer import deduplicate_jobs, normalize_salary, normalize_skills
from job_rag.schemas import JobPosting


class NormalizerTest(unittest.TestCase):
    def test_normalize_salary_parses_day_range(self) -> None:
        result = normalize_salary("200-300/day")
        self.assertEqual(result["salary_min"], 200)
        self.assertEqual(result["salary_max"], 300)
        self.assertEqual(result["salary_unit"], "day")

    def test_normalize_skills_deduplicates_aliases(self) -> None:
        result = normalize_skills(["python", "Python", "browser-use", "Browser Use"])
        self.assertEqual(result, ["Python", "Browser Use"])

    def test_deduplicate_jobs_by_url(self) -> None:
        first = JobPosting(job_id="job_1", url="https://example.com/job", title="A", company="C")
        second = JobPosting(job_id="job_2", url="https://example.com/job#top", title="A", company="C")
        self.assertEqual(len(deduplicate_jobs([first, second])), 1)


if __name__ == "__main__":
    unittest.main()

