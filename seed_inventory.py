"""Seed the inventory table with common field service materials."""

from database import SessionLocal, engine
from models.models import Base, Inventory

# Ensure tables exist
Base.metadata.create_all(bind=engine)

SEED_DATA = [
    # Plumbing
    {"item_name": "Copper Pipe (1/2 inch)",   "quantity": 30,  "unit": "piece",  "unit_cost": 12.50},
    {"item_name": "Copper Pipe (3/4 inch)",   "quantity": 20,  "unit": "piece",  "unit_cost": 15.00},
    {"item_name": "PVC Pipe (2 inch)",        "quantity": 25,  "unit": "piece",  "unit_cost": 8.00},
    {"item_name": "Elbow Joint",              "quantity": 50,  "unit": "piece",  "unit_cost": 3.50},
    {"item_name": "Pipe Sealant",             "quantity": 15,  "unit": "tube",   "unit_cost": 6.00},
    {"item_name": "Faucet Handle",            "quantity": 10,  "unit": "piece",  "unit_cost": 18.00},
    {"item_name": "Water Heater Element",     "quantity": 5,   "unit": "piece",  "unit_cost": 45.00},
    {"item_name": "Drain Snake",              "quantity": 3,   "unit": "piece",  "unit_cost": 25.00},

    # Electrical
    {"item_name": "Electrical Outlet",        "quantity": 40,  "unit": "piece",  "unit_cost": 5.00},
    {"item_name": "Light Switch",             "quantity": 30,  "unit": "piece",  "unit_cost": 4.50},
    {"item_name": "Breaker Panel",            "quantity": 3,   "unit": "piece",  "unit_cost": 150.00},
    {"item_name": "10-Gauge Wire",            "quantity": 200, "unit": "feet",   "unit_cost": 1.20},
    {"item_name": "12-Gauge Wire",            "quantity": 300, "unit": "feet",   "unit_cost": 0.85},
    {"item_name": "Junction Box",             "quantity": 20,  "unit": "piece",  "unit_cost": 7.00},
    {"item_name": "Fluorescent Light Bulb",   "quantity": 25,  "unit": "piece",  "unit_cost": 8.50},
    {"item_name": "LED Bulb",                 "quantity": 40,  "unit": "piece",  "unit_cost": 6.00},

    # HVAC
    {"item_name": "Air Filter",              "quantity": 15,  "unit": "piece",  "unit_cost": 22.00},
    {"item_name": "Refrigerant (R-410A)",    "quantity": 10,  "unit": "pound",  "unit_cost": 35.00},
    {"item_name": "Thermostat",              "quantity": 5,   "unit": "piece",  "unit_cost": 65.00},
    {"item_name": "HVAC Filter",             "quantity": 12,  "unit": "piece",  "unit_cost": 18.00},

    # Painting
    {"item_name": "Interior Paint (White)",  "quantity": 10,  "unit": "gallon", "unit_cost": 35.00},
    {"item_name": "Exterior Paint",          "quantity": 8,   "unit": "gallon", "unit_cost": 45.00},
    {"item_name": "Paint Roller",            "quantity": 12,  "unit": "piece",  "unit_cost": 8.00},
    {"item_name": "Wood Stain",              "quantity": 6,   "unit": "can",    "unit_cost": 28.00},

    # Carpentry
    {"item_name": "Pine Lumber Board",       "quantity": 20,  "unit": "board",  "unit_cost": 12.00},
    {"item_name": "Plywood Sheet",           "quantity": 10,  "unit": "sheet",  "unit_cost": 35.00},
    {"item_name": "Wood Screws (Box)",       "quantity": 15,  "unit": "box",    "unit_cost": 9.00},
    {"item_name": "Bracket",                 "quantity": 30,  "unit": "piece",  "unit_cost": 4.00},
    {"item_name": "Drywall Sheet",           "quantity": 12,  "unit": "sheet",  "unit_cost": 14.00},

    # General
    {"item_name": "Silicone Caulk",          "quantity": 20,  "unit": "tube",   "unit_cost": 7.50},
    {"item_name": "Teflon Tape",             "quantity": 25,  "unit": "roll",   "unit_cost": 2.50},
    {"item_name": "WD-40",                   "quantity": 8,   "unit": "can",    "unit_cost": 6.00},
]


def seed():
    db = SessionLocal()
    added = 0
    skipped = 0

    for item in SEED_DATA:
        exists = db.query(Inventory).filter_by(item_name=item["item_name"]).first()
        if exists:
            skipped += 1
            continue
        db.add(Inventory(**item))
        added += 1

    db.commit()
    db.close()
    print(f"✅ Inventory seeded: {added} added, {skipped} already existed.")


if __name__ == "__main__":
    seed()
