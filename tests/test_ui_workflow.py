import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from nexus_rag.core import Index
from test_core import FakeEmbeddings


class UIWorkflowTests(unittest.TestCase):
    def test_index_search_mmr_and_stale_result_hiding(self):
        root = Path(__file__).resolve().parents[1]
        owners = []
        with tempfile.TemporaryDirectory() as directory:
            def isolated_index(_):
                owner = Index(Path(directory), FakeEmbeddings())
                owners.append(owner)
                return owner
            st.cache_resource.clear()
            try:
                with patch("nexus_rag.core.Index", side_effect=isolated_index):
                    app = AppTest.from_file(str(root / "app.py")).run(timeout=30)
                    next(b for b in app.button if b.label == "Index this document").click().run(timeout=30)
                    self.assertFalse(app.exception)
                    next(b for b in app.button if b.label == "Search locally").click().run(timeout=30)
                    self.assertTrue(any("[S1]" in panel.label for panel in app.expander))
                    app.radio[0].set_value("MMR (local)").run(timeout=30)
                    self.assertFalse(any("[S1]" in panel.label for panel in app.expander))
                    next(b for b in app.button if b.label == "Search locally").click().run(timeout=30)
                    self.assertFalse(app.exception)
                    self.assertTrue(any("[S1]" in panel.label for panel in app.expander))
            finally:
                st.cache_resource.clear()
                for owner in owners:
                    owner.close()
