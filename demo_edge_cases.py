"""FieldOps AI — Edge Case Demo Script.

Tests the AI extraction + agent workflow pipeline with tricky voice transcripts.
Runs directly against the internal Python functions (no server needed).

Usage:
    source venv/bin/activate
    python demo_edge_cases.py
"""

import asyncio
import json
import logging
import sys

from database import SessionLocal, init_db
from services.extraction import extract_job_data
from agent.orchestrator import execute_workflow

# Pretty logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s",
    datefmt="%H:%M:%S",
)

# ─── Edge-case transcripts ───────────────────────────────────────────────

EDGE_CASES = [
    {
        "name": "✅ Standard Job (Baseline)",
        "transcript": "Finished the Sharma job. Used 3 copper pipes, worked 2 hours. Heater is old — follow up in 6 months.",
        "expect": "Full pipeline: job logged, inventory updated, invoice generated, follow-up scheduled.",
    },
    {
        "name": "🚫 No Materials Used",
        "transcript": "Maintenance check at 123 Main Street for Mr. Gupta. Everything looks good, no repairs needed. 1 hour of labor. Don't bill them for this.",
        "expect": "Job logged only. No inventory update, no invoice (invoice_required=False), no follow-up.",
    },
    {
        "name": "🔧 Multiple Materials",
        "transcript": "Just wrapped up the HVAC repair for Patel Industries. Took 4 hours. Replaced 2 air filters, 1 thermostat, and 3 copper pipes. System running smoothly now.",
        "expect": "All 3 material types decremented. Invoice generated. No follow-up.",
    },
    {
        "name": "📅 Vague Follow-up Date",
        "transcript": "Fixed the leaking sink at Mrs. Kumar's place. Used 1 washer. Worked half an hour. The pipes under the house are old, should come back sometime next month to inspect.",
        "expect": "Follow-up date should be inferred (~30 days). 0.5 labor hours parsed correctly.",
    },
    {
        "name": "🗣️ Messy/Rambling Speech",
        "transcript": "Uh yeah so I went to the uh, the Verma residence right, and um, did some electrical work. Changed like 2 light switches I think. Was there for about 3 hours, maybe 3 and a half. Oh and tell them we'll send the bill.",
        "expect": "Should extract customer='Verma', job_type=electrical, 2 light switches, ~3-3.5 hours. invoice_required=True.",
    },
    {
        "name": "⚡ Zero Labor Hours",
        "transcript": "Quick stop at Reddy's shop to drop off 5 PVC pipes they ordered. No work done, just delivery.",
        "expect": "0 labor hours. No invoice. Inventory should update for 5 PVC pipes.",
    },
]


def print_separator():
    print("\n" + "=" * 70)


def print_result(extraction, agent_result):
    """Pretty-print extraction and agent results."""
    print(f"\n  📋 Extracted Data:")
    print(f"     Customer:    {extraction.customer_name}")
    print(f"     Job Type:    {extraction.job_type}")
    print(f"     Labor Hours: {extraction.labor_hours}")
    print(f"     Invoice:     {extraction.invoice_required}")
    print(f"     Confidence:  {extraction.confidence_score:.0%}")

    if extraction.materials_used:
        print(f"     Materials:")
        for m in extraction.materials_used:
            print(f"       - {m.quantity}x {m.item} ({m.unit})")
    else:
        print(f"     Materials:   (none)")

    if extraction.follow_up_date:
        print(f"     Follow-up:   {extraction.follow_up_date} — {extraction.follow_up_reason or 'N/A'}")
    else:
        print(f"     Follow-up:   (none)")

    print(f"\n  🤖 Agent Execution:")
    print(f"     Tools Run:   {', '.join(agent_result.tools_executed) or '(none)'}")
    print(f"     Success:     {agent_result.success}")
    print(f"     Summary:     {agent_result.summary}")

    if agent_result.agent_trace:
        print(f"\n  📊 Trace:")
        for t in agent_result.agent_trace:
            extra = ""
            if t.amount:
                extra = f" (${t.amount:.2f})"
            if t.due_date:
                extra = f" ({t.due_date})"
            print(f"       → {t.step}{extra}")


async def run_demo():
    print("=" * 70)
    print("🚀 FIELDOPS AI — EDGE CASE DEMO")
    print("=" * 70)

    # Initialize DB
    init_db()

    passed = 0
    failed = 0

    for i, case in enumerate(EDGE_CASES, 1):
        print_separator()
        print(f"  TEST {i}/{len(EDGE_CASES)}: {case['name']}")
        print(f"  🎙️  \"{case['transcript'][:100]}...\"")
        print(f"  🎯  Expected: {case['expect']}")

        db = SessionLocal()
        try:
            # Step 1: Extract
            extraction = await extract_job_data(case["transcript"])

            # Step 2: Orchestrate
            result = execute_workflow(extraction, db)

            print_result(extraction, result)

            if result.success:
                passed += 1
                print(f"\n  ✅ PASSED")
            else:
                failed += 1
                print(f"\n  ❌ FAILED — {result.summary}")

        except Exception as e:
            failed += 1
            print(f"\n  💥 ERROR: {e}")

        finally:
            db.close()

    print_separator()
    print(f"\n  📊 Results: {passed}/{len(EDGE_CASES)} passed, {failed} failed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_demo())
