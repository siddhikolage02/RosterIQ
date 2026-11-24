# src/services/employee_service.py

import re
from datetime import date

from sqlalchemy.orm import Session

from src.database.models import Employee, Pod

VALID_ROLES = {"Manager", "Pod Lead", "Employee"}
VALID_STATUSES = {"Active", "Inactive"}
VALID_WEEKLY_OFF_DAYS = {
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
}

POD_LEAD_EDITABLE_FIELDS = {
    "full_name",
    "email",
    "weekly_off_day",
    "date_joined",
}

MANAGER_EDITABLE_FIELDS = {
    "employee_code",
    "full_name",
    "email",
    "role",
    "employment_status",
    "weekly_off_day",
    "pod_id",
    "date_joined",
}

# =========================================================
# VALIDATION
# =========================================================

def validate_employee_code(employee_code: str):
    if not isinstance(employee_code, str):
        raise ValueError("Employee code must be text.")

    employee_code = employee_code.strip().upper()

    if not employee_code:
        raise ValueError("Employee code is required.")

    if len(employee_code) > 30:
        raise ValueError("Employee code cannot exceed 30 characters.")

    return employee_code

def validate_full_name(full_name: str):
    if not isinstance(full_name, str):
        raise ValueError("Employee name must be text.")

    full_name = full_name.strip()

    if not full_name:
        raise ValueError("Employee name is required.")

    if len(full_name) > 150:
        raise ValueError("Employee name cannot exceed 150 characters.")

    return full_name

def validate_email(email: str):
    if not isinstance(email, str):
        raise ValueError("Email must be text.")

    email = email.strip().lower()

    if not email:
        raise ValueError("Email is required.")

    if len(email) > 150:
        raise ValueError("Email cannot exceed 150 characters.")

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.match(pattern, email):
        raise ValueError("Please enter a valid email address.")

    return email

def validate_role(role: str):
    if not isinstance(role, str):
        raise ValueError("Role must be text.")

    role = role.strip()

    if role not in VALID_ROLES:
        raise ValueError("Invalid employee role.")

    return role

def validate_employment_status(status: str):
    if not isinstance(status, str):
        raise ValueError("Employment status must be text.")

    status = status.strip()

    if status not in VALID_STATUSES:
        raise ValueError("Invalid employment status.")

    return status

def validate_weekly_off_day(day):
    if day is None:
        return None

    if not isinstance(day, str):
        raise ValueError("Weekly off day must be text.")

    day = day.strip()

    if day == "":
        return None

    if day not in VALID_WEEKLY_OFF_DAYS:
        raise ValueError("Invalid weekly off day.")

    return day

def validate_pod(db: Session, pod_id):
    if pod_id is None:
        return None

    pod = db.query(Pod).filter(Pod.id == pod_id).first()

    if not pod:
        raise ValueError("Selected pod does not exist.")

    if not pod.is_active:
        raise ValueError("Cannot assign an employee to an inactive pod.")

    return pod.id

def validate_date_joined(date_joined):
    if date_joined is not None and not isinstance(date_joined, date):
        raise ValueError("Date Joined must be a valid date.")

    return date_joined

# =========================================================
# AUTHORIZATION HELPERS
# =========================================================

def _get_actor(db: Session, actor_id: int):
    if actor_id is None:
        raise PermissionError("An authenticated employee is required.")

    actor = db.query(Employee).filter(
        Employee.id == actor_id
    ).first()

    if not actor:
        raise PermissionError("Authenticated employee not found.")

    if actor.employment_status != "Active":
        raise PermissionError("Inactive employees cannot perform actions.")

    return actor

def _get_employee_internal(db: Session, employee_id: int):
    return db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

def _require_manager(actor):
    if actor.role != "Manager":
        raise PermissionError("Only Managers can perform this action.")

def _require_employee_access(actor, target):
    if actor.role == "Manager":
        return

    if actor.id == target.id:
        return

    if actor.role == "Pod Lead":
        if actor.pod_id is not None and actor.pod_id == target.pod_id:
            return

    raise PermissionError("You do not have permission to access this employee.")

def _ensure_manager_exists(db: Session):
    manager_count = db.query(Employee).filter(
        Employee.role == "Manager",
        Employee.employment_status == "Active",
    ).count()

    if manager_count < 1:
        raise ValueError("The system must have at least one active Manager.")

def _ensure_not_last_active_manager(db: Session, employee: Employee):
    if (
        employee.role == "Manager"
        and employee.employment_status == "Active"
    ):
        manager_count = db.query(Employee).filter(
            Employee.role == "Manager",
            Employee.employment_status == "Active",
        ).count()

        if manager_count <= 1:
            raise ValueError(
                "The last active Manager cannot be demoted or deactivated."
            )

# =========================================================
# CREATE EMPLOYEE
# =========================================================

def create_employee(
    db: Session,
    actor_id: int,
    employee_code: str,
    full_name: str,
    email: str,
    role: str,
    employment_status: str = "Active",
    weekly_off_day: str = None,
    pod_id: int = None,
    date_joined: date = None,
):
    actor = _get_actor(db, actor_id)
    _require_manager(actor)

    employee_code = validate_employee_code(employee_code)
    full_name = validate_full_name(full_name)
    email = validate_email(email)
    role = validate_role(role)
    employment_status = validate_employment_status(employment_status)
    weekly_off_day = validate_weekly_off_day(weekly_off_day)
    pod_id = validate_pod(db, pod_id)
    date_joined = validate_date_joined(date_joined)

    if db.query(Employee).filter(
        Employee.employee_code == employee_code
    ).first():
        raise ValueError("This employee code already exists.")

    if db.query(Employee).filter(
        Employee.email == email
    ).first():
        raise ValueError("This email address already exists.")

    employee = Employee(
        employee_code=employee_code,
        full_name=full_name,
        email=email,
        role=role,
        employment_status=employment_status,
        weekly_off_day=weekly_off_day,
        pod_id=pod_id,
        date_joined=date_joined,
    )

    try:
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee

    except Exception:
        db.rollback()
        raise

# =========================================================
# READ EMPLOYEE
# =========================================================

def get_employee_by_id(
    db: Session,
    employee_id: int,
    actor_id: int,
):
    actor = _get_actor(db, actor_id)

    employee = _get_employee_internal(db, employee_id)

    if not employee:
        return None

    _require_employee_access(actor, employee)

    return employee

def get_all_employees(
    db: Session,
    actor_id: int,
):
    actor = _get_actor(db, actor_id)

    if actor.role == "Manager":
        return (
            db.query(Employee)
            .order_by(Employee.employee_code)
            .all()
        )

    if actor.role == "Pod Lead":
        if actor.pod_id is None:
            return []

        return (
            db.query(Employee)
            .filter(Employee.pod_id == actor.pod_id)
            .order_by(Employee.employee_code)
            .all()
        )

    raise PermissionError(
        "You do not have permission to view the employee directory."
    )

# =========================================================
# UPDATE EMPLOYEE
# =========================================================

def update_employee(
    db: Session,
    employee_id: int,
    actor_id: int,
    **updates,
):
    actor = _get_actor(db, actor_id)

    employee = _get_employee_internal(db, employee_id)

    if not employee:
        raise ValueError("Employee not found.")

    _require_employee_access(actor, employee)

    if actor.role == "Manager":
        allowed_fields = MANAGER_EDITABLE_FIELDS

    elif actor.role == "Pod Lead":
        if employee.role == "Manager":
            raise PermissionError(
                "Pod Leads cannot edit Manager records."
            )

        allowed_fields = POD_LEAD_EDITABLE_FIELDS

    else:
        raise PermissionError(
            "You do not have permission to edit employees."
        )

    invalid_fields = set(updates.keys()) - allowed_fields

    if invalid_fields:
        raise PermissionError(
            "You are not permitted to modify: "
            + ", ".join(sorted(invalid_fields))
        )

    # Validate and normalize provided fields.
    if "employee_code" in updates:
        updates["employee_code"] = validate_employee_code(
            updates["employee_code"]
        )

        duplicate = db.query(Employee).filter(
            Employee.employee_code == updates["employee_code"],
            Employee.id != employee_id,
        ).first()

        if duplicate:
            raise ValueError("This employee code already exists.")

    if "full_name" in updates:
        updates["full_name"] = validate_full_name(
            updates["full_name"]
        )

    if "email" in updates:
        updates["email"] = validate_email(updates["email"])

        duplicate = db.query(Employee).filter(
            Employee.email == updates["email"],
            Employee.id != employee_id,
        ).first()

        if duplicate:
            raise ValueError("This email address already exists.")

    if "role" in updates:
        updates["role"] = validate_role(updates["role"])

    if "employment_status" in updates:
        updates["employment_status"] = validate_employment_status(
            updates["employment_status"]
        )

    if "weekly_off_day" in updates:
        updates["weekly_off_day"] = validate_weekly_off_day(
            updates["weekly_off_day"]
        )

    if "pod_id" in updates:
        updates["pod_id"] = validate_pod(db, updates["pod_id"])

    if "date_joined" in updates:
        updates["date_joined"] = validate_date_joined(
            updates["date_joined"]
        )

    # Protect the last active Manager.
    if employee.role == "Manager" and employee.employment_status == "Active":
        becoming_non_manager = (
            updates.get("role", employee.role) != "Manager"
        )

        becoming_inactive = (
            updates.get("employment_status", employee.employment_status)
            != "Active"
        )

        if becoming_non_manager or becoming_inactive:
            _ensure_not_last_active_manager(db, employee)

    try:
        for field, value in updates.items():
            setattr(employee, field, value)

        _ensure_manager_exists(db)

        db.commit()
        db.refresh(employee)

        return employee

    except Exception:
        db.rollback()
        raise

# =========================================================
# DEACTIVATE EMPLOYEE
# =========================================================

def deactivate_employee(
    db: Session,
    employee_id: int,
    actor_id: int,
):
    actor = _get_actor(db, actor_id)
    _require_manager(actor)

    employee = _get_employee_internal(db, employee_id)

    if not employee:
        raise ValueError("Employee not found.")

    if employee.id == actor.id:
        raise PermissionError("You cannot deactivate your own account.")

    if employee.employment_status == "Inactive":
        raise ValueError("Employee is already inactive.")

    _ensure_not_last_active_manager(db, employee)

    try:
        employee.employment_status = "Inactive"

        db.commit()
        db.refresh(employee)

        return employee

    except Exception:
        db.rollback()
        raise