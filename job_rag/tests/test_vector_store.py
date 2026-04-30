import importlib.util
import tempfile
import unittest
from pathlib import Path

from job_rag.config import PROJECT_ROOT
from job_rag.indexing.embedder import OpenAICompatibleEmbeddingProvider, get_embedding_provider
from job_rag.indexing.vector_store import ChromaVectorStoreBackend, get_vector_store_backend, index_jobs, search_jobs
from job_rag.schemas import JobPosting


def workspace_tempdir() -> tempfile.TemporaryDirectory:
    root = PROJECT_ROOT / ".job_rag_test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=root, ignore_cleanup_errors=True)


class VectorStoreTest(unittest.TestCase):
    def test_embedding_and_vector_backend_interfaces_default_to_local(self) -> None:
        provider = get_embedding_provider()
        backend = get_vector_store_backend()
        self.assertEqual(provider.name, "local")
        self.assertEqual(backend.name, "local")
        self.assertTrue(provider.embed_query("Python RAG"))

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
        with workspace_tempdir() as temp_dir:
            path = Path(temp_dir) / "index.json"
            index_jobs(jobs, index_path=path)
            results = search_jobs("Python RAG LLM", top_k=1, index_path=path)
        self.assertEqual(results[0]["job_id"], "job_ai")
        self.assertGreater(results[0]["score"], 0)
        self.assertEqual(results[0]["backend"], "local")
        self.assertEqual(results[0]["embedding_provider"], "local")

    def test_openai_compatible_provider_falls_back_without_local_credentials(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider(api_key="", base_url="", model="")
        embedding = provider.embed_query("Python RAG")
        self.assertTrue(embedding)

    @unittest.skipIf(importlib.util.find_spec("chromadb") is None, "chromadb is not installed")
    def test_chroma_backend_indexes_and_searches_jobs(self) -> None:
        jobs = [
            JobPosting(
                job_id="job_rag",
                url="local",
                title="RAG Engineer",
                company="Example",
                skills=["Python", "RAG", "Vector DB"],
                requirements=["Build vector retrieval systems."],
            ),
            JobPosting(
                job_id="job_ui",
                url="local2",
                title="UI Engineer",
                company="Example",
                skills=["React", "CSS"],
                requirements=["Build frontend pages."],
            ),
        ]
        with workspace_tempdir() as temp_dir:
            backend = ChromaVectorStoreBackend(persist_dir=temp_dir, collection_name="test_jobs")
            index_path = backend.index_jobs(jobs)
            results = backend.search_jobs("Python RAG vector database", top_k=1, index_path=index_path)
        self.assertEqual(results[0]["job_id"], "job_rag")
        self.assertEqual(results[0]["backend"], "chroma")
        self.assertGreaterEqual(results[0]["score"], 0)


if __name__ == "__main__":
    unittest.main()
