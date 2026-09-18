"""Real embedding smoke test. First run downloads the public model."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nexus_rag.core import Index, LocalEmbeddings, read_pdf

_, chunks, _ = read_pdf((ROOT / "samples/handbook.pdf").read_bytes(), "handbook.pdf")
cases = [
    ("What is the deadline for reimbursement?", 1),
    ("How often can I do my job from home?", 2),
    ("How much can I spend on professional development each year?", 3),
]
with TemporaryDirectory() as directory:
    index = Index(Path(directory), LocalEmbeddings(ROOT / ".cache"))
    try:
        index.add(chunks)
        for question, expected_page in cases:
            results = index.search(question, chunks[0].metadata["doc_id"], k=1)
            page = results[0][0].metadata["page"]
            print(f"{'PASS' if page == expected_page else 'FAIL'} page {page}: {question}")
            assert page == expected_page
    finally:
        index.close()
