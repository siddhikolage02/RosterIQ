from datetime import date

from src.database.models import (
    Employee,
    Assignment,
    LeaveRequest,
    EmployeeAvailability,
    Process,
    RosterEntry,
)
from src.services.calendar_service import is_working_day


def check_employee_eligibility(
    db,
    employee_id,
    process_id,
    work_date,
    roster_id=None,
    exclude_roster_entry_id=None,
):
    """
    Check whether an employee is eligible for a process
    on a particular date.
    """

    if not isinstance(work_date, date):
        raise ValueError("work_date must be a datetime.date value.")

    reasons = []

    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

    if employee is None:
        return {
            "eligible": False,
            "reasons": ["Employee does not exist."]
        }

    if employee.employment_status != "Active":
        reasons.append("Employee is not active.")

    process = db.query(Process).filter(
        Process.id == process_id
    ).first()

    if process is None:
        return {
            "eligible": False,
            "reasons": ["Process does not exist."]
        }

    if not process.is_active:
        reasons.append("Process is inactive.")

    if not is_working_day(db, process_id, work_date):
        reasons.append("Process is not operating on this date.")

    if employee.weekly_off_day == work_date.strftime("%A"):
        reasons.append("Employee has a weekly off.")

    # Employee must have an active assignment
    # qualifying them for this process on this date.
    qualified = db.query(Assignment).filter(
        Assignment.employee_id == employee_id,
        Assignment.process_id == process_id,
        Assignment.assignment_status == "Active",
        Assignment.start_date <= work_date,
        (
            (Assignment.end_date.is_(None))
            | (Assignment.end_date >= work_date)
        ),
    ).first()

    if not qualified:
        reasons.append(
            "Employee is not assigned to this process on this date."
        )

    # Check date-specific availability.
    availability = db.query(EmployeeAvailability).filter(
        EmployeeAvailability.employee_id == employee_id,
        EmployeeAvailability.availability_date == work_date,
    ).first()

    if availability and availability.status == "Unavailable":
        reasons.append(
            availability.reason or "Employee is unavailable."
        )

    # Check approved leave.
    approved_leave = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status == "Approved",
        LeaveRequest.start_date <= work_date,
        LeaveRequest.end_date >= work_date,
    ).first()

    if approved_leave:
        reasons.append(
            f"Employee has approved {approved_leave.leave_type} leave."
        )

        # Prevent scheduling the same employee more than once
    # on the same date within the current roster.
    existing_entry_query = db.query(RosterEntry).filter(
        RosterEntry.employee_id == employee_id,
        RosterEntry.roster_date == work_date,
        RosterEntry.status != "Cancelled",
    )

    if roster_id is not None:
        existing_entry_query = existing_entry_query.filter(
            RosterEntry.roster_id == roster_id
        )

    if exclude_roster_entry_id is not None:
        existing_entry_query = existing_entry_query.filter(
            RosterEntry.id != exclude_roster_entry_id
        )

    if existing_entry_query.first():
        reasons.append(
            "Employee is already scheduled on this date."
        )

    return {
        "eligible": len(reasons) == 0,
        "reasons": reasons,
    }