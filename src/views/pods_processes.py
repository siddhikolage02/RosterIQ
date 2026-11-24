
import streamlit as st
import pandas as pd

from datetime import date

from src.database.connection import SessionLocal
from src.services.organization_service import (
    OrganizationError,
    get_organization_data,
    create_pod,
    update_pod,
    assign_pod_lead,
    create_brand,
    update_brand,
    create_process,
    update_process,
    create_assignment,
    update_assignment,
    deactivate_record,
)


def render_pods_processes():

    st.title("Pods & Processes")
    st.caption("Organizational structure and workforce assignments.")

    actor_id = st.session_state.get("employee_id")
    db = SessionLocal()

    try:
        data = get_organization_data(db, actor_id)

        actor = data["actor"]
        manager = actor.role == "Manager"
        pod_lead = actor.role == "Pod Lead"

        tabs = st.tabs([
            "Pods",
            "Brands",
            "Processes",
            "Assignments",
        ])

        # =================================================
        # PODS
        # =================================================

        with tabs[0]:

            st.subheader("Pods")

            if manager:

                with st.expander("➕ Create Pod"):
                    with st.form("create_pod_form"):
                        name = st.text_input("Pod Name")
                        description = st.text_area("Description")
                        submitted = st.form_submit_button("Create Pod")

                    if submitted:
                        try:
                            create_pod(db, actor_id, name, description)
                            st.success("Pod created successfully.")
                            st.rerun()
                        except OrganizationError as exc:
                            st.error(str(exc))

                active_pods = [
                    p for p in data["pods"] if p.is_active
                ]

                if active_pods:

                    pod_map = {
                        f"{p.name} (ID: {p.id})": p.id
                        for p in active_pods
                    }

                    with st.expander("✏️ Edit Pod"):
                        with st.form("edit_pod_form"):
                            selected_pod = st.selectbox(
                                "Select Pod",
                                list(pod_map.keys()),
                                key="edit_pod_select",
                            )

                            pod = db.query(
                                type(data["pods"][0])
                            ).filter(
                                type(data["pods"][0]).id
                                == pod_map[selected_pod]
                            ).first()

                            new_name = st.text_input(
                                "Pod Name",
                                value=pod.name,
                            )

                            new_description = st.text_area(
                                "Description",
                                value=pod.description or "",
                            )

                            submitted = st.form_submit_button("Save Changes")

                        if submitted:
                            try:
                                update_pod(
                                    db,
                                    actor_id,
                                    pod.id,
                                    new_name,
                                    new_description,
                                )
                                st.success("Pod updated.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

                    with st.expander("👤 Assign / Change Pod Lead"):

                        eligible_leads = [
                            e for e in data["employees"]
                            if e.role == "Pod Lead"
                            and e.employment_status == "Active"
                        ]

                        if eligible_leads:

                            lead_map = {
                                f"{e.full_name} ({e.employee_code})": e.id
                                for e in eligible_leads
                            }

                            with st.form("assign_lead_form"):

                                selected_pod = st.selectbox(
                                    "Pod",
                                    list(pod_map.keys()),
                                )

                                selected_lead = st.selectbox(
                                    "Pod Lead",
                                    list(lead_map.keys()),
                                )

                                submitted = st.form_submit_button(
                                    "Assign Pod Lead"
                                )

                            if submitted:
                                try:
                                    assign_pod_lead(
                                        db,
                                        actor_id,
                                        pod_map[selected_pod],
                                        lead_map[selected_lead],
                                    )
                                    st.success("Pod lead assigned.")
                                    st.rerun()
                                except OrganizationError as exc:
                                    st.error(str(exc))

                        else:
                            st.info("No active Pod Lead employees available.")

                    with st.expander("Deactivate Pod"):

                        with st.form("deactivate_pod_form"):
                            selected = st.selectbox(
                                "Pod",
                                list(pod_map.keys()),
                            )

                            submitted = st.form_submit_button(
                                "Deactivate Pod"
                            )

                        if submitted:
                            try:
                                deactivate_record(
                                    db,
                                    actor_id,
                                    "pod",
                                    pod_map[selected],
                                )
                                st.success("Pod deactivated.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

            if data["pods"]:

                st.dataframe(
                    pd.DataFrame([
                        {
                            "Pod": p.name,
                            "Description": p.description,
                            "Lead": (
                                p.lead.full_name
                                if p.lead else "Not assigned"
                            ),
                            "Status": (
                                "Active" if p.is_active else "Inactive"
                            ),
                            "Employees": len(p.employees),
                        }
                        for p in data["pods"]
                    ]),
                    hide_index=True,
                    width="stretch",
                )

            else:
                st.info("No pods available.")

        # =================================================
        # BRANDS
        # =================================================

        with tabs[1]:

            st.subheader("Brands")

            if manager:

                with st.expander("➕ Create Brand"):

                    with st.form("create_brand_form"):
                        brand_name = st.text_input("Brand Name")
                        brand_description = st.text_area("Description")
                        submitted = st.form_submit_button("Create Brand")

                    if submitted:
                        try:
                            create_brand(
                                db,
                                actor_id,
                                brand_name,
                                brand_description,
                            )
                            st.success("Brand created.")
                            st.rerun()
                        except OrganizationError as exc:
                            st.error(str(exc))

                active_brands = [
                    b for b in data["brands"] if b.is_active
                ]

                if active_brands:

                    brand_map = {
                        f"{b.name} (ID: {b.id})": b.id
                        for b in active_brands
                    }

                    with st.expander("✏️ Edit Brand"):

                        with st.form("edit_brand_form"):

                            selected = st.selectbox(
                                "Brand",
                                list(brand_map.keys()),
                            )

                            brand = next(
                                b for b in active_brands
                                if b.id == brand_map[selected]
                            )

                            new_name = st.text_input(
                                "Brand Name",
                                value=brand.name,
                            )

                            new_description = st.text_area(
                                "Description",
                                value=brand.description or "",
                            )

                            submitted = st.form_submit_button("Save Changes")

                        if submitted:
                            try:
                                update_brand(
                                    db,
                                    actor_id,
                                    brand.id,
                                    new_name,
                                    new_description,
                                )
                                st.success("Brand updated.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

                    with st.expander("Deactivate Brand"):

                        with st.form("deactivate_brand_form"):
                            selected = st.selectbox(
                                "Brand",
                                list(brand_map.keys()),
                                key="deactivate_brand",
                            )

                            submitted = st.form_submit_button(
                                "Deactivate Brand"
                            )

                        if submitted:
                            try:
                                deactivate_record(
                                    db,
                                    actor_id,
                                    "brand",
                                    brand_map[selected],
                                )
                                st.success("Brand deactivated.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

            if data["brands"]:

                st.dataframe(
                    pd.DataFrame([
                        {
                            "Brand": b.name,
                            "Description": b.description,
                            "Status": (
                                "Active" if b.is_active else "Inactive"
                            ),
                            "Processes": len(b.processes),
                        }
                        for b in data["brands"]
                    ]),
                    hide_index=True,
                    width="stretch",
                )

            else:
                st.info("No brands available.")

        # =================================================
        # PROCESSES
        # =================================================

        with tabs[2]:

            st.subheader("Processes")

            if manager:

                active_brands = [
                    b for b in data["brands"] if b.is_active
                ]

                brand_map = {
                    b.name: b.id for b in active_brands
                }

                if brand_map:

                    with st.expander("➕ Create Process"):

                        with st.form("create_process_form"):

                            name = st.text_input("Process Name")

                            selected_brand = st.selectbox(
                                "Brand",
                                list(brand_map.keys()),
                            )

                            minimum_staff = st.number_input(
                                "Minimum Staff",
                                min_value=1,
                                value=1,
                            )

                            calendar = st.selectbox(
                                "Operating Calendar",
                                ["daily", "weekdays", "year_round"],
                            )

                            description = st.text_area("Description")

                            submitted = st.form_submit_button(
                                "Create Process"
                            )

                        if submitted:
                            try:
                                create_process(
                                    db,
                                    actor_id,
                                    name,
                                    brand_map[selected_brand],
                                    minimum_staff,
                                    calendar,
                                    description,
                                )
                                st.success("Process created.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

                active_processes = [
                    p for p in data["processes"] if p.is_active
                ]

                if active_processes:

                    process_map = {
                        f"{p.name} (ID: {p.id})": p.id
                        for p in active_processes
                    }

                    with st.expander("✏️ Edit Process"):

                        with st.form("edit_process_form"):

                            selected = st.selectbox(
                                "Process",
                                list(process_map.keys()),
                            )

                            process = next(
                                p for p in active_processes
                                if p.id == process_map[selected]
                            )

                            new_name = st.text_input(
                                "Process Name",
                                value=process.name,
                            )

                            brand_names = list(brand_map.keys())

                            current_brand_name = next(
                                (
                                    name for name, bid in brand_map.items()
                                    if bid == process.brand_id
                                ),
                                brand_names[0],
                            )

                            new_brand = st.selectbox(
                                "Brand",
                                brand_names,
                                index=brand_names.index(
                                    current_brand_name
                                ),
                            )

                            new_minimum = st.number_input(
                                "Minimum Staff",
                                min_value=1,
                                value=process.minimum_staff,
                            )

                            calendars = [
                                "daily",
                                "weekdays",
                                "year_round",
                            ]

                            new_calendar = st.selectbox(
                                "Operating Calendar",
                                calendars,
                                index=calendars.index(
                                    process.operating_calendar
                                    if process.operating_calendar
                                    in calendars
                                    else "daily"
                                ),
                            )

                            new_description = st.text_area(
                                "Description",
                                value=process.description or "",
                            )

                            submitted = st.form_submit_button(
                                "Save Changes"
                            )

                        if submitted:
                            try:
                                update_process(
                                    db,
                                    actor_id,
                                    process.id,
                                    new_name,
                                    brand_map[new_brand],
                                    new_minimum,
                                    new_calendar,
                                    new_description,
                                )
                                st.success("Process updated.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

                    with st.expander("Deactivate Process"):

                        with st.form("deactivate_process_form"):

                            selected = st.selectbox(
                                "Process",
                                list(process_map.keys()),
                                key="deactivate_process",
                            )

                            submitted = st.form_submit_button(
                                "Deactivate Process"
                            )

                        if submitted:
                            try:
                                deactivate_record(
                                    db,
                                    actor_id,
                                    "process",
                                    process_map[selected],
                                )
                                st.success("Process deactivated.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

            if data["processes"]:

                brand_names = {
                    b.id: b.name for b in data["brands"]
                }

                st.dataframe(
                    pd.DataFrame([
                        {
                            "Process": p.name,
                            "Brand": brand_names.get(
                                p.brand_id, "Unknown"
                            ),
                            "Minimum Staff": p.minimum_staff,
                            "Calendar": p.operating_calendar,
                            "Status": (
                                "Active" if p.is_active else "Inactive"
                            ),
                        }
                        for p in data["processes"]
                    ]),
                    hide_index=True,
                    width="stretch",
                )

            else:
                st.info("No processes available.")

        # =================================================
        # ASSIGNMENTS
        # =================================================

        with tabs[3]:

            st.subheader("Employee Assignments")

            if manager or pod_lead:

                active_employees = [
                    e for e in data["employees"]
                    if e.employment_status == "Active"
                ]

                active_processes = [
                    p for p in data["processes"]
                    if p.is_active
                ]

                employee_map = {
                    f"{e.full_name} ({e.employee_code})": e.id
                    for e in active_employees
                }

                process_map = {
                    f"{p.name} (ID: {p.id})": p.id
                    for p in active_processes
                }

                if employee_map and process_map:

                    with st.expander("➕ Create Assignment"):

                        with st.form("create_assignment_form"):

                            selected_employee = st.selectbox(
                                "Employee",
                                list(employee_map.keys()),
                            )

                            selected_process = st.selectbox(
                                "Process",
                                list(process_map.keys()),
                            )

                            start_date = st.date_input(
                                "Start Date",
                                value=date.today(),
                            )

                            has_end = st.checkbox(
                                "Assignment has an end date"
                            )

                            end_date = (
                                st.date_input("End Date")
                                if has_end else None
                            )

                            primary = st.checkbox(
                                "Primary Assignment"
                            )

                            submitted = st.form_submit_button(
                                "Create Assignment"
                            )

                        if submitted:
                            try:
                                create_assignment(
                                    db,
                                    actor_id,
                                    employee_map[selected_employee],
                                    process_map[selected_process],
                                    start_date,
                                    end_date,
                                    primary,
                                )
                                st.success("Assignment created.")
                                st.rerun()
                            except OrganizationError as exc:
                                st.error(str(exc))

                    active_assignments = [
                        a for a in data["assignments"]
                        if a.assignment_status == "Active"
                    ]

                    if active_assignments:

                        assignment_map = {
                            (
                                f"Assignment #{a.id} | "
                                f"{next((e.full_name for e in active_employees if e.id == a.employee_id), 'Employee')} | "
                                f"{next((p.name for p in active_processes if p.id == a.process_id), 'Process')}"
                            ): a.id
                            for a in active_assignments
                        }

                        with st.expander("✏️ Edit Assignment"):

                            with st.form("edit_assignment_form"):

                                selected = st.selectbox(
                                    "Assignment",
                                    list(assignment_map.keys()),
                                )

                                assignment = next(
                                    a for a in active_assignments
                                    if a.id == assignment_map[selected]
                                )

                                employee_labels = list(employee_map.keys())

                                current_employee = next(
                                    (
                                        label
                                        for label, eid in employee_map.items()
                                        if eid == assignment.employee_id
                                    ),
                                    employee_labels[0],
                                )

                                new_employee = st.selectbox(
                                    "Employee",
                                    employee_labels,
                                    index=employee_labels.index(
                                        current_employee
                                    ),
                                )

                                process_labels = list(process_map.keys())

                                current_process = next(
                                    (
                                        label
                                        for label, pid in process_map.items()
                                        if pid == assignment.process_id
                                    ),
                                    process_labels[0],
                                )

                                new_process = st.selectbox(
                                    "Process",
                                    process_labels,
                                    index=process_labels.index(
                                        current_process
                                    ),
                                )

                                new_start = st.date_input(
                                    "Start Date",
                                    value=assignment.start_date,
                                )

                                new_has_end = st.checkbox(
                                    "Assignment has an end date",
                                    value=assignment.end_date is not None,
                                )

                                new_end = (
                                    st.date_input(
                                        "End Date",
                                        value=assignment.end_date or date.today(),
                                    )
                                    if new_has_end else None
                                )

                                new_primary = st.checkbox(
                                    "Primary Assignment",
                                    value=assignment.is_primary,
                                )

                                submitted = st.form_submit_button(
                                    "Save Assignment"
                                )

                            if submitted:
                                try:
                                    update_assignment(
                                        db,
                                        actor_id,
                                        assignment.id,
                                        employee_map[new_employee],
                                        process_map[new_process],
                                        new_start,
                                        new_end,
                                        new_primary,
                                    )
                                    st.success("Assignment updated.")
                                    st.rerun()
                                except OrganizationError as exc:
                                    st.error(str(exc))

                        with st.expander("Deactivate Assignment"):

                            with st.form("deactivate_assignment_form"):

                                selected = st.selectbox(
                                    "Assignment",
                                    list(assignment_map.keys()),
                                    key="deactivate_assignment",
                                )

                                submitted = st.form_submit_button(
                                    "Deactivate Assignment"
                                )

                            if submitted:
                                try:
                                    deactivate_record(
                                        db,
                                        actor_id,
                                        "assignment",
                                        assignment_map[selected],
                                    )
                                    st.success("Assignment deactivated.")
                                    st.rerun()
                                except OrganizationError as exc:
                                    st.error(str(exc))

                else:
                    st.info(
                        "Active employees and processes are required."
                    )

            if data["assignments"]:

                employee_names = {
                    e.id: e.full_name for e in data["employees"]
                }

                process_names = {
                    p.id: p.name for p in data["processes"]
                }

                st.dataframe(
                    pd.DataFrame([
                        {
                            "ID": a.id,
                            "Employee": employee_names.get(
                                a.employee_id, "Unknown"
                            ),
                            "Process": process_names.get(
                                a.process_id, "Unknown"
                            ),
                            "Start Date": a.start_date,
                            "End Date": a.end_date,
                            "Status": a.assignment_status,
                            "Primary": (
                                "Yes" if a.is_primary else "No"
                            ),
                        }
                        for a in data["assignments"]
                    ]),
                    hide_index=True,
                    width="stretch",
                )

            else:
                st.info("No assignments available.")

    except OrganizationError as exc:
        st.error(str(exc))

    finally:
        db.close()
