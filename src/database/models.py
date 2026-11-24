
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.database.connection import Base


# ----------------------------------
# 1. POD TABLE
# ----------------------------------

class Pod(Base):
    __tablename__ = "pods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # The employee who leads this pod
    lead_employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=True
    )

    is_active = Column(Boolean, default=True)

    # Relationships
    employees = relationship(
        "Employee",
        back_populates="pod",
        foreign_keys="Employee.pod_id"
    )

    lead = relationship(
        "Employee",
        foreign_keys=[lead_employee_id],
        post_update=True
    )


# ----------------------------------
# 2. EMPLOYEE TABLE
# ----------------------------------

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    employee_code = Column(String(30), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)

    role = Column(String(50), default="Employee")
    employment_status = Column(String(30), default="Active")

    weekly_off_day = Column(String(20), nullable=True)

    pod_id = Column(
        Integer,
        ForeignKey("pods.id"),
        nullable=True
    )

    date_joined = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    pod = relationship(
        "Pod",
        back_populates="employees",
        foreign_keys=[pod_id]
    )

    assignments = relationship(
        "Assignment",
        back_populates="employee",
        cascade="all, delete-orphan"
    )

    availability_records = relationship(
        "EmployeeAvailability",
        back_populates="employee",
        cascade="all, delete-orphan"
    )

    leave_requests = relationship(
        "LeaveRequest",
        back_populates="employee",
        cascade="all, delete-orphan",
        foreign_keys="LeaveRequest.employee_id"
    )

    roster_entries = relationship(
        "RosterEntry",
        back_populates="employee"
    )

# ----------------------------------
# USER ACCOUNT TABLE
# ----------------------------------

class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        unique=True,
        nullable=False,
    )

    password_hash = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


# ----------------------------------
# 3. BRAND TABLE
# ----------------------------------

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # A brand can have multiple processes
    processes = relationship(
        "Process",
        back_populates="brand",
        cascade="all, delete-orphan"
    )


# ----------------------------------
# 4. PROCESS TABLE
# ----------------------------------

class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    brand_id = Column(
        Integer,
        ForeignKey("brands.id"),
        nullable=False
    )

    minimum_staff = Column(Integer, default=1)

    # Example: daily, year_round, weekdays
    operating_calendar = Column(
        String(30),
        default="daily"
    )

    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    brand = relationship(
        "Brand",
        back_populates="processes"
    )

    assignments = relationship(
        "Assignment",
        back_populates="process",
        cascade="all, delete-orphan"
    )

    calendar = relationship(
        "OperatingCalendar",
        back_populates="process",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "name",
            name="unique_process_per_brand"
        ),
    )

    roster_entries = relationship(
        "RosterEntry",
        back_populates="process"
    )


# ----------------------------------
# 5. ASSIGNMENT TABLE
# ----------------------------------

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    process_id = Column(
        Integer,
        ForeignKey("processes.id"),
        nullable=False
    )

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    assignment_status = Column(
        String(30),
        default="Active"
    )

    is_primary = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    employee = relationship(
        "Employee",
        back_populates="assignments"
    )

    process = relationship(
        "Process",
        back_populates="assignments"
    )


# ----------------------------------
# 6. EMPLOYEE AVAILABILITY TABLE
# ----------------------------------

class EmployeeAvailability(Base):
    __tablename__ = "employee_availability"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    availability_date = Column(Date, nullable=False)

    # Available or unavailable
    status = Column(String(30), nullable=False)

    reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship(
        "Employee",
        back_populates="availability_records"
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "availability_date",
            name="unique_employee_availability_date"
        ),
    )


# ----------------------------------
# 7. LEAVE REQUEST TABLE
# ----------------------------------

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Planned leave, sick leave, emergency, comp-off
    leave_type = Column(String(40), nullable=False)

    # Pending, Approved, Rejected, Cancelled
    status = Column(String(30), default="Pending")

    reason = Column(Text, nullable=True)

    reviewed_by = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=True
    )

    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship(
        "Employee",
        back_populates="leave_requests",
        foreign_keys=[employee_id]
    )

    reviewer = relationship(
        "Employee",
        foreign_keys=[reviewed_by]
    )


# ----------------------------------
# 8. OPERATING CALENDAR TABLE
# ----------------------------------

class OperatingCalendar(Base):
    __tablename__ = "operating_calendars"

    id = Column(Integer, primary_key=True, index=True)

    # Each process gets its own operating calendar
    process_id = Column(
        Integer,
        ForeignKey("processes.id"),
        nullable=False,
        unique=True
    )

    calendar_name = Column(String(100), nullable=False)

    # Example: Monday,Tuesday,Wednesday,Thursday,Friday
    working_days = Column(String(150), nullable=False)

    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    process = relationship(
        "Process",
        back_populates="calendar"
    )

    holidays = relationship(
        "PublicHoliday",
        back_populates="calendar",
        cascade="all, delete-orphan"
    )


# ----------------------------------
# 9. PUBLIC HOLIDAY TABLE
# ----------------------------------

class PublicHoliday(Base):
    __tablename__ = "public_holidays"

    id = Column(Integer, primary_key=True, index=True)

    calendar_id = Column(
        Integer,
        ForeignKey("operating_calendars.id"),
        nullable=False
    )

    holiday_date = Column(Date, nullable=False)

    holiday_name = Column(String(150), nullable=False)

    description = Column(Text, nullable=True)

    calendar = relationship(
        "OperatingCalendar",
        back_populates="holidays"
    )

    __table_args__ = (
        UniqueConstraint(
            "calendar_id",
            "holiday_date",
            name="unique_holiday_per_calendar"
        ),
    )


# ----------------------------------
# 10. ROSTER RUN TABLE
# ----------------------------------

class RosterRun(Base):
    __tablename__ = "roster_runs"

    id = Column(Integer, primary_key=True, index=True)

    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    # Draft, Published, Archived
    status = Column(String(30), default="Draft")

    created_at = Column(DateTime, default=datetime.utcnow)

    entries = relationship(
        "RosterEntry",
        back_populates="roster",
        cascade="all, delete-orphan"
    )

# ----------------------------------
# 11. ROSTER ENTRY TABLE
# ----------------------------------

class RosterEntry(Base):
    __tablename__ = "roster_entries"

    id = Column(Integer, primary_key=True, index=True)

    roster_id = Column(
        Integer,
        ForeignKey("roster_runs.id"),
        nullable=False
    )

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    process_id = Column(
        Integer,
        ForeignKey("processes.id"),
        nullable=False
    )

    roster_date = Column(Date, nullable=False)

    # Scheduled, Completed, Cancelled
    status = Column(String(30), default="Scheduled")

    created_at = Column(DateTime, default=datetime.utcnow)

    roster = relationship(
        "RosterRun",
        back_populates="entries"
    )

    employee = relationship(
        "Employee",
        back_populates="roster_entries"
    )

    process = relationship(
        "Process",
        back_populates="roster_entries"
    )

    __table_args__ = (
        UniqueConstraint(
            "roster_id",
            "employee_id",
            "roster_date",
            name="unique_employee_per_roster_day"
        ),
    )


# ----------------------------------
# ROSTER APPROVAL TABLE
# ----------------------------------

class RosterApproval(Base):
    __tablename__ = "roster_approvals"

    id = Column(Integer, primary_key=True, index=True)

    roster_id = Column(
        Integer,
        ForeignKey("roster_runs.id"),
        nullable=False,
    )

    submitted_by_employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False,
    )

    reviewed_by_employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=True,
    )

    status = Column(String(30), default="Pending", nullable=False)

    comments = Column(Text, nullable=True)

    submitted_at = Column(DateTime, default=datetime.utcnow)

    reviewed_at = Column(DateTime, nullable=True)


# ----------------------------------
# ROSTER CHANGE LOG TABLE
# ----------------------------------

class RosterChangeLog(Base):
    __tablename__ = "roster_change_logs"

    id = Column(Integer, primary_key=True, index=True)

    roster_id = Column(
        Integer,
        ForeignKey("roster_runs.id"),
        nullable=False,
    )

    entry_id = Column(
        Integer,
        ForeignKey("roster_entries.id"),
        nullable=True,
    )

    changed_by_employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False,
    )

    action = Column(String(50), nullable=False)

    old_values = Column(Text, nullable=True)

    new_values = Column(Text, nullable=True)

    comments = Column(Text, nullable=True)

    changed_at = Column(DateTime, default=datetime.utcnow)
