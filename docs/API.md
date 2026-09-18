# REST and streaming API

Start with `python -m uvicorn nexus_rag.api:app --host 127.0.0.1 --port 8000 --no-access-log` in the project virtual environment, or use the combined launcher. Interactive OpenAPI documentation: http://127.0.0.1:8000/docs.

## Endpoints

| Method and path | Input | Output |
| --- | --- | --- |
| `GET /health` | None | Local service status/version |
| `POST /documents` | Multipart field `file`, text-based PDF | Document hash, filename, readable page/chunk counts, skipped pages |
| `GET /documents` | None | Successfully indexed document catalog |
| `POST /search` | Query JSON | Source passages and stage trace |
| `POST /ask/stream` | Query JSON plus key and consent | Server-Sent Events stream |

Query example for local retrieval:

```json
{
  "doc_id": "replace-with-the-upload-response-doc_id",
  "question": "Who approves a learning purchase?",
  "mode": "mmr",
  "k": 3,
  "fetch_k": 10,
  "mmr_lambda": 0.7
}
```

`doc_id` must be an actual 64-character lowercase SHA-256 returned from upload. `mode` is `baseline`, `mmr` or `advanced`. `k` is 1–8; `fetch_k` is at least k and at most 24. The MMR lambda weights relevance: 1 prioritises relevance; lower values penalise redundancy more strongly.

For advanced retrieval or answer generation, add `"consent": true` and supply `groq_api_key` in the JSON request, or configure the server's local environment. Never put credentials in URLs. Keys are not written to the document catalog or returned in responses. This local example uses HTTP loopback, not a remote encrypted transport. Do not expose it on a public interface.

## SSE contract

```text
event: status
data: {"stage":"retrieving"}

event: evidence
data: {"sources":[...],"trace":{...}}

event: token
data: {"text":"An answer fragment"}

event: done
data: {"answer":"Complete answer [S1]","citations":{...}}
```

Clients must parse complete SSE events, not assume one TCP read equals one event. See `nexus_rag/api_client.py`. A provider failure after response headers have been sent is an **error event**, not a new HTTP error status. The error may follow partial tokens; discard or clearly label that partial answer. There is no `done` event on that error path. The final citation audit validates ID ranges only, not semantic support. Tokens are provisional until `done`.

Before streaming starts, invalid input, missing consent/key and unknown document IDs return ordinary HTTP errors. Validation responses omit input values to avoid reflecting credentials.

## Storage and boundaries

- The UI uses `.data/`; the API uses `.api-data/`. They share pipeline code but have independent local document indexes, so upload a document to each interface you use. This avoids two processes opening the same embedded Qdrant database. The API self-check handles its own fictional sample upload.
- One API process owns its database. In-process index access is serialised. Do not use multiple workers with local Qdrant; use Qdrant Server and redesign auth/storage for concurrent production use.
- Uploaded PDF bytes are read and processed, not saved as source files. Extracted text, metadata and vectors persist locally. The catalog becomes visible only after successful indexing; interrupted uploads can be retried using stable IDs.
- Request bodies are capped at 16 MB; PDF content at 15 MB and 150 pages. These limits do not make untrusted PDF parsing production-safe: production needs parser isolation, time/memory quotas and malware/file controls.
- Cross-origin browser requests are rejected. The service binds to loopback. An optional `NEXUS_API_TOKEN` enables a local bearer-token check; it is not a multi-user identity system. No external deployment was performed.
