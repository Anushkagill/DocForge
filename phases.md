# DocForge — Implementation Phases

> **Purpose:** Defines the implementation ORDER. Read `rules.md` before starting. `architecture.md` is the technical source of truth; `prd.md` defines requirements; `design.md` defines UI behavior; `memory.md` records actual progress.
>
> **Phase numbering:** Integer phases only: **Phase 0, Phase 1, Phase 2, Phase 3…**. Never use decimal/subphase identifiers such as 0.1, 0.2, 3.1 or 3.0.1. Tasks inside a phase use ordinary bullets or headings, not phase numbers.
>
> **Status at document creation:** All phases not started. The owner has approved the architecture direction; this is not implementation approval for any individual phase.

## How to use this plan

The owner will explicitly ask for an implementation plan for a phase (for example, “give me the implementation plan for Phase 1”). Antigravity must then explain scope, dependencies, files, steps, risks and tests without changing code. When the owner separately says to implement that phase, implement only that phase. After implementation, the owner may request a separate phase explanation file; that file is a learning artifact generated on request and is not a seventh core project specification file.

One phase at a time. Do not start the next phase until the owner has reviewed the completed phase and explicitly approved moving on.

## Status tracker

| Phase | Title | Milestone | Status |
|---:|---|---|---|
| 0 | Project foundation and deployment feasibility | Foundation | Not started |
| 1 | Evaluation dataset and measurement harness | Foundation | Not started |
| 2 | Database foundation, authentication and tenant isolation | Core platform | Not started |
| 3 | Secure PDF storage, upload and ingestion jobs | Core platform | Not started |
| 4 | PDF parsing, layout and provenance | Core RAG | Not started |
| 5 | Structure-aware chunking and embedding | Core RAG | Not started |
| 6 | Lexical, dense and hybrid retrieval baseline | Core RAG | Not started |
| 7 | Gemini generation, citations and privacy enforcement | Core RAG | Not started |
| 8 | API and core application experience | Public MVP | Not started |
| 9 | Retrieval optimization, reranking and verification | Quality milestone | Not started |
| 10 | Tables, scanned PDFs and OCR | Coverage milestone | Not started |
| 11 | Deployment hardening, testing, CI/CD and recovery | Public release | Not started |
| 12 | Final evaluation, polish and portfolio release | Resume-ready | Not started |

Status values: Not started · Planning · In progress · Awaiting owner review · Done · Blocked.

## Definition of Done — every phase

- [ ] Phase objective and acceptance criteria are met with evidence.
- [ ] Tests run; actual commands and outputs are reported. Never claim unrun tests passed.
- [ ] Privacy/security regression tests still pass where relevant.
- [ ] Evaluation is rerun from Phase 1 onward; metrics, counts, config hash and model IDs are recorded.
- [ ] Dependency licenses and relevant decisions are documented in the six core files (no ADR directory).
- [ ] `memory.md` is updated with actual current state, issues and next action.
- [ ] The owner receives a concise report and approves before the next phase.
- [ ] If the owner requests it, a separate beginner-friendly explanation file for this phase is created with actual implementation details and test evidence.

## Phase 0 — Project foundation and deployment feasibility

**Goal:** establish the development environment and verify the constraints that could invalidate the architecture before substantial implementation.

**Work:**
- Collect actual OS, CPU, RAM, disk and development environment details.
- Inspect repository state and create a clean repository structure consistent with `architecture.md`.
- Establish Python and frontend environment/tooling candidates; present a decision brief before choosing unapproved dependencies.
- Verify current official docs for Render Free/Valkey, Neon PostgreSQL/pgvector, Neon Object Storage, Cloudflare R2 and Vercel.
- Verify both Neon Object Storage and R2 for private objects, signed URLs, HTTP Range, CORS/PDF.js, pricing/limits/region before the storage implementation phase.
- Verify Gemini candidate model IDs, embedding dimensions, token-count support, quota/pricing, data handling and region. No model ID is assumed until checked.
- Establish secrets/environment-variable handling, `.gitignore`, basic logging and a minimal test command.
- Record free-tier limitations and fallback decision evidence.

**Acceptance criteria:**
- Environment facts recorded in `memory.md`.
- Required providers' current capabilities and limits are documented with official sources and verification dates.
- Both primary and fallback object-storage options are evaluated before Phase 3.
- No secrets or private PDFs are committed.
- A clean checkout can install dependencies and run the initial checks.
- Any architecture assumption that fails is brought to the owner before implementation continues.

## Phase 1 — Evaluation dataset and measurement harness

**Goal:** build the ruler before tuning the RAG engine.

**Work:**
- Select a small representative set of public, license-compatible English PDFs: text-heavy, multi-column and simple-table examples initially; add scans/tables later.
- Create a corpus manifest with source, license, type, pages and notes.
- Create a labelled question set (initial target approximately 40–60 if feasible): factual lookup, definitions, section explanation and unanswerable questions. Add gold answer, evidence passage, page and region when applicable.
- Split into tuning and locked test sets; document exactly when locked data may be used.
- Implement metric/report scaffolding for retrieval, answer correctness, citation support, location, abstention and reliability/performance.
- Implement a trivial baseline to prove the harness/report works before real retrieval.
- Record provisional thresholds and uncertainty; do not tune against the locked set.

**Acceptance criteria:**
- Corpus licenses and question labels are reviewed.
- One command produces a complete report for the trivial baseline.
- Tuning/locked split membership is fixed and documented.
- Report includes counts, failures, config hash and run date.

## Phase 2 — Database foundation, authentication and tenant isolation

**Goal:** build the secure multi-user foundation before user-owned documents or jobs exist.

**Work:**
- Finalize relational schema and migrations for users, OAuth identities, refresh sessions, knowledge bases and foundational audit records.
- Implement email/password authentication using Argon2id (`argon2-cffi`) and Google OAuth/OIDC.
- Implement DocForge-issued access and refresh JWTs in Secure, HttpOnly cookies; refresh rotation, revocation, CSRF and explicit CORS.
- Implement application authorization and PostgreSQL RLS with transaction-scoped user context.
- Ensure app DB role is not superuser/BYPASSRLS; separate migration privileges.
- Add basic auth rate limits, safe auth errors and minimal audit events.
- Add cross-user and pooled-connection isolation tests.
- Password reset and email verification must be included before public account flows are considered production-ready; choose email provider only through an explicit decision brief.

**Acceptance criteria:**
- Registration, login, Google login, refresh, logout and session revocation pass tests.
- Argon2id hashes are verified; no plaintext or bcrypt paths exist.
- User A cannot access User B's KBs or sessions through API or direct DB access under app role.
- RLS context does not leak across pooled connections.
- CSRF/CORS/cookie settings are validated against intended deployment domains.
- Migration works on both a clean DB and an existing test DB.

## Phase 3 — Secure PDF storage, upload and ingestion jobs

**Goal:** accept PDFs safely and make ingestion durable without blocking API requests.

**Decision gate:** choose Neon Object Storage only if Phase 0 verification passed; otherwise use already-verified R2. Confirm object adapter, limits and exact URL behavior.

**Work:**
- Implement private object storage adapter and opaque object keys.
- Implement backend authorization before signed URL issuance; test short-lived URL behavior and PDF.js Range/CORS.
- Implement upload validation: signature/MIME, size, page count, encryption/corruption and safe filenames.
- Create document/job records in PostgreSQL and enqueue identifiers-only Celery tasks through Render Key Value/Valkey-compatible broker.
- Run FastAPI and Celery as separate processes in the same Render service for initial deployment, with bounded worker concurrency.
- Implement durable job states, stage checkpoints, retries, idempotency and stale-job reconciliation.
- Enforce one document belongs to one KB; same file in another KB is independent.
- Add basic upload limits and user-visible status/errors.

**Acceptance criteria:**
- Private PDF upload and signed access work for the authorized owner only.
- PDF.js can load pages using Range requests; expired URL can be refreshed.
- Invalid/oversized/encrypted/corrupt files fail with typed errors and no crash.
- Jobs survive broker/worker restart through PostgreSQL state and reconciliation.
- One document failure does not block another; existing indexed docs are not reprocessed.
- Object keys and signed URLs are not exposed in logs.

## Phase 4 — PDF parsing, layout and provenance

**Goal:** turn born-digital PDFs into trustworthy page and block records with stable source coordinates.

**Work:**
- Compare PyMuPDF and any justified parser alternative on the selected corpus; review licenses.
- Implement parser adapter in isolated process with timeout, memory and page limits.
- Extract pages, dimensions, rotation, crop metadata, text blocks, headings/paragraphs/lists, reading order and bounding boxes.
- Preserve parser-native coordinates and convert into canonical coordinate convention.
- Persist page/block records and extraction quality metadata.
- Build a box-overlay/debug renderer to visually inspect stored boxes.
- Add golden-file and hostile-file suites.

**Acceptance criteria:**
- All tier-1 corpus PDFs parse or fail with documented typed errors.
- Visual overlays confirm page/region alignment for representative pages.
- Rotation, crop, scaling and page-size coordinate tests pass.
- Hostile PDFs do not crash the API/worker or exceed configured resource limits.
- Extracted text and block provenance are reproducible under pinned parser/config versions.

## Phase 5 — Structure-aware chunking and embeddings

**Goal:** produce retrieval-ready chunks without losing source traceability.

**Work:**
- Implement structure-aware chunking over blocks and heading hierarchy.
- Preserve a list of source block IDs and `(page, bbox)` references per chunk; chunks may span pages.
- Start with provisional 500–700-token target, 80–100 overlap and sensible minimum/maximum; use Gemini token-count API where supported and local estimates for planning.
- Implement Gemini embedding adapter behind a narrow interface, called only through EgressGate for cloud-allowed content.
- Store model ID, dimensions, input hash and embedding/index config metadata.
- Keep one active embedding space. If model changes later, require explicit re-embedding of the corpus before switching.
- Add duplicate/idempotency constraints and embedding failure recovery.

**Acceptance criteria:**
- Chunk-to-block-to-page/box provenance can be traced and visually inspected.
- Chunk sizes and boundaries are reported; no arbitrary loss of source text.
- Embedding dimensions/model metadata are validated and consistent between corpus and query vectors.
- Local-only documents never reach Gemini (canary test).
- Re-running ingestion does not create duplicate chunks/vectors.

## Phase 6 — Lexical, dense and hybrid retrieval baseline

**Goal:** establish measurable retrieval before adding reranking.

**Work:**
- Implement PostgreSQL full-text search using `tsvector` and `ts_rank`/`ts_rank_cd`; do not label it BM25.
- Implement pgvector exact nearest-neighbor search as correctness baseline.
- Compare lexical-only, dense-only and hybrid RRF retrieval on the tuning set.
- Start with up to 20 lexical + 20 dense candidates; tune candidate counts and final evidence size (initially 5–8 chunks).
- Add query-time snapshot of eligible indexed document IDs and enforce KB/document scope.
- Record candidate ranks/scores, latency and retrieved source locations.
- Benchmark HNSW only if exact vector search is too slow; retain only if latency improves with acceptable recall. Skip IVFFlat initially.

**Acceptance criteria:**
- One command reports Recall@k, MRR and nDCG with counts for lexical, dense and hybrid variants.
- Query cannot retrieve across KB/user boundaries.
- Query snapshot is used consistently through retrieval and citations.
- Exact vector search is a reproducible reference baseline.
- Retrieval thresholds are set from baseline evidence and frozen before tuning.

## Phase 7 — Gemini generation, citations and privacy enforcement

**Goal:** generate a grounded answer from retrieved evidence and resolve citations to the original PDF.

**Work:**
- Implement Gemini generation adapter and structured answer schema.
- Implement prompt templates that delimit document evidence as untrusted data and instruct the model not to follow embedded instructions.
- Implement EgressGate as the only outbound path for document-derived content.
- Enforce `local-only` default and explicit `cloud-allowed` consent; propagate strictest privacy label to derived content.
- Implement CitationResolver from answer citation IDs to retrieved chunks, source quote spans, page and bounding boxes.
- Reject fabricated citation IDs or citations outside query snapshot/KB scope.
- Add deterministic source validation and evidence-only behavior when AI mode is unavailable.
- Document multi-call Gemini path and handle timeouts/429 with bounded retries.

**Acceptance criteria:**
- API-enabled query returns structured answer and valid citations for answerable test cases.
- Material claims are checked by deterministic source validation and Gemini semantic verification.
- At most one corrective retrieval attempt can run; unsupported material claim after that attempt causes answer-level abstention.
- Unknown citation IDs, wrong document/page and out-of-scope citations are rejected.
- Local-only canary text never appears in any fake/real outbound adapter test.
- API quota/provider failure never produces an unsupported confident answer.
- Logs contain no document text, sensitive prompt, secrets or signed URLs.

## Phase 8 — API and core application experience (public MVP)

**Goal:** expose the core workflow as a usable deployed product.

**Work:**
- Implement authenticated KB/document APIs and core React screens described in `design.md`.
- Support multiple KBs, multi-PDF upload, ingestion status and per-document privacy selection.
- Support KB-wide and selected-document query scope; clearly show incomplete ingestion coverage.
- Implement question/answer/evidence panel, citations and PDF.js viewer with page/region navigation.
- Implement answer-level strict abstention for MVP. If a material claim remains unsupported, withhold the whole generated answer and show abstention/evidence-only response.
- Implement query trace/latency basics, error/loading/empty states and basic rate limits.
- Add frontend unit/component and Playwright journey tests.

**Acceptance criteria:**
- User can register/login, create KB, upload PDFs, wait for indexing, ask questions and inspect cited source.
- Cross-user access is denied in end-to-end tests.
- KB-wide and selected-document scopes work correctly.
- In-progress documents are never silently searchable; coverage warnings are truthful.
- Answer-level abstention and citation navigation work.
- Main MVP release-gate checklist in `prd.md` passes.

## Phase 9 — Retrieval optimization and quality calibration

**Goal:** improve retrieval and calibrate the already-working MVP verification/abstention pipeline only where evidence supports the extra complexity.

**Work:**
- Run held-out ablation: hybrid FTS + pgvector + RRF baseline versus Gemini Flash relevance scoring/reranking.
- Enable reranking only if quality gain justifies API calls, latency and quota; otherwise document rejection/deferment and keep hybrid baseline.
- Analyze retrieval misses and tune candidate count, evidence count and chunking only on the tuning set.
- Evaluate and calibrate the Phase 7 semantic verifier against human-reviewed labels; do not treat an LLM judge as ground truth.
- Improve the Phase 7 one-attempt corrective retrieval only if measured failure analysis identifies a specific weakness; retain the hard one-attempt limit and fixed query scope snapshot.
- Claim-level filtering is a later Milestone 3 enhancement and requires separate evaluation and owner approval.

**Acceptance criteria:**
- Reranker decision includes held-out metrics, p50/p95 latency, API-call impact and explicit adopt/reject/defer result.
- Verifier error analysis is compared with human labels and any threshold change is justified on tuning data.
- Corrective attempt remains bounded to one and cannot widen scope beyond the original snapshot.
- Answer-level abstention remains the MVP behavior; no partial generated answer is shown as verified.
- API failure/quota exhaustion during verification does not mark an answer verified.

## Phase 10 — Tables, scanned PDFs and OCR

**Goal:** extend beyond born-digital paragraph retrieval with measured table and scan support.

**Work:**
- Benchmark OCR options (OCRmyPDF/Tesseract and justified alternatives) for accuracy, speed, license and coordinate quality.
- Detect scanned pages and OCR them with confidence and canonical boxes.
- Evaluate table extraction/serialization that preserves rows, columns, cells or region boxes.
- Detect figure/chart regions; MVP behavior for charts is display region and state values are not reliably interpreted.
- Extend corpus/question set and re-run retrieval/answer evaluation.

**Acceptance criteria:**
- OCR location accuracy is measured against labelled boxes with agreed tolerance.
- Table lookup quality is measured and failure modes documented.
- OCR confidence and source type are preserved.
- Privacy rules are enforced for any cloud OCR (default to local processing where feasible; any outbound cloud OCR requires cloud-allowed + EgressGate).

## Phase 11 — Deployment hardening, testing, CI/CD and recovery

**Goal:** prepare the public deployment for safe, repeatable operation within the accepted free-tier limitations.

**Work:**
- Configure Vercel, Render, Render Key Value/Valkey, Neon and verified object storage using environment secrets.
- Configure explicit CORS, cookie domains/SameSite/Secure behavior, CSRF, trusted proxy settings and HTTPS.
- Add GitHub Actions for backend lint/type/tests, frontend checks/build, migration validation and relevant integration tests.
- Add structured logs, request/job IDs, stage timings, error categories, queue depth and provider call/usage metadata where available.
- Test rate limits, upload limits, provider 429/timeouts, worker restart/reconciliation and signed URL expiry.
- Define retention for query history, audit events, logs and backups.
- Test deletion cleanup and retry behavior.
- Verify Neon and object-storage backups/recovery; perform a manual restore test for both DB and PDFs.
- Run security checks for app auth + RLS, object access, prompt injection, malicious PDF handling and secrets.
- Document shared Render resource contention and free-tier sleep/restart limitations.

**Acceptance criteria:**
- CI checks pass on a clean push; deployment only occurs after required checks.
- Public domain uses secure cookie/CORS/CSRF configuration.
- Cross-tenant and signed URL authorization tests pass against deployed-like configuration.
- DB and object files can be restored together in a manual drill.
- Job reconciliation works after broker/worker restart.
- No secrets/private PDFs in repository or logs.
- Provider limitations and privacy disclosures are visible and accurate.

## Phase 12 — Final evaluation, polish and portfolio release

**Goal:** demonstrate a reliable, understandable RAG product with honest measured results.

**Work:**
- Run final tuning-set analysis and the locked test set only at the designated final gate.
- Report six metric families with counts, config/model IDs, date and uncertainty.
- Compare lexical, dense, hybrid and reranker (if retained) variants.
- Review failure taxonomy: extraction, chunking, retrieval, ranking, generation, citations, verification, abstention and infrastructure.
- Polish UI accessibility and primary workflows toward WCAG 2.2 AA principles.
- Prepare README, architecture diagram, deployment guide, demo script, case study and interview talking points.
- Ensure every phase explanation artifact requested by owner is accurate and includes actual commands/results.

**Acceptance criteria:**
- Public MVP and resume-ready checklists pass or each unmet item is explicitly disclosed.
- Locked test set is used only as specified; no post-hoc tuning on locked results.
- Results are reproducible from documented commands/config.
- Repository is clean, setup/deployment instructions are current, and demo uses non-sensitive public data.

## Backlog — not scheduled

Claim-level filtering; Knowledge Graph experiment only if failure analysis justifies it; chart understanding; cross-KB search; shared documents across KBs; additional languages; advanced monitoring/budget controls if usage warrants them; separate always-on worker service if the free deployment proves insufficient.
