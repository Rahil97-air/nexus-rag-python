"""Offline generation-contract tests; not a test of a real LLM's accuracy."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from langchain_core.documents import Document
from nexus_rag.core import answer, generation_error_message


class GenerationTests(unittest.TestCase):
    def test_errors_do_not_disclose_raw_provider_messages(self):
        import httpx
        from groq import BadRequestError, AuthenticationError
        response = httpx.Response(400, request=httpx.Request("POST", "https://api.groq.com"))
        error = BadRequestError("PRIVATE RAW ERROR", response=response,
                                body={"error": {"code": "model_not_found"}})
        self.assertIn("unavailable", generation_error_message(error))
        self.assertNotIn("PRIVATE", generation_error_message(error))
        auth = AuthenticationError("PRIVATE KEY", response=response, body={})
        self.assertIn("rejected", generation_error_message(auth))
        self.assertNotIn("PRIVATE", generation_error_message(auth))

    def test_no_evidence_does_not_call_provider(self):
        with patch("langchain_groq.ChatGroq") as provider:
            self.assertIn("couldn't find evidence", answer("Anything?", [], "test", "fake"))
            provider.assert_not_called()

    def test_source_labels_and_grounding_in_prompt(self):
        doc = Document(page_content="Submit claims within 30 days.",
                       metadata={"source": "handbook.pdf", "page": 1})
        with patch("langchain_groq.ChatGroq") as provider:
            provider.return_value.invoke.return_value = SimpleNamespace(content="Within 30 days. [S1]")
            result = answer("What is the deadline?", [(doc, 0.8)], "test", "fake")
            messages = provider.return_value.invoke.call_args.args[0]
            self.assertIn("untrusted data", messages[0].content)
            self.assertIn("evidence is insufficient", messages[0].content)
            self.assertIn("[S1] handbook.pdf, page 1", messages[1].content)
            self.assertIn(doc.page_content, messages[1].content)
            self.assertEqual(result, "Within 30 days. [S1]")

    def test_provider_failure_is_not_fabricated_as_an_answer(self):
        doc = Document(page_content="Evidence", metadata={"source": "sample.pdf", "page": 1})
        with patch("langchain_groq.ChatGroq") as provider:
            provider.return_value.invoke.side_effect = RuntimeError("test outage")
            with self.assertRaises(RuntimeError):
                answer("Question", [(doc, 0.5)], "test", "fake")
