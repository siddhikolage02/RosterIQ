
from datetime import date

from src.database.connection import SessionLocal
from src.database.models import (
    Pod,
    Employee,
    Brand,
    Process,
    Assignment,
)


def seed_database():
    db = SessionLocal()

    try:
        # Prevent duplicate sample data
        if db.query(Employee).first():
            print("Sample data already exists.")
            print("No duplicate records were added.")
            return

        print("Adding RosterIQ sample data...")

        # ----------------------------------
        # 1. CREATE FIVE PODS
        # ----------------------------------

        pod_names = [
            "Alpha Pod",
            "Beta Pod",
            "Gamma Pod",
            "Delta Pod",
            "Omega Pod",
        ]

        pods = []

        for name in pod_names:
            pod = Pod(
                name=name,
                description=f"Team responsible for {name} operations"
            )
            db.add(pod)
            pods.append(pod)

        db.flush()

        # ----------------------------------
        # 2. CREATE 30 EMPLOYEES
        # ----------------------------------

        employee_names = [
            "Aarav Sharma",
            "Vivaan Patel",
            "Aditya Verma",
            "Arjun Mehta",
            "Reyansh Shah",
            "Ishaan Gupta",
            "Ananya Rao",
            "Diya Nair",
            "Aadhya Singh",
            "Saanvi Joshi",
            "Myra Kulkarni",
            "Pari Desai",
            "Riya Kapoor",
            "Sara Khan",
            "Ira Mishra",
            "Kavya Iyer",
            "Meera Reddy",
            "Anika Das",
            "Tara Malhotra",
            "Kiara Jain",
            "Kabir Sinha",
            "Rohan Kulkarni",
            "Dev Malhotra",
            "Atharv Rao",
            "Krish Shah",
            "Dhruv Nair",
            "Yash Mehta",
            "Neil Kapoor",
            "Samarth Joshi",
            "Vedant Desai",
        ]

        employees = []

        for index, name in enumerate(employee_names, start=1):

            pod_index = (index - 1) // 6

            role = "Employee"

            if index == 1:
                role = "Manager"
            elif index in [2, 8, 14, 20, 26]:
                role = "Pod Lead"

            employee = Employee(
                employee_code=f"EMP{index:03d}",
                full_name=name,
                email=f"employee{index:03d}@rosteriq.demo",
                role=role,
                employment_status="Active",
                weekly_off_day="Sunday",
                pod_id=pods[pod_index].id,
                date_joined=date(2026, 1, 1),
            )

            db.add(employee)
            employees.append(employee)

        db.flush()

        # Assign one pod lead to each pod
        lead_employee_ids = [2, 8, 14, 20, 26]

        for pod, employee_id in zip(pods, lead_employee_ids):
            pod.lead_employee_id = employee_id

        # ----------------------------------
        # 3. CREATE TEN BRANDS
        # ----------------------------------

        brand_names = [
            "Northstar Retail",
            "Bluewave Finance",
            "Evergreen Foods",
            "UrbanNest Living",
            "PixelPoint Electronics",
            "Sunrise Healthcare",
            "CloudNine Travel",
            "BrightPath Education",
            "NovaStyle Fashion",
            "GreenLeaf Wellness",
        ]

        brands = []

        for name in brand_names:
            brand = Brand(
                name=name,
                description=f"Sample client brand: {name}",
                is_active=True,
            )
            db.add(brand)
            brands.append(brand)

        db.flush()

        # ----------------------------------
        # 4. CREATE TEN PROCESSES
        # ----------------------------------

        process_names = [
            "Customer Support",
            "Transaction Processing",
            "Order Management",
            "Customer Queries",
            "Technical Support",
            "Appointment Management",
            "Booking Operations",
            "Student Support",
            "Sales Support",
            "Wellness Operations",
        ]

        calendars = [
            "year_round",
            "daily",
            "weekdays",
            "daily",
            "year_round",
            "daily",
            "weekdays",
            "daily",
            "year_round",
            "weekdays",
        ]

        processes = []

        for index, brand in enumerate(brands):
            process = Process(
                name=process_names[index],
                brand_id=brand.id,
                minimum_staff=1 if index < 8 else 3,
                operating_calendar=calendars[index],
                description=f"Operations for {brand.name}",
                is_active=True,
            )

            db.add(process)
            processes.append(process)

        db.flush()

        # ----------------------------------
        # 5. CREATE EMPLOYEE ASSIGNMENTS
        # ----------------------------------

        # First eight brands: one employee each
        # Last two brands: three employees each

        assignment_plan = {
            0: [1],
            1: [2],
            2: [3],
            3: [4],
            4: [5],
            5: [6],
            6: [7],
            7: [8],
            8: [9, 10, 11],
            9: [12, 13, 14],
        }

        for process_index, employee_numbers in assignment_plan.items():

            for position, employee_number in enumerate(employee_numbers):

                assignment = Assignment(
                    employee_id=employee_number,
                    process_id=processes[process_index].id,
                    start_date=date(2026, 1, 1),
                    assignment_status="Active",
                    is_primary=(position == 0),
                )

                db.add(assignment)

        # Save everything
        db.commit()

        print("\nSample data added successfully!")
        print("Employees: 30")
        print("Pods: 5")
        print("Brands: 10")
        print("Processes: 10")
        print("Assignments: 14")

    except Exception as error:
        db.rollback()
        print("Error while adding sample data:", error)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
