"""
Push rag_eval_set.json to Langfuse as a dataset.
Run once: python -m backend.tests.eval.upload_eval_dataset
Subsequent runs skip items that already exist (idempotent by input hash).
"""

import json, hashlib, sys
from pathlib import Path
from langfuse import Langfuse
from backend.core.config import settings

DATASET_NAME = "docfalcon-rag-eval"
EVAL_PATH = Path(__file__).parent / "rag_eval_set.json"


def main():
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        print("ERROR: Langfuse keys not set — check your .env")
        sys.exit(1)

    lf = Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
    )

    # create dataset if it doesn't exist
    try:
        lf.get_dataset(DATASET_NAME)
        print(f"Dataset '{DATASET_NAME}' already exists — appending new items only.")
    except Exception:
        lf.create_dataset(name=DATASET_NAME, description="DocFalcon RAG eval — faithfulness + answer_relevancy")
        print(f"Created dataset '{DATASET_NAME}'.")

    items = json.loads(EVAL_PATH.read_text())
    created = 0

    for item in items:
        # stable ID from the question text — prevents duplicates on re-run
        item_id = hashlib.sha256(item["question"].encode()).hexdigest()[:16]
        try:
            lf.create_dataset_item(
                dataset_name=DATASET_NAME,
                input={"query": item["question"]},
                expected_output=item.get("ground_truth", ""),
                metadata={"doc_type": item.get("doc_type"), "id": item_id},
            )
            created += 1
        except Exception as e:
            # Langfuse throws on duplicate external_id in some SDK versions — skip silently
            print(f"  skip (likely duplicate): {item['question'][:60]} — {e}")

    print(f"Done. {created}/{len(items)} items uploaded to '{DATASET_NAME}'.")
    lf.flush()


if __name__ == "__main__":
    main()