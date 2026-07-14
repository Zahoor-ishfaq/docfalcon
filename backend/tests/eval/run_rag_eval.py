"""Ragas evaluation harness for RAG pipeline.

Usage (from project root):
    $env:EVAL_COMPANY_ID="<company_id>"
    python -m backend.tests.eval.run_rag_eval

Uploads samples once (idempotent by file hash), runs all questions, computes Ragas metrics.
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from bson import ObjectId
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from ragas.run_config import RunConfig
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings

from backend.core.config import settings
from backend.core.database import get_db
from backend.services.ocr import extract_text
from backend.services.rag import index_document, retrieve
from backend.services.chat import answer as rag_answer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rag_eval")

# Faithfulness + answer_relevancy don't need ground_truth — better fit for our placeholder eval set.
THRESHOLD = 0.85
EVAL_SET = Path(__file__).parent / "rag_eval_set.json"
COMPANY_ID = os.getenv("EVAL_COMPANY_ID")


async def _ensure_indexed(doc_type: str, sample_path: str) -> str:
    path = Path(sample_path)
    if not path.exists():
        raise FileNotFoundError(f"Sample missing: {path}")

    content_type = "application/pdf" if path.suffix == ".pdf" else "image/png"
    data = path.read_bytes()
    file_hash = hashlib.sha256(data).hexdigest()
    db = get_db()
    company_oid = ObjectId(COMPANY_ID)

    existing = await db.documents.find_one({"file_hash": file_hash, "company_id": company_oid})
    if existing:
        return str(existing["_id"])

    raw_text = extract_text(data, content_type)
    doc = {"company_id": company_oid, "employee_id": None, "doc_type": doc_type,
           "file_hash": file_hash, "extracted_fields": {}, "raw_text": raw_text, "created_at": None}
    inserted = await db.documents.insert_one(doc)
    await index_document(str(inserted.inserted_id), COMPANY_ID, doc_type, raw_text)
    return str(inserted.inserted_id)


async def _build_dataset() -> Dataset:
    eval_set = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    rows = []
    for group in eval_set:
        doc_id = await _ensure_indexed(group["doc_type"], group["sample_path"])
        log.info("indexed doc_type=%s doc_id=%s", group["doc_type"], doc_id)
        for q in group["questions"]:
            chunks = await retrieve(q["question"], COMPANY_ID, doc_id, limit=8)
            result = await rag_answer(q["question"], COMPANY_ID, doc_id)
            rows.append({
                "user_input": q["question"],
                "retrieved_contexts": [c["text"] for c in chunks],
                "response": result["answer"],
            })
    return Dataset.from_list(rows)


async def main():
    if not COMPANY_ID:
        log.error("Set EVAL_COMPANY_ID env var to a real company_id from your DB")
        sys.exit(1)
    if not settings.ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY missing — needed for Claude judge")
        sys.exit(1)

    ds = await _build_dataset()

    # Claude Haiku judge — reliable rate limits, ~$0.15 total. Groq free tier can't sustain Ragas concurrency.
    judge = ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=settings.ANTHROPIC_API_KEY, temperature=0, max_tokens=512)
    embed = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    # max_workers=4 keeps well below any rate limit; retry budget generous for transient failures.
    run_config = RunConfig(max_workers=4, timeout=120, max_retries=5)

    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy],
        llm=judge,
        embeddings=embed,
        run_config=run_config,
    )
    log.info("results=%s", result)

    scores = result.to_pandas()[["faithfulness", "answer_relevancy"]].mean().to_dict()
    print("\n=== RAG Eval Results ===")
    for k, v in scores.items():
        status = "PASS" if v >= THRESHOLD else "FAIL"
        print(f"[{status}] {k}: {v:.3f} (threshold {THRESHOLD})")

    if any(v < THRESHOLD for v in scores.values()):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())