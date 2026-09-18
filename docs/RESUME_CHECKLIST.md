# Resume feature checklist

Scope: implement the Nexus RAG project described in Mohd Rahil's supplied resume, using Python as explicitly requested. The original resume PDF is unchanged.

| Resume feature | Implementation | Where to inspect |
| --- | --- | --- |
| Uploaded PDFs | Size/page limits, corrupt/encrypted/scanned-only rejection | `core.py: read_pdf`; UI upload; `POST /documents` |
| Page-aware chunking | Split each page separately, retain one-based physical PDF page | `read_pdf` |
| Local embeddings | BGE-small via FastEmbed ONNX, 384-dimensional vectors, token guard | `LocalEmbeddings` |
| Qdrant vector search | Persistent local collection, cosine similarity, document filter | `Index` |
| Question reformulation | Original question plus up to two validated Groq-generated variants | `GroqStages.reformulate` |
| Result deduplication | Stable chunk IDs, keep strongest retrieved score | `deduplicate` |
| Maximal Marginal Relevance | Greedy relevance-minus-redundancy selection on local vectors | `mmr_select` |
| LLM-based reranking | Groq orders candidate IDs; schema and permutation validation | `GroqStages.rerank` |
| Prompt orchestration | LangChain prompt templates, model calls and JSON parsing | `pipeline.py` |
| Context-grounded answers | Evidence-only instructions, explicit insufficient-evidence behavior | `stream_answer` |
| Streaming APIs | Server-Sent Events: status, evidence, token, done/error | `POST /ask/stream` |
| Source attribution | Stable source labels, filename, page, chunk ID, original text; ID audit | `sources`, `citation_audit` |
| REST APIs | Health, document upload/catalog, search, streamed answer, OpenAPI docs | `api.py` |

Implementation is not the same as universal reliability. See `VERIFICATION.md` for tests actually run. The app explicitly labels fallback stages; an LLM failure is not counted as successful reranking. Citation ID validation does not establish that a claim is true.

## Accurate technology wording

Use **Python, LangChain, Qdrant, Groq, FastAPI, Streamlit, REST APIs** for this implementation. It is not a LangChain.js/React application. Do not claim those technologies solely because the older resume listed them.

Suggested project bullets, subject to your own understanding and demonstrated results:

- Built a Python RAG application for PDF question answering with page-aware chunking, local embeddings, Qdrant search and source/page attribution.
- Implemented question reformulation, deduplication, MMR and LLM-based reranking, with inspectable traces and explicit fallbacks.
- Exposed document ingestion, retrieval and streamed grounded answers through FastAPI REST/SSE endpoints and a Streamlit interface.

Do not add an accuracy percentage from the small synthetic development fixtures to the resume. No public production deployment or real-user scale testing is claimed.
