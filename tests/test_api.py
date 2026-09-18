import json
import os
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from nexus_rag.api import create_app
from nexus_rag.api_client import parse_sse
from nexus_rag.core import Index
from test_core import FakeEmbeddings, pdf_bytes


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"NEXUS_API_TOKEN": "", "GROQ_API_KEY": ""})
        self.env.start()
        self.app = create_app(self.tmp.name,
                             index_factory=lambda root: Index(root, FakeEmbeddings()),
                             answer_stream=lambda *args: iter(["Thirty days ", "[S1]"]))
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()
        self.tmp.cleanup()

    def upload(self):
        return self.client.post("/documents", files={"file": ("sample.pdf", pdf_bytes(["Expense claims due within 30 days."]), "application/pdf")})

    def test_upload_search_and_catalog(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        doc = response.json()
        result = self.client.post("/search", json={"doc_id": doc["doc_id"], "question": "expense"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["sources"][0]["page"], 1)
        self.assertEqual(len(self.client.get("/documents").json()["documents"]), 1)

    def test_unknown_document_and_invalid_pdf(self):
        self.assertEqual(self.client.post("/search", json={"doc_id": "a"*64, "question": "q"}).status_code, 404)
        self.assertEqual(self.client.post("/documents", files={"file": ("bad.pdf", b"bad")}).status_code, 400)

    def test_no_consent_no_provider_call(self):
        doc = self.upload().json()
        payload = {"doc_id": doc["doc_id"], "question": "q", "groq_api_key": "fake"}
        self.assertEqual(self.client.post("/ask/stream", json=payload).status_code, 400)
        payload["mode"] = "advanced"
        self.assertEqual(self.client.post("/search", json=payload).status_code, 400)

    def test_sse_event_order_and_completion(self):
        doc = self.upload().json()
        response = self.client.post("/ask/stream", json={"doc_id": doc["doc_id"], "question": "expense",
                                                        "consent": True, "groq_api_key": "fake"})
        events = list(parse_sse(response.text.splitlines()))
        self.assertEqual([e for e, _ in events], ["status", "evidence", "token", "token", "done"])
        self.assertEqual(events[-1][1]["answer"], "Thirty days [S1]")
        self.assertEqual(events[-1][1]["citations"]["invalid_ids"], [])

    def test_validation_does_not_echo_secrets(self):
        response = self.client.post("/search", json={"question": "q", "doc_id": "bad", "groq_api_key": "PRIVATE-SECRET"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("PRIVATE-SECRET", response.text)

    def test_oversized_body_is_rejected(self):
        response = self.client.post("/documents", content=b"x" * (16 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)

    def test_identical_upload_is_idempotent(self):
        data = pdf_bytes(["Expense claim within 30 days."])
        first = self.client.post("/documents", files={"file": ("same.pdf", data)})
        again = self.client.post("/documents", files={"file": ("same.pdf", data)})
        self.assertEqual(first.json()["doc_id"], again.json()["doc_id"])
        self.assertTrue(again.json()["already_indexed"])
        self.assertEqual(len(self.client.get("/documents").json()["documents"]), 1)

    def test_cross_origin_blocked_and_auth_supported(self):
        self.assertEqual(self.client.get("/health", headers={"Origin": "https://evil.example"}).status_code, 403)
        with patch.dict(os.environ, {"NEXUS_API_TOKEN": "local-test-token"}):
            self.assertEqual(self.client.get("/health").status_code, 401)
            self.assertEqual(self.client.get("/health", headers={"Authorization": "Bearer local-test-token"}).status_code, 200)

    def test_partial_stream_failure_is_error_not_done(self):
        self.client.__exit__(None, None, None)
        def broken(*args):
            yield "partial"
            raise RuntimeError("private provider message")
        self.app = create_app(self.tmp.name, index_factory=lambda root: Index(root, FakeEmbeddings()), answer_stream=broken)
        self.client = TestClient(self.app)
        self.client.__enter__()
        doc = self.upload().json()
        response = self.client.post("/ask/stream", json={"doc_id": doc["doc_id"], "question": "q", "consent": True, "groq_api_key": "fake"})
        events = list(parse_sse(response.text.splitlines()))
        self.assertEqual(events[-1][0], "error")
        self.assertNotIn("done", [e for e, _ in events])
        self.assertNotIn("private provider", response.text)
