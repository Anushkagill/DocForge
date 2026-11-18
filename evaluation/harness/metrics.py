"""Evaluation Metrics Computation.

Provides exact, deterministic implementations of:
- Fractional Recall@k (passage-level)
- Mean Reciprocal Rank (MRR, question-level)
- Normalized Discounted Cumulative Gain (nDCG@k, ranking quality)
- Dual Abstention Metrics (Precision, Recall, False Abstention Rate)

All formulas and edge cases match the approved Phase 1 specification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from evaluation.harness.interfaces import RetrievedPassage


@dataclass
class QuestionEvaluationInput:
    """Input payload representing a question, its gold evidence, and retrieved results."""

    question_id: str
    question_type: str
    is_answerable: bool
    gold_evidence_ids: list[str] = field(default_factory=list)
    retrieved_passages: list[RetrievedPassage] = field(default_factory=list)


@dataclass
class QuestionScore:
    """Per-question evaluation results."""

    question_id: str
    question_type: str
    is_answerable: bool
    recall_at_k: float | None = None
    reciprocal_rank: float | None = None
    ndcg_at_k: float | None = None
    is_abstention: bool = False
    is_correct_abstention: bool = False
    is_false_abstention: bool = False


@dataclass
class MetricSummary:
    """Aggregated evaluation metrics for a dataset run."""

    total_questions: int
    answerable_count: int
    unanswerable_count: int
    top_k: int

    # Retrieval metrics (computed only over answerable questions)
    mean_recall_at_k: float
    mrr: float
    mean_ndcg_at_k: float

    # Abstention metrics (reported together as mandatory dual metrics)
    correct_abstentions: int
    false_abstentions: int
    incorrect_answers_on_unanswerable: int
    total_abstentions_issued: int
    abstention_precision: float
    abstention_recall: float
    false_abstention_rate: float

    # Per-type breakdown
    type_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)
    question_scores: list[QuestionScore] = field(default_factory=list)


def compute_question_recall_at_k(
    gold_evidence_ids: list[str],
    retrieved: list[RetrievedPassage],
    k: int,
) -> float:
    """Compute passage-level fractional Recall@k for a single answerable question.

    Formula:
        Recall@k(q) = |{gold_passages} ∩ {retrieved_top_k}| / |gold_passages|

    Fractional behavior:
        - If 2 gold passages exist and 1 is retrieved: returns 0.5.
        - If 1 gold passage exists and is retrieved: returns 1.0.
        - If 1 gold passage exists and 0 are retrieved: returns 0.0.

    Edge cases:
        - If gold_evidence_ids is empty: raises ValueError (data integrity error for answerable questions).
        - If retrieved is empty: returns 0.0.
    """
    if not gold_evidence_ids:
        raise ValueError("Answerable question cannot have empty gold_evidence_ids.")

    if not retrieved or k <= 0:
        return 0.0

    top_k_passages = retrieved[:k]
    retrieved_ids = set()
    for p in top_k_passages:
        if getattr(p, "matched_evidence_ids", None):
            retrieved_ids.update(p.matched_evidence_ids)
        elif p.evidence_id:
            retrieved_ids.add(p.evidence_id)
    matched_count = sum(1 for gid in gold_evidence_ids if gid in retrieved_ids)
    return matched_count / len(gold_evidence_ids)


def compute_question_mrr(
    gold_evidence_ids: list[str],
    retrieved: list[RetrievedPassage],
) -> float:
    """Compute Reciprocal Rank (RR) for a single answerable question.

    Formula:
        RR(q) = 1 / rank_of_first_matching_passage
        RR(q) = 0.0 if no retrieved passage matches any gold evidence.
    """
    if not gold_evidence_ids:
        raise ValueError("Answerable question cannot have empty gold_evidence_ids.")

    gold_set = set(gold_evidence_ids)
    for idx, p in enumerate(retrieved, start=1):
        p_ids = (
            set(p.matched_evidence_ids)
            if getattr(p, "matched_evidence_ids", None)
            else ({p.evidence_id} if p.evidence_id else set())
        )
        if p_ids & gold_set:
            return 1.0 / idx
    return 0.0


def compute_question_ndcg_at_k(
    gold_evidence_ids: list[str],
    retrieved: list[RetrievedPassage],
    k: int,
) -> float:
    """Compute Normalized Discounted Cumulative Gain (nDCG@k) with binary relevance.

    Formula:
        DCG@k(q) = Σ_{i=1}^{k} rel_i / log2(i + 1)
        IDCG@k(q) = Σ_{i=1}^{min(k, |gold|)} 1 / log2(i + 1)
        nDCG@k(q) = DCG@k(q) / IDCG@k(q)

    Binary relevance:
        rel_i = 1 if retrieved passage i matches a gold evidence ID, 0 otherwise.
    """
    if not gold_evidence_ids:
        raise ValueError("Answerable question cannot have empty gold_evidence_ids.")

    if k <= 0 or not retrieved:
        return 0.0

    gold_set = set(gold_evidence_ids)
    top_k_passages = retrieved[:k]

    dcg = 0.0
    for idx, p in enumerate(top_k_passages, start=1):
        p_ids = (
            set(p.matched_evidence_ids)
            if getattr(p, "matched_evidence_ids", None)
            else ({p.evidence_id} if p.evidence_id else set())
        )
        rel = 1.0 if (p_ids & gold_set) else 0.0
        dcg += rel / math.log2(idx + 1)

    # Ideal DCG: all gold items ranked first, up to k
    ideal_count = min(k, len(gold_evidence_ids))
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_count + 1))

    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def evaluate_run(
    questions: list[QuestionEvaluationInput],
    top_k: int = 5,
) -> MetricSummary:
    """Evaluate an entire dataset run and produce aggregate and per-question metrics."""
    scores: list[QuestionScore] = []

    answerable_count = 0
    unanswerable_count = 0

    recall_sum = 0.0
    rr_sum = 0.0
    ndcg_sum = 0.0

    correct_abstentions = 0
    false_abstentions = 0
    incorrect_answers_on_unanswerable = 0
    total_abstentions_issued = 0

    type_map: dict[str, list[QuestionScore]] = {}

    for q in questions:
        # Determine whether system abstained (empty retrieved list signifies abstention in retrieval)
        is_abstention = len(q.retrieved_passages) == 0

        qs = QuestionScore(
            question_id=q.question_id,
            question_type=q.question_type,
            is_answerable=q.is_answerable,
            is_abstention=is_abstention,
        )

        if is_abstention:
            total_abstentions_issued += 1

        if q.is_answerable:
            answerable_count += 1
            if is_abstention:
                qs.is_false_abstention = True
                false_abstentions += 1

            r_k = compute_question_recall_at_k(
                q.gold_evidence_ids, q.retrieved_passages, top_k
            )
            rr = compute_question_mrr(q.gold_evidence_ids, q.retrieved_passages)
            ndcg = compute_question_ndcg_at_k(
                q.gold_evidence_ids, q.retrieved_passages, top_k
            )

            qs.recall_at_k = r_k
            qs.reciprocal_rank = rr
            qs.ndcg_at_k = ndcg

            recall_sum += r_k
            rr_sum += rr
            ndcg_sum += ndcg
        else:
            unanswerable_count += 1
            if is_abstention:
                qs.is_correct_abstention = True
                correct_abstentions += 1
            else:
                incorrect_answers_on_unanswerable += 1

        scores.append(qs)
        type_map.setdefault(q.question_type, []).append(qs)

    mean_recall = (recall_sum / answerable_count) if answerable_count > 0 else 0.0
    mrr = (rr_sum / answerable_count) if answerable_count > 0 else 0.0
    mean_ndcg = (ndcg_sum / answerable_count) if answerable_count > 0 else 0.0

    abstention_precision = (
        (correct_abstentions / total_abstentions_issued)
        if total_abstentions_issued > 0
        else 0.0
    )
    abstention_recall = (
        (correct_abstentions / unanswerable_count) if unanswerable_count > 0 else 0.0
    )
    false_abstention_rate = (
        (false_abstentions / answerable_count) if answerable_count > 0 else 0.0
    )

    type_breakdown: dict[str, dict[str, Any]] = {}
    for q_type, q_scores in type_map.items():
        ans_scores = [s for s in q_scores if s.is_answerable]
        ans_count = len(ans_scores)
        unans_count = len(q_scores) - ans_count
        type_breakdown[q_type] = {
            "total": len(q_scores),
            "answerable": ans_count,
            "unanswerable": unans_count,
            "mean_recall_at_k": (
                sum(s.recall_at_k or 0.0 for s in ans_scores) / ans_count
                if ans_count > 0
                else None
            ),
            "mrr": (
                sum(s.reciprocal_rank or 0.0 for s in ans_scores) / ans_count
                if ans_count > 0
                else None
            ),
        }

    return MetricSummary(
        total_questions=len(questions),
        answerable_count=answerable_count,
        unanswerable_count=unanswerable_count,
        top_k=top_k,
        mean_recall_at_k=mean_recall,
        mrr=mrr,
        mean_ndcg_at_k=mean_ndcg,
        correct_abstentions=correct_abstentions,
        false_abstentions=false_abstentions,
        incorrect_answers_on_unanswerable=incorrect_answers_on_unanswerable,
        total_abstentions_issued=total_abstentions_issued,
        abstention_precision=abstention_precision,
        abstention_recall=abstention_recall,
        false_abstention_rate=false_abstention_rate,
        type_breakdown=type_breakdown,
        question_scores=scores,
    )
