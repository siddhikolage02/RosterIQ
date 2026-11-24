
from sqlalchemy.orm import Session

from src.database.models import Employee, UserAccount
from src.auth.password_service import hash_password, verify_password


def create_user_account(
    db: Session,
    employee_id: int,
    password: str,
):
    """Create a login account for an existing employee."""

    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

    if not employee:
        raise ValueError("Employee not found.")

    if employee.employment_status != "Active":
        raise ValueError("Inactive employees cannot receive accounts.")

    existing = db.query(UserAccount).filter(
        UserAccount.employee_id == employee_id
    ).first()

    if existing:
        raise ValueError("This employee already has a login account.")

    account = UserAccount(
        employee_id=employee_id,
        password_hash=hash_password(password),
        is_active=True,
    )

    try:
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    except Exception:
        db.rollback()
        raise


def authenticate_user(
    db: Session,
    email: str,
    password: str,
):
    """Authenticate an employee using email and password."""

    employee = db.query(Employee).filter(
        Employee.email == email
    ).first()

    if not employee or employee.employment_status != "Active":
        return None

    account = db.query(UserAccount).filter(
        UserAccount.employee_id == employee.id,
        UserAccount.is_active.is_(True),
    ).first()

    if not account:
        return None

    if not verify_password(password, account.password_hash):
        return None

    return employee


def deactivate_user_account(
    db: Session,
    employee_id: int,
):
    """Deactivate an employee's login account."""

    account = db.query(UserAccount).filter(
        UserAccount.employee_id == employee_id
    ).first()

    if not account:
        raise ValueError("User account not found.")

    try:
        account.is_active = False
        db.commit()
        db.refresh(account)
        return account

    except Exception:
        db.rollback()
        raise
