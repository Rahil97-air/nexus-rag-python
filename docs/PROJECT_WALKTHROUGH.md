# Understand your finished local project

## Explain it in one sentence

“I built a Python document-question-answering application that retrieves relevant passages from PDFs and asks an LLM to answer using those passages, with page-level source references.”

The model is not trained on the uploaded PDF. The PDF is processed into searchable evidence. At question time, selected evidence is included in the prompt.

## What happens when you index a PDF?

1. **Read pages:** pypdf extracts text. Every page keeps its physical PDF page number; a printed page label may differ.
2. **Split text:** each page is split into chunks of at most 600 characters. Up to 100 characters overlap to preserve some context near boundaries. Different pages are not joined.
3. **Assign IDs:** a hash identifies the document bytes. A stable UUID identifies each chunk, allowing identical uploads to reuse the same entries.
4. **Embed locally:** a pretrained BGE-small model turns each chunk into a vector. This is inference, not training. A token guard prevents silent truncation of overly long input.
5. **Store:** Qdrant stores vectors alongside the text, filename, page and IDs. Those labels are metadata.

## Three retrieval modes

**Baseline:** embed the question and retrieve the most similar chunks. It is fast, local, inexpensive and a useful comparison point.

**MMR:** retrieve a larger candidate pool, then favour a balance between relevance to the question and diversity from already selected chunks. This can reduce redundant evidence. It can also remove useful overlapping passages, so it must be evaluated—not assumed to improve accuracy.

**Multi-stage:** first ask Groq to produce up to two alternative queries. For a two-part question, the alternatives can focus on the separate parts. Search every query, merge results by chunk ID, apply MMR, then ask Groq to reorder the candidates by usefulness for answering the original question. Select the final top-k passages.

Deduplication and MMR solve different problems: deduplication removes the *same chunk* returned by multiple queries; MMR reduces redundancy between *different chunks*.

The reranker never creates new evidence. It returns candidate IDs only. Its output is checked for missing, duplicate and invented IDs. If rewriting or reranking fails, the trace explicitly reports a fallback.

## How is the answer generated?

The prompt contains instructions, the original question and the final evidence passages with labels such as [S1]. Groq writes the answer, and the UI displays text as it arrives. This is streaming; it improves perceived responsiveness, not the underlying model's factual accuracy.

The model is instructed to acknowledge missing information. A similarity score cannot establish that a document contains the answer: even an unrelated question has nearest neighbours.

The citation audit checks whether referenced labels exist. It does **not** check whether a sentence truly follows from its cited passage. Factual grounding still needs evaluation and manual inspection.

## What does the API add?

The Streamlit interface is for a person. The FastAPI service exposes the same pipeline to programs:

- Upload a document and receive its document ID.
- Search it and receive structured passages/metadata.
- Request a streamed answer and receive structured events.

SSE stands for Server-Sent Events. Our event types are `status`, `evidence`, `token`, `done` and `error`. A client must not treat partial tokens as a completed answer if the stream ends with an error.

For a simple local setup, the UI and API use separate embedded-Qdrant directories. This prevents two processes from locking the same database file. A deployed architecture would typically use a separate Qdrant server plus authentication and per-user document access controls.

## What did testing actually show?

Read `VERIFICATION.md` for current counts and live observations. The larger synthetic fixture contains eight pages, 16 chunks and 24 answerable questions, plus three absent-answer questions. With three retrieved passages, baseline covered all required evidence for 22 answerable questions and MMR for 21. Those findings are useful debugging evidence, not general accuracy statistics.

Unit tests cover deterministic behavior with fake vectors/providers. Real embedding tests check local retrieval. Live tests check actual Groq integration. These are different levels of evidence; passing one does not imply the others passed.

## Decisions you should be able to defend

- **Why Python?** It matches your learning background and allows a clear implementation with LangChain, FastAPI and local embedding libraries.
- **Why local embeddings?** PDF chunks can be embedded without sending them to the generation provider; the model runs on this computer after download.
- **Why page metadata?** Users can locate the original evidence instead of receiving an untraceable answer.
- **Why retain a baseline?** Advanced stages add latency, cost and failure modes. Measurement should justify their use.
- **Why explicit fallbacks?** A provider failure should not masquerade as a successful reranking stage.
- **Why no accuracy percentage in the resume?** The synthetic development data is small and not a held-out, representative test set.

## Five-minute demo script

1. Index the fictional handbook and show one chunk with its page metadata.
2. Ask the remote-work and learning-approval question in Multi-stage mode.
3. Show the rewritten queries, deduplication count and completed stage statuses.
4. Generate the streamed answer; point to each cited passage.
5. Ask about paid holiday entitlement and check that the answer acknowledges missing information.
6. Show the API docs and automated tests. Explain the local-only security and evaluation limits honestly.

Your resume should say **LangChain (Python)**, not **LangChain.js**, for this implementation. The original resume file has not been edited.
