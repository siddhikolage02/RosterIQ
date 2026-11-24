
import pytest

from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.database.models import Pod, Employee, Brand, Process, Assignment

from src.services.organization_service import (
    OrganizationError,
    create_pod,
    create_brand,
    create_process,
    create_assignment,
    update_assignment,
    assign_pod_lead,
    deactivate_record,
    get_organization_data,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = Session()

    # Manager
    manager = Employee(
        employee_code="TEST-MGR",
        full_name="Test Manager",
        email="manager@test.com",
        role="Manager",
        employment_status="Active",
    )

    session.add(manager)
    session.flush()

    # Pods
    pod1 = Pod(name="Test Pod 1", is_active=True)
    pod2 = Pod(name="Test Pod 2", is_active=True)

    session.add_all([pod1, pod2])
    session.flush()

    # Pod Lead
    lead = Employee(
        employee_code="TEST-LEAD",
        full_name="Test Lead",
        email="lead@test.com",
        role="Pod Lead",
        employment_status="Active",
        pod_id=pod1.id,
    )

    # Pod employees
    employee1 = Employee(
        employee_code="TEST-EMP1",
        full_name="Employee One",
        email="emp1@test.com",
        role="Employee",
        employment_status="Active",
        pod_id=pod1.id,
    )

    employee2 = Employee(
        employee_code="TEST-EMP2",
        full_name="Employee Two",
        email="emp2@test.com",
        role="Employee",
        employment_status="Active",
        pod_id=pod2.id,
    )

    employee3 = Employee(
        employee_code="TEST-EMP3",
        full_name="Employee Three",
        email="emp3@test.com",
        role="Employee",
        employment_status="Active",
        pod_id=pod1.id,
    )

    session.add_all([lead, employee1, employee2, employee3])
    session.flush()

    pod1.lead_employee_id = lead.id

    brand = Brand(
        name="Test Brand",
        is_active=True,
    )

    session.add(brand)
    session.flush()

    process = Process(
        name="Test Process",
        brand_id=brand.id,
        minimum_staff=1,
        operating_calendar="daily",
        is_active=True,
    )

    session.add(process)
    session.flush()

    session.commit()

    yield {
        "db": session,
        "manager": manager,
        "lead": lead,
        "employee1": employee1,
        "employee2": employee2,
        "employee3": employee3,
        "pod1": pod1,
        "pod2": pod2,
        "brand": brand,
        "process": process,
    }

    session.close()
    engine.dispose()


def test_manager_can_create_pod(db):
    pod = create_pod(
        db["db"],
        db["manager"].id,
        "New Test Pod",
    )

    assert pod.name == "New Test Pod"
    assert pod.is_active is True


def test_employee_cannot_create_pod(db):
    with pytest.raises(OrganizationError):
        create_pod(
            db["db"],
            db["employee1"].id,
            "Unauthorized Pod",
        )


def test_manager_can_create_brand(db):
    brand = create_brand(
        db["db"],
        db["manager"].id,
        "New Test Brand",
    )

    assert brand.name == "New Test Brand"


def test_employee_cannot_create_brand(db):
    with pytest.raises(OrganizationError):
        create_brand(
            db["db"],
            db["employee1"].id,
            "Unauthorized Brand",
        )


def test_manager_can_create_process(db):
    process = create_process(
        db["db"],
        db["manager"].id,
        "New Process",
        db["brand"].id,
        minimum_staff=2,
    )

    assert process.minimum_staff == 2


def test_pod_lead_can_assign_own_pod_employee(db):
    assignment = create_assignment(
        db["db"],
        db["lead"].id,
        db["employee1"].id,
        db["process"].id,
        date.today(),
    )

    assert assignment.employee_id == db["employee1"].id


def test_pod_lead_cannot_assign_other_pod_employee(db):
    with pytest.raises(OrganizationError):
        create_assignment(
            db["db"],
            db["lead"].id,
            db["employee2"].id,
            db["process"].id,
            date.today(),
        )


def test_employee_cannot_create_assignment(db):
    with pytest.raises(OrganizationError):
        create_assignment(
            db["db"],
            db["employee1"].id,
            db["employee1"].id,
            db["process"].id,
            date.today(),
        )


def test_overlapping_assignment_is_rejected(db):
    start = date.today()

    create_assignment(
        db["db"],
        db["manager"].id,
        db["employee1"].id,
        db["process"].id,
        start,
        start + timedelta(days=10),
    )

    with pytest.raises(OrganizationError):
        create_assignment(
            db["db"],
            db["manager"].id,
            db["employee1"].id,
            db["process"].id,
            start + timedelta(days=5),
            start + timedelta(days=15),
        )


def test_non_overlapping_assignment_is_allowed(db):
    start = date.today()

    create_assignment(
        db["db"],
        db["manager"].id,
        db["employee1"].id,
        db["process"].id,
        start,
        start + timedelta(days=5),
    )

    assignment = create_assignment(
        db["db"],
        db["manager"].id,
        db["employee1"].id,
        db["process"].id,
        start + timedelta(days=6),
        start + timedelta(days=10),
    )

    assert assignment.id is not None


def test_manager_cannot_deactivate_process_with_active_assignment(db):
    create_assignment(
        db["db"],
        db["manager"].id,
        db["employee1"].id,
        db["process"].id,
        date.today(),
    )

    with pytest.raises(OrganizationError):
        deactivate_record(
            db["db"],
            db["manager"].id,
            "process",
            db["process"].id,
        )


def test_employee_cannot_deactivate_assignment(db):
    assignment = create_assignment(
        db["db"],
        db["manager"].id,
        db["employee1"].id,
        db["process"].id,
        date.today(),
    )

    with pytest.raises(OrganizationError):
        deactivate_record(
            db["db"],
            db["employee1"].id,
            "assignment",
            assignment.id,
        )


def test_pod_lead_only_sees_own_pod_employees(db):
    data = get_organization_data(
        db["db"],
        db["lead"].id,
    )

    employee_ids = {
        employee.id for employee in data["employees"]
    }

    assert db["employee1"].id in employee_ids
    assert db["employee3"].id in employee_ids
    assert db["employee2"].id not in employee_ids


def test_pod_lead_cannot_deactivate_other_pod_assignment(db):
    assignment = create_assignment(
        db["db"],
        db["manager"].id,
        db["employee2"].id,
        db["process"].id,
        date.today(),
    )

    with pytest.raises(OrganizationError):
        deactivate_record(
            db["db"],
            db["lead"].id,
            "assignment",
            assignment.id,
        )
