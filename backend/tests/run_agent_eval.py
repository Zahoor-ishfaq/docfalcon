"""Agent eval — 10 synthetic ZIPs from existing samples. Target: ≥80% task success."""

import asyncio
import io
import json
import os
import zipfile
from pathlib import Path

SAMPLES = Path(__file__).parent.parent.parent.parent / "docs" / "samples"
RESULTS_PATH = Path(__file__).parent / "agent_eval_results.json"

# Each scenario: list of (relative_path, expected_doc_type)
# Built from existing samples — iqamas + contracts + visas
SCENARIOS = [
    # Single iqama
    [("iqama/iqama_01.png", "iqama")],
    [("iqama/iqama_02.png", "iqama")],
    # Single contract
    [("contract/contract_01.pdf", "contract")],
    [("contract/contract_02.pdf", "contract")],
    # Single visa
    [("visa/visa_01.png", "visa")],
    # Iqama + contract (same employee — agent should create once)
    [("iqama/iqama_03.png", "iqama"), ("contract/contract_03.pdf", "contract")],
    # Two iqamas (different employees)
    [("iqama/iqama_04.png", "iqama"), ("iqama/iqama_05.png", "iqama")],
    # Iqama + visa
    [("iqama/iqama_06.png", "iqama"), ("visa/visa_02.png", "visa")],
    # Mixed: iqama + contract + visa
    [("iqama/iqama_07.png", "iqama"), ("contract/contract_04.pdf", "contract"), ("visa/visa_03.png", "visa")],
    # Two contracts
    [("contract/contract_05.pdf", "contract"), ("iqama/iqama_08.png", "iqama")],
]


def _build_zip(scenario: list[tuple[str, str]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for rel_path, _ in scenario:
            full = SAMPLES / rel_path
            if full.exists():
                zf.write(full, arcname=full.name)
    buf.seek(0)
    return buf.read()


async def _run_scenario(idx: int, scenario: list[tuple[str, str]]) -> dict:
    """Run one scenario through the agent, return eval result."""
    import httpx

    zip_bytes = _build_zip(scenario)
    existing_files = [s for s in scenario if (SAMPLES / s[0]).exists()]
    expected_doc_types = [dt for _, dt in existing_files]

    # Hit the live API — requires backend running on 8000 with a valid token
    token = os.environ.get("EVAL_TOKEN", "")
    if not token:
        return {"scenario": idx, "skipped": True, "reason": "EVAL_TOKEN not set"}

    events = []
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/onboard",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("eval.zip", zip_bytes, "application/zip")},
        ) as resp:
            if resp.status_code != 200:
                return {"scenario": idx, "error": f"HTTP {resp.status_code}", "task_success": False}
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        events.append(json.loads(line[6:]))
                    except Exception:
                        pass

    tool_calls = [e for e in events if e.get("type") in ("tool_start", "tool_end")]
    errors = [e for e in events if e.get("type") == "tool_error"]
    summary = next((e["data"] for e in events if e.get("type") == "summary"), {})

    # Task success: got a summary with no crashes, processed count matches file count
    processed = summary.get("processed", 0)
    task_success = (
        processed == len(existing_files)
        and len(errors) == 0
        and "processed" in summary
    )

    # Tool accuracy: classify was called for each file, extract was called for each file
    classify_calls = sum(1 for e in tool_calls if e.get("tool") == "classify_document" and e.get("type") == "tool_start")
    extract_calls = sum(1 for e in tool_calls if e.get("tool") == "extract_document" and e.get("type") == "tool_start")
    tool_accuracy = (classify_calls == len(existing_files) and extract_calls == len(existing_files))

    return {
        "scenario": idx,
        "files": [s[0] for s in existing_files],
        "task_success": task_success,
        "tool_accuracy": tool_accuracy,
        "tool_calls_total": len(tool_calls) // 2,  # start+end pairs
        "errors": len(errors),
        "summary": summary,
    }


async def main():
    print(f"Running {len(SCENARIOS)} agent eval scenarios...\n")
    results = []
    for i, scenario in enumerate(SCENARIOS):
        print(f"Scenario {i+1}/{len(SCENARIOS)}: {[s[0] for s in scenario]}")
        result = await _run_scenario(i + 1, scenario)
        results.append(result)
        status = "✅ PASS" if result.get("task_success") else ("⏭ SKIP" if result.get("skipped") else "❌ FAIL")
        print(f"  {status} — {result}\n")

    runnable = [r for r in results if not r.get("skipped")]
    if runnable:
        task_success_rate = sum(1 for r in runnable if r.get("task_success")) / len(runnable)
        tool_accuracy_rate = sum(1 for r in runnable if r.get("tool_accuracy")) / len(runnable)
        avg_tool_calls = sum(r.get("tool_calls_total", 0) for r in runnable) / len(runnable)

        print("=" * 50)
        print(f"Task success rate : {task_success_rate:.1%}  (target ≥80%)")
        print(f"Tool accuracy rate: {tool_accuracy_rate:.1%}")
        print(f"Avg tool calls    : {avg_tool_calls:.1f}")
        print(f"{'PASS' if task_success_rate >= 0.8 else 'FAIL'}")

        summary = {
            "task_success_rate": round(task_success_rate, 3),
            "tool_accuracy_rate": round(tool_accuracy_rate, 3),
            "avg_tool_calls": round(avg_tool_calls, 1),
            "pass": task_success_rate >= 0.8,
            "scenarios": results,
        }
    else:
        print("All scenarios skipped — set EVAL_TOKEN env var to a valid JWT access token.")
        summary = {"skipped": True, "scenarios": results}

    RESULTS_PATH.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved to {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())