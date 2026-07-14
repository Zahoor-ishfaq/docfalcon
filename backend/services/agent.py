"""Multi-doc onboarding agent — Claude reasons, tools execute."""

import hashlib
import json
import logging
import time
from typing import AsyncGenerator
from datetime import datetime, timezone

from bson import ObjectId
import anthropic

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.tracing import get_tracer
from backend.tools.classify_document import classify_document
from backend.tools.extract_document import extract_document
from backend.tools.search_employees import search_employees
from backend.tools.create_employee import create_employee
from backend.tools.update_employee import update_employee
from backend.tools.compare_names import compare_names
from backend.services.rag import index_document

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "classify_document",
        "description": "Classify document type from OCR text. Call first for every file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_index": {"type": "integer", "description": "Index into the files list"},
            },
            "required": ["file_index"],
        },
    },
    {
        "name": "extract_document",
        "description": "Run LLM extraction on a file given its detected doc_type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_index": {"type": "integer"},
                "doc_type": {"type": "string", "enum": ["iqama", "visa", "contract"]},
            },
            "required": ["file_index", "doc_type"],
        },
    },
    {
        "name": "search_employees",
        "description": "Find existing employee by iqama_number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "iqama_number": {"type": "string"},
            },
            "required": ["iqama_number"],
        },
    },
    {
        "name": "compare_names",
        "description": "Fuzzy-match two names to catch transliteration variants.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_a": {"type": "string"},
                "name_b": {"type": "string"},
            },
            "required": ["name_a", "name_b"],
        },
    },
    {
        "name": "create_employee",
        "description": "Create a new employee from extracted fields.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_index": {"type": "integer"},
            },
            "required": ["file_index"],
        },
    },
    {
        "name": "update_employee",
        "description": "Update an existing employee with fields from a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string"},
                "file_index": {"type": "integer"},
            },
            "required": ["employee_id", "file_index"],
        },
    },
]

SYSTEM_PROMPT = """You are an HR document onboarding agent for Saudi workplace compliance.

You will receive a list of files (by index). For each file:
1. classify_document → get doc_type
2. extract_document → get structured fields
3. If iqama: search_employees by iqama_number
   - If found: compare_names(extracted vs existing), then update_employee
   - If not found: create_employee
4. Move to next file

Process ALL files before finishing. Be efficient — do not call tools unnecessarily.
After all files are processed, respond with a JSON summary:
{"processed": N, "created": M, "updated": K, "flagged": [...]}

flagged = list of {file_index, reason} for files with errors or name mismatches below 0.7."""


async def run_agent(
    files: list[dict],
    company_id: str,
    user_id: str,
) -> AsyncGenerator[dict, None]:
    """Yields progress events; caller streams them as SSE."""

    lf = get_tracer()
    trace = None
    try:
        if lf:
            trace = lf.trace(
                name="onboard_agent",
                user_id=user_id,
                metadata={"company_id": company_id, "file_count": len(files)},
            )
    except Exception:
        trace = None

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    state: dict[int, dict] = {}
    for i, f in enumerate(files):
        state[i] = {
            "name": f["name"],
            "raw_text": f["raw_text"],
            "contents": f["contents"],
            "content_type": f["content_type"],
        }

    messages = [
        {
            "role": "user",
            "content": f"Process these {len(files)} files: "
            + json.dumps([{"index": i, "name": f["name"]} for i, f in enumerate(files)]),
        },
    ]

    async def _dispatch(name: str, args: dict) -> tuple[str, dict]:
        idx = args.get("file_index")
        s = state.get(idx, {}) if idx is not None else {}

        span = None
        t0 = time.monotonic()
        try:
            if trace:
                span = trace.span(name=name, input=args, metadata={"file": s.get("name")})
        except Exception:
            span = None

        try:
            if name == "classify_document":
                result = await classify_document(s["raw_text"])
                state[idx]["doc_type"] = result["doc_type"]

            elif name == "extract_document":
                db = get_db()
                file_hash = hashlib.sha256(s["contents"]).hexdigest()

                # Reuse cached extraction — skip LLM but still populate state for create_employee
                existing = await db.documents.find_one({
                    "file_hash": file_hash,
                    "company_id": ObjectId(company_id),
                })
                if existing:
                    state[idx]["fields"] = existing["extracted_fields"]
                    state[idx]["raw_text"] = existing.get("raw_text", "")
                    state[idx]["document_id"] = str(existing["_id"])
                    result = {"fields": existing["extracted_fields"], "cached": True}
                else:
                    extracted = await extract_document(s["contents"], s["content_type"], args["doc_type"])
                    state[idx]["fields"] = extracted["fields"]
                    state[idx]["raw_text"] = extracted["raw_text"]
                    doc = {
                        "company_id": ObjectId(company_id),
                        "employee_id": None,
                        "doc_type": args["doc_type"],
                        "file_hash": file_hash,
                        "extracted_fields": extracted["fields"],
                        "raw_text": extracted["raw_text"],
                        "llm_provider": extracted["provider"],
                        "tokens_used": extracted["tokens_used"],
                        "cost_usd": extracted["cost_usd"],
                        "created_at": datetime.now(timezone.utc),
                    }
                    inserted = await db.documents.insert_one(doc)
                    state[idx]["document_id"] = str(inserted.inserted_id)
                    try:
                        await index_document(
                            str(inserted.inserted_id), company_id,
                            args["doc_type"], extracted["raw_text"],
                            extracted_fields=extracted["fields"],
                        )
                    except Exception as e:
                        logger.error("agent_rag_index_failed file=%s error=%s", s["name"], str(e)[:200])
                    result = {"fields": extracted["fields"], "cached": False}

            elif name == "search_employees":
                result = await search_employees(args["iqama_number"], company_id)

            elif name == "compare_names":
                result = compare_names(args["name_a"], args["name_b"])

            elif name == "create_employee":
                employee_id = await create_employee(company_id, s.get("fields", {}))
                state[idx]["employee_id"] = employee_id
                result = {"employee_id": employee_id, "created": True}

            elif name == "update_employee":
                success = await update_employee(args["employee_id"], s.get("fields", {}))
                result = {"updated": success}

            else:
                result = {"error": f"unknown tool: {name}"}

            try:
                if span:
                    span.end(output=result, metadata={"latency_ms": round((time.monotonic() - t0) * 1000)})
            except Exception:
                pass

            return json.dumps(result), result

        except Exception as e:
            try:
                if span:
                    span.end(output={"error": str(e)}, level="ERROR")
            except Exception:
                pass
            raise

    MAX_ITERATIONS = len(files) * 8
    iterations = 0

    while iterations < MAX_ITERATIONS:
        iterations += 1

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if hasattr(b, "text")), "{}")
            raw = text[text.find("{"):text.rfind("}") + 1]
            try:
                summary = json.loads(raw)
            except Exception:
                summary = {"processed": len(files), "created": 0, "updated": 0, "flagged": []}

            try:
                if lf:
                    lf.flush()
            except Exception:
                pass

            yield {"type": "summary", "data": summary}
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            args = block.input

            yield {
                "type": "tool_start",
                "tool": tool_name,
                "input": args,
                "file": state.get(args.get("file_index", -1), {}).get("name"),
            }

            try:
                result_str, result_dict = await _dispatch(tool_name, args)
                yield {"type": "tool_end", "tool": tool_name, "output": result_dict}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                yield {"type": "tool_error", "tool": tool_name, "error": str(e)[:200]}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                    "is_error": True,
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    else:
        yield {"type": "error", "error": "Agent exceeded max iterations"}
