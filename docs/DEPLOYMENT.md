# Public portfolio demo

Source: https://github.com/Rahil97-air/nexus-rag-python

Live demo: https://rahil97-nexus-rag.streamlit.app/

Deployed on Streamlit Community Cloud, branch `main`, entrypoint `portfolio_app.py`, Python 3.12. Verified on 18 September 2026: the app starts, downloads the embedding model, indexes the three-page fictional handbook, and retrieves the expense deadline passage as the first result with page attribution. Live Groq generation was verified locally; no owner key was copied to the hosted demo and hosted Groq generation has not been tested.

The public entrypoint uses only the bundled fictional handbook. Arbitrary uploads and the local REST developer panel are disabled. Its embedded index is separate from the full local app. Visitors supply their own session-only Groq key for advanced retrieval and generation; owner environment keys are ignored. Do not add an owner's API key to hosting secrets. Baseline/MMR retrieval requires no key.

On the hosted app, embeddings run on the hosting server, not the visitor's computer. With explicit consent, questions and passages go to Groq. Keys are transmitted to the hosting server and Groq, so use a limited key and revoke it after testing. Closing a browser is not a guarantee of immediate server-memory deletion.

The first indexing operation downloads the embedding model. Cold starts, provider limits, memory limits and restarts may interrupt a demo. Hosted storage is not a durable database or backup. This is a portfolio demo, not a production service with a security or availability guarantee.

The full PDF-upload application and FastAPI/SSE service remain available locally via `Start Nexus.cmd`. They are not deployed as public API services.

Never publish `.env`, `.streamlit/secrets.toml`, virtual environments, private PDFs, resumes, indexes, caches or logs. `scripts/package_source.py` builds an explicit source/sample-only bundle.
