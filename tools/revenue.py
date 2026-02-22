"""Tool: Record revenue from an invoice."""

import logging
from datetime import date
from sqlalchemy.orm import Session

from models.models import RevenueEntry
from schemas.extraction import ToolResult

logger = logging.getLogger(__name__)


def update_revenue(job_id: int, amount: float, db: Session) -> ToolResult:
    """
    Record a revenue entry from a generated invoice.

    Only runs after a successful invoice generation.
    """
    if amount <= 0:
        return ToolResult(
            tool_name="update_revenue",
            success=True,
            message="No revenue to record",
        )

    logger.info(f"Recording revenue: ${amount:.2f} from job {job_id}...")

    try:
        entry = RevenueEntry(
            date=date.today(),
            amount=amount,
            source="invoice",
            job_id=job_id,
        )
        db.add(entry)
        db.flush()

        logger.info(f"Revenue recorded: ${amount:.2f}")

        return ToolResult(
            tool_name="update_revenue",
            success=True,
            message=f"Revenue of ${amount:.2f} recorded",
            data={"revenue_id": entry.id, "amount": amount},
        )

    except Exception as e:
        logger.error(f"Failed to record revenue: {str(e)}")
        return ToolResult(
            tool_name="update_revenue",
            success=False,
            message=f"Failed to record revenue: {str(e)}",
        )
