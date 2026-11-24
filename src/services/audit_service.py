
import json

from sqlalchemy.orm import Session

from src.database.models import RosterChangeLog


def log_roster_change(
    db: Session,
    roster_id: int,
    changed_by_employee_id: int,
    action: str,
    entry_id: int = None,
    old_values: dict = None,
    new_values: dict = None,
    comments: str = None,
):
    """Add a roster activity record to the current transaction."""

    log = RosterChangeLog(
        roster_id=roster_id,
        entry_id=entry_id,
        changed_by_employee_id=changed_by_employee_id,
        action=action,
        old_values=json.dumps(old_values, default=str) if old_values is not None else None,
        new_values=json.dumps(new_values, default=str) if new_values is not None else None,
        comments=comments,
    )

    db.add(log)
    db.flush()

    return log


def get_roster_change_history(db: Session, roster_id: int):
    """Return chronological change history for a roster."""

    return (
        db.query(RosterChangeLog)
        .filter(RosterChangeLog.roster_id == roster_id)
        .order_by(RosterChangeLog.changed_at, RosterChangeLog.id)
        .all()
    )


def get_employee_change_history(db: Session, employee_id: int):
    """Return changes made by a particular employee."""

    return (
        db.query(RosterChangeLog)
        .filter(
            RosterChangeLog.changed_by_employee_id == employee_id
        )
        .order_by(RosterChangeLog.changed_at.desc())
        .all()
    )
