# DocForge — System Architecture

> **Purpose:** Defines HOW DocForge is structured. `prd.md` defines WHAT; `design.md` defines the user experience; `phases.md` defines implementation ORDER; `rules.md` defines HOW the owner and Antigravity work; `memory.md` records CURRENT STATE.
>
> **Status:** Owner-approved architecture direction. Provider-specific capabilities, exact model IDs, current quotas, prices and free-tier limits remain verification gates before the relevant implementation phase.

## 1. Product and architecture goals

DocForge is a publicly deployed, multi-user PDF question-answering application. Its main value is excellent retrieval and grounded answers, not infrastructure breadth.

Priority order:
1. Accurate PDF extraction, layout/structure preservation and source provenance.
2. Retrieval quality, measured with a repeatable evaluation set.
3. Grounded answer generation, citation validation and safe abstention.
4. Reproducible evaluation and measurable latency/quality improvements.
5. Secure multi-user isolation, reliable ingestion/deletion and deployment readiness.
6. Maintainable code and an owner who understands and can explain every phase.

Do not add enterprise infrastructure (Kubernetes, Kafka, microservice sprawl, multi-region failover, elaborate quota platforms) without measured need. Free-first is a cost preference, not permission to weaken security or data integrity.

## 2. High-level architecture

```text
React + TypeScript + Vite + Tailwind
  ├─ Authentication and account settings
  ├─ Knowledge-base library and multi-PDF upload
  ├─ KB-wide or selected-document question scope
  ├─ Question, answer, evidence and citation panel
  └─ PDF.js viewer with page/region navigation
                 |
                 v
FastAPI + Pydantic API
  ├─ Authentication, authorization and RLS context
  ├─ KB/document/query use cases
  ├─ EgressGate and privacy policy
  └─ Query orchestration and observability
        |                         |
        v                         v
Neon PostgreSQL + pgvector    Private object storage
  ├─ users/sessions            └─ Original PDFs and durable
  ├─ KB/document/job records       derived files
  ├─ pages/blocks/chunks
  ├─ vectors + full-text
  └─ query/citation/audit data
        ^
        |
Celery worker process -- Render Key Value / Valkey broker
  └─ PDF parsing, normalization, chunking, embedding and indexing

Gemini API: embeddings, optional measured reranking, generation,
and semantic verification for cloud-allowed content only.
```

FastAPI and Celery run as separate processes in the same Render service for the free-first deployment; the worker is not a thread inside FastAPI. This saves a separate service but allows parsing/embedding batches to compete with API requests for CPU and memory. Keep concurrency and batch sizes bounded and measure API latency; split services only if evidence or platform limits require it.

## 3. Selected stack and provider direction

### Frontend
- React, TypeScript, Vite and Tailwind CSS.
- PDF.js for browser PDF rendering and navigation.
- Vitest, React Testing Library and Playwright for tests.

### Backend and data
- Python, FastAPI and Pydantic.
- Neon managed PostgreSQL with pgvector and PostgreSQL full-text search.
- SQLAlchemy 2.x, Alembic and psycopg 3.
- Celery for asynchronous ingestion; Redis-compatible broker for task transport.
- `pdfminer.six` (`pdfminer.six==20231228`, MIT) + `pypdf` (`pypdf>=4.3.0,<5.0.0`, BSD-3-Clause) as the primary born-digital PDF parser stack under permissive licensing (PyMuPDF evaluated and rejected due to AGPL-3.0 copyleft conflicts with DocForge's MIT license).
- Evaluate Docling against complex-layout PDFs before adding it to the primary pipeline.
- OCRmyPDF + Tesseract are candidates for scanned PDFs after a representative benchmark.

### AI
- Gemini API is the sole configured AI provider initially: embeddings, answer generation, semantic verification and (only if evaluation justifies it) model-based relevance scoring/reranking.
- No automatic OpenAI fallback, no Ollama, no locally hosted embedding or generation model.
- Exact model IDs, dimensions, API capabilities, quotas, pricing, region and data-handling terms must be checked against current official documentation before use.
- Keep a narrow provider adapter so another provider can be added only after an explicit future decision.

### Storage and deployment
- Neon Object Storage is preferred for permanent original PDFs, conditional on verifying private-object access, short-lived signed URLs, HTTP Range support, CORS/PDF.js compatibility, current free-tier availability, limits, pricing and region.
- Cloudflare R2 is the fallback. **Verify both Neon Object Storage and R2 before Phase 2's storage implementation gate**; do not start investigating R2 only after Neon fails.
- Use an S3-compatible storage adapter to reduce provider lock-in.
- Local filesystem is temporary processing storage only, never permanent production storage.
- Deployment target: Vercel Hobby frontend; Render Free Web Service for FastAPI + Celery as separate processes; Render Key Value/Valkey as broker; Neon PostgreSQL; verified object storage; Gemini API. Verify current plans, regional compatibility and capabilities before implementation. Free tiers can change.

## 4. Architectural principles

- Keep domain logic independent of FastAPI, vendor SDKs, parser SDKs and ORM-specific types.
- Use narrow interfaces and adapters; wire dependencies in one composition root.
- PostgreSQL is canonical for users, ownership, document metadata, ingestion jobs, extracted content, provenance, chunks, vectors, citations, query traces and audit records.
- Object storage owns original PDFs and durable derived artifacts.
- Redis/Valkey transports Celery messages only. It is not canonical job state and its free tier may be non-persistent.
- Every outbound request containing document-derived content must pass through EgressGate.
- Every query is scoped to one selected KB and either all eligible documents or an explicit subset. No cross-KB search in MVP.
- A document belongs to exactly one KB in MVP. Uploading the same PDF into another KB creates an independent document and ingestion process.
- Preserve provenance from every chunk to source blocks, page(s), region(s) and original PDF.
- Start with plain Python orchestration. Do not add LangChain/LangGraph unless stateful control flow becomes demonstrably difficult to maintain.

## 5. Core domain records

- **User:** UUID, normalized unique email, nullable password hash for Google-only accounts, timestamps and status.
- **OAuth identity:** provider + provider subject unique; linked to local user only after secure verification/account-linking.
- **Refresh session:** user, hashed refresh token or secure session identifier, expiry, rotation/revocation and reuse-detection metadata.
- **KnowledgeBase:** owner user, name and timestamps.
- **Document:** exactly one `knowledge_base_id`, display name, content hash, opaque object key, byte/page size, privacy label, lifecycle status, parser/chunker/index versions and timestamps.
- **Page:** document, physical page index, dimensions, rotation and crop metadata.
- **Block:** page, type, text/structured payload, reading order, source type, extraction quality, parser ID, bounding box and coordinate-space ID.
- **Chunk:** document, ordered source block IDs, text, section path, token estimate, chunker version, source page-region references and content hash.
- **Embedding metadata:** chunk, provider/model identifier, dimensions, normalization/distance metric, input hash and index/config version.
- **Citation:** document/chunk references, evidence span, page/region references and validation status.
- **Query/trace:** KB and query-time eligible-document snapshot, selected scope, candidate/evidence IDs and scores, model/prompt versions, answer status, citations, abstention reason, stage timings and errors.
- **Audit event:** actor if known, event type, resource type/ID, timestamp and limited safe metadata. Never store secrets, signed URLs, document contents or raw prompts.

## 6. PDF coordinates and provenance

- Preserve parser-native coordinates and normalize to one documented canonical convention.
- Store page dimensions, rotation, crop box and coordinate-space identifier.
- A chunk may span multiple blocks, pages and bounding boxes; never assume one chunk equals one page or one rectangle.
- Convert canonical coordinates to PDF.js viewport coordinates in one tested adapter.
- If coordinates are missing or unreliable, show a page-level citation rather than inventing a highlight.
- Test rotation, crop, scaling, coordinate origins and page-size variations.

## 7. Ingestion pipeline

`Create/select KB -> Upload -> Fast Container Streaming Validation in FastAPI -> Store original object -> Persist document/job in PostgreSQL (with compensating object delete on DB commit failure) -> Enqueue Celery task with job_id only -> Worker atomic claim with fencing token and lease -> Parse -> Normalize -> Persist pages/blocks -> Structure-aware chunk -> Persist chunks -> Embed if cloud-allowed -> Persist vectors -> Maintain PostgreSQL full-text index -> Mark indexed only when all required stages complete`

Rules:
- FastAPI performs container-level validation while streaming into a bounded spool buffer (`SpooledTemporaryFile`), checking signature/magic bytes (`%PDF-`), MIME type (`application/pdf`), size limits (1 byte to 50 MB), filename sanitization, and SHA-256 hash. Heavy parsing, page counting, OCR, chunking, and embedding never run inside the upload request. Memory per upload is strictly bounded to prevent OOM on Render Free (512 MB).
- Structural/document validation (page count limit, encryption check, syntax corruption, parser timeouts) executes in the worker sandbox during extraction; failures are recorded as typed error codes.
- Upload consistency uses two-phase coordination: store object in storage, then commit Document (status `uploaded`) and IngestionJob (status `pending`) in PostgreSQL. If database commit fails, execute compensating storage deletion to eliminate orphaned objects.
- Each PDF has an independent job and outcome. One failure does not block others.
- Adding a PDF processes only that PDF; do not reprocess existing indexed PDFs.
- Deduplication is enforced via a partial unique index: `UNIQUE (knowledge_base_id, content_hash) WHERE deleted_at IS NULL`, allowing re-upload of previously deleted files while safely rejecting concurrent duplicate uploads with HTTP 409 Conflict.
- Celery task payloads contain ONLY `job_id: str` using JSON serialization (reject pickle). The worker resolves document ID, user ID, and object key directly from PostgreSQL upon claiming.
- PostgreSQL is the canonical source of truth for job lifecycle, stage checkpoints, attempts, heartbeats, and safe error information. Redis/Valkey transports ephemeral queue messages only.
- Strict lifecycle and checkpoint separation:
  - **Document status:** `uploaded`, `queued`, `processing`, `indexed`, `failed`, `cancelled`, `deleting`, `deleted`.
  - **IngestionJob status:** `pending`, `running`, `succeeded`, `failed`, `cancelled`.
  - **Job stage:** `extracting`, `ocr_processing`, `chunking`, `embedding`, `indexing`. (In Phase 3, the upload verification stage is reported truthfully as `storage_verification`).
  - **Stage checkpoints:** structured JSONB object recording per-stage status (`completed`, `failed`), start/finish timestamps, and metadata.
- Atomic job claiming with fencing tokens: `ingest_internal.worker_claim_job` assigns a unique `claim_token` (UUID) upon claim, updates status to `running`, records `worker_id`, increments `attempt_count`, and sets `lease_expires_at`. Only one worker can acquire a job, preventing duplicate processing.
- Fencing enforcement and lease authorization: all subsequent worker operations (`worker_heartbeat`, `worker_checkpoint_stage`, `worker_complete_job`, `worker_fail_job`) require matching `claim_token`, valid unexpired lease (`lease_expires_at >= clock_timestamp()`), and verify `documents.deleted_at IS NULL` atomically. An expired lease immediately rejects mutations even before another worker reclaims the job. Stale workers whose lease expired or whose document was cancelled/deleting receive `FALSE` and halt immediately.
- Consistent parent-first row-locking order: worker, reconciliation, and deletion transactions must always lock parent `documents` first (`FOR UPDATE OF d`), then child `ingestion_jobs` to eliminate database deadlocks. If a document is deleting, deleted, or cancelled, worker operations immediately reject mutations without partial state changes.
- Failure atomicity and retry semantics:
  - **Retryable vs. terminal failure:** Transient infrastructure errors (temporary storage timeouts, network blips) are not failed immediately by the worker; the worker task exits, its lease expires, and reconciliation redispatches the job if attempts remain. Terminal errors (unsupported/corrupted PDF syntax, missing storage object, max attempts reached) invoke `ingest_internal.worker_fail_job`, which atomically locks the parent document first, sets document status to `failed`, sets job status to `failed` with typed error code/message, and terminates execution.
  - **Retry exhaustion:** If `attempt_count >= max_attempts`, reconciliation transitions both abandoned `running` jobs and stuck `pending` jobs to terminal `failed` status (`error_code = 'max_attempts_exceeded'`), cascading document status to `failed` and preventing infinite worker crash loops.
- Dual-case reconciliation (`reconcile_jobs`): discovers both stuck `pending` jobs (un-dispatched or lost on broker wipe) and abandoned `running` jobs (worker OOM or expired heartbeat). For retryable jobs (`attempt_count < max_attempts`), reconciliation resets `status = 'pending'`, clears `worker_id`, `claim_token`, and `lease_expires_at`, updates `enqueued_at = clock_timestamp()`, and re-dispatches `ingest_document(job_id)`. Jobs whose documents are deleting or deleted are cancelled immediately. Concurrent reconciliation runs are protected by PostgreSQL transaction advisory locks (`pg_try_advisory_xact_lock`).
- Phase 3 worker stub boundary: the Phase 3 stub verifies storage object presence, checkpoints stage as `storage_verification`, and leaves the document status truthfully in `uploaded`. A document is NEVER marked `indexed` or `processing` in Phase 3; extraction is strictly Phase 4, and search indexing is strictly Phase 6.
- Document availability is atomic: searchable only after all required MVP ingestion/indexing stages succeed. Partial states are explicit.
- `local-only` documents can be parsed, viewed and searched lexically without hosted model calls. They are not eligible for Gemini embedding or AI answer generation.
- `cloud-allowed` documents may use Gemini-powered RAG, subject to EgressGate.

## 8. Query pipeline

### 8.1 Scope, retrieval and sequencing

`Question -> Authenticate/authorize -> Resolve KB + selected scope -> Snapshot eligible indexed document IDs -> Enforce privacy/mode -> Query embedding when cloud-allowed -> PostgreSQL full-text retrieval + pgvector dense retrieval -> RRF fusion -> optional measured reranking -> Context assembly -> Answerability check -> Gemini generation -> Deterministic citation/source validation -> Gemini semantic claim/evidence verification -> Grounded answer or abstention`

- Default scope is all eligible indexed documents in one selected KB. Users can restrict scope to selected indexed PDFs.
- Resolve eligible document IDs at query start. Use the same snapshot for retrieval, context assembly and citation validation, even if ingestion completes mid-query.
- PostgreSQL full-text search is the lexical path; use ranking such as `ts_rank`/`ts_rank_cd`. Do not call it BM25.
- Baseline retrieval compares lexical-only, dense-only and hybrid. Initially retrieve up to 20 lexical and 20 dense candidates, fuse with Reciprocal Rank Fusion (RRF), then tune candidate and evidence counts on held-out evaluation.
- **Reranking is not assumed to help.** First establish the FTS + pgvector + RRF hybrid baseline. Add Gemini Flash-based relevance scoring only if a held-out ablation demonstrates enough quality improvement to justify its extra API call, latency and quota. Keep the hybrid baseline available for comparison and fallback. This is a model-based relevance scorer, not a dedicated cross-encoder.
- Initial final evidence size is approximately 5–8 chunks, tuned through evaluation.
- Use one consistent embedding model for corpus chunks and query vectors. Store model identifier and dimensions with index configuration. Do not mix incompatible vector spaces.
- Exact vector search is the correctness baseline. Add HNSW only if measured latency requires it and recall remains acceptable. Skip IVFFlat initially.
- Token counts: use official Gemini token-counting functionality where supported; use a lightweight local estimate for chunking/context planning. Do not assume `tiktoken` exactly counts Gemini tokens.
- Chunking begins with a provisional 500–700-token target, 80–100 overlap and meaningful structural boundaries; benchmark and tune rather than treating these as immutable.

### 8.2 Gemini calls and known cost exposure

A cloud-allowed question can trigger multiple Gemini API calls. A typical fully enabled path may use query embedding, reranking (if enabled), answer generation and semantic verification. A corrective attempt may add more embedding/retrieval/reranking/generation/verification calls depending on where failure occurs. Therefore one user question does **not** equal one model API call: four calls are possible on the reranking-enabled path, and a corrective attempt can make it five or more.

This is an accepted controlled-MVP limitation, not a hidden assumption. There is no dedicated BudgetGuard, per-user/per-KB budget system, global usage dashboard or alerting in MVP. Keep normal provider quota handling, 429 handling, timeouts and bounded retries. Never retry repeatedly or silently switch providers. Revisit budget controls if usage grows beyond a controlled portfolio/single-owner deployment.

### 8.3 Verification and abstention

- Deterministic checks cover ownership, KB scope, query snapshot, document/chunk existence, page validity, provenance and citation integrity.
- Gemini semantic verification assesses whether material answer claims are supported by cited evidence. An LLM judge is imperfect; evaluate it against human-reviewed examples.
- Permit **one corrective retrieval attempt maximum**, with bounded query rewrite/expansion and the original scope snapshot. No infinite loops.
- **MVP abstention is answer-level:** if any material claim fails verification after the one corrective attempt, withhold the entire generated answer and return a clear abstention message or evidence-only display.
- Claim-level filtering (return supported claims while removing unsupported ones) is a later Milestone 3 improvement, not MVP behavior.
- If verification is unavailable, do not label an answer verified; use controlled abstention/evidence-only behavior.
- Never turn API failure, quota exhaustion or unsupported evidence into a confident answer.

### 8.4 Privacy modes

- **Local Evidence Mode (LEM):** no document-derived content is sent to Gemini. PDF viewing, metadata and PostgreSQL full-text evidence are available. No semantic embeddings, hosted reranking, Gemini generation or Gemini verification. Do not call this fully offline; it is local-evidence-capable with API-dependent AI features.
- **API-Enabled AI Mode (AIM):** requires explicit `cloud-allowed` label and EgressGate approval for every outbound request. Gemini embeddings, optional measured reranking, generation and verification may run.

## 9. Authentication and multi-tenant isolation

- Build authentication inside DocForge. No Supabase Auth, Firebase Auth, Clerk, Auth0 or managed auth product.
- Support email/password and Google OAuth 2.0 / OpenID Connect.
- Hash passwords with Argon2id using `argon2-cffi`; never bcrypt or plaintext. Store the encoded hash; use library-generated salts; support rehash on parameter upgrades. Benchmark parameters on deployment hardware and bound concurrent hashing.
- Google-only accounts have a nullable password hash.
- DocForge issues short-lived access JWT and refresh JWT after either login method. Both are Secure, HttpOnly cookies; never localStorage/sessionStorage.
- Refresh tokens rotate; store only hashed refresh tokens or secure session identifiers in PostgreSQL; detect reuse and revoke token family/session. Logout revokes the server-side session and clears cookies.
- Validate JWT signature, algorithm allowlist, expiry, issuer, audience and claims. Exact signing/key rotation, token lifetimes and cookie settings must be finalized before implementation.
- Cookie auth requires CSRF protection. CORS uses explicit frontend origins with credentials; never wildcard credentialed CORS. Choose SameSite/domain/path for actual deployed domains.
- Google Authorization Code/OIDC uses state and PKCE where supported/appropriate. Verify Google ID token signature, issuer, audience, expiry, nonce where used and verified email with a vetted library. Client secret stays backend-only.
- Do not automatically merge accounts solely because email strings match; use secure account-linking rules.
- FastAPI derives identity from verified token; never trust frontend-supplied user IDs.
- Use **both application-level authorization and PostgreSQL RLS** on user-owned tables. Set transaction-scoped user context (`SET LOCAL`/`set_config(..., true)`) to avoid pooled-connection leakage. App DB role must not be superuser or `BYPASSRLS`; use a separate migration role and `FORCE ROW LEVEL SECURITY` where appropriate.
- Worker authorization resolves owner/permissions from trusted PostgreSQL records, not arbitrary task payload fields.
- Test cross-user access to KBs, documents, chunks, vector search, citations, jobs and object URLs; test connection reuse and worker context.
- Password reset and email verification are required before treating public account flows as production-ready; exact email provider is a later explicit decision.

## 10. Object access, privacy and EgressGate

- Original PDFs are private by default in object storage.
- Backend checks authentication and document ownership before issuing a short-lived signed URL. PDF.js accesses the object directly; FastAPI does not proxy every PDF byte.
- Signed URLs are temporary bearer credentials. Start with a short expiry (5 minutes default), configure `ResponseCacheControl='no-store, private'` on the presigned GET request parameters so storage endpoints serve anti-caching headers directly to the browser, do not log signed URLs, and refresh after expiry.
- Verify provider support for private access, signed URLs, HTTP Range requests, CORS and PDF.js before implementation. If Neon fails a required check, use the already-verified R2 fallback.
- Privacy labels: `local-only` by default; `cloud-allowed` only after explicit user choice. Derived chunks/artifacts inherit the most restrictive source label.
- EgressGate is the sole enforcement point for every Gemini request containing question/document-derived content. Check label, operation, provider allowlist and payload policy.
- Local-only content must never be sent to Gemini, including embeddings, reranking, generation, verification or evaluation judging.
- Automatic PII detection/redaction and enterprise DLP are out of MVP. Do not claim automatic PII protection. Explain cloud processing and provider data handling clearly to users.
- Treat PDF content as untrusted input; defend against prompt injection. Never follow instructions found inside retrieved documents as system/developer instructions.
- Enforce strict upload validation boundaries: fast streaming container checks in FastAPI (magic bytes `%PDF-`, MIME type `application/pdf`, size limits, safe filename sanitization, SHA-256 hash) bounded by a 5 MB spool buffer; structural and document checks in the worker (page count, encryption detection, syntax corruption, parser timeouts). Signature validation checks container format only and does not verify internal PDF syntax integrity.
- Use fully opaque, server-generated object keys with random 128-bit UUIDs (`objects/{uuid4().hex[:2]}/{uuid4().hex}.pdf`); never include document IDs, user IDs, or original filenames in storage object paths.
- Database catalog ownership integrity: enforce a composite foreign key `(knowledge_base_id, user_id) REFERENCES public.knowledge_bases(id, user_id)` on both `public.documents` and `public.upload_intents`, guaranteeing at the database level that a document or upload intent's user_id matches the KB owner.
- Storage orphan recovery: PostgreSQL-backed `upload_intents` protocol records pending uploads with heartbeat lease renewals before and during streaming to storage. Upon DB commit or compensating delete, the intent is cleared. A periodic paginated cleaner uses a restricted cross-tenant maintenance gateway (`maintenance_inspect_storage_keys`) to safely cross-check storage keys older than 2 hours against committed documents and active upload intents, safely purging unreferenced orphan objects without risking active uploads.
- Logs and audit records must not contain passwords, tokens, signed URLs, document text or sensitive prompts.

## 11. Jobs, deployment and operational boundaries

- Free-first target: Vercel Hobby frontend; Render Free Web Service with FastAPI and Celery as separate processes in the same service; Render Key Value/Valkey as broker; Neon PostgreSQL; verified Neon Object Storage or R2; Gemini API.
- Verify current Render free-service behavior, sleep/restart limits, memory/CPU, Valkey compatibility/connections/persistence, Neon plan limits, object-storage pricing and region before launch.
- Render Free may sleep/restart; ingestion may pause or be delayed. Valkey free storage may be non-persistent. PostgreSQL remains canonical and reconciliation recovers eligible work.
- Database role separation: introduce dedicated restricted database roles `docforge_worker` and `docforge_operator`. The API role (`docforge_app`) receives table grants for upload creation and metadata queries (column-restricted UPDATE on `display_name` only; NO direct UPDATE on `status` or `deleted_at`), and executes deletion initiation strictly via `ingest_internal.api_begin_document_deletion`. The worker role (`docforge_worker`) interacts with the database 100% exclusively through `ingest_internal` SECURITY DEFINER gateway functions (with fixed `search_path = pg_catalog, public, pg_temp`) and has ZERO direct table grants on any table in `public`. Function owner `docforge_definer` holds `BYPASSRLS` and minimal required table grants (`SELECT, INSERT, UPDATE` on documents/jobs; `SELECT, UPDATE, DELETE` on upload_intents) to mediate cross-tenant gateway operations under `FORCE ROW LEVEL SECURITY`. Administrative recovery of exhausted cleanups is granted exclusively to `docforge_operator` via `ingest_internal.operator_retry_cleanup`. `CREATE` on schema `public` is revoked from `PUBLIC` and all runtime roles to prevent search path shadowing.
- Resource contention: embedding batches and parsing in the shared Render instance can compete with FastAPI for CPU/memory and increase API latency. Bound worker concurrency/batches and measure; split services only if limits or measurements require it.
- Do not promise production-grade uptime or always-on ingestion on free tiers. Public deployment is portfolio-grade with limitations disclosed.
- Add basic rate limits for login/password reset, uploads and question-answering; enforce request/PDF size, page and processing-time limits. Return clear 429 responses.
- Structured JSON logs, request IDs, job IDs, per-stage latency, errors, queue depth and provider-call/token metadata where available are sufficient initially. No Prometheus/Grafana/OpenTelemetry infrastructure unless measurements justify it.
- GitHub Actions runs lint/type checks, tests, migration checks and production builds. Deploy only after required checks pass.
- Use Alembic migrations; review scripts; test fresh and existing databases; backup before risky production migrations. Test restore of both database and object files before public launch.
- Deletion protocol: Two-phase deletion. The API initiates deletion atomically via `ingest_internal.api_begin_document_deletion(document_id)` which derives authenticated identity from the transaction-scoped `app.current_user_id` context, sets `deleted_at = clock_timestamp()` and `status = 'deleting'` and cancels active jobs (clearing worker ownership and lease metadata: `worker_id = NULL, claim_token = NULL, lease_expires_at = NULL`), then dispatches an asynchronous cleanup task `cleanup_deleted_document(document_id: str)`. The worker acquires an exclusive durable cleanup claim (`cleanup_claim_token`, `cleanup_lease_expires_at`) via `ingest_internal.worker_claim_cleanup_task`, deletes the object from storage, verifies deletion, deletes derived database records, and marks `status = 'deleted'` via `ingest_internal.worker_finalize_document_deletion` requiring valid cleanup ownership and clearing lease tokens. Interrupted or crashed cleanups are discovered via gateway `ingest_internal.reconcile_cleanup_candidates` and recovered safely by reconciliation; cleanups failing 5 attempts (either via worker-reported failure or via worker crash with lease expiration after the 5th attempt) transition document status to `failed` (`cleanup_error_code = 'cleanup_exhausted'`) with persisted error details, clearing cleanup metadata and preventing attempt 6 from ever being granted, recoverable exclusively via `ingest_internal.operator_retry_cleanup`. Completed and failed ingestion job records are retained for 30 days for operational audit before automated pruning.
- Minimal audit events cover login success/failure, authorization failures, important document/KB deletion, password changes and session revocation. Skip clickstream/activity analytics and separate audit infrastructure.
- Accessibility target: WCAG 2.2 AA principles for main workflows; do not claim certification without an audit.

## 12. Decision Register

This is the authoritative record of accepted decisions and supersedes contradictory historical notes in earlier drafts.

| ID | Decision | Accepted direction |
|---|---|---|
| D-01 | Password hashing | Argon2id via `argon2-cffi`; no bcrypt |
| D-02 | Permanent PDF storage | Neon Object Storage if required checks pass; R2 fallback verified before Phase 2 storage gate |
| D-03 | Deployment | Vercel + Render API/worker same service + Render Key Value/Valkey + Neon + object storage + Gemini; verify current limits |
| D-04 | Retrieval | PostgreSQL full-text + pgvector + RRF baseline; Gemini reranking only after held-out ablation proves value |
| D-05 | Verification | Deterministic source/citation checks + Gemini semantic verification |
| D-06 | Corrective retrieval | One bounded corrective attempt maximum |
| D-07 | Abstention | Answer-level strict abstention in MVP; claim-level filtering later |
| D-08 | Tenant isolation | Application authorization + PostgreSQL RLS |
| D-09 | BudgetGuard | No dedicated BudgetGuard; normal quota/429 handling only |
| D-10 | AI provider | Gemini only initially; no automatic OpenAI/local fallback |
| D-11 | PDF access | Backend-authorized short-lived signed URLs; PDF.js direct object access |
| D-12 | Audit | Minimal security/resource-change audit events |
| D-13 | PII | No automatic PII detection/redaction; EgressGate and explicit privacy labels |
| D-14 | Embedding upgrades | One consistent active model; record model/dimensions; explicit full re-embedding if changed |
| D-15 | Rate limiting | Basic login, upload and query limits; no elaborate quota platform |
| D-16 | Observability | Structured logs, IDs, per-stage latency, errors and RAG metrics |
| D-17 | CI/CD | GitHub Actions quality gates; deploy after checks pass |
| D-18 | Documentation | Exactly six core Markdown files; no ADR directory; this register lives here |
| D-19 | Document membership | One PDF belongs to exactly one KB in MVP |
| D-20 | Phase gates | Every phase has observable, testable acceptance criteria and dependencies |
| D-21 | Token counting | Gemini official counting where supported + lightweight local estimate |
| D-22 | Vector index | Exact baseline; HNSW only when benchmark justifies; no IVFFlat initially |
| D-23 | Migrations | Reviewed Alembic migrations, clean/existing DB tests and backup before risky changes |
| D-24 | Deletion/retention | Complete cleanup with tracked retries and documented retention |
| D-25 | Recovery | Verify database + object-storage restore manually before public launch |
| D-26 | Frontend tests/accessibility | Vitest + React Testing Library + Playwright; WCAG 2.2 AA principles |
| D-27 | Documentation workflow | Owner asks for a phase plan, then separately approves implementation, then may request a separate phase explanation file |
| D-28 | Phase numbering | Integer phases only: 0, 1, 2, 3…; no decimal/subphase identifiers |
| D-29 | PDF parser engine & licensing | Permissive licensing (Option B): adopted `pdfminer.six` (MIT) + `pypdf` (BSD-3-Clause); rejected PyMuPDF due to AGPL-3.0 copyleft obligations on MIT codebase |
| D-30 | Corpus reprocessing | One-time script executing `enqueue_document_parsing()` for Phase 3 corpus documents (Option A); no bulk schema backfill |
| D-31 | Canonical coordinate convention | PDF.js viewport coordinates with origin (0,0) at top-left; 4-corner transformation $T_\theta$ with CropBox offsets and rotation-dependent dimension swaps |
| D-32 | PDF parser safety & limits | Process isolation via CLI subprocess runner, bounded chunked stdout/stderr readers (64 KB stderr ceiling, 10-line batching), single fixed immutable `MAX_PDF_PAGES = 500` ceiling |
| D-33 | Active Gemini Embedding Model & SDK Pinning | Pinned `google-genai>=0.8.0,<4.0.0` (installed 3.3.0); adopted actively maintained `gemini-embedding-001` with MRL output dimensionality of 768; deprecated `text-embedding-004` and `google-generativeai` rejected |
| D-34 | Generational Ingestion Architecture | Multi-version `document_generations` table with monotonic integer indexing, active/staged/superseded status, and composite foreign keys `(document_id, user_id, generation_id)` ensuring atomic zero-downtime promotion and safe rollback |
| D-35 | Database-Authoritative EgressGate | Privacy classification resolved exclusively via database gateways; callers cannot bypass or override privacy labels; zero external egress for `local-only` documents; fail-closed execution |
| D-36 | Canonical Structure-Aware Chunking & Provenance | Structure-aware boundary accumulation (target 600, max 800 tokens); exact Unicode code-point offsets `[start_char, end_char)`; deterministic `\n\n` join; database-enforced text reconstruction and independent SHA-256 validation via `worker_insert_chunks_batch` |
| D-37 | Exact pgvector Cosine Search Baseline (No Vector Index) | Exact nearest-neighbor cosine distance (`<=>`) without vector index initially per D-22; sequential scan mathematical baseline; HNSW evaluated only if empirical benchmark demonstrates latency need |
| D-38 | Privacy-Authoritative Retrieval & Mixed-Scope Egress | Dense search evaluates `cloud-allowed` documents with live query-time revalidation (`d.privacy_label = 'cloud-allowed'`); local-only documents participate in lexical retrieval with zero cloud egress; query embedding requires mandatory fail-closed `IEgressGate` verification |
| D-39 | Reciprocal Rank Fusion ($k=60$) in Python Domain Layer | Deterministic RRF ($k=60$) in Python domain layer; pre-sorted and deduplicated candidate lists; deep non-mutation via `copy.deepcopy()`; dual-source signal provenance preserved |
| D-40 | Generated `tsvector STORED` Column with `websearch_to_tsquery` | Generated `text_search_vector` column on `chunks` with GIN index; native PostgreSQL `websearch_to_tsquery` parser; migration 0005 checks definitions and tracks object provenance via `managed_by:0005_retrieval_indexes` |
| D-41 | Question-Aware Multi-Evidence Mapping with Ordered Anchors | Prevents cross-question evidence contamination by scoping mapping strictly to evaluated `question_id`; maps chunks to gold passages via ordered anchor segment matching within single chunks |
| D-42 | Primary Generation Model & Provider Terms | Adopt `gemini-3.8-flash` as primary GA generation and verification model; provider terms explicitly disclosed: free tier data subject to human review/product training; paid tier enterprise confidential; pre-flight verification gate mandatory |
| D-43 | Canonical Segment-Based Answer Architecture | Eliminate independent free-form answer fields; model outputs ordered sequence of typed `AnswerSegment` objects (`FACTUAL` vs `STRUCTURAL`); final answer assembled strictly from verified factual segments; uncited factual segments rejected |
| D-44 | Layered Prompt Injection Defense | Structured SDK Content Parts (`types.Part`) isolating trusted framing from untrusted evidence, contextual escaping (`escape_evidence_text`), explicit `tools=[]` configuration, downstream deterministic snapshot validation, and semantic verification |
| D-45 | Strict 4-Level Identifier & Scope Validation | Citations explicitly reference `chunk_id` via `[chunk:<chunk_uuid>]`; validation enforces: (1) chunk $\in$ evidence, (2) generation $\in$ snapshot, (3) document $\in$ snapshot, (4) KB/user ownership; hard security failures immediately abstain without retry |
| D-46 | Conservative Calibrated AnswerabilityGate | Fast-reject triage filter calibrated on `tuning_questions.json` ($\tau_{\text{noise}} = 0.25$); drops queries where all signals indicate total noise; preserves potentially answerable queries for model grounding; never tuned on locked split |
| D-47 | Strictly Bounded Corrective Retrieval & Global Budget | Exactly one corrective retrieval attempt for evidence insufficiency; preserves immutable query snapshot; newly retrieved chunks validated against snapshot and deduplicated; global budget $\le 60.0\text{s}$ deadline and $\le 6$ total provider calls |
| D-48 | Strict 1:1 Claim Semantic Verification & Conservative Abstention | Verifier evaluates each material claim individually against cited chunk texts (`SUPPORTED`, `UNSUPPORTED`, `UNCERTAIN`); `UNCERTAIN` treated conservatively as unsupported; strict answer-level abstention if any material claim fails |
| D-62 | Mathematical Coordinate Normalization & Multi-Region Citations | Store all citation bounding boxes in normalized $[0, 1] \times [0, 1]$ relative to unrotated CropBox; multi-region boxes in `citation_regions` with IoU $\ge 0.85$ deduplication and reading-order sort; DPR canvas scaling with CSS layout overlays |
| D-63 | Relational Tenant Ownership & Composite Integrity Constraints | Direct PostgreSQL tenant boundaries via composite unique and foreign keys across `query_scope_documents`, `query_citations`, and `chunks` preventing cross-tenant scope injections |
| D-64 | Synchronous Terminal QueryResponse & Internal Lifecycle Decoupling | Strictly synchronous `POST .../queries` returning only terminal states (`answered`, `abstained`, `failed`); non-null `answer_status` and `total_latency_ms`; empty defaults for citations and local evidence |
| D-65 | Unified Idempotency State Machine, Execution-Mode Hashing & Atomic Acquisition | Canonical SHA-256 hash incorporating `execution_mode`, `knowledge_base_id`, query text, and scope; atomic zero-orphan candidate trace rollback on conflict; 24h key TTL; periodic 10m maintenance pruning |
| D-66 | Durable Privacy Concurrency via Durable State, Pub/Sub Acceleration & Pre-Commit Fencing | Durable Valkey key `docforge:privacy_revocation:<doc_id>`, Pub/Sub acceleration, streaming checks, socket severing, and mandatory pre-commit DB check; fail-closed abstention |
| D-67 | Resource-Bounded Killable PDF Parsing Subprocess & Explicit Cleanup | Validation executed in isolated child worker process group (`pdf_validator.py`); 15s timeout, 512 MB memory limit, process-group `SIGKILL` + `wait()` reaping, guaranteed `try...finally` spool cleanup |
| D-68 | Valkey Distributed Singleton Mutex for Celery Beat Scheduler | Subclassed `DocForgeBeatScheduler` with atomic Valkey mutex (`docforge:celerybeat:singleton_lock`, 15s TTL), 4s capped tick sleep, and dedicated heartbeat thread; non-owners skip task dispatch |
| D-69 | Strict Scope Document Deduplication, Empty Scope Rejection & Auditing Snapshots | `scope_document_ids=None` queries entire KB; `[]` rejected with HTTP 422; duplicate IDs deduplicated; immutable auditing snapshot (`is_eligible`, `exclusion_reason`, `privacy_label_snapshot`) in `query_scope_documents` |
| D-70 | Multi-Tenant Security Definer Maintenance Gateways & Terminal-Only Pruning | Retention and maintenance deletes isolated in `maintenance_internal` schema owned by `docforge_definer` with forced RLS and parameter bounds validation; pruning restricted strictly to terminal traces |
| D-71 | Race-Free Supervisor Process Lifecycle, Process Groups & Child Reaping | Supervisor registers signal handlers before spawning `uvicorn` and `celery` in process groups (`setsid`); graceful 10s SIGTERM escalation to SIGKILL; zombie child reaping via `waitpid` |
| D-72 | S3 Orphaned Upload Periodic Reconciliation | Hourly Celery Beat task `docforge.reconcile_orphaned_s3_objects` purging S3 upload objects older than 2 hours lacking committed document |
| D-73 | Complete Execution-Mode Matrix & Boundary Enforcement | Strict execution-mode matrix covering `auto`, `cloud_allowed`, `local_only`, and `partitioned`; local-only document contents never transmitted across the network |

## 13. Open verification gates

These are evidence checks, not undecided architecture choices:
- Neon Object Storage and Cloudflare R2: private access, signed URL behavior, HTTP Range, CORS, PDF.js compatibility, limits, pricing and region; both verified before storage implementation.
- Render: current free-service sleep/restart behavior, resource limits, Valkey compatibility and connection/persistence limits.
- Neon PostgreSQL: pgvector availability, plan limits, backup/restore capabilities and region.
- Gemini: exact model IDs, embedding dimensions, supported token-count endpoint, quota, price, latency and data-handling terms.
- Gemini reranking: supported model behavior, free quota/price, latency and held-out relevance quality before enabling.
- Dependency licenses, parser safety and deployment provider terms before adoption.
