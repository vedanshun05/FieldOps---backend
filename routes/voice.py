"""Voice processing route — the main entry point for the AI pipeline."""

import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.transcription import transcribe_audio
from services.extraction import extract_job_data
from agent.orchestrator import execute_workflow
from schemas.extraction import VoiceResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["voice"])


@router.post("/voice", response_model=VoiceResponse)
async def process_voice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Process a voice note through the full AI pipeline:
    1. Transcribe audio (Whisper)
    2. Extract structured data (GPT)
    3. Execute autonomous workflow (Agent)
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

    return VoiceResponse(
        transcript=transcript,
        extraction=extraction,
        agent_result=agent_result,
        execution=agent_result.execution,
        agent_trace=agent_result.agent_trace,
    )
