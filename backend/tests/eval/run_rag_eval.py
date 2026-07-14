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
from datetime import datetime
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


async def _build_dataset() -> tuple[Dataset, list[dict]]:
    eval_set = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    rows = []
    items_meta = []  # track question text for Langfuse item matching
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
            items_meta.append({"question": q["question"]})
    return Dataset.from_list(rows), items_meta


async def main():
    if not COMPANY_ID:
        log.error("Set EVAL_COMPANY_ID env var to a real company_id from your DB")
        sys.exit(1)
    if not settings.ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY missing — needed for Claude judge")
        sys.exit(1)

    ds, items_meta = await _build_dataset()

    # Claude Haiku judge — reliable rate limits, ~$0.15 total. Groq free tier can't sustain Ragas concurrency.
    judge = ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=settings.ANTHROPIC_API_KEY, temperature=0, max_tokens=512)
    embed = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    run_config = RunConfig(max_workers=4, timeout=120, max_retries=5)

    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy],
        llm=judge,
        embeddings=embed,
        run_config=run_config,
    )
    log.info("results=%s", result)

    df = result.to_pandas()
    per_row = df[["faithfulness", "answer_relevancy"]].to_dict(orient="records")
    scores = df[["faithfulness", "answer_relevancy"]].mean().to_dict()

    faithfulness_score = scores["faithfulness"]
    answer_relevancy_score = scores["answer_relevancy"]

    # log scores to Langfuse dataset run
    try:
        from langfuse import Langfuse
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            lf = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
            run_name = f"rag-eval-{datetime.utcnow().strftime('%Y%m%d-%H%M')}"
            dataset = lf.get_dataset("docfalcon-rag-eval")
            for item, score_row in zip(dataset.items, per_row):
                with item.observe(run_name=run_name) as trace:
                    trace.score(name="faithfulness",     value=score_row.get("faithfulness", 0))
                    trace.score(name="answer_relevancy", value=score_row.get("answer_relevancy", 0))
            lf.flush()
            print(f"Scores logged to Langfuse run '{run_name}'.")
    except Exception as e:
        print(f"Langfuse score upload skipped: {e}")

    print("\n=== RAG Eval Results ===")
    for k, v in scores.items():
        status = "PASS" if v >= THRESHOLD else "FAIL"
        print(f"[{status}] {k}: {v:.3f} (threshold {THRESHOLD})")

    if faithfulness_score < THRESHOLD or answer_relevancy_score < THRESHOLD:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())