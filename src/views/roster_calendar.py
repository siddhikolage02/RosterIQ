import calendar
from datetime import date

import pandas as pd
import streamlit as st

from src.database.connection import SessionLocal
from src.database.models import Employee, Process, RosterEntry, RosterRun, Assignment
from src.services.roster_service import create_roster, get_all_rosters, get_roster_entries
from src.scheduling.roster_edit_service import (
    add_manual_roster_entry,
    update_manual_roster_entry,
    cancel_manual_roster_entry,
)
from src.scheduling.validation_service import validate_roster
from src.scheduling.eligibility_service import check_employee_eligibility


def _actor():
    employee_id = st.session_state.get("employee_id")
    role = st.session_state.get("role", "Employee")
    if not employee_id:
        st.error("Your session has expired. Please log in again.")
        st.stop()
    if role not in ("Manager", "Pod Lead"):
        st.error("Only Managers and Pod Leads can access roster management.")
        st.stop()
    return employee_id, role


def _month_label(month, year):
    return date(year, month, 1).strftime("%B %Y")


def _get_scoped_options(db, actor_id, role, roster_id, work_date=None):
    actor = db.query(Employee).filter(Employee.id == actor_id).first()
    if not actor or actor.employment_status != "Active":
        raise PermissionError("Your employee account is not active.")

    employees_query = db.query(Employee).filter(Employee.employment_status == "Active")
    processes_query = db.query(Process).filter(Process.is_active.is_(True))

    if role == "Pod Lead":
        if not actor.pod_id:
            raise PermissionError("Your account is not assigned to a pod.")
        employees_query = employees_query.filter(Employee.pod_id == actor.pod_id)
        processes_query = processes_query.join(Assignment).join(Employee).filter(
            Employee.pod_id == actor.pod_id,
            Assignment.assignment_status == "Active",
        ).distinct()

    employees = employees_query.order_by(Employee.full_name).all()
    processes = processes_query.order_by(Process.name).all()

    # Pod Leads can only see roster entries belonging to their own pod.
    entries_query = db.query(RosterEntry).filter(RosterEntry.roster_id == roster_id)
    if role == "Pod Lead":
        entries_query = entries_query.join(Employee, RosterEntry.employee_id == Employee.id).filter(
            Employee.pod_id == actor.pod_id
        )
    entries = entries_query.order_by(RosterEntry.roster_date, RosterEntry.process_id).all()
    return actor, employees, processes, entries


def _render_calendar(roster, entries):
    st.subheader("Monthly roster calendar")
    month_matrix = calendar.monthcalendar(roster.year, roster.month)
    entries_by_day = {}
    for entry in entries:
        if entry.status != "Cancelled":
            entries_by_day.setdefault(entry.roster_date.day, []).append(entry)

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    header = st.columns(7)
    for col, day_name in zip(header, weekdays):
        col.markdown(f"**{day_name[:3]}**")

    for week in month_matrix:
        cells = st.columns(7)
        for col, day_number in zip(cells, week):
            with col:
                if day_number == 0:
                    st.markdown(" ")
                    continue
                day_entries = entries_by_day.get(day_number, [])
                st.markdown(f"**{day_number}**")
                if not day_entries:
                    st.caption("No assignments")
                else:
                    for entry in day_entries:
                        st.caption(f"{entry.employee.full_name} · {entry.process.name}")


def render_roster_calendar():
    st.title("Roster Calendar")
    st.caption("Create, review and manage monthly employee assignments.")
    actor_id, role = _actor()

    db = SessionLocal()
    try:
        today = date.today()
        st.subheader("Monthly roster")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            selected_month = st.selectbox(
                "Month", list(range(1, 13)), index=today.month - 1,
                format_func=lambda value: calendar.month_name[value],
            )
        with col2:
            selected_year = st.number_input("Year", min_value=2026, max_value=2100, value=max(2026, today.year), step=1)
        with col3:
            st.write("")
            st.write("")
            if role == "Manager":
                if st.button("＋ Create monthly roster", type="primary", use_container_width=True):
                    existing = db.query(RosterRun).filter(
                        RosterRun.month == selected_month,
                        RosterRun.year == int(selected_year),
                    ).first()
                    if existing:
                        st.warning(f"A roster already exists for {_month_label(selected_month, int(selected_year))} (Roster #{existing.id}).")
                    else:
                        try:
                            new_roster = create_roster(db, int(selected_month), int(selected_year))
                            st.success(f"Created roster #{new_roster.id} for {_month_label(selected_month, int(selected_year))}.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

        rosters = get_all_rosters(db)
        if role == "Pod Lead":
            # Pod Leads may work with the roster for the selected month, but their entries are scoped below.
            pass
        if not rosters:
            st.info("No monthly rosters have been created yet. A Manager can create the first roster above.")
            return

        roster_options = {
            f"{_month_label(r.month, r.year)} · {r.status} · #{r.id}": r.id
            for r in rosters
        }
        matching = next((label for label, rid in roster_options.items() if rid == next((r.id for r in rosters if r.month == selected_month and r.year == int(selected_year)), -1)), None)
        selected_label = st.selectbox(
            "Select roster", list(roster_options.keys()),
            index=list(roster_options.keys()).index(matching) if matching else 0,
        )
        roster_id = roster_options[selected_label]
        roster = db.query(RosterRun).filter(RosterRun.id == roster_id).first()

        actor, employees, processes, scoped_entries = _get_scoped_options(db, actor_id, role, roster_id)
        all_entries = get_roster_entries(db, roster_id)
        visible_entries = scoped_entries

        total = len([e for e in visible_entries if e.status != "Cancelled"])
        metrics = st.columns(4)
        metrics[0].metric("Roster status", roster.status)
        metrics[1].metric("Visible assignments", total)
        metrics[2].metric("Employees", len({e.employee_id for e in visible_entries if e.status != "Cancelled"}))
        metrics[3].metric("Processes", len({e.process_id for e in visible_entries if e.status != "Cancelled"}))

        tab_calendar, tab_entries, tab_manage, tab_validation = st.tabs(
            ["Calendar", "Assignment list", "Manage assignments", "Validation"]
        )
        with tab_calendar:
            _render_calendar(roster, visible_entries)

        with tab_entries:
            rows = [
                {
                    "Date": entry.roster_date,
                    "Employee": entry.employee.full_name,
                    "Employee Code": entry.employee.employee_code,
                    "Pod": entry.employee.pod.name if entry.employee.pod else "Unassigned",
                    "Process": entry.process.name,
                    "Brand": entry.process.brand.name if entry.process.brand else "—",
                    "Status": entry.status,
                }
                for entry in visible_entries
            ]
            if rows:
                frame = pd.DataFrame(rows).sort_values(["Date", "Process", "Employee"])
                st.dataframe(frame, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download roster CSV", frame.to_csv(index=False).encode("utf-8"),
                    file_name=f"roster_{roster.year}_{roster.month:02d}.csv", mime="text/csv",
                )
            else:
                st.info("There are no visible assignments in this roster.")

        with tab_manage:
            if roster.status != "Draft":
                st.info("Only Draft rosters can be modified. Submit this roster through the approval workflow when it is ready.")
            elif not employees or not processes:
                st.warning("No eligible employees or active processes are available in your access scope.")
            else:
                st.markdown("#### Add assignment")
                with st.form(f"add_roster_entry_{roster.id}"):
                    add_cols = st.columns(3)
                    with add_cols[0]:
                        add_employee = st.selectbox("Employee", employees, format_func=lambda e: f"{e.full_name} ({e.employee_code})", key=f"add_emp_{roster.id}")
                    with add_cols[1]:
                        add_process = st.selectbox("Process", processes, format_func=lambda p: f"{p.brand.name} · {p.name}", key=f"add_proc_{roster.id}")
                    with add_cols[2]:
                        add_date = st.date_input("Assignment date", value=date(roster.year, roster.month, 1), min_value=date(roster.year, roster.month, 1), max_value=date(roster.year, roster.month, calendar.monthrange(roster.year, roster.month)[1]), key=f"add_date_{roster.id}")
                    add_submitted = st.form_submit_button("Add assignment", type="primary", use_container_width=True)
                if add_submitted:
                    try:
                        add_manual_roster_entry(db, roster.id, add_employee.id, add_process.id, add_date, actor_id)
                        st.success("Assignment added and audit history recorded.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

                st.divider()
                st.markdown("#### Edit or cancel assignment")
                editable_entries = [e for e in visible_entries if e.status != "Cancelled"]
                if editable_entries:
                    entry_labels = {
                        f"{e.roster_date} · {e.employee.full_name} · {e.process.name} · Entry #{e.id}": e
                        for e in editable_entries
                    }
                    selected_entry_label = st.selectbox("Select assignment", list(entry_labels.keys()), key=f"entry_select_{roster.id}")
                    selected_entry = entry_labels[selected_entry_label]
                    edit_cols = st.columns(3)
                    with edit_cols[0]:
                        current_employee_index = next((i for i, e in enumerate(employees) if e.id == selected_entry.employee_id), 0)
                        edit_employee = st.selectbox("Reassign employee", employees, index=current_employee_index, format_func=lambda e: f"{e.full_name} ({e.employee_code})", key=f"edit_emp_{selected_entry.id}")
                    with edit_cols[1]:
                        current_process_index = next((i for i, p in enumerate(processes) if p.id == selected_entry.process_id), 0)
                        edit_process = st.selectbox("Change process", processes, index=current_process_index, format_func=lambda p: f"{p.brand.name} · {p.name}", key=f"edit_proc_{selected_entry.id}")
                    with edit_cols[2]:
                        edit_date = st.date_input("Change date", value=selected_entry.roster_date, min_value=date(roster.year, roster.month, 1), max_value=date(roster.year, roster.month, calendar.monthrange(roster.year, roster.month)[1]), key=f"edit_date_{selected_entry.id}")
                    edit_col, cancel_col = st.columns(2)
                    with edit_col:
                        if st.button("Save assignment changes", key=f"save_entry_{selected_entry.id}", use_container_width=True):
                            try:
                                update_manual_roster_entry(
                                    db, selected_entry.id, actor_id,
                                    new_employee_id=edit_employee.id,
                                    new_process_id=edit_process.id,
                                    new_roster_date=edit_date,
                                )
                                st.success("Assignment updated and audit history recorded.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
                    with cancel_col:
                        if st.button("Cancel assignment", key=f"cancel_entry_{selected_entry.id}", use_container_width=True):
                            try:
                                cancel_manual_roster_entry(db, selected_entry.id, actor_id)
                                st.success("Assignment cancelled and audit history recorded.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
                else:
                    st.info("There are no active assignments to edit or cancel.")

        with tab_validation:
            if st.button("Run roster validation", key=f"validate_{roster.id}"):
                result = validate_roster(db, roster.id)
                st.session_state[f"roster_validation_{roster.id}"] = result
            result = st.session_state.get(f"roster_validation_{roster.id}")
            if result:
                validation_cols = st.columns(3)
                validation_cols[0].metric("Scheduled entries", result["total_entries"])
                validation_cols[1].metric("Eligibility conflicts", result["conflict_count"])
                validation_cols[2].metric("Coverage gaps", result["coverage_gap_count"])
                if result["is_valid"]:
                    st.success("Roster validation passed. No eligibility conflicts or coverage gaps were found.")
                else:
                    st.error("Roster validation found issues. Resolve them before submitting for approval.")
                    if result["conflicts"]:
                        st.markdown("**Eligibility conflicts**")
                        st.dataframe(pd.DataFrame(result["conflicts"]), use_container_width=True, hide_index=True)
                    if result["coverage_gaps"]:
                        st.markdown("**Coverage gaps**")
                        st.dataframe(pd.DataFrame(result["coverage_gaps"]), use_container_width=True, hide_index=True)
            else:
                st.caption("Run validation to check eligibility, leave, availability, weekly offs, operating days and minimum process staffing.")

    except PermissionError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Roster Calendar could not be loaded: {exc}")
    finally:
        db.close()
