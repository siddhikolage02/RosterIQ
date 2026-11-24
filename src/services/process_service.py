
from sqlalchemy.orm import Session

from src.database.models import Process, Brand


def create_process(
    db: Session,
    name: str,
    brand_id: int,
    minimum_staff: int = 1,
    operating_calendar: str = "daily",
    description: str = None,
):
    """Create a new process under a brand."""

    name = name.strip()

    if not name:
        raise ValueError("Process name is required.")

    if minimum_staff < 1:
        raise ValueError("Minimum staff must be at least 1.")

    valid_calendars = {"daily", "weekdays", "year_round"}

    if operating_calendar not in valid_calendars:
        raise ValueError("Invalid operating calendar.")

    brand = (
        db.query(Brand)
        .filter(Brand.id == brand_id)
        .first()
    )

    if not brand:
        raise ValueError("Brand not found.")

    existing = (
        db.query(Process)
        .filter(
            Process.name == name,
            Process.brand_id == brand_id
        )
        .first()
    )

    if existing:
        raise ValueError("This process already exists under this brand.")

    process = Process(
        name=name,
        brand_id=brand_id,
        minimum_staff=minimum_staff,
        operating_calendar=operating_calendar,
        description=description.strip() if description else None,
        is_active=True,
    )

    try:
        db.add(process)
        db.commit()
        db.refresh(process)
        return process

    except Exception:
        db.rollback()
        raise


def get_process_by_id(db: Session, process_id: int):
    """Retrieve one process by ID."""

    return (
        db.query(Process)
        .filter(Process.id == process_id)
        .first()
    )


def get_all_processes(db: Session):
    """Retrieve all processes with their associated brands."""

    return (
        db.query(Process)
        .order_by(Process.id)
        .all()
    )


def get_processes_by_brand(db: Session, brand_id: int):
    """Retrieve processes belonging to a particular brand."""

    return (
        db.query(Process)
        .filter(Process.brand_id == brand_id)
        .order_by(Process.id)
        .all()
    )


def update_process(db: Session, process_id: int, **updates):
    """Update process information."""

    process = get_process_by_id(db, process_id)

    if not process:
        raise ValueError("Process not found.")

    allowed_fields = {
        "name",
        "brand_id",
        "minimum_staff",
        "operating_calendar",
        "description",
    }

    invalid_fields = set(updates.keys()) - allowed_fields

    if invalid_fields:
        raise ValueError(
            f"These fields cannot be updated: {', '.join(invalid_fields)}"
        )

    if "name" in updates:
        updates["name"] = updates["name"].strip()

        if not updates["name"]:
            raise ValueError("Process name cannot be empty.")

    if "minimum_staff" in updates and updates["minimum_staff"] < 1:
        raise ValueError("Minimum staff must be at least 1.")

    if "brand_id" in updates:
        brand = (
            db.query(Brand)
            .filter(Brand.id == updates["brand_id"])
            .first()
        )

        if not brand:
            raise ValueError("Brand not found.")

    if "operating_calendar" in updates:
        valid_calendars = {"daily", "weekdays", "year_round"}

        if updates["operating_calendar"] not in valid_calendars:
            raise ValueError("Invalid operating calendar.")

    if "description" in updates and updates["description"] is not None:
        updates["description"] = updates["description"].strip()

    try:
        for field, value in updates.items():
            setattr(process, field, value)

        db.commit()
        db.refresh(process)
        return process

    except Exception:
        db.rollback()
        raise


def deactivate_process(db: Session, process_id: int):
    """Deactivate a process without deleting its history."""

    process = get_process_by_id(db, process_id)

    if not process:
        raise ValueError("Process not found.")

    process.is_active = False

    try:
        db.commit()
        db.refresh(process)
        return process

    except Exception:
        db.rollback()
        raise
