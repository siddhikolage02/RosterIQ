
from sqlalchemy.orm import Session

from src.database.models import Pod, Employee


def create_pod(
    db: Session,
    name: str,
    description: str = None,
    lead_employee_id: int = None,
):
    """Create a new pod."""

    name = name.strip()

    if not name:
        raise ValueError("Pod name is required.")

    existing = (
        db.query(Pod)
        .filter(Pod.name == name)
        .first()
    )

    if existing:
        raise ValueError("This pod already exists.")

    if lead_employee_id is not None:
        lead = (
            db.query(Employee)
            .filter(Employee.id == lead_employee_id)
            .first()
        )

        if not lead:
            raise ValueError("Pod lead employee not found.")

    pod = Pod(
        name=name,
        description=description.strip() if description else None,
        lead_employee_id=lead_employee_id,
        is_active=True,
    )

    try:
        db.add(pod)
        db.commit()
        db.refresh(pod)
        return pod

    except Exception:
        db.rollback()
        raise


def get_pod_by_id(db: Session, pod_id: int):
    """Retrieve one pod by ID."""

    return (
        db.query(Pod)
        .filter(Pod.id == pod_id)
        .first()
    )


def get_all_pods(db: Session):
    """Retrieve all pods."""

    return (
        db.query(Pod)
        .order_by(Pod.id)
        .all()
    )


def get_pod_employees(db: Session, pod_id: int):
    """Retrieve all employees belonging to a pod."""

    pod = get_pod_by_id(db, pod_id)

    if not pod:
        raise ValueError("Pod not found.")

    return (
        db.query(Employee)
        .filter(Employee.pod_id == pod_id)
        .order_by(Employee.id)
        .all()
    )


def update_pod(db: Session, pod_id: int, **updates):
    """Update pod information."""

    pod = get_pod_by_id(db, pod_id)

    if not pod:
        raise ValueError("Pod not found.")

    allowed_fields = {
        "name",
        "description",
        "lead_employee_id",
    }

    invalid_fields = set(updates.keys()) - allowed_fields

    if invalid_fields:
        raise ValueError(
            f"These fields cannot be updated: {', '.join(invalid_fields)}"
        )

    if "name" in updates:
        updates["name"] = updates["name"].strip()

        if not updates["name"]:
            raise ValueError("Pod name cannot be empty.")

    if "lead_employee_id" in updates:
        lead_id = updates["lead_employee_id"]

        if lead_id is not None:
            lead = (
                db.query(Employee)
                .filter(Employee.id == lead_id)
                .first()
            )

            if not lead:
                raise ValueError("Pod lead employee not found.")

    if "description" in updates and updates["description"] is not None:
        updates["description"] = updates["description"].strip()

    try:
        for field, value in updates.items():
            setattr(pod, field, value)

        db.commit()
        db.refresh(pod)
        return pod

    except Exception:
        db.rollback()
        raise


def deactivate_pod(db: Session, pod_id: int):
    """Deactivate a pod without deleting its history."""

    pod = get_pod_by_id(db, pod_id)

    if not pod:
        raise ValueError("Pod not found.")

    pod.is_active = False

    try:
        db.commit()
        db.refresh(pod)
        return pod

    except Exception:
        db.rollback()
        raise
