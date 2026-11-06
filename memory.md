# DocForge — Project Memory

> **Purpose:** concise current state so a future Antigravity session can resume accurately. This is the live status file, not a duplicate architecture document. Never store secrets, private document content or personal data here.

## 1. Snapshot

DocForge is a publicly deployed, free-first, multi-user PDF RAG application. Users organize PDFs into knowledge bases, ask questions over a selected KB or selected documents, and receive grounded answers with citations to source documents/pages/regions. The core priority is retrieval quality, answer reliability, evaluation and latency—not infrastructure breadth.

## 2. Current project state

| Field | Current value |
|---|---|
| Implementation status | Phase 0 completed; awaiting owner review |
| Last completed implementation phase | Phase 0 — Project foundation and deployment feasibility |
| Next owner action | Review Phase 0 completion and approve Phase 1 implementation |
| Current phase | Phase 0 — Project foundation and deployment feasibility (Completed) |
| Approved core docs | `architecture.md`, `design.md`, `memory.md`, `phases.md`, `prd.md`, `rules.md` |
| Phase numbering | Integer only: 0, 1, 2, 3…; no decimal/subphase IDs |
| ADR policy | No ADR directory or ADR files; accepted decisions live in `architecture.md` Decision Register |
| Phase explanation | `PHASE_0_NOTES.md` created on owner request |
| Latest tag | None |
| Active branch | `phase-0-foundation` |
| Blockers | None; ready for Phase 1 corpus selection |

## 3. Environment and corpus

| Item | Status |
|---|---|
| OS | Microsoft Windows 11 Pro (10.0.26300) |
| CPU | Intel(R) Core(TM) i7-10610U @ 1.80GHz (4 physical cores, 8 logical processors) |
| RAM | 15.78 GB total (~5.9 GB available during Phase 0 baseline) |
| GPU | Intel(R) UHD Graphics (integrated) |
| Disk | 198.91 GB total (38.2 GB free) |
| Python / Pip | Python 3.11.9 (`.venv`), Pip 24.0 |
| Node.js / NPM | Node.js v24.3.0, npm 11.4.2 |
| Git | Git 2.50.1.windows.1 |
| Public evaluation corpus | Not selected; scheduled for Phase 1 |
| Evaluation question set | Not created; scheduled for Phase 1 |
| Tuning/locked split | Not created; scheduled for Phase 1 |
| Baseline metrics | None; no retrieval metrics measured yet |
| Deployment provider verification | Verified 2026-11-06 (Neon, Render, R2, Vercel, Gemini) |

## 4. Standing constraints

1. Public deployment is the target. Security, privacy, reliability and safe failure are required even on free tiers.
2. Free-first; no mandatory paid service/API. Verify current free quotas and limits before implementation/deployment.
3. Gemini is the only configured AI provider initially. No automatic OpenAI fallback and no local AI models.
4. New documents default to `local-only`; Gemini use requires explicit `cloud-allowed` consent enforced by EgressGate.
5. Local Evidence Mode provides PDF viewing, metadata and PostgreSQL full-text evidence only; it does not provide Gemini embeddings, semantic retrieval, generation or verification.
6. One PDF belongs to exactly one KB in MVP. Same PDF uploaded to another KB creates an independent document/ingestion.
7. Query scope is one KB or selected docs in that KB; no cross-KB search in MVP.
8. PostgreSQL is canonical job/document state; Redis/Valkey is queue transport only.
9. FastAPI and Celery are separate processes in one Render service initially; resource contention and free-tier sleep/restarts are accepted, documented limitations.
10. No dedicated BudgetGuard; keep normal 429/quota handling and bounded retries.
11. Reranking only if held-out ablation shows enough benefit over hybrid RRF to justify latency/API use.
12. MVP answer-level strict abstention after at most one corrective retrieval attempt; claim-level filtering is later.
13. Exactly six core Markdown files; no ADR folder/template or extra permanent specification file.
14. Owner requests a plan, separately approves implementation, then may request a separate phase explanation file.
15. One integer-numbered phase at a time; no decimal/subphase identifiers.

## 5. Accepted decisions

The authoritative details are in `architecture.md` → `## Decision Register`. High-level summary:

- Argon2id password hashing; email/password + Google OAuth; DocForge-issued access and refresh JWTs in Secure, HttpOnly cookies.
- Application authorization + PostgreSQL RLS.
- Neon Object Storage preferred if verified; Cloudflare R2 fallback must also be verified before storage implementation.
- Vercel frontend, Render FastAPI + Celery same service, Render Key Value/Valkey broker, Neon PostgreSQL and Gemini API, subject to current official verification.
- Private PDFs accessed by PDF.js through short-lived signed URLs after backend ownership check.
- PyMuPDF primary born-digital parser; evaluate Docling for complex layouts; OCR later.
- Structure-aware chunking and preserved page/block/bounding-box provenance.
- PostgreSQL full-text + pgvector + RRF baseline; exact vector search initially; HNSW only if benchmarks justify it.
- Gemini Flash-based relevance scoring/reranking is an evaluated option, not automatically active.
- Deterministic citation checks + Gemini semantic verification; one corrective attempt; answer-level abstention in MVP.
- Minimal security audit logging, basic API rate limits, structured logs and stage-level latency.
- Alembic migration discipline, deletion cleanup/retries, DB+object restore test, GitHub Actions, frontend tests and WCAG 2.2 AA principles.

## 6. Current phase tracker

All phases follow strict integer numbering. See `phases.md` for goals, work and acceptance criteria.

| Phase | Title | Status |
|---:|---|---|
| 0 | Project foundation and deployment feasibility | Done (Awaiting owner review) |
| 1 | Evaluation dataset and measurement harness | Planning / Not started |
| 2 | Database foundation, authentication and tenant isolation | Not started |
| 3 | Secure PDF storage, upload and ingestion jobs | Not started |
| 4 | PDF parsing, layout and provenance | Not started |
| 5 | Structure-aware chunking and embedding | Not started |
| 6 | Lexical, dense and hybrid retrieval baseline | Not started |
| 7 | Gemini generation, citations and privacy enforcement | Not started |
| 8 | API and core application experience | Not started |
| 9 | Retrieval optimization, reranking and verification | Not started |
| 10 | Tables, scanned PDFs and OCR | Not started |
| 11 | Deployment hardening, testing, CI/CD and recovery | Not started |
| 12 | Final evaluation, polish and portfolio release | Not started |

## 7. Provider verification and feasibility findings (Verified: 2026-11-06)

| Provider | Service / Role | Key Verified Capabilities & Limits | Fallback / Impact on Architecture |
|---|---|---|---|
| **Neon** | PostgreSQL + pgvector (Primary relational & vector DB) | 1 GB storage hard-cap per project, 100 CU-hrs compute/month. Autoscales to 2 CU (~8GB RAM), scale-to-zero after 5 min. `pgvector` fully supported on Free Tier. 6-hr PITR window, 10 branches/project. Egress: 5 GB/mo. | No fallback needed; 1GB storage is adequate for MVP text chunks and vectors. Bounded batch size required. |
| **Neon** | Object Storage (Evaluated primary) | S3-compatible API, requires `forcePathStyle: true`. Supports presigned URLs (`getSignedUrl`), HTTP `Range` requests (206 Partial Content), and CORS (`PutBucketCors`). Pricing: $0.023/GB-mo storage, metered egress. | Feasible, but Cloudflare R2 has a dedicated free tier (10 GB storage + zero egress). |
| **Cloudflare** | R2 Object Storage (Evaluated fallback / alternative) | S3-compatible API. 10 GB storage free/mo. 1M Class A ops (writes) free/mo. 10M Class B ops (reads/presigned GET/Range) free/mo. **Zero egress fees**. Presigned URLs and HTTP Range requests fully supported. | Strongest free-tier candidate for Phase 3 storage decision gate. Zero egress protects portfolio budget. |
| **Render** | Free Web Service (FastAPI + Celery) | 512 MB RAM, ~0.1 CPU, 750 free instance hours/month. Sleeps after 15 min idle; cold start takes 30–60s. | Both FastAPI & Celery share 512MB RAM. Concurrency strictly bounded to 1–2 workers to prevent OOM. |
| **Render** | Key Value / Valkey (Celery broker) | 25 MB max memory. In-memory ONLY — **NO persistence** (wiped on crash/restart/deploy). | Validates D-03: PostgreSQL MUST be canonical job state; Redis/Valkey carries queue messages only. Startup reconciliation recovers lost tasks. |
| **Vercel** | Hobby Plan (React Frontend Hosting) | 100 GB Fast Data Transfer/mo (hard cap). 100 deploys/day, 45 min build limit. Free custom domains. Global edge CDN. Non-commercial personal use. | Fully sufficient for static React/Vite SPA bundle. |
| **Google** | Gemini API (AI Embeddings, Generation, Verification) | Embedding model: `text-embedding-004` (768 dimensions, 3,000 max input tokens, official `countTokens` support). Generation: `gemini-2.0-flash`. Free tier: ~10–15 RPM, ~250k–1M TPM. Returns 429 on quota exhaustion. | **Critical privacy finding:** Free Tier inputs may be reviewed and used to train Google models; Paid Tier does NOT train on data. Directly validates DocForge's `local-only` default and strict EgressGate enforcement. |

## 8. Evaluation and dependency records

### Adopted Dependencies (Declared in `backend/pyproject.toml`)

| Package | Version constraint | Actual installed | License | Role / Justification |
|---|---|---|---|---|
| `pydantic` | `>=2.7.0` | `2.14.3` | MIT | Core data validation and schema definitions |
| `pydantic-settings` | `>=2.2.0` | `2.16.2` | MIT | Twelve-factor environment variable loading |
| `pytest` | `>=8.0.0` | `9.2.0` | MIT | Unit and regression test execution runner |
| `pytest-asyncio` | `>=0.23.0` | `1.4.1.post1` | Apache-2.0 | Async test execution support |
| `ruff` | `>=0.4.0` | `0.17.4` | MIT | Fast linter and code formatter |

### Evaluation Metrics Baseline

No evaluation dataset exists yet (scheduled for Phase 1).

## 9. Session log

| Date | Work completed | Next action |
|---|---|---|
| 2026-11-06 | Consolidated prior project specifications with owner-approved architecture review; clarified multi-call Gemini cost exposure, measured reranking, answer-level MVP abstention, integer-only phase numbering and owner-controlled plan/implement/explanation workflow. | Completed Phase 0 implementation |
| 2026-11-06 | Implemented Phase 0: Collected hardware & runtime environment; initialized git on branch `phase-0-foundation`; created `.gitignore`, `.env.example`, `backend/pyproject.toml` (single source of truth), clean package structure (`domain`, `adapters`, `api`, `workers`, `config`), `pydantic-settings` configuration, structured JSON logging, and 4/4 passing unit tests; scaffolded Vite React TS frontend; verified all 5 external providers (Neon, Render, R2, Vercel, Gemini) against live official documentation; authored beginner-friendly `PHASE_0_NOTES.md`. | Owner review of Phase 0 and approval to start Phase 1 |
