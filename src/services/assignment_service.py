
from datetime import date

from sqlalchemy.orm import Session

from src.database.models import Assignment, Employee, Process


def create_assignment(
    db: Session,
    employee_id: int,
    process_id: int,
    start_date: date,
    end_date: date = None,
    assignment_status: str = "Active",
    is_primary: bool = False,
):
    """Assign an employee to a process."""

    if end_date is not None and end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")

    # Verify that the employee exists
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise ValueError("Employee not found.")

    if employee.employment_status.lower() != "active":
        raise ValueError("Cannot assign an inactive employee.")

    # Verify that the process exists
    process = (
        db.query(Process)
        .filter(Process.id == process_id)
        .first()
    )

    if not process:
        raise ValueError("Process not found.")

    if not process.is_active:
        raise ValueError("Cannot assign employees to an inactive process.")

    assignment = Assignment(
        employee_id=employee_id,
        process_id=process_id,
        start_date=start_date,
        end_date=end_date,
        assignment_status=assignment_status,
        is_primary=is_primary,
    )

    try:
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    except Exception:
        db.rollback()
        raise


def get_assignment_by_id(db: Session, assignment_id: int):
    """Retrieve one assignment by ID."""

    return (
        db.query(Assignment)
        .filter(Assignment.id == assignment_id)
        .first()
    )


def get_all_assignments(db: Session):
    """Retrieve all assignments."""

    return (
        db.query(Assignment)
        .order_by(Assignment.id)
        .all()
    )


def get_assignments_by_employee(db: Session, employee_id: int):
    """Retrieve all assignments belonging to an employee."""

    return (
        db.query(Assignment)
        .filter(Assignment.employee_id == employee_id)
        .order_by(Assignment.start_date)
        .all()
    )


def get_assignments_by_process(db: Session, process_id: int):
    """Retrieve all assignments belonging to a process."""

    return (
        db.query(Assignment)
        .filter(Assignment.process_id == process_id)
        .order_by(Assignment.start_date)
        .all()
    )


def update_assignment(db: Session, assignment_id: int, **updates):
    """Update an existing assignment."""

    assignment = get_assignment_by_id(db, assignment_id)

    if not assignment:
        raise ValueError("Assignment not found.")

    allowed_fields = {
        "employee_id",
        "process_id",
        "start_date",
        "end_date",
        "assignment_status",
        "is_primary",
    }

    invalid_fields = set(updates.keys()) - allowed_fields

    if invalid_fields:
        raise ValueError(
            f"These fields cannot be updated: {', '.join(invalid_fields)}"
        )

    employee_id = updates.get("employee_id", assignment.employee_id)
    process_id = updates.get("process_id", assignment.process_id)
    start_date = updates.get("start_date", assignment.start_date)
    end_date = updates.get("end_date", assignment.end_date)

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise ValueError("Employee not found.")

    if employee.employment_status.lower() != "active":
        raise ValueError("Cannot assign an inactive employee.")

    process = (
        db.query(Process)
        .filter(Process.id == process_id)
        .first()
    )

    if not process:
        raise ValueError("Process not found.")

    if not process.is_active:
        raise ValueError("Cannot assign employees to an inactive process.")

    if end_date is not None and end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")

    try:
        for field, value in updates.items():
            setattr(assignment, field, value)

        db.commit()
        db.refresh(assignment)
        return assignment

    except Exception:
        db.rollback()
        raise


def deactivate_assignment(db: Session, assignment_id: int):
    """Deactivate an assignment without deleting its history."""

    assignment = get_assignment_by_id(db, assignment_id)

    if not assignment:
        raise ValueError("Assignment not found.")

    assignment.assignment_status = "Inactive"

    try:
        db.commit()
        db.refresh(assignment)
        return assignment

    except Exception:
        db.rollback()
        raise
