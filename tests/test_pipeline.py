import unittest
from types import SimpleNamespace
from unittest.mock import patch
from langchain_core.documents import Document
from langchain_core.messages import AIMessageChunk
from nexus_rag.pipeline import (deduplicate, mmr_select, retrieve, GroqStages,
                                citation_audit, stream_answer)


def hit(text, ident, score=0.8):
    return (Document(page_content=text, metadata={"chunk_id": ident, "source": "test.pdf", "page": 1}), score)


class Vectors:
    def embed_query(self, text):
        return [1.0, 0.0]

    def embed_documents(self, texts):
        return [[0.0, 1.0] if text == "different" else [1.0, 0.0] for text in texts]


class Stages:
    def reformulate(self, question):
        return ["other phrasing", "other phrasing"]

    def rerank(self, question, hits):
        return list(reversed(hits))


class PipelineTests(unittest.TestCase):
    def test_dedup_keeps_best_score_and_distinct_ids(self):
        results = deduplicate([hit("same", "a", .4), hit("same", "a", .9), hit("same", "b", .8)])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][1], .9)

    def test_mmr_diversifies_redundant_results(self):
        results = mmr_select("query", [hit("same", "a"), hit("same", "b"), hit("different", "c")],
                             Vectors(), 2, relevance_weight=.3)
        self.assertEqual([h[0].metadata["chunk_id"] for h in results], ["a", "c"])

    def test_advanced_stages_and_query_dedup(self):
        calls = []
        def search(q, doc_id, k):
            calls.append((q, doc_id))
            return [hit("same", "a"), hit("different", "b")]
        index = SimpleNamespace(search=search, embeddings=Vectors())
        result = retrieve(index, "question", "chosen-doc", mode="advanced", k=2, stages=Stages())
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call[1] == "chosen-doc" for call in calls))
        self.assertEqual(result.trace["duplicates_removed"], 2)
        self.assertEqual(result.trace["stages"]["rerank"], "completed")
        self.assertEqual(result.hits[0][0].metadata["chunk_id"], "b")

    def test_provider_failures_are_explicit_fallbacks(self):
        class Broken:
            def reformulate(self, q):
                raise RuntimeError("private")
            def rerank(self, q, h):
                raise RuntimeError("private")
        index = SimpleNamespace(search=lambda *a, **kw: [hit("same", "a")], embeddings=Vectors())
        result = retrieve(index, "question", "doc", mode="advanced", stages=Broken())
        self.assertEqual(len(result.trace["warnings"]), 2)
        self.assertNotIn("private", str(result.trace))
        self.assertEqual(result.trace["stages"]["rerank"], "fallback")

    def test_invalid_rerank_ids_are_rejected(self):
        with patch.object(GroqStages, "_json", return_value={"ids": [1, 1]}):
            stage = GroqStages("fake-key")
            with self.assertRaises(ValueError):
                stage.rerank("q", [hit("same", "a"), hit("different", "b")])

    def test_id_audit_does_not_claim_factual_verification(self):
        audit = citation_audit("A claim [S1] and another [S99]", [hit("same", "a")])
        self.assertEqual(audit["invalid_ids"], ["S99"])
        self.assertIn("not factual", audit["note"])
        self.assertEqual(citation_audit("Citation 【S1】", [hit("same", "a")])["cited_ids"], ["S1"])
        self.assertEqual(citation_audit("Citation [S01]", [hit("same", "a")])["invalid_ids"], ["S01"])

    def test_stream_preserves_chunks_and_evidence(self):
        class LLM:
            def stream(self, messages):
                self.messages = messages
                yield AIMessageChunk(content="Answer ")
                yield AIMessageChunk(content="[S1]")
        llm = LLM()
        self.assertEqual(list(stream_answer("q", [hit("same", "a")], "fake", llm=llm)), ["Answer ", "[S1]"])
        self.assertIn("[S1] test.pdf, PDF page 1", llm.messages[1].content)

    def test_local_modes_do_not_need_key(self):
        index = SimpleNamespace(search=lambda *a, **kw: [hit("same", "a")], embeddings=Vectors())
        for mode in ("baseline", "mmr"):
            self.assertTrue(retrieve(index, "q", "doc", mode=mode).hits)
        with self.assertRaises(ValueError):
            retrieve(index, "q", "doc", mode="advanced")
