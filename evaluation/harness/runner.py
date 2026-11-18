"""Evaluation Runner Orchestrator.

Orchestrates the entire evaluation workflow:
1. Loads verified corpus manifest and question set.
2. Invokes the specified Retriever protocol.
3. Computes exact metrics via the metrics engine.
4. Generates a deterministic config hash.
5. Produces both JSON report and human-readable stdout summary.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from evaluation.harness.interfaces import Retriever
from evaluation.harness.loader import (
    load_corpus_manifest,
    load_question_set,
)
from evaluation.harness.metrics import QuestionEvaluationInput, evaluate_run
from evaluation.harness.report import generate_report_dict


def compute_config_hash(
    retriever_name: str,
    top_k: int,
    split_name: str,
    question_ids: list[str],
) -> str:
    """Compute deterministic SHA-256 config hash over run parameters."""
    hasher = hashlib.sha256()
    hasher.update(retriever_name.encode("utf-8"))
    hasher.update(str(top_k).encode("utf-8"))
    hasher.update(split_name.encode("utf-8"))
    hasher.update(",".join(sorted(question_ids)).encode("utf-8"))
    return hasher.hexdigest()[:16]


def run_evaluation(
    retriever: Retriever,
    use_locked: bool = False,
    top_k: int = 5,
    output_path: Path | str | None = None,
    evaluation_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Execute evaluation against tuning or locked dataset."""
    base_dir = (
        Path(evaluation_dir)
        if evaluation_dir
        else Path(__file__).resolve().parent.parent
    )

    manifest_path = base_dir / "corpus_manifest.json"
    manifest = load_corpus_manifest(manifest_path)

    split_name = "locked" if use_locked else "tuning"
    question_file = (
        base_dir / "questions" / "locked_questions.json"
        if use_locked
        else base_dir / "questions" / "tuning_questions.json"
    )

    questions = load_question_set(question_file)
    question_inputs: list[QuestionEvaluationInput] = []

    retriever_name = getattr(retriever, "name", retriever.__class__.__name__)

    for q in questions:
        # Retrieve candidate passages
        if hasattr(retriever, "retrieve_for_question"):
            retrieved = retriever.retrieve_for_question(
                question_text=q.question, question_id=q.id, top_k=top_k
            )
        else:
            retrieved = retriever.retrieve(q.question, top_k=top_k)

        # Build evaluation input
        gold_ids = [ev.evidence_id for ev in q.evidence]
        question_inputs.append(
            QuestionEvaluationInput(
                question_id=q.id,
                question_type=q.question_type,
                is_answerable=q.is_answerable,
                gold_evidence_ids=gold_ids,
                retrieved_passages=retrieved,
            )
        )

    summary = evaluate_run(question_inputs, top_k=top_k)

    q_ids = [q.id for q in questions]
    cfg_hash = compute_config_hash(retriever_name, top_k, split_name, q_ids)
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()

    notes = [
        f"Corpus verified: {len(manifest)} documents loaded.",
        f"Evaluated split: {split_name} ({len(questions)} questions).",
    ]

    report = generate_report_dict(
        summary=summary,
        split_name=split_name,
        config_hash=cfg_hash,
        run_timestamp=timestamp,
        retriever_name=retriever_name,
        notes=notes,
    )

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report
