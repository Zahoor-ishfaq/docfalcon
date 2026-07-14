from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json, anthropic

from backend.core.dependencies import get_current_user
from backend.core.config import settings
from backend.core.tracing import get_tracer, trace_generation

from backend.tools.get_expiring_documents import get_expiring_documents
from backend.tools.get_employee_summary import get_employee_summary
from backend.tools.check_name_mismatch import check_name_mismatch

router = APIRouter(prefix="/compliance", tags=["compliance"])

MODEL = "claude-haiku-4-5-20251001"

TOOLS = [
    {
        "name": "get_expiring_documents",
        "description": "Find employees with iqama, passport, or visa expiring within N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Lookahead window in days", "default": 30}
            },
            "required": [],
        },
    },
    {
        "name": "get_employee_summary",
        "description": "Get all document fields and expiry status for a single employee by name or iqama number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_or_iqama": {"type": "string", "description": "Employee name (partial) or iqama number"}
            },
            "required": ["name_or_iqama"],
        },
    },
    {
        "name": "check_name_mismatch",
        "description": "Find employees where the name on the iqama does not match the name on the contract.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

SYSTEM = (
    "You are a Saudi HR compliance assistant. "
    "Answer only using the provided tools — never invent data. "
    "Be concise and factual. Format dates as YYYY-MM-DD."
)


async def _dispatch(tool_name: str, tool_input: dict, company_id: str) -> str:
    if tool_name == "get_expiring_documents":
        result = await get_expiring_documents(company_id, tool_input.get("days", 30))
    elif tool_name == "get_employee_summary":
        result = await get_employee_summary(company_id, tool_input["name_or_iqama"])
    elif tool_name == "check_name_mismatch":
        result = await check_name_mismatch(company_id)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result, default=str)


class AskRequest(BaseModel):
    query: str


@router.post("/ask")

async def ask(request: Request, body: AskRequest, user=Depends(get_current_user)):
    company_id = user["company_id"]
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def stream():
        messages = [{"role": "user", "content": body.query}]
        tools_used = []
        total_in, total_out = 0, 0

        # agentic loop — max 5 iterations to guard against runaway
        for _ in range(5):
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM,
                tools=TOOLS,
                messages=messages,
            )

            total_in += response.usage.input_tokens
            total_out += response.usage.output_tokens

            tool_calls = [b for b in response.content if b.type == "tool_use"]
            for tc in tool_calls:
                yield f"data: {json.dumps({'type': 'tool', 'name': tc.name, 'input': tc.input})}\n\n"

            if response.stop_reason != "tool_use":
                answer = next((b.text for b in response.content if hasattr(b, "text")), "")
                yield f"data: {json.dumps({'type': 'answer', 'text': answer, 'tools_used': tools_used})}\n\n"
                yield "data: [DONE]\n\n"

                cost_usd = round((total_in / 1_000_000) * 1.0 + (total_out / 1_000_000) * 5.0, 6)
                trace_generation(
                    get_tracer(),
                    trace_name="compliance_ask",
                    model=MODEL,
                    input=body.query,
                    output=answer,
                    input_tokens=total_in,
                    output_tokens=total_out,
                    cost_usd=cost_usd,
                )
                return

            tool_results = []
            for tc in tool_calls:
                tools_used.append(tc.name)
                result_str = await _dispatch(tc.name, tc.input, company_id)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result_str,
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        yield f"data: {json.dumps({'type': 'error', 'text': 'Agent loop limit reached'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
