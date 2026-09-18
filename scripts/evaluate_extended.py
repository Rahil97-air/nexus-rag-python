"""Deterministic local baseline vs MMR evaluation; never calls Groq."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nexus_rag.benchmark import benchmark_pdf, CASES
from nexus_rag.core import Index, LocalEmbeddings, read_pdf
from nexus_rag.pipeline import retrieve


def evidence_recall(hits, targets):
    found = sum(any(doc.metadata["page"] == page and phrase.casefold() in " ".join(doc.page_content.split()).casefold()
                    for doc, _ in hits) for page, phrase in targets)
    return found / len(targets) if targets else None


def main():
    pages, chunks, _ = read_pdf(benchmark_pdf(), "extended-handbook.pdf")
    report = {"pages": len(pages), "chunks": len(chunks), "k": 3,
              "limits": "Synthetic development fixture, not held-out accuracy. Absent-answer cases are diagnostic, not scored as successes.", "modes": {}}
    with TemporaryDirectory() as directory:
        index = Index(Path(directory), LocalEmbeddings(ROOT / ".cache"))
        try:
            index.add(chunks)
            for mode in ("baseline", "mmr"):
                rows = []
                for question, targets in CASES:
                    result = retrieve(index, question, chunks[0].metadata["doc_id"], mode=mode, k=3)
                    recall = evidence_recall(result.hits, targets)
                    rows.append({"question": question, "expected": targets, "evidence_recall": recall,
                                 "retrieved_pages": [d.metadata["page"] for d, _ in result.hits]})
                recalls = [r["evidence_recall"] for r in rows if r["evidence_recall"] is not None]
                report["modes"][mode] = {"mean_evidence_recall_at_3": sum(recalls) / len(recalls),
                                         "complete_evidence_questions": sum(r == 1 for r in recalls),
                                         "answerable_questions": len(recalls), "cases": rows}
        finally:
            index.close()
    destination = ROOT / "test-results/extended-retrieval.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({**report, "modes": {m: {k: v for k, v in r.items() if k != "cases"} for m, r in report["modes"].items()}}, indent=2))
    print(destination)


if __name__ == "__main__":
    main()
