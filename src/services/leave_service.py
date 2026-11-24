
from datetime import date, datetime

from sqlalchemy.orm import Session

from src.database.models import Employee, LeaveRequest, EmployeeAvailability


# --------------------------------------------------
# LEAVE REQUEST MANAGEMENT
# --------------------------------------------------

def create_leave_request(
    db: Session,
    employee_id: int,
    start_date: date,
    end_date: date,
    leave_type: str,
    reason: str = None,
):
    """Create a new employee leave request."""

    if end_date < start_date:
        raise ValueError("Leave end date cannot be before start date.")

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise ValueError("Employee not found.")

    if employee.employment_status.lower() != "active":
        raise ValueError("Inactive employees cannot request leave.")

    if not leave_type.strip():
        raise ValueError("Leave type is required.")

    leave_request = LeaveRequest(
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        leave_type=leave_type.strip(),
        status="Pending",
        reason=reason.strip() if reason else None,
    )

    try:
        db.add(leave_request)
        db.commit()
        db.refresh(leave_request)
        return leave_request

    except Exception:
        db.rollback()
        raise


def get_leave_request_by_id(db: Session, request_id: int):
    """Retrieve one leave request."""

    return (
        db.query(LeaveRequest)
        .filter(LeaveRequest.id == request_id)
        .first()
    )


def get_all_leave_requests(db: Session):
    """Retrieve all leave requests."""

    return (
        db.query(LeaveRequest)
        .order_by(LeaveRequest.start_date)
        .all()
    )


def get_employee_leave_requests(db: Session, employee_id: int):
    """Retrieve leave requests belonging to one employee."""

    return (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == employee_id)
        .order_by(LeaveRequest.start_date)
        .all()
    )


def review_leave_request(
    db: Session,
    request_id: int,
    reviewer_id: int,
    decision: str,
):
    """Approve or reject a pending leave request."""

    leave_request = get_leave_request_by_id(db, request_id)

    if not leave_request:
        raise ValueError("Leave request not found.")

    if leave_request.status != "Pending":
        raise ValueError("Only pending leave requests can be reviewed.")

    if decision not in {"Approved", "Rejected"}:
        raise ValueError("Decision must be Approved or Rejected.")

    reviewer = (
        db.query(Employee)
        .filter(Employee.id == reviewer_id)
        .first()
    )

    if not reviewer:
        raise ValueError("Reviewer employee not found.")

    if reviewer.employment_status.lower() != "active":
        raise ValueError("An inactive employee cannot review leave.")

    try:
        leave_request.status = decision
        leave_request.reviewed_by = reviewer_id
        leave_request.reviewed_at = datetime.now()

        db.commit()
        db.refresh(leave_request)
        return leave_request

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# EMPLOYEE AVAILABILITY MANAGEMENT
# --------------------------------------------------

def set_employee_availability(
    db: Session,
    employee_id: int,
    availability_date: date,
    status: str,
    reason: str = None,
):
    """Create or update an employee's availability for a date."""

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise ValueError("Employee not found.")

    if employee.employment_status.lower() != "active":
        raise ValueError("Cannot update availability for an inactive employee.")

    if status not in {"Available", "Unavailable"}:
        raise ValueError("Status must be Available or Unavailable.")

    record = (
        db.query(EmployeeAvailability)
        .filter(
            EmployeeAvailability.employee_id == employee_id,
            EmployeeAvailability.availability_date == availability_date,
        )
        .first()
    )

    try:
        if record:
            record.status = status
            record.reason = reason.strip() if reason else None
        else:
            record = EmployeeAvailability(
                employee_id=employee_id,
                availability_date=availability_date,
                status=status,
                reason=reason.strip() if reason else None,
            )
            db.add(record)

        db.commit()
        db.refresh(record)
        return record

    except Exception:
        db.rollback()
        raise


def get_employee_availability(db: Session, employee_id: int):
    """Retrieve all availability records for an employee."""

    return (
        db.query(EmployeeAvailability)
        .filter(EmployeeAvailability.employee_id == employee_id)
        .order_by(EmployeeAvailability.availability_date)
        .all()
    )


def get_availability_for_date(db: Session, target_date: date):
    """Retrieve availability records for a particular date."""

    return (
        db.query(EmployeeAvailability)
        .filter(EmployeeAvailability.availability_date == target_date)
        .all()
    )
