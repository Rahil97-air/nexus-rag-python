import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from langchain_core.embeddings import Embeddings
from nexus_rag.core import read_pdf, Index, COLLECTION


def pdf_bytes(texts):
    output = BytesIO()
    canvas = Canvas(output)
    for text in texts:
        canvas.drawString(50, 700, text)
        canvas.showPage()
    canvas.save()
    return output.getvalue()


class FakeEmbeddings(Embeddings):
    """Deterministic test fixture, NOT a semantic model."""
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        return [float("expense" in text.lower()), float("remote" in text.lower()), 0.1]


class CoreTests(unittest.TestCase):
    def test_pages_and_stable_ids(self):
        data = pdf_bytes(["Expense claims due within 30 days.", "", "Remote work needs approval."])
        pages, chunks, skipped = read_pdf(data, "policies.pdf")
        self.assertEqual([p.metadata["page"] for p in pages], [1, 3])
        self.assertEqual(skipped, [2])
        self.assertEqual([c.metadata["chunk_id"] for c in chunks],
                         [c.metadata["chunk_id"] for c in read_pdf(data, "renamed.pdf")[1]])
        self.assertTrue(all(len(c.page_content) <= 600 for c in chunks))

    def test_invalid_and_empty_pdf(self):
        for data in (b"not a PDF", pdf_bytes([""])):
            with self.assertRaises(ValueError):
                read_pdf(data, "bad.pdf")

    def test_index_dedup_filter_and_persistence(self):
        a = read_pdf(pdf_bytes(["Expense claims due within 30 days."]), "a.pdf")[1]
        b = read_pdf(pdf_bytes(["Remote work needs approval."]), "b.pdf")[1]
        with tempfile.TemporaryDirectory() as directory:
            index = Index(Path(directory), FakeEmbeddings())
            try:
                index.add(a)
                index.add(a)
                index.add(b)
                self.assertEqual(index.client.count(COLLECTION, exact=True).count, 2)
                hits = index.search("expense", b[0].metadata["doc_id"])
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0][0].metadata["source"], "b.pdf")
                with self.assertRaises(ValueError):
                    index.search(" ", a[0].metadata["doc_id"])
            finally:
                index.close()
            reopened = Index(Path(directory), FakeEmbeddings())
            try:
                self.assertEqual(len(reopened.search("expense", a[0].metadata["doc_id"])), 1)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
