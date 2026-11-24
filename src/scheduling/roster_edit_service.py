
from datetime import date

from sqlalchemy.orm import Session

from src.database.models import Employee, RosterRun, RosterEntry
from src.scheduling.eligibility_service import check_employee_eligibility
from src.scheduling.validation_service import validate_roster
from src.auth.permission_service import has_role
from src.services.audit_service import log_roster_change


def _require_roster_editor(db: Session, changed_by_employee_id: int):
    """Verify that the person making a change is an active Manager or Pod Lead."""

    employee = db.query(Employee).filter(
        Employee.id == changed_by_employee_id
    ).first()

    if not employee:
        raise PermissionError("The acting employee does not exist.")

    if employee.employment_status != "Active":
        raise PermissionError("Inactive employees cannot edit rosters.")

    if not has_role(employee, ["Manager", "Pod Lead"]):
        raise PermissionError(
            "Only Managers and Pod Leads can edit rosters."
        )

    return employee


def _require_employee_scope(db: Session, actor, target_employee_id: int):
    """Keep Pod Leads inside their own pod; Managers may manage all pods."""
    target = db.query(Employee).filter(Employee.id == target_employee_id).first()
    if target is None:
        raise ValueError("Target employee does not exist.")
    if actor.role == "Pod Lead" and (
        actor.pod_id is None or target.pod_id != actor.pod_id
    ):
        raise PermissionError("Pod Leads can only manage employees in their own pod.")
    return target


def add_manual_roster_entry(
    db: Session,
    roster_id: int,
    employee_id: int,
    process_id: int,
    roster_date: date,
    changed_by_employee_id: int,
):
    """Add an entry to a draft roster and record the action."""

    actor = _require_roster_editor(db, changed_by_employee_id)
    _require_employee_scope(db, actor, employee_id)

    roster = db.query(RosterRun).filter(
        RosterRun.id == roster_id
    ).first()

    if not roster:
        raise ValueError("Roster not found.")

    if roster.status != "Draft":
        raise ValueError("Only draft rosters can be edited.")

    if not isinstance(roster_date, date):
        raise ValueError("roster_date must be a date.")

    if roster_date.month != roster.month or roster_date.year != roster.year:
        raise ValueError("Entry date must belong to the roster month.")

    eligibility = check_employee_eligibility(
        db,
        employee_id,
        process_id,
        roster_date,
        roster_id=roster_id,
    )

    if not eligibility["eligible"]:
        raise ValueError(
            "Employee is not eligible: "
            + "; ".join(eligibility["reasons"])
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
        db.flush()

        validation = validate_roster(db, roster_id)

        if not validation["is_valid"]:
            raise ValueError(
                "Roster validation failed. Manual change was not saved."
            )

        log_roster_change(
            db=db,
            roster_id=roster_id,
            entry_id=entry.id,
            changed_by_employee_id=changed_by_employee_id,
            action="Manual Entry Added",
            new_values={
                "employee_id": entry.employee_id,
                "process_id": entry.process_id,
                "roster_date": entry.roster_date,
                "status": entry.status,
            },
        )

        db.commit()
        db.refresh(entry)
        return entry

    except Exception:
        db.rollback()
        raise


def update_manual_roster_entry(
    db: Session,
    entry_id: int,
    changed_by_employee_id: int,
    new_employee_id: int = None,
    new_process_id: int = None,
    new_roster_date: date = None,
):
    """Update a draft roster entry and record old and new values."""

    actor = _require_roster_editor(db, changed_by_employee_id)

    entry = db.query(RosterEntry).filter(
        RosterEntry.id == entry_id
    ).first()

    if not entry:
        raise ValueError("Roster entry not found.")

    _require_employee_scope(db, actor, entry.employee_id)

    roster = db.query(RosterRun).filter(
        RosterRun.id == entry.roster_id
    ).first()

    if not roster or roster.status != "Draft":
        raise ValueError("Only draft rosters can be edited.")

    if entry.status == "Cancelled":
        raise ValueError("Cancelled entries cannot be edited.")

    old_values = {
        "employee_id": entry.employee_id,
        "process_id": entry.process_id,
        "roster_date": entry.roster_date,
        "status": entry.status,
    }

    employee_id = (
        new_employee_id
        if new_employee_id is not None
        else entry.employee_id
    )

    process_id = (
        new_process_id
        if new_process_id is not None
        else entry.process_id
    )

    roster_date = (
        new_roster_date
        if new_roster_date is not None
        else entry.roster_date
    )

    _require_employee_scope(db, actor, employee_id)

    if not isinstance(roster_date, date):
        raise ValueError("roster_date must be a date.")

    if roster_date.month != roster.month or roster_date.year != roster.year:
        raise ValueError("Entry date must belong to the roster month.")

    duplicate = db.query(RosterEntry).filter(
        RosterEntry.roster_id == entry.roster_id,
        RosterEntry.employee_id == employee_id,
        RosterEntry.roster_date == roster_date,
        RosterEntry.id != entry.id,
        RosterEntry.status != "Cancelled",
    ).first()

    if duplicate:
        raise ValueError(
            "Employee already has another roster entry on this date."
        )

    eligibility = check_employee_eligibility(
        db,
        employee_id,
        process_id,
        roster_date,
        roster_id=entry.roster_id,
        exclude_roster_entry_id=entry.id,
    )

    if not eligibility["eligible"]:
        raise ValueError(
            "Employee is not eligible: "
            + "; ".join(eligibility["reasons"])
        )

    try:
        entry.employee_id = employee_id
        entry.process_id = process_id
        entry.roster_date = roster_date

        db.flush()

        validation = validate_roster(db, roster.id)

        if not validation["is_valid"]:
            raise ValueError(
                "Roster validation failed. Manual change was not saved."
            )

        new_values = {
            "employee_id": entry.employee_id,
            "process_id": entry.process_id,
            "roster_date": entry.roster_date,
            "status": entry.status,
        }

        log_roster_change(
            db=db,
            roster_id=roster.id,
            entry_id=entry.id,
            changed_by_employee_id=changed_by_employee_id,
            action="Manual Entry Updated",
            old_values=old_values,
            new_values=new_values,
        )

        db.commit()
        db.refresh(entry)
        return entry

    except Exception:
        db.rollback()
        raise


def cancel_manual_roster_entry(
    db: Session,
    entry_id: int,
    changed_by_employee_id: int,
):
    """Cancel an entry in a draft roster and record the action."""

    actor = _require_roster_editor(db, changed_by_employee_id)

    entry = db.query(RosterEntry).filter(
        RosterEntry.id == entry_id
    ).first()

    if not entry:
        raise ValueError("Roster entry not found.")

    _require_employee_scope(db, actor, entry.employee_id)

    roster = db.query(RosterRun).filter(
        RosterRun.id == entry.roster_id
    ).first()

    if not roster or roster.status != "Draft":
        raise ValueError("Only draft rosters can be edited.")

    if entry.status == "Cancelled":
        raise ValueError("Entry is already cancelled.")

    old_values = {
        "employee_id": entry.employee_id,
        "process_id": entry.process_id,
        "roster_date": entry.roster_date,
        "status": entry.status,
    }

    try:
        entry.status = "Cancelled"

        db.flush()

        validation = validate_roster(db, roster.id)

        if not validation["is_valid"]:
            raise ValueError(
                "Cancellation creates roster conflicts or coverage gaps. "
                "The change was not saved."
            )

        new_values = {
            "employee_id": entry.employee_id,
            "process_id": entry.process_id,
            "roster_date": entry.roster_date,
            "status": entry.status,
        }

        log_roster_change(
            db=db,
            roster_id=roster.id,
            entry_id=entry.id,
            changed_by_employee_id=changed_by_employee_id,
            action="Manual Entry Cancelled",
            old_values=old_values,
            new_values=new_values,
        )

        db.commit()
        db.refresh(entry)
        return entry

    except Exception:
        db.rollback()
        raise
