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
- PyMuPDF as the primary born-digital PDF parser, subject to license review.
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

`Create/select KB -> Upload -> Validate each PDF -> Assign document ID and privacy label -> Store original object -> Persist document/job in PostgreSQL -> Enqueue identifiers-only Celery task -> Parse -> Normalize -> Persist pages/blocks -> Structure-aware chunk -> Persist chunks -> Embed if cloud-allowed -> Persist vectors -> Maintain PostgreSQL full-text index -> Mark indexed only when all required stages complete`

Rules:
- FastAPI validates and persists upload/job records, enqueues work and returns promptly. Long parsing/OCR/chunking/embedding never runs inside the upload request.
- Each PDF has an independent job and outcome. One failure does not block others.
- Adding a PDF processes only that PDF; do not reprocess existing indexed PDFs.
- Celery task payloads contain identifiers and minimal routing metadata, never raw PDF bytes or large extracted text.
- PostgreSQL persists job state, stage checkpoints, counters, attempts, heartbeat, timestamps and safe error information.
- Redis/Valkey carries queue messages only. Reconciliation re-enqueues eligible stale/incomplete jobs after broker/worker restarts.
- Use bounded concurrency, timeouts, retries and idempotent writes. Use content hashes, stable IDs and uniqueness constraints to prevent duplicate chunks/vectors.
- Document availability is atomic: searchable only after all required MVP ingestion/indexing stages succeed. Partial states are explicit.
- Suggested states: `uploaded`, `queued`, `extracting`, `ocr_processing`, `chunking`, `embedding`, `indexing`, `indexed`, `failed`, `cancelled`.
- Show truthful progress counters; never fabricate a percentage when total work is unknown.
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
- Signed URLs are temporary bearer credentials. Start with a short expiry (for example, five minutes), do not log them, and refresh after expiry.
- Verify provider support for private access, signed URLs, HTTP Range requests, CORS and PDF.js before implementation. If Neon fails a required check, use the already-verified R2 fallback.
- Privacy labels: `local-only` by default; `cloud-allowed` only after explicit user choice. Derived chunks/artifacts inherit the most restrictive source label.
- EgressGate is the sole enforcement point for every Gemini request containing question/document-derived content. Check label, operation, provider allowlist and payload policy.
- Local-only content must never be sent to Gemini, including embeddings, reranking, generation, verification or evaluation judging.
- Automatic PII detection/redaction and enterprise DLP are out of MVP. Do not claim automatic PII protection. Explain cloud processing and provider data handling clearly to users.
- Treat PDF content as untrusted input; defend against prompt injection. Never follow instructions found inside retrieved documents as system/developer instructions.
- Validate file signatures, MIME type, size, page count, encryption and parser resource limits. Use generated opaque object keys; never trust user paths.
- Logs must not contain passwords, tokens, signed URLs, document text or sensitive prompts.

## 11. Jobs, deployment and operational boundaries

- Free-first target: Vercel Hobby frontend; Render Free Web Service with FastAPI and Celery as separate processes in the same service; Render Key Value/Valkey as broker; Neon PostgreSQL; verified Neon Object Storage or R2; Gemini API.
- Verify current Render free-service behavior, sleep/restart limits, memory/CPU, Valkey compatibility/connections/persistence, Neon plan limits, object-storage pricing and region before launch.
- Render Free may sleep/restart; ingestion may pause or be delayed. Valkey free storage may be non-persistent. PostgreSQL remains canonical and reconciliation recovers eligible work.
- Resource contention: embedding batches and parsing in the shared Render instance can compete with FastAPI for CPU/memory and increase API latency. Bound worker concurrency/batches and measure; split services only if limits or measurements require it.
- Do not promise production-grade uptime or always-on ingestion on free tiers. Public deployment is portfolio-grade with limitations disclosed.
- Add basic rate limits for login/password reset, uploads and question-answering; enforce request/PDF size, page and processing-time limits. Return clear 429 responses.
- Structured JSON logs, request IDs, job IDs, per-stage latency, errors, queue depth and provider-call/token metadata where available are sufficient initially. No Prometheus/Grafana/OpenTelemetry infrastructure unless measurements justify it.
- GitHub Actions runs lint/type checks, tests, migration checks and production builds. Deploy only after required checks pass.
- Use Alembic migrations; review scripts; test fresh and existing databases; backup before risky production migrations. Test restore of both database and object files before public launch.
- Deletion removes source PDF, derived artifacts, page/block/chunk records, embeddings, full-text entries, caches and related records. Track incomplete cleanup and retry; never claim deletion complete while required copies remain. Define retention for query history, audit events, logs and backups.
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

## 13. Open verification gates

These are evidence checks, not undecided architecture choices:
- Neon Object Storage and Cloudflare R2: private access, signed URL behavior, HTTP Range, CORS, PDF.js compatibility, limits, pricing and region; both verified before storage implementation.
- Render: current free-service sleep/restart behavior, resource limits, Valkey compatibility and connection/persistence limits.
- Neon PostgreSQL: pgvector availability, plan limits, backup/restore capabilities and region.
- Gemini: exact model IDs, embedding dimensions, supported token-count endpoint, quota, price, latency and data-handling terms.
- Gemini reranking: supported model behavior, free quota/price, latency and held-out relevance quality before enabling.
- Dependency licenses, parser safety and deployment provider terms before adoption.
