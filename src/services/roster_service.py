
from datetime import date

from sqlalchemy.orm import Session

from src.database.models import (
    RosterRun,
    RosterEntry,
    Employee,
    Process,
)

def create_roster(db: Session, month: int, year: int):
    """Create a new monthly draft roster."""

    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12.")

    if year < 2026:
        raise ValueError("Invalid roster year.")

    roster = RosterRun(
        month=month,
        year=year,
        status="Draft",
    )

    try:
        db.add(roster)
        db.commit()
        db.refresh(roster)
        return roster

    except Exception:
        db.rollback()
        raise

def get_roster_by_id(db: Session, roster_id: int):
    """Retrieve a roster using its ID."""

    return (
        db.query(RosterRun)
        .filter(RosterRun.id == roster_id)
        .first()
    )

def get_all_rosters(db: Session):
    """Retrieve all monthly rosters."""

    return (
        db.query(RosterRun)
        .order_by(RosterRun.year.desc(), RosterRun.month.desc())
        .all()
    )

def add_roster_entry(
    db: Session,
    roster_id: int,
    employee_id: int,
    process_id: int,
    roster_date: date,
):
    """Add one employee to a particular process and date."""

    roster = get_roster_by_id(db, roster_id)

    if not roster:
        raise ValueError("Roster not found.")

    if roster.status != "Draft":
        raise ValueError("Only draft rosters can be modified.")

    if not isinstance(roster_date, date):
        raise ValueError("roster_date must be a date.")

    if roster_date.month != roster.month or roster_date.year != roster.year:
        raise ValueError("Entry date must belong to the roster month.")

    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

    if not employee or employee.employment_status != "Active":
        raise ValueError("Employee does not exist or is inactive.")

    process = db.query(Process).filter(
        Process.id == process_id
    ).first()

    if not process or not process.is_active:
        raise ValueError("Process does not exist or is inactive.")

    duplicate = db.query(RosterEntry).filter(
        RosterEntry.roster_id == roster_id,
        RosterEntry.employee_id == employee_id,
        RosterEntry.roster_date == roster_date,
    ).first()

    if duplicate:
        raise ValueError(
            "Employee already has a roster entry on this date."
        )

    entry = RosterEntry(
        roster_id=roster_id,
        employee_id=employee_id,
        process_id=process_id,
        roster_date=roster_date,
        status="Scheduled",
    )

    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    except Exception:
        db.rollback()
        raise

def get_roster_entries(db: Session, roster_id: int):
    """Retrieve all entries belonging to a roster."""

    return (
        db.query(RosterEntry)
        .filter(RosterEntry.roster_id == roster_id)
        .order_by(RosterEntry.roster_date, RosterEntry.process_id)
        .all()
    )

def get_roster_entries_by_date(db: Session, roster_id: int, work_date: date):
    """Retrieve roster entries for a particular date."""

    return (
        db.query(RosterEntry)
        .filter(
            RosterEntry.roster_id == roster_id,
            RosterEntry.roster_date == work_date,
        )
        .order_by(RosterEntry.process_id)
        .all()
    )


def publish_roster(db: Session, roster_id: int):
    """Prevent publication through the legacy, unauthenticated function."""

    raise PermissionError(
        "Direct publishing is disabled. "
        "Use publish_approved_roster() from approval_service "
        "with an authorized Manager account."
    )
