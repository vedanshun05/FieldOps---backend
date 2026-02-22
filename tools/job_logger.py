"""Tool: Log a completed job to the database."""

import logging
from sqlalchemy.orm import Session

from models.models import Job
from schemas.extraction import JobExtraction, ToolResult

logger = logging.getLogger(__name__)


def log_job(extraction: JobExtraction, db: Session) -> ToolResult:
    """
    Create a job record from the extracted data.

    Always runs — every voice note creates a job log entry.
    """
    logger.info(f"Logging job for {extraction.customer_name}...")

    try:
        job = Job(
            customer_name=extraction.customer_name or "Unknown",
            job_type=extraction.job_type or "General",
            materials_used=[m.model_dump() for m in extraction.materials_used],
            labor_hours=extraction.labor_hours or 0.0,
            status="completed",
            transcript=extraction.raw_transcript,
            confidence_score=extraction.confidence_score,
        )
        db.add(job)
        db.flush()  # Get the ID without committing

        logger.info(f"Job logged: ID={job.id}")
        return ToolResult(
            tool_name="log_job",
            success=True,
            message=f"Job logged for {extraction.customer_name} (ID: {job.id})",
            data={"job_id": job.id},
        )

    except Exception as e:
        logger.error(f"Failed to log job: {str(e)}")
        return ToolResult(
            tool_name="log_job",
            success=False,
            message=f"Failed to log job: {str(e)}",
        )
