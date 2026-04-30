import unittest

from job_rag.matching.scorer import compute_skill_match, score_job_match
from job_rag.schemas import JobPosting


class MatcherTest(unittest.TestCase):
    def test_skill_match(self) -> None:
        result = compute_skill_match(["Python", "RAG"], ["Python", "RAG", "Docker"])
        self.assertEqual(result["matched_skills"], ["Python", "RAG"])
        self.assertEqual(result["missing_skills"], ["Docker"])

    def test_score_job_match_range_and_reasons(self) -> None:
        resume = {
            "skills": ["Python", "RAG"],
            "target_roles": ["AI Agent Engineer"],
            "target_cities": ["Beijing"],
        }
        job = JobPosting(
            job_id="job_1",
            url="local",
            title="AI Agent Engineer",
            company="Example",
            city="Beijing",
            skills=["Python", "RAG", "Docker"],
            responsibilities=["Build RAG workflows."],
        )
        result = score_job_match(resume, job, retrieval_score=0.8)
        self.assertGreaterEqual(result.match_score, 0)
        self.assertLessEqual(result.match_score, 100)
        self.assertTrue(result.match_reasons)
        self.assertTrue(result.mismatch_reasons)


if __name__ == "__main__":
    unittest.main()
