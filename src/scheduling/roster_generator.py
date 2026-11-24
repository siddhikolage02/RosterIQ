
from datetime import date
from calendar import monthrange

from sqlalchemy import or_

from src.database.models import (
    RosterRun,
    RosterEntry,
    Employee,
    Assignment,
    Process,
)
from src.scheduling.eligibility_service import (
    check_employee_eligibility,
)
from src.scheduling.validation_service import validate_roster
from src.services.calendar_service import is_working_day


def generate_monthly_roster(db, roster_id):
    """
    Generate a monthly draft roster using active employee
    assignments and process staffing requirements.
    """

    roster = db.query(RosterRun).filter(
        RosterRun.id == roster_id
    ).first()

    if not roster:
        raise ValueError("Roster not found.")

    if roster.status != "Draft":
        raise ValueError(
            "Only Draft rosters can be automatically generated."
        )

    entries_added = 0

    # Track monthly workload to distribute assignments fairly.
    monthly_workload = {}

    try:
        processes = db.query(Process).filter(
            Process.is_active == True
        ).order_by(Process.id).all()

        days_in_month = monthrange(
            roster.year,
            roster.month
        )[1]

        for day in range(1, days_in_month + 1):

            work_date = date(
                roster.year,
                roster.month,
                day
            )

            for process in processes:

                if not is_working_day(
                    db,
                    process.id,
                    work_date
                ):
                    continue

                assigned_count = db.query(RosterEntry).filter(
                    RosterEntry.roster_id == roster_id,
                    RosterEntry.process_id == process.id,
                    RosterEntry.roster_date == work_date,
                    RosterEntry.status != "Cancelled",
                ).count()

                required_count = process.minimum_staff

                if assigned_count >= required_count:
                    continue

                # Find employees qualified for this process.
                candidates = db.query(Employee).join(
                    Assignment,
                    Assignment.employee_id == Employee.id
                ).filter(
                    Employee.employment_status == "Active",
                    Assignment.process_id == process.id,
                    Assignment.assignment_status == "Active",
                    Assignment.start_date <= work_date,
                    or_(
                        Assignment.end_date.is_(None),
                        Assignment.end_date >= work_date,
                    ),
                ).distinct().all()

                # Prefer employees with fewer assignments
                # during this roster month.
                candidates.sort(
                    key=lambda employee: (
                        monthly_workload.get(employee.id, 0),
                        employee.id,
                    )
                )

                for employee in candidates:

                    if assigned_count >= required_count:
                        break

                    result = check_employee_eligibility(
                        db,
                        employee.id,
                        process.id,
                        work_date,
                        roster_id=roster_id,
                    )

                    if not result["eligible"]:
                        continue

                    entry = RosterEntry(
                        roster_id=roster_id,
                        employee_id=employee.id,
                        process_id=process.id,
                        roster_date=work_date,
                        status="Scheduled",
                    )

                    db.add(entry)

                    # Make this assignment visible to the next
                    # eligibility check on the same date.
                    db.flush()

                    assigned_count += 1
                    entries_added += 1

                    monthly_workload[employee.id] = (
                        monthly_workload.get(employee.id, 0) + 1
                    )

        db.commit()

    except Exception:
        db.rollback()
        raise

    # Validate the completed draft after saving it.
    validation = validate_roster(db, roster_id)

    return {
        "roster_id": roster_id,
        "entries_added": entries_added,
        "total_entries": validation["total_entries"],
        "conflict_count": validation["conflict_count"],
        "coverage_gap_count": validation["coverage_gap_count"],
        "is_valid": validation["is_valid"],
    }
