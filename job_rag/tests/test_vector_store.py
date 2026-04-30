import tempfile
import unittest
from pathlib import Path

from job_rag.indexing.vector_store import index_jobs, search_jobs
from job_rag.schemas import JobPosting


class VectorStoreTest(unittest.TestCase):
    def test_index_and_search_jobs(self) -> None:
        jobs = [
            JobPosting(
                job_id="job_ai",
                url="local",
                title="AI Agent Intern",
                company="Example",
                skills=["Python", "RAG", "LLM"],
                requirements=["Build RAG applications."],
            ),
            JobPosting(
                job_id="job_fe",
                url="local2",
                title="Frontend Engineer",
                company="Example",
                skills=["React", "TypeScript"],
                requirements=["Build UI."],
            ),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "index.json"
            index_jobs(jobs, index_path=path)
            results = search_jobs("Python RAG LLM", top_k=1, index_path=path)
        self.assertEqual(results[0]["job_id"], "job_ai")
        self.assertGreater(results[0]["score"], 0)


if __name__ == "__main__":
    unittest.main()

