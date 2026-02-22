"""Tool: Update inventory based on materials used."""

import logging
from sqlalchemy.orm import Session

from models.models import Inventory
from schemas.extraction import JobExtraction, ToolResult

logger = logging.getLogger(__name__)


def update_inventory(extraction: JobExtraction, db: Session) -> ToolResult:
    """
    Decrement inventory for each material used in the job.

    Only runs when materials_used is not empty.
    Creates inventory items if they don't exist (with 0 remaining after deduction).
    """
    if not extraction.materials_used:
        return ToolResult(
            tool_name="update_inventory",
            success=True,
            message="No materials to update",
        )

    logger.info(f"Updating inventory for {len(extraction.materials_used)} materials...")
    updates = []
    before_state = {}
    after_state = {}

    try:
        for material in extraction.materials_used:
            # Find or create inventory item
            item = db.query(Inventory).filter(
                Inventory.item_name == material.item.lower()
            ).first()

            if item:
                before_state[material.item] = item.quantity
                item.quantity = max(0, item.quantity - material.quantity)
                after_state[material.item] = item.quantity
                updates.append(f"{material.item}: {before_state[material.item]} → {after_state[material.item]}")
                logger.info(f"Inventory: {material.item} {before_state[material.item]} → {after_state[material.item]}")
            else:
                # Create new item with negative-aware initial quantity
                before_state[material.item] = 100
                new_item = Inventory(
                    item_name=material.item.lower(),
                    quantity=max(0, 100 - material.quantity),  # Assume starting stock of 100
                    unit=material.unit,
                )
                db.add(new_item)
                after_state[material.item] = new_item.quantity
                updates.append(f"{material.item}: NEW (stock: {new_item.quantity})")
                logger.info(f"Inventory: Created {material.item} with stock {new_item.quantity}")

        db.flush()

        # Build low_stock items while we are at it
        all_items = db.query(Inventory).all()
        low_stock = [i.item_name for i in all_items if i.quantity < 10]

        return ToolResult(
            tool_name="update_inventory",
            success=True,
            message=f"Updated {len(updates)} inventory items",
            data={
                "updates": updates,
                "before": before_state,
                "after": after_state,
                "low_stock": low_stock,
            },
        )

    except Exception as e:
        logger.error(f"Failed to update inventory: {str(e)}")
        return ToolResult(
            tool_name="update_inventory",
            success=False,
            message=f"Failed to update inventory: {str(e)}",
        )
