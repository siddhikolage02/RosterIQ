from src.database.connection import Base, engine

# Import models so SQLAlchemy knows about all tables
from src.database.models import (
    Pod,
    Employee,
    UserAccount,
    RosterApproval,
    RosterChangeLog,
    Brand,
    Process,
    Assignment,
    EmployeeAvailability,
    LeaveRequest,
    OperatingCalendar,
    PublicHoliday,
)


def initialize_database():
    print("Initializing RosterIQ database...")

    # Create all tables
    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully!")

    print("\nAvailable tables:")
    for table_name in Base.metadata.tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    initialize_database()
