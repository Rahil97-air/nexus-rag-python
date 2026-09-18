"""Checks session-only setup without a real key or provider requests."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from streamlit.proto.TextInput_pb2 import TextInput


class SetupTests(unittest.TestCase):
    def test_masked_session_setup_without_file_or_api(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}), patch("langchain_groq.ChatGroq") as provider:
            app = AppTest.from_file(str(root / "app.py")).run(timeout=30)
            self.assertFalse(app.exception)
            field = next(widget for widget in app.text_input if widget.label == "Groq API key")
            self.assertEqual(field.proto.type, TextInput.PASSWORD)
            field.set_value("fake-test-value-not-a-real-key").run(timeout=30)
            self.assertFalse(app.exception)
            self.assertTrue(any("not yet verified" in item.value for item in app.caption))
            provider.assert_not_called()
