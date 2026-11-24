
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database.models import (
    Employee,
    Assignment,
)

from src.scheduling.eligibility_service import (
    check_employee_eligibility,
)


def get_backup_recommendations(
    db: Session,
    process_id: int,
    work_date: date,
    roster_id: int = None,
    limit: int = 5,
):
    """
    Find eligible employees who can act as backups
    for a particular process and date.

    This function only recommends employees.
    It does not modify the roster.
    """

    if not isinstance(work_date, date):
        raise ValueError("work_date must be a date.")

    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    assignments = (
        db.query(Assignment)
        .join(Employee, Assignment.employee_id == Employee.id)
        .filter(
            Assignment.process_id == process_id,
            Assignment.assignment_status == "Active",
            Assignment.start_date <= work_date,
            or_(
                Assignment.end_date.is_(None),
                Assignment.end_date >= work_date,
            ),
            Employee.employment_status == "Active",
        )
        .order_by(Employee.id)
        .all()
    )

    recommendations = []

    checked_employee_ids = set()

    for assignment in assignments:

        employee = assignment.employee

        if employee.id in checked_employee_ids:
            continue

        checked_employee_ids.add(employee.id)

        result = check_employee_eligibility(
            db,
            employee.id,
            process_id,
            work_date,
            roster_id=roster_id,
        )

        if result["eligible"]:
            recommendations.append(employee)

        if len(recommendations) >= limit:
            break

    return recommendations
