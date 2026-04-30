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
            "projects": [
                {
                    "name": "Resume RAG System",
                    "description": "A RAG based resume and job matching project.",
                    "tech_stack": ["Python", "RAG"],
                }
            ],
            "target_roles": ["AI Agent Engineer"],
            "target_cities": ["Beijing"],
            "salary_expectation": "Negotiable",
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
        self.assertIn("score_detail", result.to_dict())
        self.assertIn("semantic_similarity", result.score_detail)
        self.assertIn("project_relevance", result.score_detail)
        self.assertIn("city_match", result.score_detail)
        self.assertIn("education_or_experience_match", result.score_detail)
        self.assertIn("job_type_or_salary_match", result.score_detail)
        self.assertTrue(any("Docker" in reason for reason in result.mismatch_reasons))
        self.assertFalse(any("Docker" in reason and "匹配" in reason for reason in result.match_reasons))


if __name__ == "__main__":
    unittest.main()
