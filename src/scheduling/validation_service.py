
from calendar import monthrange

from src.database.models import (
    RosterRun,
    RosterEntry,
    Process,
)
from src.scheduling.eligibility_service import (
    check_employee_eligibility,
)
from src.services.calendar_service import is_working_day


def validate_roster(db, roster_id):
    """
    Validate employee eligibility and minimum staffing
    for a monthly roster.
    """

    roster = db.query(RosterRun).filter(
        RosterRun.id == roster_id
    ).first()

    if not roster:
        raise ValueError("Roster not found.")

    conflicts = []
    coverage_gaps = []

    entries = db.query(RosterEntry).filter(
        RosterEntry.roster_id == roster_id,
        RosterEntry.status != "Cancelled",
    ).all()

    # Check every scheduled employee entry.
    for entry in entries:
        result = check_employee_eligibility(
            db,
            entry.employee_id,
            entry.process_id,
            entry.roster_date,
            roster_id=roster_id,
            exclude_roster_entry_id=entry.id,
        )

        if not result["eligible"]:
            conflicts.append({
                "employee": entry.employee.full_name,
                "process": entry.process.name,
                "date": entry.roster_date,
                "reasons": result["reasons"],
            })

    # Check minimum staffing for every active process
    # on every operating day of the roster month.
    processes = db.query(Process).filter(
        Process.is_active == True
    ).all()

    days_in_month = monthrange(
        roster.year,
        roster.month
    )[1]

    for process in processes:
        for day in range(1, days_in_month + 1):
            work_date = __import__("datetime").date(
                roster.year,
                roster.month,
                day,
            )

            if not is_working_day(db, process.id, work_date):
                continue

            assigned_count = db.query(RosterEntry).filter(
                RosterEntry.roster_id == roster_id,
                RosterEntry.process_id == process.id,
                RosterEntry.roster_date == work_date,
                RosterEntry.status != "Cancelled",
            ).count()

            required_count = process.minimum_staff

            if assigned_count < required_count:
                coverage_gaps.append({
                    "process": process.name,
                    "date": work_date,
                    "required": required_count,
                    "assigned": assigned_count,
                    "shortage": required_count - assigned_count,
                })

    return {
        "roster_id": roster.id,
        "month": roster.month,
        "year": roster.year,
        "total_entries": len(entries),
        "conflicts": conflicts,
        "coverage_gaps": coverage_gaps,
        "conflict_count": len(conflicts),
        "coverage_gap_count": len(coverage_gaps),
        "is_valid": (
            len(conflicts) == 0
            and len(coverage_gaps) == 0
        ),
    }
