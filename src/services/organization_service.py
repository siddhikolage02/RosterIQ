
from datetime import date

from sqlalchemy.orm import Session

from src.database.models import (
    Pod,
    Employee,
    Brand,
    Process,
    Assignment,
)


class OrganizationError(Exception):
    pass


# =====================================================
# AUTHORIZATION
# =====================================================

def get_actor(db: Session, actor_id: int):
    actor = db.query(Employee).filter(
        Employee.id == actor_id,
        Employee.employment_status == "Active",
    ).first()

    if not actor:
        raise OrganizationError("Active employee account required.")

    return actor


def require_manager(actor):
    if actor.role != "Manager":
        raise OrganizationError("Manager permission required.")


def require_manager_or_pod_lead(actor):
    if actor.role not in ("Manager", "Pod Lead"):
        raise OrganizationError("Insufficient permissions.")


def require_assignment_scope(actor, employee):
    if actor.role == "Pod Lead" and employee.pod_id != actor.pod_id:
        raise OrganizationError(
            "You can only manage employees in your own pod."
        )


# =====================================================
# ORGANIZATION DATA
# =====================================================

def get_organization_data(db: Session, actor_id: int):
    actor = get_actor(db, actor_id)

    if actor.role == "Manager":
        pods = db.query(Pod).order_by(Pod.name).all()
        employees = db.query(Employee).order_by(Employee.full_name).all()
        brands = db.query(Brand).order_by(Brand.name).all()
        processes = db.query(Process).order_by(Process.name).all()
        assignments = db.query(Assignment).all()

    elif actor.role == "Pod Lead":
        if not actor.pod_id:
            raise OrganizationError(
                "Your account is not assigned to a pod."
            )

        pods = db.query(Pod).filter(
            Pod.id == actor.pod_id
        ).all()

        employees = db.query(Employee).filter(
            Employee.pod_id == actor.pod_id
        ).all()

        assignments = db.query(Assignment).join(
            Employee,
            Assignment.employee_id == Employee.id,
        ).filter(
            Employee.pod_id == actor.pod_id
        ).all()

        process_ids = {a.process_id for a in assignments}

        processes = db.query(Process).filter(
            Process.id.in_(process_ids)
        ).all() if process_ids else []

        brand_ids = {p.brand_id for p in processes}

        brands = db.query(Brand).filter(
            Brand.id.in_(brand_ids)
        ).all() if brand_ids else []

    else:
        pods = []
        employees = [actor]

        assignments = db.query(Assignment).filter(
            Assignment.employee_id == actor.id
        ).all()

        process_ids = {a.process_id for a in assignments}

        processes = db.query(Process).filter(
            Process.id.in_(process_ids)
        ).all() if process_ids else []

        brand_ids = {p.brand_id for p in processes}

        brands = db.query(Brand).filter(
            Brand.id.in_(brand_ids)
        ).all() if brand_ids else []

    return {
        "actor": actor,
        "pods": pods,
        "employees": employees,
        "brands": brands,
        "processes": processes,
        "assignments": assignments,
    }


# =====================================================
# PODS
# =====================================================

def create_pod(db, actor_id, name, description=None):
    actor = get_actor(db, actor_id)
    require_manager(actor)

    name = name.strip()

    if not name:
        raise OrganizationError("Pod name is required.")

    if db.query(Pod).filter(Pod.name.ilike(name)).first():
        raise OrganizationError("A pod with this name already exists.")

    pod = Pod(
        name=name,
        description=description.strip() if description else None,
        is_active=True,
    )

    db.add(pod)
    db.commit()
    db.refresh(pod)

    return pod


def update_pod(db, actor_id, pod_id, name, description=None):
    actor = get_actor(db, actor_id)
    require_manager(actor)

    pod = db.query(Pod).filter(Pod.id == pod_id).first()

    if not pod:
        raise OrganizationError("Pod not found.")

    name = name.strip()

    if not name:
        raise OrganizationError("Pod name is required.")

    duplicate = db.query(Pod).filter(
        Pod.name.ilike(name),
        Pod.id != pod_id,
    ).first()

    if duplicate:
        raise OrganizationError("Another pod already uses this name.")

    pod.name = name
    pod.description = description.strip() if description else None

    db.commit()
    db.refresh(pod)

    return pod


def assign_pod_lead(db, actor_id, pod_id, employee_id):
    actor = get_actor(db, actor_id)
    require_manager(actor)

    pod = db.query(Pod).filter(
        Pod.id == pod_id,
        Pod.is_active.is_(True),
    ).first()

    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.employment_status == "Active",
    ).first()

    if not pod or not employee:
        raise OrganizationError("Active pod and employee are required.")

    if employee.role != "Pod Lead":
        raise OrganizationError(
            "Selected employee must have Pod Lead role."
        )

    if employee.pod_id not in (None, pod.id):
        raise OrganizationError(
            "Employee already belongs to another pod."
        )

    old_lead = pod.lead_employee_id

    if old_lead and old_lead != employee.id:
        old_employee = db.query(Employee).filter(
            Employee.id == old_lead
        ).first()

        if old_employee and old_employee.pod_id == pod.id:
            old_employee.pod_id = None

    pod.lead_employee_id = employee.id
    employee.pod_id = pod.id

    db.commit()
    db.refresh(pod)

    return pod


# =====================================================
# BRANDS
# =====================================================

def create_brand(db, actor_id, name, description=None):
    actor = get_actor(db, actor_id)
    require_manager(actor)

    name = name.strip()

    if not name:
        raise OrganizationError("Brand name is required.")

    if db.query(Brand).filter(Brand.name.ilike(name)).first():
        raise OrganizationError("Brand already exists.")

    brand = Brand(
        name=name,
        description=description.strip() if description else None,
        is_active=True,
    )

    db.add(brand)
    db.commit()
    db.refresh(brand)

    return brand


def update_brand(db, actor_id, brand_id, name, description=None):
    actor = get_actor(db, actor_id)
    require_manager(actor)

    brand = db.query(Brand).filter(
        Brand.id == brand_id
    ).first()

    if not brand:
        raise OrganizationError("Brand not found.")

    name = name.strip()

    if not name:
        raise OrganizationError("Brand name is required.")

    duplicate = db.query(Brand).filter(
        Brand.name.ilike(name),
        Brand.id != brand_id,
    ).first()

    if duplicate:
        raise OrganizationError("Another brand uses this name.")

    brand.name = name
    brand.description = description.strip() if description else None

    db.commit()
    db.refresh(brand)

    return brand


# =====================================================
# PROCESSES
# =====================================================

def create_process(
    db,
    actor_id,
    name,
    brand_id,
    minimum_staff=1,
    operating_calendar="daily",
    description=None,
):
    actor = get_actor(db, actor_id)
    require_manager(actor)

    name = name.strip()

    if not name:
        raise OrganizationError("Process name is required.")

    if minimum_staff < 1:
        raise OrganizationError("Minimum staff must be at least 1.")

    if operating_calendar not in (
        "daily",
        "weekdays",
        "year_round",
    ):
        raise OrganizationError("Invalid operating calendar.")

    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.is_active.is_(True),
    ).first()

    if not brand:
        raise OrganizationError("Active brand not found.")

    duplicate = db.query(Process).filter(
        Process.brand_id == brand_id,
        Process.name.ilike(name),
    ).first()

    if duplicate:
        raise OrganizationError(
            "This process already exists under this brand."
        )

    process = Process(
        name=name,
        brand_id=brand_id,
        minimum_staff=minimum_staff,
        operating_calendar=operating_calendar,
        description=description.strip() if description else None,
        is_active=True,
    )

    db.add(process)
    db.commit()
    db.refresh(process)

    return process


def update_process(
    db,
    actor_id,
    process_id,
    name,
    brand_id,
    minimum_staff,
    operating_calendar,
    description=None,
):
    actor = get_actor(db, actor_id)
    require_manager(actor)

    process = db.query(Process).filter(
        Process.id == process_id
    ).first()

    if not process:
        raise OrganizationError("Process not found.")

    name = name.strip()

    if not name:
        raise OrganizationError("Process name is required.")

    if minimum_staff < 1:
        raise OrganizationError("Minimum staff must be at least 1.")

    if operating_calendar not in (
        "daily",
        "weekdays",
        "year_round",
    ):
        raise OrganizationError("Invalid operating calendar.")

    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.is_active.is_(True),
    ).first()

    if not brand:
        raise OrganizationError("Active brand not found.")

    duplicate = db.query(Process).filter(
        Process.brand_id == brand_id,
        Process.name.ilike(name),
        Process.id != process_id,
    ).first()

    if duplicate:
        raise OrganizationError(
            "This process already exists under this brand."
        )

    process.name = name
    process.brand_id = brand_id
    process.minimum_staff = minimum_staff
    process.operating_calendar = operating_calendar
    process.description = description.strip() if description else None

    db.commit()
    db.refresh(process)

    return process


# =====================================================
# ASSIGNMENTS
# =====================================================

def validate_assignment_dates(start_date, end_date):
    if not isinstance(start_date, date):
        raise OrganizationError("A valid start date is required.")

    if end_date and end_date < start_date:
        raise OrganizationError(
            "End date cannot precede start date."
        )


def check_assignment_overlap(
    db,
    employee_id,
    process_id,
    start_date,
    end_date,
    exclude_assignment_id=None,
):
    query = db.query(Assignment).filter(
        Assignment.employee_id == employee_id,
        Assignment.process_id == process_id,
        Assignment.assignment_status == "Active",
    )

    if exclude_assignment_id is not None:
        query = query.filter(
            Assignment.id != exclude_assignment_id
        )

    new_end = end_date or date.max

    for existing in query.all():
        existing_end = existing.end_date or date.max

        if existing.start_date <= new_end and existing_end >= start_date:
            raise OrganizationError(
                "An active assignment already overlaps this date range."
            )


def create_assignment(
    db,
    actor_id,
    employee_id,
    process_id,
    start_date,
    end_date=None,
    is_primary=False,
):
    actor = get_actor(db, actor_id)
    require_manager_or_pod_lead(actor)

    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.employment_status == "Active",
    ).first()

    process = db.query(Process).filter(
        Process.id == process_id,
        Process.is_active.is_(True),
    ).first()

    if not employee or not process:
        raise OrganizationError(
            "Active employee and process are required."
        )

    require_assignment_scope(actor, employee)

    validate_assignment_dates(start_date, end_date)

    check_assignment_overlap(
        db,
        employee_id,
        process_id,
        start_date,
        end_date,
    )

    assignment = Assignment(
        employee_id=employee_id,
        process_id=process_id,
        start_date=start_date,
        end_date=end_date,
        assignment_status="Active",
        is_primary=is_primary,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def update_assignment(
    db,
    actor_id,
    assignment_id,
    employee_id,
    process_id,
    start_date,
    end_date=None,
    is_primary=False,
):
    actor = get_actor(db, actor_id)
    require_manager_or_pod_lead(actor)

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id
    ).first()

    if not assignment:
        raise OrganizationError("Assignment not found.")

    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.employment_status == "Active",
    ).first()

    process = db.query(Process).filter(
        Process.id == process_id,
        Process.is_active.is_(True),
    ).first()

    if not employee or not process:
        raise OrganizationError(
            "Active employee and process are required."
        )

    require_assignment_scope(actor, employee)

    # Pod Lead cannot edit assignments belonging to another pod.
    if actor.role == "Pod Lead":
        existing_employee = db.query(Employee).filter(
            Employee.id == assignment.employee_id
        ).first()

        require_assignment_scope(actor, existing_employee)

    validate_assignment_dates(start_date, end_date)

    check_assignment_overlap(
        db,
        employee_id,
        process_id,
        start_date,
        end_date,
        exclude_assignment_id=assignment.id,
    )

    assignment.employee_id = employee_id
    assignment.process_id = process_id
    assignment.start_date = start_date
    assignment.end_date = end_date
    assignment.is_primary = is_primary

    db.commit()
    db.refresh(assignment)

    return assignment


# =====================================================
# DEACTIVATION
# =====================================================

def deactivate_record(db, actor_id, record_type, record_id):
    actor = get_actor(db, actor_id)

    models = {
        "pod": Pod,
        "brand": Brand,
        "process": Process,
        "assignment": Assignment,
    }

    model = models.get(record_type)

    if model is None:
        raise OrganizationError("Invalid record type.")

    record = db.query(model).filter(
        model.id == record_id
    ).first()

    if not record:
        raise OrganizationError("Record not found.")

    if record_type != "assignment":
        require_manager(actor)

    if record_type == "pod":
        if not record.is_active:
            raise OrganizationError("Pod is already inactive.")

        if db.query(Employee).filter(
            Employee.pod_id == record_id
        ).first():
            raise OrganizationError(
                "Move employees out of this pod before deactivating it."
            )

        record.is_active = False

    elif record_type == "brand":
        if not record.is_active:
            raise OrganizationError("Brand is already inactive.")

        if db.query(Process).filter(
            Process.brand_id == record_id,
            Process.is_active.is_(True),
        ).first():
            raise OrganizationError(
                "Deactivate its active processes first."
            )

        record.is_active = False

    elif record_type == "process":
        if not record.is_active:
            raise OrganizationError("Process is already inactive.")

        if db.query(Assignment).filter(
            Assignment.process_id == record_id,
            Assignment.assignment_status == "Active",
        ).first():
            raise OrganizationError(
                "Deactivate active assignments first."
            )

        record.is_active = False

    else:
        if record.assignment_status != "Active":
            raise OrganizationError("Assignment is already inactive.")

        employee = db.query(Employee).filter(
            Employee.id == record.employee_id
        ).first()

        require_manager_or_pod_lead(actor)

        if actor.role == "Pod Lead":
            require_assignment_scope(actor, employee)

        record.assignment_status = "Inactive"

    db.commit()

    return True
