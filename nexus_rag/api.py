"""Loopback-only REST/SSE entry point. One process owns its Qdrant directory."""
from contextlib import asynccontextmanager
import hmac
import json
import os
from pathlib import Path
from threading import RLock
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from starlette.middleware.trustedhost import TrustedHostMiddleware

from nexus_rag.core import Index, read_pdf, generation_error_message
from nexus_rag.pipeline import GroqStages, DEFAULT_MODEL, retrieve, sources, stream_answer, citation_audit

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 16 * 1024 * 1024


class BodyLimitMiddleware:
    """Bound request bodies even when Content-Length is missing or misleading."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        pieces, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > MAX_BODY:
                return await JSONResponse({"detail": "Request body exceeds 16 MB."}, status_code=413)(scope, receive, send)
            pieces.append(body)
            if not message.get("more_body", False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(pieces), "more_body": False}
            return await receive()
        await self.app(scope, bounded_receive, send)


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1600)
    doc_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    mode: Literal["baseline", "mmr", "advanced"] = "baseline"
    k: int = Field(default=4, ge=1, le=8)
    fetch_k: int = Field(default=10, ge=1, le=24)
    mmr_lambda: float = Field(default=0.7, ge=0, le=1)
    consent: bool = False
    groq_api_key: SecretStr | None = Field(default=None, max_length=1024)


def sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(root=None, index_factory=Index, stages_factory=GroqStages, answer_stream=stream_answer):
    root = Path(root or ROOT / ".api-data")
    load_dotenv(ROOT / ".env")
    lock = RLock()
    holder = {}

    def index():
        if "index" not in holder:
            holder["index"] = index_factory(root)
        return holder["index"]

    def catalog():
        path = root / "documents.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    @asynccontextmanager
    async def lifespan(app):
        yield
        if "index" in holder:
            holder["index"].close()

    app = FastAPI(title="Nexus RAG API", version="1.0.0", lifespan=lifespan,
                  description="Local single-user PDF Q&A. /ask/stream emits status, evidence, token, done or error SSE events.")
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        # Block drive-by cross-origin web requests. This is NOT multi-user auth.
        origin = request.headers.get("origin")
        if origin and origin not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
            return JSONResponse({"detail": "Cross-origin requests are disabled."}, status_code=403)
        expected = os.getenv("NEXUS_API_TOKEN", "")
        if expected and not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {expected}"):
            return JSONResponse({"detail": "API authentication required."}, status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default includes input values, which might contain a key.
        return JSONResponse({"detail": [{"location": list(e["loc"]), "type": e["type"]}
                                        for e in exc.errors()]}, status_code=422)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "1.0.0", "scope": "local-single-user"}

    @app.get("/documents")
    def documents():
        with lock:
            return {"documents": list(catalog().values())}

    @app.post("/documents", status_code=201)
    def upload_document(file: UploadFile = File(...)):
        try:
            data = file.file.read(15 * 1024 * 1024 + 1)
            pages, chunks, skipped = read_pdf(data, file.filename or "document.pdf")
            doc_id = chunks[0].metadata["doc_id"]
            with lock:
                records = catalog()
                if doc_id in records:
                    return {**records[doc_id], "already_indexed": True}
                index().add(chunks)
                record = {"doc_id": doc_id, "filename": chunks[0].metadata["source"],
                          "pages": len(pages), "chunks": len(chunks), "skipped_pages": skipped}
                records[doc_id] = record
                temp = root / "documents.tmp"
                temp.write_text(json.dumps(records, indent=2), encoding="utf-8")
                temp.replace(root / "documents.json")
                return {**record, "already_indexed": False}
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        except Exception:
            raise HTTPException(503, "Indexing failed. Check model cache, disk and process ownership; retry safely.") from None
        finally:
            file.file.close()

    def key_for(query, require=False):
        key = query.groq_api_key.get_secret_value() if query.groq_api_key else os.getenv("GROQ_API_KEY", "")
        if require:
            if not query.consent:
                raise HTTPException(400, "Explicit consent is required to send question/passages to Groq.")
            if not key:
                raise HTTPException(400, "A Groq API key is required.")
        return key

    def validate(query):
        if not query.question.strip() or query.fetch_k < query.k:
            raise HTTPException(400, "Question must be nonempty and fetch_k must be at least k.")
        with lock:
            if query.doc_id not in catalog():
                raise HTTPException(404, "Document is not indexed in this API workspace.")

    def run_retrieval(query, key):
        with lock:
            stages = stages_factory(key, DEFAULT_MODEL) if query.mode == "advanced" else None
            return retrieve(index(), query.question, query.doc_id, mode=query.mode, k=query.k,
                            fetch_k=query.fetch_k, mmr_lambda=query.mmr_lambda, stages=stages)

    @app.post("/search")
    def search(query: Query):
        validate(query)
        key = key_for(query, query.mode == "advanced")
        try:
            result = run_retrieval(query, key)
            return {"sources": sources(result.hits), "trace": result.trace}
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        except Exception:
            raise HTTPException(503, "Retrieval failed. Check the local index and model.") from None

    @app.post("/ask/stream")
    def ask_stream(query: Query):
        validate(query)
        key = key_for(query, True)
        def events():
            try:
                yield sse("status", {"stage": "retrieving"})
                result = run_retrieval(query, key)
                yield sse("evidence", {"sources": sources(result.hits), "trace": result.trace})
                parts = []
                for token in answer_stream(query.question, result.hits, key, DEFAULT_MODEL):
                    parts.append(token)
                    yield sse("token", {"text": token})
                text = "".join(parts)
                if not text.strip():
                    raise ValueError("Empty model output")
                yield sse("done", {"answer": text, "citations": citation_audit(text, result.hits)})
            except Exception as exc:
                yield sse("error", {"message": generation_error_message(exc), "partial_answer_validated": False})
        return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    return app


app = create_app()
