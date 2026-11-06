# DocForge — Product and UI Design

> **Purpose:** Defines the user-facing experience and interaction behavior. It does not redefine backend architecture; see `architecture.md`. Visual styling may evolve, but privacy, scope, status and evidence behaviors below are product requirements.

## 1. Experience principles

1. **Evidence is visible:** answers and source references are presented together; citations are interactive.
2. **Clear scope:** the user can always tell which KB and documents a question searches.
3. **Truthful status:** queued, processing, indexed and failed documents are distinguishable; partial coverage is never hidden.
4. **Privacy is understandable:** users choose whether document content may be sent to Gemini and see the current privacy mode.
5. **Safe failure:** show understandable errors, quota/unavailable states and abstention rather than fabricated success.
6. **Focused interface:** prioritize upload, search, answer quality, citations and PDF inspection over analytics/administrative complexity.
7. **Accessible interaction:** keyboard support, visible focus, semantic controls, clear labels and WCAG 2.2 AA principles for primary journeys.

## 2. Information architecture

Primary navigation:
- **Knowledge Bases** — list/create/rename/delete owned KBs.
- **Workspace** — selected KB, document list, upload and question-answering.
- **Account** — profile, connected Google identity, sessions/logout and privacy/help information.

A user can have multiple KBs. Each PDF belongs to exactly one KB. No cross-KB search or document sharing in MVP.

## 3. Main screens

### 3.1 Authentication

- Registration and login with email/password.
- Google sign-in.
- Clear validation and generic safe authentication errors; do not reveal whether an email exists unnecessarily.
- Session expiry/refresh should normally be transparent. If refresh fails, return to login with a clear message.
- Password reset and email verification UI must be added before public account flows are called production-ready.

### 3.2 Knowledge Base library

Display each KB with its name, document count, creation/update information and a clear action to open it. Provide create, rename and delete actions with confirmation for destructive deletion. Empty state explains how to create the first KB.

### 3.3 Knowledge Base workspace

Workspace layout should prioritize:
- KB name and context.
- Document upload area and list.
- Per-document ingestion status and privacy label.
- Search scope selector: all eligible indexed documents in this KB or selected documents.
- Question composer and conversation/evidence area.

Document list states:
- Uploaded/queued/processing: visible but not searchable yet.
- Indexed: eligible for search.
- Failed: show safe reason and retry action when retry is supported.
- Cancelled/deleting: show transitional state until cleanup completes.

If a KB has documents still processing or failed, show a coverage notice. The user may continue with ready documents, but the app must say which documents are excluded. Selected-document scope should disable non-indexed documents.

### 3.4 Upload flow

- User chooses target KB and selects one or more PDFs.
- Validate client-side for usability, but backend validation is authoritative.
- For each file, show filename, size, privacy label, upload result and ingestion status.
- New uploads default to `local-only`.
- Before enabling `cloud-allowed`, show a plain-language disclosure: extracted text/document-derived content may be sent to Gemini for embeddings, reranking (if enabled), generation and verification; link to the provider data-handling explanation available in the product.
- User must explicitly opt in; do not preselect cloud permission.
- Explain that local-only documents can be viewed and searched lexically but cannot use Gemini semantic embeddings or AI answers.
- Do not show an upload as indexed until all required stages have completed.

### 3.5 Question and answer workspace

- Clearly show selected KB and active scope (all indexed docs or selected docs).
- Question input supports submit, loading and error states.
- During processing, show a truthful progress/status indicator. Do not imply streaming if not implemented.
- Answer panel distinguishes verified grounded answer, abstention, provider unavailable/quota exhausted and incomplete coverage.
- Show source citations close to the claims/evidence they support.
- Citation chip/row includes document name, page number and a short quote/snippet when available.
- Selecting a citation opens the corresponding PDF and navigates to the page/region.
- If region coordinates are unavailable or unreliable, navigate to the page without drawing a false highlight.
- MVP answer-level abstention: if a material claim remains unsupported after one corrective attempt, do not display the generated answer as a partial answer. Show an abstention explanation and, where safe, evidence-only references.
- Do not expose internal chain-of-thought. User-facing traces may show concise stage status and latency, not hidden reasoning.

### 3.6 PDF viewer

- Use PDF.js.
- Support page navigation, zoom and fit controls, text selection where available, and citation-region overlay.
- Highlight selected citation region with an accessible non-color-only cue (outline/label in addition to color).
- Correctly handle page rotation, crop boxes, scaling and different page sizes.
- Signed URL expiry should trigger a fresh backend authorization request; show an understandable error if access cannot be refreshed.
- PDF.js loads private PDFs directly from short-lived signed URLs after FastAPI ownership authorization; never make the bucket public for convenience.

### 3.7 Account and privacy

- Show connected login methods and session/logout controls.
- Explain that documents default to local-only and cloud AI requires explicit per-document consent.
- Allow users to inspect/change privacy labels under a clear policy. Changing cloud-allowed back to local-only must prevent future Gemini egress; define whether existing embeddings/derived artifacts are deleted or retained under the strictest label before implementation.
- Provide document, KB and account deletion actions with confirmation and truthful cleanup status.
- Do not claim automatic PII detection/redaction.

## 4. Core user journeys

### Journey A — First-time user
1. Register or sign in with Google.
2. Create a knowledge base.
3. Upload one or more PDFs.
4. Keep local-only or explicitly opt in to cloud-allowed AI processing.
5. Watch ingestion states until documents become indexed.
6. Ask a question against the KB or selected documents.
7. Inspect citations in the PDF viewer.

### Journey B — Add another PDF while using the KB
1. Upload another PDF to the existing KB.
2. Existing indexed documents remain searchable.
3. New PDF remains excluded until fully indexed.
4. UI displays incomplete-coverage notice.
5. Once indexed, new PDF becomes eligible for subsequent queries.

### Journey C — Ask a question with insufficient evidence
1. User submits question.
2. System searches within fixed query scope snapshot.
3. If answerability/verification fails, one corrective retrieval attempt may run.
4. If material claim remains unsupported, UI shows answer-level abstention and optionally evidence-only references.

### Journey D — Access control
1. User opens an owned PDF; frontend asks backend for access.
2. Backend validates session and ownership.
3. Backend issues a short-lived signed URL.
4. PDF.js loads from object storage.
5. A different user or expired/revoked session cannot obtain a new URL.

### Journey E — Delete a document
1. User confirms deletion.
2. Document is removed from searchable scope immediately (tombstone/soft-delete state).
3. Background cleanup removes original object and derived records/indexes.
4. UI shows complete only after required cleanup succeeds; failures remain visible/retryable.

## 5. UI states and copy principles

- **Empty:** explain the next action, do not show a blank panel.
- **Loading:** identify what is loading (upload, indexing, retrieval, answer verification).
- **Processing:** show stage or truthful progress; avoid fake percentage.
- **Incomplete coverage:** state that some selected-scope documents are not indexed and excluded.
- **Failed:** give a safe, actionable error and retry where possible.
- **Quota/provider unavailable:** explain temporary AI unavailability; never imply a confident answer was produced.
- **Abstention:** say evidence was insufficient to verify the answer; distinguish from technical failure.
- **Privacy:** clearly state whether Gemini processing is allowed for selected documents.
- **Deletion:** distinguish deletion requested, cleanup in progress and cleanup complete.

## 6. Accessibility requirements

- Semantic HTML landmarks, headings and buttons.
- All main journeys keyboard-operable with visible focus.
- Inputs have persistent labels; validation and status changes are announced accessibly.
- Text/background contrast and focus indicators meet WCAG 2.2 AA principles.
- Do not use color as the only status/citation indicator.
- Dialogs manage focus and return focus when closed.
- PDF viewer controls have accessible names and keyboard alternatives where practical; document any PDF.js limitations.
- Test primary workflows with keyboard and at least one screen-reader smoke test before resume-ready release.

## 7. Visual direction

Use a clean, restrained research/workspace interface. Favor readable typography, generous spacing, clear hierarchy and neutral surfaces. Keep the answer and source evidence visually connected. Use a consistent status system for queued/processing/indexed/failed and privacy labels. Avoid decorative dashboards that do not help users complete a task or understand RAG quality.

Exact colors, fonts, responsive breakpoints and component library are implementation choices to be made in the relevant phase after reviewing accessibility and deployment constraints.

## 8. Explicitly deferred UI

- Admin/analytics dashboards and detailed usage budgets.
- Knowledge graph visualization.
- Cross-KB search and shared-document management.
- Automatic PII detection/redaction controls.
- Complex user roles/organization workspaces.
- Advanced chart interpretation.
