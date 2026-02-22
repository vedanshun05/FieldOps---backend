"""Agent orchestrator — the core AI depth component.

Receives structured extraction data, determines which tools to call,
executes them in the correct order, logs reasoning traces, and handles failures.
"""

import logging
from sqlalchemy.orm import Session

from schemas.extraction import (
    JobExtraction, AgentResult, AgentStep, ToolResult,
    ExecutionSummary, AgentTraceStep
)
from tools.job_logger import log_job
from tools.inventory import update_inventory
from tools.invoice import generate_invoice
from tools.followup import schedule_followup
from tools.revenue import update_revenue

logger = logging.getLogger(__name__)


def _determine_tools(extraction: JobExtraction) -> list[dict]:
    """
    Analyze extraction data and determine which tools to call.

    Business rules:
    1. Always log the job (mandatory)
    2. If materials_used is not empty → update inventory
    3. If invoice_required is True → generate invoice
    4. If invoice generated → update revenue
    5. If follow_up_date exists → schedule follow-up
    """
    tools = []

    # Rule 1: Always log the job
    tools.append({
        "name": "log_job",
        "reasoning": "Every completed job must be logged for tracking and audit purposes.",
    })

    # Rule 2: Materials → inventory
    if extraction.materials_used:
        materials_list = ", ".join(f"{m.quantity} {m.item}" for m in extraction.materials_used)
        tools.append({
            "name": "update_inventory",
            "reasoning": f"Materials were used ({materials_list}). Inventory must be decremented to maintain accurate stock levels.",
        })

    # Rule 3: Invoice
    if extraction.invoice_required:
        tools.append({
            "name": "generate_invoice",
            "reasoning": f"Job is billable ({extraction.labor_hours}h labor). Invoice must be generated for the customer.",
        })
        # Rule 4: Revenue follows invoice
        tools.append({
            "name": "update_revenue",
            "reasoning": "Invoice was generated. Revenue entry must be recorded for financial tracking.",
        })

    # Rule 5: Follow-up
    if extraction.follow_up_date:
        tools.append({
            "name": "schedule_followup",
            "reasoning": f"Follow-up requested: '{extraction.follow_up_date}' — {extraction.follow_up_reason or 'general follow-up'}. Must be scheduled.",
        })

    return tools


def execute_workflow(extraction: JobExtraction, db: Session) -> AgentResult:
    """
    Execute the full autonomous workflow:
    1. Analyze extraction
    2. Determine required tools based on business rules
    3. Execute tools in correct order with reasoning traces
    4. Handle failures gracefully
    5. Return full execution report
    """
    logger.info("=" * 60)
    logger.info("AGENT ORCHESTRATOR — Starting workflow")
    logger.info(f"Customer: {extraction.customer_name}")
    logger.info(f"Job Type: {extraction.job_type}")
    logger.info("=" * 60)

    steps: list[AgentStep] = []
    tools_executed: list[str] = []
    job_id: int | None = None
    invoice_amount: float = 0.0
    
    execution_summary = ExecutionSummary()
    agent_trace: list[AgentTraceStep] = []

    # Step 1: Analyze and plan
    planned_tools = _determine_tools(extraction)
    steps.append(AgentStep(
        step_number=1,
        action="analyze_extraction",
        reasoning=f"Analyzed voice transcript. Identified {len(planned_tools)} actions required: {', '.join(t['name'] for t in planned_tools)}.",
    ))
    logger.info(f"Step 1: Planned {len(planned_tools)} tools: {[t['name'] for t in planned_tools]}")

    # Step 2+: Execute each tool
    step_num = 2
    for tool_plan in planned_tools:
        tool_name = tool_plan["name"]
        reasoning = tool_plan["reasoning"]

        logger.info(f"Step {step_num}: Executing {tool_name}...")
        logger.info(f"  Reasoning: {reasoning}")

        result: ToolResult | None = None

        try:
            if tool_name == "log_job":
                result = log_job(extraction, db)
                if result.success and result.data:
                    job_id = result.data.get("job_id")

            elif tool_name == "update_inventory":
                result = update_inventory(extraction, db)

            elif tool_name == "generate_invoice":
                if job_id is None:
                    result = ToolResult(
                        tool_name="generate_invoice",
                        success=False,
                        message="Cannot generate invoice: job_id not available",
                    )
                else:
                    result = generate_invoice(extraction, job_id, db)
                    if result.success and result.data:
                        invoice_amount = result.data.get("total_amount", 0.0)

            elif tool_name == "update_revenue":
                if job_id is None or invoice_amount <= 0:
                    result = ToolResult(
                        tool_name="update_revenue",
                        success=False,
                        message="Cannot record revenue: no invoice generated",
                    )
                else:
                    result = update_revenue(job_id, invoice_amount, db)

            elif tool_name == "schedule_followup":
                if job_id is None:
                    result = ToolResult(
                        tool_name="schedule_followup",
                        success=False,
                        message="Cannot schedule follow-up: job_id not available",
                    )
                else:
                    result = schedule_followup(extraction, job_id, db)

        except Exception as e:
            logger.error(f"Tool {tool_name} crashed: {str(e)}")
            result = ToolResult(
                tool_name=tool_name,
                success=False,
                message=f"Unexpected error: {str(e)}",
            )

        # Log step
        step = AgentStep(
            step_number=step_num,
            action=f"execute_{tool_name}",
            reasoning=reasoning,
            tool_name=tool_name,
            result=result,
        )
        steps.append(step)

        if result and result.success:
            tools_executed.append(tool_name)
            logger.info(f"  ✓ {tool_name}: {result.message}")
            
            # --- Populate Agent Trace and Summary ---
            if tool_name == "log_job":
                execution_summary.job_logged = True
                agent_trace.append(AgentTraceStep(step="JOB_LOGGED"))
                
            elif tool_name == "update_inventory":
                execution_summary.inventory_updated = True
                if result.data:
                    agent_trace.append(AgentTraceStep(
                        step="INVENTORY_UPDATED",
                        before=result.data.get("before"),
                        after=result.data.get("after")
                    ))
                    execution_summary.low_stock_items = result.data.get("low_stock", [])
                    
            elif tool_name == "generate_invoice":
                execution_summary.invoice_generated = True
                if result.data:
                    amt = result.data.get("total_amount", 0.0)
                    agent_trace.append(AgentTraceStep(
                        step="INVOICE_GENERATED",
                        amount=amt
                    ))
                    
            elif tool_name == "update_revenue":
                execution_summary.revenue_added = invoice_amount
                agent_trace.append(AgentTraceStep(
                    step="REVENUE_RECORDED",
                    amount=invoice_amount
                ))
                
            elif tool_name == "schedule_followup":
                execution_summary.followup_scheduled = True
                if result.data:
                    due = result.data.get("scheduled_date")
                    execution_summary.next_followup_date = due
                    agent_trace.append(AgentTraceStep(
                        step="FOLLOWUP_SCHEDULED",
                        due_date=due
                    ))
            # ----------------------------------------
            
        else:
            msg = result.message if result else "Unknown error"
            logger.warning(f"  ✗ {tool_name}: {msg}")

        step_num += 1

    # Commit all changes
    try:
        db.commit()
        logger.info("Database changes committed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit DB changes: {str(e)}")
        return AgentResult(
            extraction=extraction,
            steps=steps,
            tools_executed=tools_executed,
            success=False,
            summary=f"Workflow failed at commit stage: {str(e)}",
        )

    # Build summary
    summary_parts = []
    if job_id:
        summary_parts.append(f"Job #{job_id} logged for {extraction.customer_name}")
    if "update_inventory" in tools_executed:
        summary_parts.append(f"{len(extraction.materials_used)} inventory items updated")
    if "generate_invoice" in tools_executed:
        summary_parts.append(f"Invoice generated: ${invoice_amount:.2f}")
    if "update_revenue" in tools_executed:
        summary_parts.append(f"Revenue recorded: ${invoice_amount:.2f}")
    if "schedule_followup" in tools_executed:
        summary_parts.append(f"Follow-up scheduled: {extraction.follow_up_date}")

    summary = " | ".join(summary_parts)

    logger.info("=" * 60)
    logger.info(f"AGENT COMPLETE: {summary}")
    logger.info(f"Tools executed: {len(tools_executed)}/{len(planned_tools)}")
    logger.info("=" * 60)

    return AgentResult(
        extraction=extraction,
        steps=steps,
        tools_executed=tools_executed,
        success=True,
        summary=summary,
        execution=execution_summary,
        agent_trace=agent_trace,
    )
