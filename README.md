# Nexus RAG — Multi-stage PDF Q&A

A from-scratch **Python / LangChain / Qdrant / Groq / FastAPI / Streamlit** project. Upload a text-based PDF locally, inspect chunks, compare retrieval methods, and stream an answer with source/page references. A sample-only portfolio demo is deployed online; this is not a production-certified service.

## Start on this computer

**[Open the live demo](https://rahil97-nexus-rag.streamlit.app/)** · [Public source](https://github.com/Rahil97-air/nexus-rag-python). The sample-only cloud entrypoint is `portfolio_app.py`; see [deployment and privacy boundaries](docs/DEPLOYMENT.md). Index the fictional handbook, then search without a key. Advanced retrieval and answers require your own Groq key and consent.

Double-click **Start Nexus.cmd** in this folder, or run:

```powershell
.\.venv\Scripts\python.exe scripts/run_local.py
```

App: http://127.0.0.1:8501 — API docs: http://127.0.0.1:8000/docs.

Keep the launcher window open. Ctrl+C stops only processes it started. If a port is already occupied, it leaves that process untouched rather than killing it.

## Full demo

1. Paste your Groq key into the masked sidebar field if needed—not into chat. The application does not save this session-only key to disk.
2. Select the fictional handbook and click **Index this document**.
3. Ask **Who approves remote work and who approves a learning purchase?**
4. Choose **Multi-stage (Groq)**, tick its consent box and run retrieval.
5. Inspect the trace: original question, rewritten queries, raw/unique hits, MMR and reranking status. Failed stages are explicitly labelled as fallbacks.
6. Tick the answer consent box and click **Generate answer**. The answer streams into the page. Check its [S1]/[S2] citations against the displayed passages.
7. Ask **How many paid holiday days do employees receive?** The sample does not contain that answer; the response should say information is missing.

Baseline and MMR search run locally without an API key. Advanced retrieval sends your question and candidate passages to Groq; generation sends your question and final passages. Use fictional content first. Provider limits and billing apply; the app does not change your account or billing settings.

## Implemented features

Preparation: **PDF → page-aware chunks → local embeddings → Qdrant**.

Advanced question path: **original + up to two LLM rewrites → vector search → deduplication → MMR → LLM reranking → grounded streamed answer**.

| Feature | Implementation |
| --- | --- |
| PDF ingestion | pypdf, one-based physical page metadata; 15 MB / 150-page limits; invalid/encrypted/scanned-only rejection |
| Chunking | Recursive splitting within each page: 600 characters, up to 100 overlap |
| Local embeddings | BGE-small via FastEmbed ONNX, cached public model, token-budget guard |
| Vector database | Persistent local Qdrant; cosine similarity; document filtering; stable chunk IDs |
| Reformulation | LangChain prompt/model/JSON parser, up to two intent-preserving query variants |
| Deduplication | Merge identical chunk IDs across queries, retain highest retrieved similarity |
| MMR | Greedy relevance-minus-redundancy selection, default relevance lambda 0.7 |
| LLM reranking | Validated candidate-ID permutation; explicit fallback if the response is invalid |
| Answers | Evidence-only instructions, token streaming, source labels and citation-ID audit |
| REST/SSE | Upload, document catalog, search, streamed answer, health and OpenAPI docs |

Default model: `openai/gpt-oss-20b`, **hosted by Groq**. It needs a Groq key, not an OpenAI key. The original Llama model was unavailable to the tested account; the replacement worked in live calls. Availability can change.

## Fresh setup

Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/create_sample.py
.\.venv\Scripts\python.exe scripts/run_local.py
```

The first embedding use downloads the public model; embeddings then run locally. For optional persistent key configuration, copy `.env.example` to `.env` and edit it locally. Never commit credentials. The sidebar method requires no file editing.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_retrieval.py
.\.venv\Scripts\python.exe scripts/evaluate.py
.\.venv\Scripts\python.exe scripts/evaluate_extended.py
```

All **27 automated tests passed**. Unit tests use fake providers/vectors where appropriate. The local live UI and REST/SSE multi-stage smoke tests also passed. Hosted indexing, baseline and MMR retrieval passed; hosted Groq generation has not been tested. Retrieval scripts use the real embedding model, without Groq. The extended synthetic fixture has eight pages and 16 chunks. At k=3, complete-evidence counts were **22/24 baseline** and **21/24 MMR**. This is not a held-out accuracy benchmark or a resume-ready performance claim.

The app's **Developer checks: REST API and streaming** panel runs a consent-controlled live API test using the fictional sample. It reports stage status, streamed token events and citations without copying the key into the report.

## Project map

| File | Purpose |
| --- | --- |
| `app.py` | Interface and stage inspection |
| `nexus_rag/core.py` | Loading, splitting, embeddings, Qdrant and safe errors |
| `nexus_rag/pipeline.py` | Rewriting, deduplication, MMR, reranking, streaming and citations |
| `nexus_rag/api.py` | REST/SSE service |
| `nexus_rag/api_client.py` | Reference SSE parser and live integration check |
| `nexus_rag/benchmark.py` | Fictional eight-page PDF fixture generated in memory |
| `docs/START_HERE.md` | First learning session |
| `docs/PROJECT_WALKTHROUGH.md` | Beginner-friendly explanation and demo script |
| `docs/RESUME_CHECKLIST.md` | Resume feature-to-code mapping and Python wording |
| `docs/API.md` | Endpoints, event protocol and security boundaries |
| `docs/VERIFICATION.md` | Measured results and limitations |

## Boundaries

- **Full app/API: local single-user project.** Only the sample-only portfolio entrypoint is publicly hosted. No production authentication or scale guarantees. Do not expose the full local app/API ports publicly.
- The UI uses `.data/`; the API uses `.api-data/`. They share pipeline code but have independent indexes. Upload/index in each interface you use. Embedded Qdrant requires one owning process per directory.
- Text-based English PDFs are the target. OCR, image understanding and reliable complex-table parsing are not included or claimed in the supplied resume.
- Similarity is **not confidence**. With query rewriting it may be the highest score across variants, not a reranker score.
- Citation auditing validates labels, not factual support. Hallucination and prompt injection remain possible. Review evidence.
- Streamed text is provisional until completion. A failed stream is incomplete, not a finished answer.
- Unusual text can hit the token guard. Changing chunk/model settings requires a new collection and re-indexing.
- Identical PDF bytes reuse IDs; changed PDFs are separate documents. No document-deletion/version-management UI is included.
- Failed ingestion can leave unlisted partial chunks; stable IDs make retry safe. The API catalog becomes visible only after successful indexing.
- Your key is session-only unless you explicitly configure `.env`. Closing the session may require entering it again.

References: [LangChain Groq](https://docs.langchain.com/oss/python/integrations/chat/groq), [LangChain Qdrant](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant), [FastEmbed](https://qdrant.github.io/fastembed/Getting%20Started/), [FastAPI streaming](https://fastapi.tiangolo.com/advanced/custom-response/), [Groq models](https://console.groq.com/docs/models).
