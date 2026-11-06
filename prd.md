# DocForge — Product Requirements Document

> **Purpose:** Defines WHAT DocForge does, who it serves, its scope and how success is measured. Architecture lives in `architecture.md`; user experience in `design.md`; implementation order in `phases.md`.
>
> **Product direction:** publicly deployed, free-first, multi-user PDF RAG application. Strong RAG quality is the primary differentiator. No insecure shortcuts for free hosting.

## 1. Summary

DocForge lets users organize PDFs into knowledge bases, ask natural-language questions over a selected knowledge base or selected documents, and receive evidence-grounded answers with citations to the source document, page and region. Selecting a citation opens the PDF at the cited location. When evidence is insufficient or verification fails, DocForge abstains rather than inventing an answer.

DocForge is more than a basic “chat with PDF” interface because it preserves source provenance, evaluates retrieval and answer quality, verifies citations and exposes enough trace/latency information to improve the system scientifically.

## 2. Problem

Finding a specific fact in a long report is slow. Generic PDF chat systems can miss relevant passages, lose table/layout context, hallucinate unsupported details and provide citations that do not actually support their claims. Users need to inspect the source quickly and know when the system does not have enough evidence.

## 3. Goals and non-goals

### Goals
- G1: Grounded answers with document, page and source-region citations.
- G2: Honest answer-level abstention in MVP when material evidence is insufficient.
- G3: Multiple PDFs organized into multiple knowledge bases per user.
- G4: Query either the whole selected KB or a selected subset of its indexed documents.
- G5: Born-digital PDFs first; tables and scanned pages in a later milestone.
- G6: Secure public deployment with user isolation, private files and reliable ingestion/deletion.
- G7: Hybrid retrieval baseline and measured reranking, not complexity by assumption.
- G8: A repeatable evaluation dataset and metrics for retrieval, answer quality, citations, locations, abstention and reliability.
- G9: Owner understands every implementation phase well enough to explain it in an interview.

### MVP non-goals
- Knowledge Graph RAG, Kafka, Kubernetes, microservice sprawl or multi-region failover.
- Automatic PII detection/redaction or enterprise DLP.
- Cross-KB search, document sharing across KBs, or one document linked to multiple KBs.
- Automatic provider fallback or local AI models.
- Chart-number extraction or calculations over tables.
- Claim-level filtering of partially supported answers (later milestone).
- Elaborate BudgetGuard, usage dashboards, enterprise monitoring or compliance certification.
- Guaranteed always-on ingestion or production-grade uptime on free tiers.

## 4. Users and usage model

- **Primary users:** people who create an account and upload their own PDFs for research, study or work.
- **Reviewers:** interviewers/recruiters who inspect the public deployment, repository, architecture and evaluation evidence.
- Each user owns their own knowledge bases and documents. All operations are isolated by application authorization and PostgreSQL RLS.
- The product is publicly accessible, but initial expected usage is controlled portfolio/demo usage. Design for safe public access, not hypothetical enterprise traffic.

## 5. Scope and document support

### 5.1 Document tiers

| Tier | Content | Target milestone |
|---|---|---|
| Tier 1 | Born-digital PDFs: paragraphs, headings, lists, reading order, multi-column text and basic layout | MVP |
| Tier 2 | Harder tables and scanned pages with OCR and confidence/location metadata | Later milestone |
| Tier 3 | Figures/charts: detect and display region; explicitly state that values are not reliably interpreted | Later/stretch |

### 5.2 Question types

MVP: factual lookup, definitions, short explanations of a section, and unanswerable questions that must cause abstention. Cross-document reasoning within a selected KB is supported by the product scope, but the quality is bounded by retrieval evaluation and the evidence supplied. Table lookup and scanned-page questions are later milestones. Whole-document summaries, chart reading and calculations over tables are not MVP requirements.

### 5.3 Scope rules

- One query selects one KB. Search never crosses KB boundaries in MVP.
- Query scope is either all eligible indexed documents in that KB or an explicit subset.
- A document belongs to exactly one KB. Uploading the same PDF into another KB creates an independent record and ingestion job.
- Only fully indexed documents are searchable. In-progress/failed documents are clearly identified.
- Query-start snapshot of eligible indexed document IDs is fixed for retrieval and citation validation.
- English is the initial supported language.
- Maximum file size/page count must be set after provider and deployment verification; reject over-limit files with a clear message.

## 6. Functional requirements

Priority: **M** = MVP/public-release baseline; **S** = later milestone; **C** = conditional experiment.

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Register/login with email/password and Google sign-in; secure sessions and logout | M |
| FR-02 | Create, list, rename and delete owned knowledge bases | M |
| FR-03 | Upload multiple PDFs to a selected KB; validate file signature/type, size, page count, encryption and corruption | M |
| FR-04 | Ingest born-digital PDFs asynchronously with visible status and safe errors | M |
| FR-05 | Extract pages, blocks, reading order, headings/paragraphs/lists and source bounding boxes | M |
| FR-06 | Structure-aware chunking preserves page/block/region provenance | M |
| FR-07 | Generate Gemini embeddings only for cloud-allowed documents through EgressGate | M |
| FR-08 | Search selected KB or selected indexed documents; lexical, dense and hybrid baselines are measurable | M |
| FR-09 | RRF hybrid retrieval; Gemini reranking enabled only if held-out ablation proves value | M/S |
| FR-10 | Answer questions with source citations; citations resolve to document/page/region | M |
| FR-11 | Open PDF and navigate/highlight cited page/region | M |
| FR-12 | Answer-level strict abstention if material claim support fails after one corrective attempt | M |
| FR-13 | Deterministic citation/source checks and Gemini semantic verification | M for verified-answer release |
| FR-14 | One corrective retrieval attempt maximum | M for verified-answer release |
| FR-15 | Privacy labels (`local-only` default, explicit `cloud-allowed`) and EgressGate enforcement | M |
| FR-16 | Delete KB/document/account data with tracked physical cleanup and retries | M |
| FR-17 | Basic rate limits for auth, upload and query; file/request resource limits | M |
| FR-18 | Minimal security audit events | M |
| FR-19 | Per-query trace and per-stage latency/error information | M |
| FR-20 | One-command evaluation report with six metric families | M |
| FR-21 | Tables and scanned pages with OCR confidence and region provenance | S |
| FR-22 | Streaming answers and polished citation interactions | S |
| FR-23 | Claim-level filtering of supported claims | S (Milestone 3) |
| FR-24 | Chart region display with explicit interpretation limitation | S |
| FR-25 | Knowledge Graph experiment only if failure analysis justifies it | C |

## 7. Privacy modes and AI behavior

- New documents default to `local-only`.
- User must explicitly choose `cloud-allowed` before document-derived content can be sent to Gemini.
- Derived artifacts inherit the most restrictive source privacy label.
- **Local Evidence Mode:** PDF viewing, metadata and PostgreSQL full-text evidence are available without sending document-derived content to Gemini. No semantic embedding, Gemini reranking, Gemini generation or Gemini verification. Do not describe the product as fully offline.
- **API-Enabled AI Mode:** Gemini-powered embeddings/retrieval enhancements/generation/verification are available only after EgressGate approves each outbound request.
- Automatic PII detection/redaction is not included. UI must explain cloud processing and provider data handling without implying that PII has been detected or removed.
- If a selected scope contains documents that are not indexed, explain incomplete coverage. In-progress documents are not silently treated as searchable.

## 8. Non-functional requirements

| Area | Requirement |
|---|---|
| Security | Secure cookies, CSRF protection, explicit CORS, Argon2id, app authorization + RLS, private object storage, signed URL ownership checks |
| Privacy | Fail closed; one EgressGate; no local-only content leaves the system; no sensitive content/secrets in logs |
| Reliability | Durable PostgreSQL job state, idempotent tasks, bounded retries, atomic indexing, reconciliation after broker/worker restart |
| Performance | Measure end-to-end and per-stage p50/p95; tune using representative corpus; no unverified latency promise |
| Retrieval quality | Lexical-only, dense-only, hybrid and reranker ablations on same held-out data |
| Answer quality | Human-labelled correctness, citation support, abstention and false-abstention metrics |
| Modularity | Replaceable parser, embedding, storage, retrieval and generation adapters behind narrow interfaces |
| Maintainability | Type hints, migrations, focused modules, dependency/license review, reproducible configuration |
| Deployment | Public deployment with free-first services and documented sleep/quota/resource limitations |
| Accessibility | WCAG 2.2 AA principles for primary workflows; no compliance claim without audit |
| Learning | Each phase has a separate beginner-friendly explanation artifact when requested by the owner |

## 9. RAG evaluation and success metrics

Build a labelled evaluation set before implementing the real retrieval pipeline. Start with approximately 40–60 questions if corpus size permits; the final count depends on available public PDFs and labelling capacity. Include answerable and unanswerable questions, factual lookup, definitions, section explanation, table questions and later scanned-page questions. Store gold answer, evidence passage, page and region where applicable.

Maintain a tuning split and a locked test split. Do not tune against the locked set. Report counts with percentages, config hash, model IDs and date. Small sets are noisy; do not treat one- or two-point changes as meaningful without uncertainty/sample-size context.

| Metric family | Example measures | Initial target status |
|---|---|---|
| Retrieval quality | Recall@k, MRR, nDCG, rank of first gold passage | Provisional; set/freeze after baseline |
| Answer correctness | Human-labelled correct/partial/wrong | Provisional; set/freeze after baseline |
| Citation support | Supported citations / claims, citation correctness | Provisional; set/freeze after baseline |
| Location accuracy | Correct page, region overlap/IoU against gold boxes | Provisional; set/freeze after parser baseline |
| Abstention quality | Correct abstentions and false abstentions reported together | Provisional; set/freeze after baseline |
| Reliability/performance | hostile-file crashes, ingestion failures, p50/p95 stage and end-to-end latency | Set after representative tests and deployment measurements |

Every ablation changes one factor at a time on the same split and config. Reranking must demonstrate a held-out gain that justifies API calls, latency and quota before it becomes active. Semantic verifier quality must be compared with human review; an LLM judge is not ground truth.

## 10. Known limitations and explicit trade-offs

- A cloud-allowed query may trigger several Gemini API calls: query embedding, optional reranking, generation and semantic verification. One corrective attempt may trigger additional calls. A fully enabled normal path may therefore involve about four calls, and a corrective path five or more. One question is not one API call.
- There is no dedicated BudgetGuard, per-user/per-KB budgets, global usage dashboard or usage alerts in MVP. Normal 429/quota handling and bounded retries remain. Revisit budget controls if usage grows beyond controlled portfolio usage.
- Gemini is the only configured provider initially. No automatic OpenAI/local fallback.
- Local Evidence Mode does not provide Gemini-powered semantic retrieval or generation.
- Render Free may sleep/restart; same-service worker activity may delay API responses; ingestion may be delayed. Do not promise always-on or production-grade SLA on free tiers.
- Signed URLs are temporary bearer credentials; anyone holding a valid URL can access the file until expiry.
- No automatic PII detection/redaction. Users must understand cloud-processing consent.
- MVP strict abstention is answer-level: if any material claim remains unsupported after one corrective attempt, withhold the whole generated answer. Claim-level filtering is later.
- Exact free-tier limits, model IDs, pricing, API quotas and storage capabilities are time-sensitive verification gates.

## 11. Release gates

### Public MVP gate
- [ ] Account registration/login, Google login, secure session handling and logout work.
- [ ] User can create multiple KBs and upload multiple PDFs into a selected KB.
- [ ] Cross-user KB/document/chunk/query/citation/object access is denied by app checks and RLS.
- [ ] Private PDF access uses backend-authorized signed URLs and PDF.js Range loading works.
- [ ] Born-digital PDF ingestion is asynchronous, idempotent, recoverable and atomically searchable.
- [ ] PDF extraction preserves page/block/region provenance and visual overlay checks pass.
- [ ] Structure-aware chunks, embeddings and full-text index are queryable.
- [ ] Lexical-only, dense-only and hybrid RRF baselines are measured; reranking is only enabled if the ablation supports it.
- [ ] User can query one KB or selected indexed docs; no cross-KB leakage.
- [ ] Answers have validated citations and navigate to source pages/regions.
- [ ] Answer-level abstention works after at most one corrective attempt.
- [ ] EgressGate prevents any local-only content from reaching Gemini; canary/offline tests pass.
- [ ] Delete operations clean originals and derived records or visibly report/retry incomplete cleanup.
- [ ] Basic rate limits, upload limits, audit events and error handling work.
- [ ] CI checks, frontend/backend/integration tests and database migration checks pass.
- [ ] Backup/restore procedure for database and objects has been manually tested.
- [ ] Deployment limitations and provider data handling are disclosed.
- [ ] Evaluation report includes all six metric families and real counts/config IDs.

### Resume-ready gate
- [ ] Public MVP gate remains green.
- [ ] Tables and scanned-page OCR support has measured accuracy and provenance.
- [ ] Reranker decision has an ablation report (including negative result if rejected).
- [ ] Streaming works without exposing unverified content as verified.
- [ ] UI handles loading, empty, failed, partial-ingestion, quota, expired URL, abstention and authorization states.
- [ ] Locked evaluation set is run only at the designated final gate.
- [ ] README, architecture explanation, demo script and case study use real measured numbers.

## 12. Constraints and assumptions

- Free-first is preferred; no mandatory paid API/service. Free quotas and provider plans can change and must be verified before launch.
- Gemini only initially; no local AI model and no automatic provider fallback.
- Public/non-sensitive documents are used for development/evaluation unless explicit cloud-processing consent and provider terms have been reviewed.
- Public deployment is intended for portfolio/demo use, not enterprise-scale traffic.
- Hardware, corpus, final PDF limits and exact performance targets remain pending Phase 0/1 evidence.

## 13. Roadmap beyond MVP

Claim-level filtering; chart understanding; Knowledge Graph experiment only if failure analysis supports it; multi-KB document sharing; cross-KB search; additional languages; more advanced operational monitoring or budget controls if usage warrants them.

## 14. Top risks

| Risk | Mitigation |
|---|---|
| Bounding boxes drift | Canonical coordinate convention, rotation/crop tests, overlay validation |
| Parser quality caps retrieval | Compare parsers on representative corpus; golden-file tests |
| Citation exists but doesn't support claim | Deterministic validation + semantic check + human-labelled evaluation |
| No ground truth | Labelled question set before real pipeline |
| Prompt injection in PDFs | Treat document text as untrusted data; no answerer tools/side effects; validate citations |
| Malicious PDFs | Validation, parser isolation, resource limits and hostile-file suite |
| Multi-tenant leakage | App authorization + RLS + cross-user tests + object ownership checks |
| Provider outage/quota | Bounded retries, explicit failure/abstention, recoverable jobs; no silent fallback |
| Free-tier sleep/resource contention | Disclose limitations, bound worker concurrency, reconcile jobs |
| Data deletion incomplete | Track cleanup and retry; do not claim success prematurely |
| Scope creep | Phase gates and complexity budget; require evidence for optional components |
| Owner understanding lags implementation | One phase at a time and separate phase explanation artifacts |

## 15. Change log

- 2026-11-06: Reconciled product requirements with the owner-approved 26-point review and subsequent clarifications; public-deployment and RAG-quality priorities made authoritative.
