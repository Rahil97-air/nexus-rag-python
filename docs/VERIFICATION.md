# First-milestone verification

## Final local feature verification — 18 September 2026

Deployment verification: **27 automated tests passed**, including a public-entrypoint test that verifies uploads and local API controls are absent and an owner environment key is not used. Windows-only dependencies have platform markers. Streamlit Community Cloud successfully built and started the Python 3.12 public entrypoint. Hosted model initialization, three-page indexing and baseline retrieval passed: the expense-claim question ranked the supporting page first (similarity 0.851). Hosted Groq generation remains untested; the live checks below were local. GitHub's recursive tree contains exactly the 37 intended source/sample files, matching the local file hashes.

**26 automated tests passed** on the final feature implementation. They cover PDF extraction, stable IDs, persistence, document filtering, deduplication, MMR diversity, query reformulation orchestration, reranking validation/fallbacks, stream ordering/errors, source labels, input/body limits, consent, secret-safe errors, API upload/search, duplicate upload handling, and UI indexing/search/stale-result handling. Mocked providers are used for deterministic offline tests; they do not establish live LLM quality.

Live Groq-backed UI check:

- Question: “Who approves remote work and who approves a learning purchase?”
- Original question plus two intent-preserving rewritten queries.
- Nine raw hits, three unique chunks, six duplicates removed.
- MMR and LLM reranking both completed, with no fallback warnings in the successful run.
- Streamed answer correctly identified the team lead for remote work and manager for learning purchases; the corresponding evidence was on pages 2 and 3.
- An earlier reranking response failed validation and explicitly fell back to MMR. The reranking instructions were tightened and the successful live run was repeated. Provider-generated citation bracket variants were also handled consistently.

Live REST/SSE integration check through the running API:

- Fictional handbook uploaded through `POST /documents`.
- `POST /ask/stream` ran advanced retrieval successfully with no stage warnings.
- Observed event order: **status → evidence → token → done**, including **37 nonempty token events** in this run.
- Final answer cited **S1 and S2**; no invalid source IDs.
- The answer correctly named the two approvers. This is a smoke test on one answerable question, not a general faithfulness benchmark.
- The earlier absent-holiday-answer live check also passed (see historical notes below); broader abstention evaluation remains future work.

Extended local retrieval fixture (generated in memory): **8 pages, 16 chunks, 24 answerable questions and 3 absent-answer questions**, k=3:

| Mode | Questions with all required evidence | Mean required-evidence recall |
| --- | --- | --- |
| Baseline | 22/24 | 93.75% |
| MMR, lambda 0.7 | 21/24 | 91.67% |

Scoring checks both expected page and a labelled supporting phrase in the retrieved text. Absent-answer cases are diagnostic only and are not counted as successes. MMR did not improve this fixture at these settings. No broad claim that advanced retrieval improves accuracy is made; the complete advanced pipeline was live smoke-tested, not benchmarked across all 27 questions.

Reproduce offline/local checks with the README commands. The generated detailed local report is `test-results/extended-retrieval.json`; no API keys are in that report. The app's developer panel can repeat the live API check with explicit consent.

### Completion boundary

The requested resume feature set is implemented in **Python** and exercised through the UI and API. The original resume PDF is unchanged; its LangChain.js label should not be used to describe this implementation. Public deployment, production hardening, OCR, multi-user identity/access control, parser isolation and large representative evaluation are **not** claimed complete. These were not features in the supplied resume and require separate scope/choices.

The UI and API use independent local databases. Only fictional sample content was transmitted in these live checks; the user's key stayed in the application/session and was not copied into code, logs, reports or the source bundle.

---

## Historical first-milestone notes

Executed on this Windows computer on 17 September 2026 with the versions in `requirements.txt`.

| Check | Result |
| --- | --- |
| Dependency compatibility (`pip check`) | Passed |
| PDF extraction, original page numbering, stable chunk IDs | Passed |
| Invalid and blank PDF rejection | Passed |
| Duplicate indexing, selected-document filtering, persistent reopening | Passed |
| Real local embedding retrieval: reimbursement → page 1 | Passed |
| Real local embedding retrieval: work from home → page 2 | Passed |
| Real local embedding retrieval: professional development → page 3 | Passed |
| Streamlit AppTest: initial render, index button, search button, source/page display | Passed |
| Live Groq answer generation | Subsequently passed two sample checks; see below |

These small tests verify the initial plumbing and three retrieval examples. They do not establish general retrieval accuracy, reliable abstention, citation faithfulness, production security or scanned-PDF support. The model download initially hit a Windows symlink-permission issue; its automatic retry completed successfully and the model is now cached.

The interface interaction check can be repeated with `python scripts/check_app.py` in the project virtual environment, with the app stopped. It indexes only the fictional sample into the local database.

## Expanded baseline evaluation

Run `python scripts/evaluate.py` with the project virtual environment. It uses an isolated database, does not call Groq, and writes a detailed generated report to `test-results/retrieval.json`.

The development set has 14 answerable questions (including two multi-page questions) and three questions whose answers are absent. On this three-page fictional corpus:

- A relevant page ranked first for 13/14 answerable questions.
- Both retrieved passages together contained all expected pages for 13/14 questions.
- Mean per-question page recall at two passages was 96.4%.
- Six offline unit tests passed, including three generation-contract tests using a mocked provider. Those tests do not demonstrate real LLM accuracy.

Observed failures:

1. The course-purchase approval question ranked expenses before learning; the correct page was second.
2. The combined remote-work and learning-approval question retrieved remote work and expenses, missing learning at k=2.
3. The absent holiday-entitlement question still returned a similarity of 0.7031. A score alone must not be presented as confidence or sufficient evidence.

These are deliberately small development checks, not a held-out benchmark or a résumé-ready accuracy claim. Returning all three pages would trivially improve recall here and would not demonstrate a better retrieval system. Next evaluate a larger document with distractor passages before comparing retrieval changes. Live generation, answer faithfulness and refusal to answer absent questions remain unverified without a user-configured key.

## Live generation follow-up — 17 September 2026

The user entered a key in the session-only masked field. Browser-control testing used only the fictional handbook. No key was copied or written to a file.

The original `llama-3.3-70b-versatile` request was rejected as model unavailable for the account. After checking current provider documentation, the default was changed to Groq-hosted `openai/gpt-oss-20b`; the prompt and retrieval pipeline were preserved. Network access was also required. Provider errors now display safe categories rather than raw response contents.

- Expense deadline: answered **30 calendar days of purchase**, citing **[S1]**, whose displayed evidence was page 1. Correct on this example.
- Paid holiday entitlement: explicitly said the supplied evidence did not contain this information. Correct abstention on this example despite a top retrieval score of 0.703.
- All **8 offline tests passed**, including the new error-message privacy check.

These two live observations supersede the earlier unverified status for these specific examples only. They do not establish general answer faithfulness or reliable abstention across arbitrary PDFs. No account settings, model permissions or billing settings were changed.

Model references consulted: [Groq's supported models](https://console.groq.com/docs/models), [official GPT-OSS-20B documentation](https://developers.openai.com/api/docs/models/gpt-oss-20b). Documentation guided the model change; actual account compatibility was established by the successful live calls.
