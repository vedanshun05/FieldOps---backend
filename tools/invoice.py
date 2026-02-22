"""Tool: Generate an invoice for a completed job."""

import logging
from sqlalchemy.orm import Session

from models.models import Invoice
from schemas.extraction import JobExtraction, ToolResult
from config import settings

logger = logging.getLogger(__name__)

# Default material costs (for demo — in production, this would be a DB lookup)
DEFAULT_MATERIAL_COSTS = {
    "copper pipe": 25.0,
    "pvc pipe": 12.0,
    "wire": 8.0,
    "circuit breaker": 35.0,
    "faucet": 45.0,
    "valve": 20.0,
    "fitting": 5.0,
    "filter": 15.0,
    "thermostat": 60.0,
    "insulation": 10.0,
}


def _estimate_material_cost(item_name: str, quantity: int) -> float:
    """Estimate cost of a material based on name matching."""
    item_lower = item_name.lower()
    for key, cost in DEFAULT_MATERIAL_COSTS.items():
        if key in item_lower:
            return cost * quantity
    # Default: $10 per unit
    return 10.0 * quantity


def generate_invoice(extraction: JobExtraction, job_id: int, db: Session) -> ToolResult:
    """
    Generate an invoice with calculated labor and materials costs.

    Only runs when invoice_required is True.
    """
    if not extraction.invoice_required:
        return ToolResult(
            tool_name="generate_invoice",
            success=True,
            message="Invoice not required",
        )

    logger.info(f"Generating invoice for job {job_id}...")

    try:
        # Calculate costs
        labor_hours_safe = extraction.labor_hours or 0.0
        labor_cost = labor_hours_safe * settings.LABOR_RATE_PER_HOUR
        materials_cost = sum(
            _estimate_material_cost(m.item, m.quantity)
            for m in extraction.materials_used
        )
        total = labor_cost + materials_cost

        invoice = Invoice(
            job_id=job_id,
            labor_cost=labor_cost,
            materials_cost=materials_cost,
            total_amount=total,
        )
        db.add(invoice)
        db.flush()

        logger.info(f"Invoice generated: ${total:.2f} (labor: ${labor_cost:.2f}, materials: ${materials_cost:.2f})")

        return ToolResult(
            tool_name="generate_invoice",
            success=True,
            message=f"Invoice generated: ${total:.2f}",
            data={
                "invoice_id": invoice.id,
                "labor_cost": labor_cost,
                "materials_cost": materials_cost,
                "total_amount": total,
            },
        )

    except Exception as e:
        logger.error(f"Failed to generate invoice: {str(e)}")
        return ToolResult(
            tool_name="generate_invoice",
            success=False,
            message=f"Failed to generate invoice: {str(e)}",
        )
