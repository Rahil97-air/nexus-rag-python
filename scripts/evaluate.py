"""Measure retrieval only; never calls Groq or reads an API key."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nexus_rag.core import Index, LocalEmbeddings, read_pdf, MODEL


def main():
    cases = json.loads((ROOT / "tests/evaluation_cases.json").read_text(encoding="utf-8"))
    _, chunks, _ = read_pdf((ROOT / "samples/handbook.pdf").read_bytes(), "handbook.pdf")
    rows = []
    with TemporaryDirectory() as directory:
        index = Index(Path(directory), LocalEmbeddings(ROOT / ".cache"))
        try:
            index.add(chunks)
            for case in cases:
                hits = index.search(case["question"], chunks[0].metadata["doc_id"], k=2)
                pages = [doc.metadata["page"] for doc, _ in hits]
                expected = set(case["pages"])
                rows.append({**case, "retrieved_pages": pages,
                             "scores": [round(float(score), 4) for _, score in hits],
                             "top1_relevant": pages[0] in expected if expected else None,
                             "page_recall_at_2": len(expected.intersection(pages)) / len(expected) if expected else None,
                             "all_evidence_at_2": expected.issubset(pages) if expected else None})
        finally:
            index.close()
    answerable = [row for row in rows if row["pages"]]
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "model": MODEL,
        "corpus_chunks": len(chunks), "answerable_questions": len(answerable),
        "unanswerable_questions": len(rows) - len(answerable),
        "top1_relevant_rate": sum(r["top1_relevant"] for r in answerable) / len(answerable),
        "mean_page_recall_at_2": sum(r["page_recall_at_2"] for r in answerable) / len(answerable),
        "all_evidence_at_2_rate": sum(r["all_evidence_at_2"] for r in answerable) / len(answerable),
        "limits": "Tiny three-page synthetic corpus; development checks, not a held-out benchmark. Absent-answer questions are diagnostic only; no abstention or answer quality was measured.",
    }
    output = ROOT / "test-results/retrieval.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Detailed report: {output}")
    for row in rows:
        if not row["pages"]:
            print(f"ABSENT ANSWER (not a pass): {row['question']} -> pages {row['retrieved_pages']}, scores {row['scores']}")


if __name__ == "__main__":
    main()
