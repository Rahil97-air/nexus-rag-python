import os
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class PublicDemoTests(unittest.TestCase):
    def test_public_entrypoint_hides_uploads_owner_key_and_local_api(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {"GROQ_API_KEY": "private-owner-key-not-for-visitors"}):
            app = AppTest.from_file(str(root / "portfolio_app.py")).run(timeout=30)
            self.assertFalse(app.exception)
            self.assertFalse(list(app.get("file_uploader")))
            self.assertTrue(any(widget.label == "Groq API key" for widget in app.text_input))
            self.assertFalse(any("API check" in widget.label for widget in app.button))
            self.assertFalse(any("key is configured" in message.value for message in app.success))
            self.assertTrue(any("fictional handbook only" in message.value for message in app.info))
