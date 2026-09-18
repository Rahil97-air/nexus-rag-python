from pathlib import Path
import os
from threading import RLock
import streamlit as st
from dotenv import load_dotenv
from nexus_rag.core import Index, read_pdf, answer, generation_error_message, MODEL
from nexus_rag.pipeline import GroqStages, DEFAULT_MODEL, retrieve, stream_answer, citation_audit

ROOT = Path(__file__).resolve().parent
PUBLIC_DEMO = bool(globals().get("PUBLIC_DEMO", False))
if not PUBLIC_DEMO:
    load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Nexus RAG · Learning Lab", page_icon="📚", layout="wide")
st.title("Nexus RAG · Learning Lab")
st.caption("Python • LangChain • local embeddings • Qdrant • optional Groq answers")
if PUBLIC_DEMO:
    st.info("Public portfolio demo: fictional handbook only. Embeddings run on the hosting server. Live Groq features use your own session key; no owner key is provided. Never enter confidential information.")
else:
    st.info("Start with the sample PDF. Text extraction and search run locally. Generating an answer sends your question and retrieved passages to Groq.")

@st.cache_resource
def get_index():
    return Index(ROOT / (".demo-data" if PUBLIC_DEMO else ".data"))

@st.cache_resource
def index_lock():
    return RLock()

with st.sidebar:
    st.header("Answer setup")
    configured_key = "" if PUBLIC_DEMO else os.getenv("GROQ_API_KEY", "")
    if configured_key:
        session_key = ""
        st.success("A key is configured on this computer.")
    else:
        st.write("No coding or file editing needed. Create a key in your own Groq account, then paste it in the masked box below—not in chat.")
        st.link_button("Open Groq API keys", "https://console.groq.com/keys")
        session_key = st.text_input("Groq API key", type="password", key="groq_session_key")
        st.caption("Used only for this browser session; this app does not save it to a file. A masked field hides the display, not the key from the running application. Entering it does not send a model request.")
        if PUBLIC_DEMO:
            st.caption("Your key is handled by this hosted app's server and sent to Groq for authentication. Use a limited/revocable key only if you trust this deployment. Local-only search needs no key.")
        if session_key:
            st.caption("Key entered (not yet verified). It will be checked when you generate an answer.")
    st.divider()
    st.header("1. Choose a document")
    upload = None if PUBLIC_DEMO else st.file_uploader("Text-based PDF (up to 15 MB / 150 pages)", type="pdf")
    sample = ROOT / "samples" / "handbook.pdf"
    use_sample = True if PUBLIC_DEMO else st.checkbox("Use fictional sample handbook", value=upload is None)
    st.caption(f"Embedding model: {MODEL}. First search setup downloads model files; text is not sent to an external embedding API.")
    st.caption("Chunk size: 600 characters · overlap: 100 characters · OCR not included")

if use_sample and sample.exists():
    data, name = sample.read_bytes(), sample.name
elif upload:
    data, name = upload.getvalue(), upload.name
else:
    st.write("Upload a PDF or generate the sample using the README instructions.")
    st.stop()

try:
    pages, chunks, skipped = read_pdf(data, name)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

doc_id = chunks[0].metadata["doc_id"]
st.subheader("2. Inspect the inputs")
st.write(f"{len(pages)} readable pages → {len(chunks)} chunks")
if skipped:
    st.warning(f"Pages without extractable text were skipped: {skipped}. Image-only content is not indexed.")
with st.expander("See extracted text and chunks"):
    st.write("Original page text")
    st.json([{"page": p.metadata["page"], "text": p.page_content} for p in pages])
    st.write("Chunks sent to the embedding model")
    st.json([{"page": c.metadata["page"], "text": c.page_content} for c in chunks])

if st.button("Index this document", type="primary"):
    try:
        with st.spinner("Loading local model and indexing… first run may take several minutes."):
            with index_lock():
                get_index().add(chunks)
        st.session_state["indexed"] = doc_id
        st.session_state.pop("result", None)
        st.success("Indexed. Re-indexing the same document does not duplicate chunks.")
    except Exception:
        st.error("Indexing failed. Check network access for the first model download, disk space, and that no second app instance holds the index. You can retry safely.")

st.subheader("3. Retrieve evidence")
question = st.text_input("Your question", "How long do I have to submit an expense claim?")
k = st.slider("Maximum passages to retrieve", 1, 8, 3)
mode_label = st.radio("Retrieval method", ["Baseline (local)", "MMR (local)", "Multi-stage (Groq)"], horizontal=True)
mode = {"Baseline (local)": "baseline", "MMR (local)": "mmr", "Multi-stage (Groq)": "advanced"}[mode_label]
key = configured_key or session_key
model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
advanced_consent = False
if mode == "advanced":
    st.caption("Original question + two rewrites → vector search → deduplication → MMR → LLM reranking. This makes up to two Groq calls before answer generation.")
    advanced_consent = st.checkbox("Allow sending this question and candidate passages to Groq for multi-stage retrieval")
can_search = st.session_state.get("indexed") == doc_id and (mode != "advanced" or (key and advanced_consent))
if st.button("Search locally" if mode != "advanced" else "Run multi-stage retrieval", disabled=not can_search):
    try:
        with st.spinner("Retrieving…"):
            with index_lock():
                retrieval = retrieve(get_index(), question, doc_id, mode=mode, k=k,
                                     fetch_k=max(10, k), stages=GroqStages(key, model) if mode == "advanced" else None)
        st.session_state["retrieval_result"] = (doc_id, question, k, mode, retrieval)
        st.session_state.pop("streamed_answer", None)
    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(generation_error_message(exc))

result = st.session_state.get("retrieval_result")
identity = (doc_id, question, k, mode)
if result and result[:4] == identity:
    retrieval = result[4]
    hits = retrieval.hits
    with st.expander("Retrieval trace: what happened at each stage", expanded=mode == "advanced"):
        st.json(retrieval.trace)
    for warning in retrieval.trace["warnings"]:
        st.warning(warning)
    for i, (doc, score) in enumerate(hits, 1):
        with st.expander(f"[S{i}] {doc.metadata['source']} · page {doc.metadata['page']} · similarity {score:.3f}", expanded=True):
            st.write(doc.page_content)
    st.caption("Similarity ranks passages; it is NOT answer confidence. Search can return passages even when the answer is absent.")
    st.subheader("4. Generate a grounded answer (optional)")
    if not key:
        st.caption("Local search is ready. To enable answers, use Answer setup in the sidebar. No restart or file editing is needed.")
    consent = st.checkbox("Send this question and the displayed passages to Groq")
    generated_now = False
    if st.button("Generate answer", disabled=not (key and consent)):
        st.session_state.pop("streamed_answer", None)
        try:
            st.caption("Streaming from Groq…")
            text = st.write_stream(stream_answer(question, hits, key, model))
            if not text or not text.strip():
                raise ValueError("Empty model response")
            st.session_state["streamed_answer"] = (identity, text, citation_audit(text, hits))
            generated_now = True
        except Exception as exc:
            st.error(generation_error_message(exc))
            st.warning("Any partial text above is incomplete; do not treat it as a finished answer.")
    saved = st.session_state.get("streamed_answer")
    if saved and saved[0] == identity:
        if not generated_now:
            st.write(saved[1])
        if saved[2]["invalid_ids"]:
            st.error(f"Invalid source references: {saved[2]['invalid_ids']}. Do not rely on this answer.")
        with st.expander("Citation ID check (not a fact check)"):
            st.json(saved[2])
        st.caption("Generated answers may be wrong. Check every citation against the passages above.")

if PUBLIC_DEMO:
    st.caption("This hosted demo does not accept private PDF uploads or expose the local REST API. The complete upload-capable app and FastAPI service are included in the source project.")
    st.stop()

with st.expander("Developer checks: REST API and streaming"):
    st.caption("The API runs on localhost:8000 with a separate local index. This check uploads only the fictional handbook and runs one multi-stage streamed answer. Your key is sent to your local API, then used only with Groq; it is not saved.")
    api_consent = st.checkbox("Allow the fictional-sample API check with Groq")
    if st.button("Run end-to-end API check", disabled=not (key and api_consent)):
        from nexus_rag.api_client import smoke_check
        try:
            with st.spinner("Testing API upload, multi-stage retrieval and streamed answer…"):
                report = smoke_check(ROOT / "samples/handbook.pdf", key)
            st.session_state["api_report"] = report
        except Exception:
            st.error("API check failed. Make sure the local API is running on port 8000. No key or raw provider error is displayed.")
    if "api_report" in st.session_state:
        st.json(st.session_state["api_report"])
