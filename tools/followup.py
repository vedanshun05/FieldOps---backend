"""Tool: Schedule a follow-up appointment."""

import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from models.models import FollowUp
from schemas.extraction import JobExtraction, ToolResult

logger = logging.getLogger(__name__)


def _parse_follow_up_date(date_str: str) -> date:
    """
    Parse a follow-up date string — handles both ISO dates and relative expressions.

    Examples:
        "2025-08-15" → date(2025, 8, 15)
        "6 months" → today + 6 months
        "2 weeks" → today + 14 days
        "next month" → today + 1 month
    """
    date_str = date_str.strip().lower()
    today = date.today()

    # Try ISO format first
    try:
        parsed = date_parser.parse(date_str).date()
        if parsed > today:
            return parsed
    except (ValueError, TypeError):
        pass

    # Relative date parsing
    if "month" in date_str:
        try:
            num = int("".join(filter(str.isdigit, date_str)) or "1")
            return today + relativedelta(months=num)
        except ValueError:
            return today + relativedelta(months=1)

    if "week" in date_str:
        try:
            num = int("".join(filter(str.isdigit, date_str)) or "1")
            return today + timedelta(weeks=num)
        except ValueError:
            return today + timedelta(weeks=1)

    if "year" in date_str:
        try:
            num = int("".join(filter(str.isdigit, date_str)) or "1")
            return today + relativedelta(years=num)
        except ValueError:
            return today + relativedelta(years=1)

    if "day" in date_str:
        try:
            num = int("".join(filter(str.isdigit, date_str)) or "1")
            return today + timedelta(days=num)
        except ValueError:
            return today + timedelta(days=1)

    # Default: 1 month from now
    logger.warning(f"Could not parse follow-up date '{date_str}', defaulting to 1 month")
    return today + relativedelta(months=1)


def schedule_followup(extraction: JobExtraction, job_id: int, db: Session) -> ToolResult:
    """
    Schedule a follow-up based on extracted date/reason.

    Only runs when follow_up_date is present.
    """
    if not extraction.follow_up_date:
        return ToolResult(
            tool_name="schedule_followup",
            success=True,
            message="No follow-up needed",
        )

    logger.info(f"Scheduling follow-up for {extraction.customer_name}...")

    try:
        scheduled_date = _parse_follow_up_date(extraction.follow_up_date)

        follow_up = FollowUp(
            job_id=job_id,
            customer_name=extraction.customer_name or "Unknown",
            scheduled_date=scheduled_date,
            reason=extraction.follow_up_reason or "General follow-up",
            status="pending",
        )
        db.add(follow_up)
        db.flush()

        logger.info(f"Follow-up scheduled: {scheduled_date} for {extraction.customer_name}")

        return ToolResult(
            tool_name="schedule_followup",
            success=True,
            message=f"Follow-up scheduled for {scheduled_date.isoformat()}",
            data={
                "follow_up_id": follow_up.id,
                "scheduled_date": scheduled_date.isoformat(),
                "reason": follow_up.reason,
            },
        )

    except Exception as e:
        logger.error(f"Failed to schedule follow-up: {str(e)}")
        return ToolResult(
            tool_name="schedule_followup",
            success=False,
            message=f"Failed to schedule follow-up: {str(e)}",
        )
