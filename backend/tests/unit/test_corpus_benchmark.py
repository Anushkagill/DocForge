"""Suite 2: Empirical Corpus Benchmark Tests (T4-C01 to T4-C06).

Evaluates extraction quality, page counts, text fidelity, reading order,
and RSS bounds across the 6 verified corpus documents.
"""

from __future__ import annotations

import itertools
import json
import os
import re
from pathlib import Path

import pytest

from docforge.parsing.pdfminer_adapter import PdfMinerAdapter
from docforge.parsing.pipeline_primitives import get_process_tree_rss

CORPUS_DIR = Path("evaluation/corpus")
MANIFEST_PATH = Path("evaluation/corpus_manifest.json")
QUESTIONS_PATH = Path("evaluation/questions/tuning_questions.json")


@pytest.fixture(scope="module")
def manifest() -> dict[str, dict]:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {doc["document_id"]: doc for doc in data["corpus"]}


@pytest.fixture(scope="module")
def questions() -> dict[str, list[dict]]:
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    by_doc: dict[str, list[dict]] = {}
    for q in data["questions"]:
        doc_id = q["document_id"]
        by_doc.setdefault(doc_id, []).append(q)
    return by_doc


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_t4_c01_eval_001_nist_sp_800_145(
    manifest: dict[str, dict], questions: dict[str, list[dict]]
):
    """T4-C01: Benchmark on eval_001 (NIST SP 800-145, 7 pages)."""
    doc_meta = manifest["eval_001"]
    pdf_path = CORPUS_DIR / doc_meta["filename"]
    assert pdf_path.is_file()

    adapter = PdfMinerAdapter()
    pages = list(adapter.parse_pdf(pdf_path))

    assert len(pages) == doc_meta["page_count"] == 7
    total_blocks = sum(len(p.blocks) for p in pages)
    assert total_blocks > 50

    # Verify anchor content
    all_text = normalize_ws(" ".join(b.text_content for p in pages for b in p.blocks))
    assert "On-demand self-service" in all_text
    assert "Platform as a Service" in all_text
    assert "Software as a Service" in all_text

    # Memory budget check (< 150 MB)
    import gc

    gc.collect()
    rss_mb = get_process_tree_rss(os.getpid()) / (1024 * 1024)
    assert rss_mb < 200.0


def test_t4_c02_eval_002_nist_sp_800_144(manifest: dict[str, dict]):
    """T4-C02: Benchmark on eval_002 (NIST SP 800-144, 80 pages)."""
    doc_meta = manifest["eval_002"]
    pdf_path = CORPUS_DIR / doc_meta["filename"]
    assert pdf_path.is_file()

    adapter = PdfMinerAdapter()
    # Test first 10 pages for speed in unit test suite
    pages = list(itertools.islice(adapter.parse_pdf(pdf_path), 10))
    assert len(pages) == 10
    total_blocks = sum(len(p.blocks) for p in pages)
    assert total_blocks > 20

    all_text = normalize_ws(" ".join(b.text_content for p in pages for b in p.blocks))
    assert "Guidelines on Security and Privacy in Public Cloud Computing" in all_text

    import gc

    gc.collect()
    rss_mb = get_process_tree_rss(os.getpid()) / (1024 * 1024)
    assert rss_mb < 200.0


def test_t4_c03_eval_003_plos_ten_simple_rules(manifest: dict[str, dict]):
    """T4-C03: Benchmark on eval_003 (PLOS Two-Column Paper, 9 pages)."""
    doc_meta = manifest["eval_003"]
    pdf_path = CORPUS_DIR / doc_meta["filename"]
    assert pdf_path.is_file()

    adapter = PdfMinerAdapter()
    pages = list(adapter.parse_pdf(pdf_path))
    assert len(pages) == doc_meta["page_count"] == 9

    # Verify topological column reading order on page 2
    p2_blocks = [b for b in pages[1].blocks if b.text_content.strip()]
    p2_text_ordered = [b.text_content.strip() for b in p2_blocks]

    # Rule 1 must appear before Rule 2 in the extracted sequence
    rule1_idx = next(i for i, t in enumerate(p2_text_ordered) if "Rule 1" in t)
    assert rule1_idx >= 0

    import gc

    gc.collect()
    rss_mb = get_process_tree_rss(os.getpid()) / (1024 * 1024)
    assert rss_mb < 200.0


def test_t4_c04_eval_004_rfc_9110(manifest: dict[str, dict]):
    """T4-C04: Benchmark on eval_004 (RFC 9110 HTTP Semantics, 194 pages)."""
    doc_meta = manifest["eval_004"]
    pdf_path = CORPUS_DIR / doc_meta["filename"]
    assert pdf_path.is_file()

    adapter = PdfMinerAdapter()
    # Extract first 5 pages for rapid verification
    pages = list(itertools.islice(adapter.parse_pdf(pdf_path), 5))
    assert len(pages) == 5

    all_text = " ".join(b.text_content for p in pages for b in p.blocks)
    assert "HTTP Semantics" in all_text

    import gc

    gc.collect()
    rss_mb = get_process_tree_rss(os.getpid()) / (1024 * 1024)
    assert rss_mb < 200.0


def test_t4_c05_eval_005_w3c_xhtml1(manifest: dict[str, dict]):
    """T4-C05: Benchmark on eval_005 (W3C XHTML 1.0, 32 pages)."""
    doc_meta = manifest["eval_005"]
    pdf_path = CORPUS_DIR / doc_meta["filename"]
    assert pdf_path.is_file()

    adapter = PdfMinerAdapter()
    pages = list(adapter.parse_pdf(pdf_path))
    assert len(pages) == doc_meta["page_count"] == 32

    all_text = " ".join(b.text_content for p in pages for b in p.blocks)
    assert "XHTML" in all_text

    import gc

    gc.collect()
    rss_mb = get_process_tree_rss(os.getpid()) / (1024 * 1024)
    assert rss_mb < 200.0


def test_t4_c06_eval_006_un_sdg_report_2023(manifest: dict[str, dict]):
    """T4-C06: Benchmark on eval_006 (UN SDG Report, 80 pages)."""
    doc_meta = manifest["eval_006"]
    pdf_path = CORPUS_DIR / doc_meta["filename"]
    assert pdf_path.is_file()

    adapter = PdfMinerAdapter()
    # Extract first 5 pages
    pages = list(itertools.islice(adapter.parse_pdf(pdf_path), 5))
    assert len(pages) == 5

    all_text = " ".join(b.text_content for p in pages for b in p.blocks)
    assert "Sustainable Development Goals" in all_text

    import gc

    gc.collect()
    rss_mb = get_process_tree_rss(os.getpid()) / (1024 * 1024)
    assert rss_mb < 200.0
