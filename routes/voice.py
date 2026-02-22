"""Voice processing route — the main entry point for the AI pipeline."""

import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.transcription import transcribe_audio
from services.extraction import extract_job_data
from agent.orchestrator import execute_workflow
from schemas.extraction import (
    VoiceResponse, AIExtractionSchema, ExecutionSchema, ResponseSchema
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["voice"])


def _build_ai_extraction(extraction, transcript: str) -> AIExtractionSchema:
    """Schema 1: Build the raw AI extraction view (LLM-friendly, semantic)."""
    intents = ["log_job"]
    if extraction.materials_used:
        intents.append("update_inventory")
    if extraction.invoice_required:
        intents.append("create_invoice")
    if extraction.follow_up_date:
        intents.append("schedule_followup")

    return AIExtractionSchema(
        customer_name=extraction.customer_name or "Unknown",
        service_type=extraction.job_type or "General",
        materials_mentioned=[
            {"item_name": m.item, "quantity": m.quantity}
            for m in extraction.materials_used
        ],
        labor_mentioned={"duration_text": f"worked {extraction.labor_hours} hours"},
        follow_up_mentioned={
            "is_required": extraction.follow_up_date is not None,
            "time_text": extraction.follow_up_date,
            "reason_text": extraction.follow_up_reason,
        },
        job_status_text="completed" if extraction.invoice_required else "pending",
        notes=transcript[:200] if len(transcript) > 200 else transcript,
        intents=intents,
    )


def _build_execution_schema(extraction, transcript: str) -> ExecutionSchema:
    """Schema 2: Build the deterministic execution contract for backend tools."""
    # Calculate follow-up days from relative text
    after_days = None
    if extraction.follow_up_date:
        text = extraction.follow_up_date.lower()
        if "month" in text:
            try:
                num = int("".join(c for c in text if c.isdigit()) or "6")
                after_days = num * 30
            except ValueError:
                after_days = 180
        elif "week" in text:
            try:
                num = int("".join(c for c in text if c.isdigit()) or "1")
                after_days = num * 7
            except ValueError:
                after_days = 7
        elif "day" in text:
            try:
                num = int("".join(c for c in text if c.isdigit()) or "1")
                after_days = num
            except ValueError:
                after_days = 1

    actions = ["log_job"]
    if extraction.materials_used:
        actions.append("update_inventory")
    if extraction.invoice_required:
        actions.extend(["create_invoice", "update_analytics"])
    if extraction.follow_up_date:
        actions.append("schedule_followup")

    return ExecutionSchema(
        customer={"name": extraction.customer_name or "Unknown", "phone": None},
        job={
            "service_type": extraction.job_type or "General",
            "status": "completed" if extraction.invoice_required else "pending",
            "notes": transcript[:200],
        },
        labor={
            "hours": extraction.labor_hours or 0,
            "rate_per_hour": settings.LABOR_RATE_PER_HOUR,
        },
        materials=[
            {"item": m.item, "quantity": m.quantity, "unit_cost": None}
            for m in extraction.materials_used
        ],
        follow_up={
            "required": extraction.follow_up_date is not None,
            "after_days": after_days,
            "reason": extraction.follow_up_reason,
        },
        invoice={"generate": extraction.invoice_required},
        actions=actions,
        meta={
            "source": "voice_note",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


def _build_response_schema(extraction, agent_result, transcript: str) -> ResponseSchema:
    """Schema 3: Build the UI response — what changed, not how."""
    ex = agent_result.execution
    return ResponseSchema(
        transcript=transcript,
        job_logged=ex.job_logged,
        inventory_updated=ex.inventory_updated,
        invoice_generated=ex.invoice_generated,
        followup_scheduled=ex.followup_scheduled,
        revenue_added=ex.revenue_added,
        low_stock_items=ex.low_stock_items,
        next_followup_date=ex.next_followup_date,
        job_summary={
            "customer_name": extraction.customer_name or "Unknown",
            "service_type": extraction.job_type or "General",
            "labor_hours": extraction.labor_hours or 0,
            "materials_used": [
                {"item": m.item, "quantity": m.quantity}
                for m in extraction.materials_used
            ],
        },
    )


@router.post("/voice", response_model=VoiceResponse)
async def process_voice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Process a voice note through the full 3-schema AI pipeline:
    1. Transcribe audio (Whisper)
    2. Extract structured data (LLM) → AI Extraction Schema
    3. Normalize → Execution Schema (agent contract)
    4. Execute autonomous workflow (Agent)
    5. Build → Response Schema (UI state)
    """
    logger.info(f"Received voice file: {file.filename}, type: {file.content_type}")

    # Validate file type
    allowed_types = ["audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/x-m4a", "video/webm"]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {file.content_type}. Use webm, wav, mp3, or m4a.",
        )

    # Step 1: Transcribe
    try:
        transcript = await transcribe_audio(file)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    # Step 2: Extract structured data
    try:
        extraction = await extract_job_data(transcript)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Data extraction failed: {str(e)}")

    # Step 3: Execute agent workflow
    try:
        agent_result = execute_workflow(extraction, db)
    except Exception as e:
        logger.error(f"Agent workflow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

    # Build 3-schema pipeline views
    ai_extraction = _build_ai_extraction(extraction, transcript)
    execution_schema = _build_execution_schema(extraction, transcript)
    response_schema = _build_response_schema(extraction, agent_result, transcript)

    return VoiceResponse(
        transcript=transcript,
        extraction=extraction,
        agent_result=agent_result,
        execution=agent_result.execution,
        agent_trace=agent_result.agent_trace,
        ai_extraction=ai_extraction,
        execution_schema=execution_schema,
        response_schema=response_schema,
    )
