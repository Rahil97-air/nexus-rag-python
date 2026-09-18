"""UI interaction smoke test. Stop the running app before this check."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=60)
assert not app.exception, list(app.exception)
app.button[0].click().run(timeout=60)
assert not app.exception, list(app.exception)
assert app.session_state["indexed"]
app.button[1].click().run(timeout=60)
assert not app.exception, list(app.exception)
assert any("[S1]" in panel.label and "page 1" in panel.label for panel in app.expander)
print("PASS: initial render, sample indexing, search and source/page display")
