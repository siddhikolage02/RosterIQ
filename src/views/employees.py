import streamlit as st
import pandas as pd

from datetime import date
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import Pod
from src.services.employee_service import (
    create_employee,
    get_all_employees,
    get_employee_by_id,
    update_employee,
    deactivate_employee,
)


# =========================================================
# HELPERS
# =========================================================

WEEKLY_OFF_OPTIONS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

ROLE_OPTIONS = [
    "Manager",
    "Pod Lead",
    "Employee",
]

STATUS_OPTIONS = [
    "Active",
    "Inactive",
]


def get_pods(db: Session):
    return (
        db.query(Pod)
        .filter(Pod.is_active.is_(True))
        .order_by(Pod.name)
        .all()
    )


def get_employee_dataframe(employees):
    data = []

    for employee in employees:
        data.append({
            "ID": employee.id,
            "Employee Code": employee.employee_code,
            "Full Name": employee.full_name,
            "Email": employee.email,
            "Role": employee.role,
            "Status": employee.employment_status,
            "Pod": employee.pod.name if employee.pod else "Unassigned",
            "Weekly Off": employee.weekly_off_day or "Not Set",
            "Date Joined": (
                employee.date_joined.strftime("%d %b %Y")
                if employee.date_joined
                else "Not Set"
            ),
        })

    return pd.DataFrame(data)


def get_current_employee(db):
    employee_id = st.session_state.get("employee_id")

    if not employee_id:
        return None

    return get_employee_by_id(
    db,
    employee_id,
    actor_id=employee_id,
)


def is_manager(employee):
    return bool(employee and employee.role == "Manager")


def is_pod_lead(employee):
    return bool(employee and employee.role == "Pod Lead")


def get_scoped_employees(db, current_employee):
    employees = get_all_employees(
    db,
    actor_id=current_employee.id,
)

    if is_pod_lead(current_employee):
        employees = [
            employee
            for employee in employees
            if employee.pod_id == current_employee.pod_id
        ]

    return employees


def employee_label(employee):
    return f"{employee.employee_code} - {employee.full_name}"


# =========================================================
# EMPLOYEE DIRECTORY
# =========================================================

def render_employee_directory(db, current_employee):
    st.subheader("Employee Directory")

    if not (is_manager(current_employee) or is_pod_lead(current_employee)):
        st.error("You don't have permission to view employee management.")
        return

    employees = get_scoped_employees(db, current_employee)

    if not employees:
        st.info("No employees found.")
        return

    employee_df = get_employee_dataframe(employees)

    search_text = st.text_input(
        "Search employees",
        placeholder="Search name, employee code or email...",
        key="employee_search",
    )

    if search_text.strip():
        search_text = search_text.strip().lower()

        search_mask = (
            employee_df["Full Name"].str.lower().str.contains(search_text, na=False)
            | employee_df["Employee Code"].str.lower().str.contains(search_text, na=False)
            | employee_df["Email"].str.lower().str.contains(search_text, na=False)
        )
        employee_df = employee_df[search_mask]

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        status_filter = st.selectbox(
            "Employment Status",
            ["All", "Active", "Inactive"],
            key="directory_status_filter",
        )

    with filter_col2:
        role_filter = st.selectbox(
            "Role",
            ["All"] + ROLE_OPTIONS,
            key="directory_role_filter",
        )

    with filter_col3:
        pod_options = ["All"] + sorted(employee_df["Pod"].dropna().unique().tolist())
        pod_filter = st.selectbox(
            "Pod",
            pod_options,
            key="directory_pod_filter",
        )

    if status_filter != "All":
        employee_df = employee_df[employee_df["Status"] == status_filter]

    if role_filter != "All":
        employee_df = employee_df[employee_df["Role"] == role_filter]

    if pod_filter != "All":
        employee_df = employee_df[employee_df["Pod"] == pod_filter]

    st.caption(f"Showing {len(employee_df)} employee(s)")
    st.dataframe(employee_df, width="stretch", hide_index=True)


# =========================================================
# ADD EMPLOYEE
# =========================================================

def render_add_employee(db, current_employee):
    if not is_manager(current_employee):
        st.warning("Only Managers can create new employee records.")
        return

    st.subheader("Add New Employee")

    pods = get_pods(db)
    pod_options = {"Unassigned": None}

    for pod in pods:
        pod_options[pod.name] = pod.id

    with st.form("add_employee_form"):
        col1, col2 = st.columns(2)

        with col1:
            employee_code = st.text_input("Employee Code *", placeholder="EMP031")
            full_name = st.text_input("Full Name *")
            email = st.text_input("Email Address *")
            role = st.selectbox("Role *", ROLE_OPTIONS)

        with col2:
            employment_status = st.selectbox("Employment Status", STATUS_OPTIONS, index=0)
            weekly_off_day = st.selectbox("Weekly Off", ["Not Set"] + WEEKLY_OFF_OPTIONS)
            selected_pod = st.selectbox("Pod", list(pod_options.keys()))
            date_joined = st.date_input(
                "Date Joined",
                value=date.today(),
                max_value=date.today(),
            )

        submitted = st.form_submit_button("Create Employee", width="stretch")

        if submitted:
            try:
                employee = create_employee(
                    db=db,
                    actor_id=current_employee.id,
                    employee_code=employee_code,
                    full_name=full_name,
                    email=email,
                    role=role,
                    employment_status=employment_status,
                    weekly_off_day=None if weekly_off_day == "Not Set" else weekly_off_day,
                    pod_id=pod_options[selected_pod],
                    date_joined=date_joined,
                )

                st.success(f"Employee {employee.employee_code} created successfully!")
                st.rerun()

            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unable to create employee: {exc}")


# =========================================================
# EDIT EMPLOYEE
# =========================================================

def render_edit_employee(db, current_employee):
    st.subheader("Edit Employee")

    if not (is_manager(current_employee) or is_pod_lead(current_employee)):
        st.error("You don't have permission to edit employees.")
        return

    employees = get_scoped_employees(db, current_employee)

    if not employees:
        st.info("No employees available to edit.")
        return

    employee_options = {
        employee_label(employee): employee.id
        for employee in employees
    }

    selected_label = st.selectbox(
        "Select Employee",
        list(employee_options.keys()),
        key="edit_employee_selection",
    )

    employee_id = employee_options[selected_label]
    employee = get_employee_by_id(
        db,
        employee_id,
        actor_id=current_employee.id,
    )

    if not employee:
        st.error("Employee record not found.")
        return

    pods = get_pods(db)
    pod_options = {"Unassigned": None}

    for pod in pods:
        pod_options[pod.name] = pod.id

    current_pod_name = employee.pod.name if employee.pod else "Unassigned"

    if current_pod_name not in pod_options:
        pod_options[current_pod_name] = employee.pod_id

    with st.form("edit_employee_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.text_input("Employee Code", value=employee.employee_code, disabled=True)
            full_name = st.text_input("Full Name", value=employee.full_name)
            email = st.text_input("Email Address", value=employee.email)
            date_joined = st.date_input(
                "Date Joined",
                value=employee.date_joined or date.today(),
                max_value=date.today(),
            )

        with col2:
            if is_manager(current_employee):
                role = st.selectbox(
                    "Role",
                    ROLE_OPTIONS,
                    index=ROLE_OPTIONS.index(employee.role) if employee.role in ROLE_OPTIONS else 2,
                )
                employment_status = st.selectbox(
                    "Employment Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(employee.employment_status)
                    if employee.employment_status in STATUS_OPTIONS
                    else 0,
                )
                selected_pod = st.selectbox(
                    "Pod",
                    list(pod_options.keys()),
                    index=list(pod_options.keys()).index(current_pod_name),
                )
            else:
                role = employee.role
                employment_status = employee.employment_status
                selected_pod = current_pod_name

                st.text_input("Role", value=employee.role, disabled=True)
                st.text_input("Employment Status", value=employee.employment_status, disabled=True)
                st.text_input("Pod", value=current_pod_name, disabled=True)

            weekly_off_day = st.selectbox(
                "Weekly Off",
                ["Not Set"] + WEEKLY_OFF_OPTIONS,
                index=WEEKLY_OFF_OPTIONS.index(employee.weekly_off_day) + 1
                if employee.weekly_off_day in WEEKLY_OFF_OPTIONS
                else 0,
            )

        submitted = st.form_submit_button("Save Changes", width="stretch")

        if submitted:
            try:
                updates = {
                    "full_name": full_name,
                    "email": email,
                    "weekly_off_day": None if weekly_off_day == "Not Set" else weekly_off_day,
                    "date_joined": date_joined,
                }

                if is_manager(current_employee):
                    updates.update({
                        "role": role,
                        "employment_status": employment_status,
                        "pod_id": pod_options[selected_pod],
                    })

                updated_employee = update_employee(
                    db,
                    employee_id,
                    actor_id=current_employee.id,
                    **updates,
                    )
                st.success(f"{updated_employee.full_name} updated successfully!")
                st.rerun()

            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unable to update employee: {exc}")


# =========================================================
# EMPLOYEE DETAILS
# =========================================================

def render_employee_details(db, current_employee):
    st.subheader("Employee Details")

    if not (is_manager(current_employee) or is_pod_lead(current_employee)):
        st.error("You don't have permission to view employee details.")
        return

    employees = get_scoped_employees(db, current_employee)

    if not employees:
        st.info("No employee records available.")
        return

    employee_options = {
        employee_label(employee): employee.id
        for employee in employees
    }

    selected_label = st.selectbox(
        "Choose Employee",
        list(employee_options.keys()),
        key="employee_details_selection",
    )

    employee = get_employee_by_id(
        db,
        employee_options[selected_label],
        actor_id=current_employee.id,
    )

    if employee:
        st.divider()

        col1, col2, col3 = st.columns(3)
        col1.metric("Employee ID", employee.id)
        col2.metric("Employee Code", employee.employee_code)
        col3.metric("Status", employee.employment_status)

        st.markdown("### Personal & Work Information")

        details = {
            "Full Name": employee.full_name,
            "Email": employee.email,
            "Role": employee.role,
            "Pod": employee.pod.name if employee.pod else "Unassigned",
            "Weekly Off": employee.weekly_off_day or "Not Set",
            "Date Joined": (
                employee.date_joined.strftime("%d %B %Y")
                if employee.date_joined
                else "Not Set"
            ),
        }

        details_df = pd.DataFrame(list(details.items()), columns=["Field", "Value"])
        details_df["Value"] = details_df["Value"].astype(str)

        st.dataframe(details_df, width="stretch", hide_index=True)


# =========================================================
# ACTIVATE / DEACTIVATE EMPLOYEE
# =========================================================

def render_employee_status_management(db, current_employee):
    if not is_manager(current_employee):
        st.warning("Only Managers can change employment status.")
        return

    st.subheader("Employee Status Management")

    employees = get_all_employees(
        db,
        actor_id=current_employee.id,
    )

    employee_options = {
        f"{employee_label(employee)} ({employee.employment_status})": employee.id
        for employee in employees
    }

    if not employee_options:
        st.info("No employee records available.")
        return

    selected_label = st.selectbox(
        "Select Employee",
        list(employee_options.keys()),
        key="status_employee_selection",
    )

    employee = get_employee_by_id(
        db,
        employee_options[selected_label],
        actor_id=current_employee.id,
    )

    if not employee:
        st.error("Employee not found.")
        return

    st.write(f"**Employee:** {employee.full_name}")
    st.write(f"**Current Status:** {employee.employment_status}")

    logged_in_employee_id = st.session_state.get("employee_id")

    if employee.id == logged_in_employee_id:
        st.warning("You cannot deactivate your own account from this screen.")
        return

    if employee.employment_status == "Active":
        st.warning(
            "Deactivating this employee will prevent them from being treated "
            "as an active employee. Their historical records will remain in the database."
        )

        confirm = st.checkbox(
            "I confirm that I want to deactivate this employee.",
            key="confirm_deactivation",
        )

        if st.button("Deactivate Employee", type="primary", disabled=not confirm):
            try:
                deactivate_employee(
                    db,
                    employee.id,
                    actor_id=current_employee.id,
                )
                st.success(f"{employee.full_name} has been deactivated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to deactivate employee: {exc}")

    else:
        confirm = st.checkbox(
            "I confirm that I want to reactivate this employee.",
            key="confirm_reactivation",
        )

        if st.button("Reactivate Employee", type="primary", disabled=not confirm):
            try:
                update_employee(
                    db,
                    employee.id,
                    actor_id=current_employee.id,
                    employment_status="Active",
                )
                st.success(f"{employee.full_name} has been reactivated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to reactivate employee: {exc}")


# =========================================================
# MAIN EMPLOYEE PAGE
# =========================================================

def render_employees():
    st.title("Employee Management")

    st.caption(
        "Manage workforce records, employee details, "
        "roles, pods and employment status."
    )

    db = SessionLocal()

    try:
        current_employee = get_current_employee(db)

        if not current_employee:
            st.error("Unable to identify the logged-in employee.")
            return

        if not (is_manager(current_employee) or is_pod_lead(current_employee)):
            st.error("You don't have permission to access Employee Management.")
            return

        employees = get_scoped_employees(db, current_employee)

        active_count = sum(employee.employment_status == "Active" for employee in employees)
        inactive_count = sum(employee.employment_status == "Inactive" for employee in employees)
        total_count = len(employees)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Employees", total_count)
        col2.metric("Active Employees", active_count)
        col3.metric("Inactive Employees", inactive_count)

        st.divider()

        tabs = st.tabs([
            "Directory",
            "Employee Details",
            "Add Employee",
            "Edit Employee",
            "Status Management",
        ])

        with tabs[0]:
            render_employee_directory(db, current_employee)

        with tabs[1]:
            render_employee_details(db, current_employee)

        with tabs[2]:
            render_add_employee(db, current_employee)

        with tabs[3]:
            render_edit_employee(db, current_employee)

        with tabs[4]:
            render_employee_status_management(db, current_employee)

    finally:
        db.close()
