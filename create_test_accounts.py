from getpass import getpass
import bcrypt
from src.database.connection import SessionLocal
from src.database.models import Employee, UserAccount
db = SessionLocal()
try:
    pod_lead = db.query(Employee).filter(
        Employee.role == "Pod Lead",
        Employee.employment_status == "Active",
    ).first()
    employee = db.query(Employee).filter(
        Employee.role == "Employee",
        Employee.employment_status == "Active",
    ).first()
    if not pod_lead or not employee:
        print("No active Pod Lead or Employee found.")
        raise SystemExit
    print("\nTEST ACCOUNTS")
    print(f"Pod Lead: {pod_lead.full_name} | {pod_lead.email}")
    print(f"Employee: {employee.full_name} | {employee.email}")
    password = getpass("\nEnter temporary password for both accounts: ")
    confirm = getpass("Confirm temporary password: ")
    if password != confirm:
        print("Passwords do not match.")
        raise SystemExit
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        raise SystemExit
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")
    created = 0
    for person in [pod_lead, employee]:
        account = db.query(UserAccount).filter(
            UserAccount.employee_id == person.id
        ).first()
        if account:
            print(f"Account already exists: {person.email}")
            continue
        db.add(UserAccount(
            employee_id=person.id,
            password_hash=password_hash,
            is_active=True,
        ))
        created += 1
    db.commit()
    print(f"\nCreated {created} test login account(s).")
    print("Use the email addresses printed above to log in.")
    print("Use the temporary password you entered.")
finally:
    db.close()
