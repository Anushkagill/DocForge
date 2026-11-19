"""Query trace, citation persistence, and atomic idempotency repository."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from docforge.api.schemas.query import (
    CitationItem,
    CitationRegion,
    LocalEvidenceItem,
    QueryResponse,
    QueryTraceDetailResponse,
)

logger = logging.getLogger(__name__)


def compute_request_hash(
    kb_id: str | UUID,
    query_text: str,
    scope_ids: list[str | UUID] | None,
    execution_mode: str,
) -> str:
    """Computes deterministic SHA-256 hash of canonical normalized request payload."""
    canonical_payload = {
        "execution_mode": execution_mode.strip().lower(),
        "knowledge_base_id": str(kb_id).lower(),
        "query_text": query_text.strip(),
        "scope_document_ids": (
            sorted(list(set(str(u).lower() for u in scope_ids)))
            if scope_ids is not None
            else None
        ),
    }
    payload_str = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


class QueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def acquire_or_handle_idempotency(
        self,
        user_id: UUID,
        key: str,
        kb_id: UUID,
        query_text_val: str,
        scope_ids: list[UUID] | None,
        execution_mode: str,
    ) -> tuple[UUID, bool, dict[str, Any] | None]:
        """
        Acquires an idempotency key or handles replay / conflict / retry.
        Returns: (query_trace_id, is_replay, cached_response_dict)
        Guarantees zero orphan candidate traces via transaction rollback on race condition.
        """
        req_hash = compute_request_hash(kb_id, query_text_val, scope_ids, execution_mode)

        # 1. Fast path: check existing key
        stmt = text("""
            SELECT status, request_hash, query_trace_id, cached_response, expires_at
            FROM public.query_idempotency_keys
            WHERE user_id = :user_id AND idempotency_key = :key
            FOR UPDATE;
        """)
        res = await self.session.execute(stmt, {"user_id": user_id, "key": key})
        existing = res.mappings().first()

        if existing:
            now_stmt = text("SELECT clock_timestamp() as now;")
            now_res = await self.session.execute(now_stmt)
            now = now_res.scalar()

            if existing["expires_at"] > now:
                # Key is active
                if existing["request_hash"] != req_hash:
                    raise HTTPException(
                        status_code=422,
                        detail="Idempotency key reuse with mismatched request payload or execution mode",
                    )
                if existing["status"] == "in_flight":
                    raise HTTPException(
                        status_code=409,
                        detail="Query with this idempotency key is currently processing",
                    )
                if existing["status"] == "completed":
                    return existing["query_trace_id"], True, existing["cached_response"]
                if existing["status"] == "failed":
                    # Same payload failed retry is explicitly permitted!
                    candidate_trace_id = uuid4()
                    await self.session.execute(
                        text("""
                            INSERT INTO public.query_traces (
                                id, user_id, knowledge_base_id, query_text, execution_mode, status
                            )
                            VALUES (:id, :user_id, :kb_id, :query_text, :mode, 'accepted');
                        """),
                        {
                            "id": candidate_trace_id,
                            "user_id": user_id,
                            "kb_id": kb_id,
                            "query_text": query_text_val.strip(),
                            "mode": execution_mode,
                        },
                    )
                    await self.session.execute(
                        text("""
                            UPDATE public.query_idempotency_keys
                            SET status = 'in_flight',
                                query_trace_id = :trace_id,
                                cached_response = NULL,
                                created_at = clock_timestamp(),
                                expires_at = clock_timestamp() + INTERVAL '24 hours'
                            WHERE user_id = :user_id AND idempotency_key = :key;
                        """),
                        {"user_id": user_id, "key": key, "trace_id": candidate_trace_id},
                    )
                    await self.session.commit()
                    return candidate_trace_id, False, None

        # 2. Key does not exist: attempt atomic acquisition
        candidate_trace_id = uuid4()
        try:
            # Step A: Insert candidate trace
            await self.session.execute(
                text("""
                    INSERT INTO public.query_traces (
                        id, user_id, knowledge_base_id, query_text, execution_mode, status
                    )
                    VALUES (:id, :user_id, :kb_id, :query_text, :mode, 'accepted');
                """),
                {
                    "id": candidate_trace_id,
                    "user_id": user_id,
                    "kb_id": kb_id,
                    "query_text": query_text_val.strip(),
                    "mode": execution_mode,
                },
            )

            # Step B: Insert idempotency key referencing candidate trace
            ins_stmt = text("""
                INSERT INTO public.query_idempotency_keys (
                    user_id, idempotency_key, request_hash, status, query_trace_id
                )
                VALUES (:user_id, :key, :hash, 'in_flight', :trace_id)
                ON CONFLICT (user_id, idempotency_key) DO NOTHING
                RETURNING idempotency_key;
            """)
            ins_res = await self.session.execute(
                ins_stmt,
                {
                    "user_id": user_id,
                    "key": key,
                    "hash": req_hash,
                    "trace_id": candidate_trace_id,
                },
            )
            acquired = ins_res.scalar()

            if acquired is None:
                # Concurrent race condition: another transaction won key insertion.
                # Rollback immediately to prevent orphan candidate trace!
                await self.session.rollback()
                return await self.acquire_or_handle_idempotency(
                    user_id, key, kb_id, query_text_val, scope_ids, execution_mode
                )

            await self.session.commit()
            return candidate_trace_id, False, None

        except Exception:
            await self.session.rollback()
            raise

    async def record_scope_documents(
        self,
        trace_id: UUID,
        user_id: UUID,
        kb_id: UUID,
        scoped_docs: list[dict[str, Any]],
    ) -> None:
        """Persists immutable snapshot records of scoped documents."""
        for doc in scoped_docs:
            await self.session.execute(
                text("""
                    INSERT INTO public.query_scope_documents (
                        query_trace_id, document_id, generation_id, knowledge_base_id, user_id,
                        is_eligible, exclusion_reason, privacy_label_snapshot
                    )
                    VALUES (
                        :trace_id, :doc_id, :gen_id, :kb_id, :user_id,
                        :is_eligible, :exclusion_reason, :privacy_label_snapshot
                    )
                    ON CONFLICT (query_trace_id, document_id) DO NOTHING;
                """),
                {
                    "trace_id": trace_id,
                    "doc_id": doc["document_id"],
                    "gen_id": doc["generation_id"],
                    "kb_id": kb_id,
                    "user_id": user_id,
                    "is_eligible": doc.get("is_eligible", True),
                    "exclusion_reason": doc.get("exclusion_reason"),
                    "privacy_label_snapshot": doc["privacy_label"],
                },
            )
        await self.session.commit()

    async def save_terminal_response(
        self,
        trace_id: UUID,
        user_id: UUID,
        response: QueryResponse,
        idempotency_key: str | None = None,
        retrieval_latency_ms: int | None = None,
        generation_latency_ms: int | None = None,
        verification_latency_ms: int | None = None,
    ) -> None:
        """Persists terminal query outcome, citations, regions, and idempotency state in a single transaction."""
        # 1. Update query_traces
        await self.session.execute(
            text("""
                UPDATE public.query_traces
                SET status = :status,
                    answer_status = :answer_status,
                    provider_model = :provider_model,
                    answer_text = :answer_text,
                    abstention_reason = :abstention_reason,
                    error_code = :error_code,
                    error_message = :error_message,
                    retrieval_latency_ms = :retrieval_latency_ms,
                    generation_latency_ms = :generation_latency_ms,
                    verification_latency_ms = :verification_latency_ms,
                    total_latency_ms = :total_latency_ms,
                    updated_at = clock_timestamp()
                WHERE id = :trace_id AND user_id = :user_id;
            """),
            {
                "trace_id": trace_id,
                "user_id": user_id,
                "status": response.status,
                "answer_status": response.answer_status,
                "provider_model": response.provider_model,
                "answer_text": response.answer_text,
                "abstention_reason": response.abstention_reason,
                "error_code": response.error_code,
                "error_message": response.error_message,
                "retrieval_latency_ms": retrieval_latency_ms,
                "generation_latency_ms": generation_latency_ms,
                "verification_latency_ms": verification_latency_ms,
                "total_latency_ms": response.total_latency_ms,
            },
        )

        # 2. Insert citations and regions
        for cit in response.citations:
            cit_id = uuid4()
            # Find generation_id for this document from query_scope_documents
            gen_res = await self.session.execute(
                text("""
                    SELECT generation_id
                    FROM public.query_scope_documents
                    WHERE query_trace_id = :trace_id AND document_id = :doc_id;
                """),
                {"trace_id": trace_id, "doc_id": cit.document_id},
            )
            gen_id = gen_res.scalar()
            if not gen_id:
                # If generation not found in scope (e.g. mock test), fetch active generation from document
                doc_gen_res = await self.session.execute(
                    text("SELECT active_generation_id FROM public.documents WHERE id = :doc_id;"),
                    {"doc_id": cit.document_id},
                )
                gen_id = doc_gen_res.scalar()

            await self.session.execute(
                text("""
                    INSERT INTO public.query_citations (
                        id, query_trace_id, document_id, generation_id, chunk_id, user_id,
                        citation_index, claim_index, claim_text, citation_type,
                        verification_status, confidence_score
                    )
                    VALUES (
                        :id, :trace_id, :doc_id, :gen_id, :chunk_id, :user_id,
                        :citation_index, :claim_index, :claim_text, :citation_type,
                        :verification_status, :confidence_score
                    );
                """),
                {
                    "id": cit_id,
                    "trace_id": trace_id,
                    "doc_id": cit.document_id,
                    "gen_id": gen_id,
                    "chunk_id": cit.chunk_id,
                    "user_id": user_id,
                    "citation_index": cit.citation_index,
                    "claim_index": cit.claim_index,
                    "claim_text": cit.claim_text,
                    "citation_type": cit.citation_type,
                    "verification_status": cit.verification_status,
                    "confidence_score": cit.confidence_score,
                },
            )

            # Insert regions
            for reg in cit.regions:
                reg_id = uuid4()
                u0, v0, u1, v1 = reg.bbox
                await self.session.execute(
                    text("""
                        INSERT INTO public.citation_regions (
                            id, citation_id, query_trace_id, user_id, page_number,
                            bbox_u0, bbox_v0, bbox_u1, bbox_v1
                        )
                        VALUES (
                            :id, :citation_id, :trace_id, :user_id, :page_number,
                            :u0, :v0, :u1, :v1
                        );
                    """),
                    {
                        "id": reg_id,
                        "citation_id": cit_id,
                        "trace_id": trace_id,
                        "user_id": user_id,
                        "page_number": reg.page_number,
                        "u0": u0,
                        "v0": v0,
                        "u1": u1,
                        "v1": v1,
                    },
                )

        # 3. Update idempotency key if provided
        if idempotency_key:
            idemp_status = "completed" if response.status in ("answered", "abstained") else "failed"
            cached_json = response.model_dump(mode="json") if idemp_status == "completed" else None
            await self.session.execute(
                text("""
                    UPDATE public.query_idempotency_keys
                    SET status = :idemp_status,
                        cached_response = :cached_response
                    WHERE user_id = :user_id AND idempotency_key = :key;
                """),
                {
                    "idemp_status": idemp_status,
                    "cached_response": json.dumps(cached_json) if cached_json else None,
                    "user_id": user_id,
                    "key": idempotency_key,
                },
            )

        await self.session.commit()

    async def get_query_trace_detail(
        self, trace_id: UUID, user_id: UUID
    ) -> QueryTraceDetailResponse | None:
        """Fetches full query detail with citations and regions."""
        trace_stmt = text("""
            SELECT id, knowledge_base_id, query_text, status, answer_status, execution_mode,
                   provider_model, answer_text, abstention_reason, error_code, error_message,
                   retrieval_latency_ms, generation_latency_ms, verification_latency_ms,
                   total_latency_ms, created_at
            FROM public.query_traces
            WHERE id = :trace_id AND user_id = :user_id;
        """)
        trace_res = await self.session.execute(trace_stmt, {"trace_id": trace_id, "user_id": user_id})
        t_row = trace_res.mappings().first()
        if not t_row:
            return None

        # Fetch citations
        cit_stmt = text("""
            SELECT id, document_id, chunk_id, citation_index, claim_index, claim_text,
                   citation_type, verification_status, confidence_score
            FROM public.query_citations
            WHERE query_trace_id = :trace_id AND user_id = :user_id
            ORDER BY citation_index ASC;
        """)
        cit_res = await self.session.execute(cit_stmt, {"trace_id": trace_id, "user_id": user_id})
        citations_list: list[CitationItem] = []

        for c_row in cit_res.mappings():
            # Fetch regions for this citation
            reg_stmt = text("""
                SELECT page_number, bbox_u0, bbox_v0, bbox_u1, bbox_v1
                FROM public.citation_regions
                WHERE citation_id = :cit_id AND user_id = :user_id
                ORDER BY page_number ASC, bbox_v1 DESC, bbox_u0 ASC;
            """)
            reg_res = await self.session.execute(reg_stmt, {"cit_id": c_row["id"], "user_id": user_id})
            regions = [
                CitationRegion(
                    page_number=r["page_number"],
                    bbox=[r["bbox_u0"], r["bbox_v0"], r["bbox_u1"], r["bbox_v1"]],
                )
                for r in reg_res.mappings()
            ]

            citations_list.append(
                CitationItem(
                    citation_index=c_row["citation_index"],
                    document_id=c_row["document_id"],
                    chunk_id=c_row["chunk_id"],
                    claim_index=c_row["claim_index"],
                    claim_text=c_row["claim_text"],
                    citation_type=c_row["citation_type"],
                    verification_status=c_row["verification_status"],
                    confidence_score=c_row["confidence_score"],
                    regions=regions,
                )
            )

        # Scoped document count
        scope_res = await self.session.execute(
            text("SELECT COUNT(*) FROM public.query_scope_documents WHERE query_trace_id = :trace_id;"),
            {"trace_id": trace_id},
        )
        scoped_count = scope_res.scalar() or 0

        return QueryTraceDetailResponse(
            query_trace_id=t_row["id"],
            knowledge_base_id=t_row["knowledge_base_id"],
            status=t_row["status"],
            answer_status=t_row["answer_status"] or "failed",
            execution_mode=t_row["execution_mode"],
            provider_model=t_row["provider_model"],
            answer_text=t_row["answer_text"],
            abstention_reason=t_row["abstention_reason"],
            error_code=t_row["error_code"],
            error_message=t_row["error_message"],
            total_latency_ms=t_row["total_latency_ms"] or 0,
            citations=citations_list,
            local_evidence=[],
            created_at=t_row["created_at"],
            retrieval_latency_ms=t_row["retrieval_latency_ms"],
            generation_latency_ms=t_row["generation_latency_ms"],
            verification_latency_ms=t_row["verification_latency_ms"],
            scoped_document_count=scoped_count,
        )

    async def list_query_traces(
        self, kb_id: UUID, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Lists historical query traces for a knowledge base."""
        stmt = text("""
            SELECT id, query_text, status, answer_status, execution_mode,
                   provider_model, abstention_reason, total_latency_ms, created_at
            FROM public.query_traces
            WHERE knowledge_base_id = :kb_id AND user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset;
        """)
        res = await self.session.execute(stmt, {"kb_id": kb_id, "user_id": user_id, "limit": limit, "offset": offset})
        return [dict(row) for row in res.mappings()]
