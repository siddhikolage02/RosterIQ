
import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import date, timedelta
from sqlalchemy import text, inspect

from src.database.connection import engine, SessionLocal
from src.database.models import RosterRun
from src.ui.components import page_header, section_title
from src.scheduling.validation_service import validate_roster


# =========================================================
# DATABASE HELPERS
# =========================================================

def get_table_count(table_name):

    inspector = inspect(engine)

    if table_name not in inspector.get_table_names():
        return 0

    with engine.connect() as connection:

        result = connection.execute(
            text(f'SELECT COUNT(*) FROM "{table_name}"')
        )

        return result.scalar() or 0


def get_active_employee_count():

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM employees
                WHERE employment_status = 'Active'
                """
            )
        )

        return result.scalar() or 0


def get_roster_data():

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT id, month, year, status
                FROM roster_runs
                ORDER BY year DESC, month DESC, id DESC
                """
            )
        )

        rows = result.fetchall()

    return pd.DataFrame(
        rows,
        columns=["Roster ID", "Month", "Year", "Status"]
    )


# =========================================================
# EMPLOYEE DISTRIBUTION BY POD
# =========================================================

def get_pod_distribution():

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    COALESCE(p.name, 'Unassigned') AS pod_name,
                    COUNT(e.id) AS employee_count
                FROM employees e
                LEFT JOIN pods p ON e.pod_id = p.id
                WHERE e.employment_status = 'Active'
                GROUP BY COALESCE(p.name, 'Unassigned')
                ORDER BY employee_count DESC
                """
            )
        )

        rows = result.fetchall()

    return pd.DataFrame(
        rows,
        columns=["Pod", "Employees"]
    )


# =========================================================
# PROCESS STAFFING DISTRIBUTION
# =========================================================

def get_process_staffing():

    today = date.today()

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    p.name AS process_name,
                    b.name AS brand_name,
                    COUNT(DISTINCT a.employee_id) AS employee_count
                FROM assignments a
                JOIN processes p ON a.process_id = p.id
                JOIN brands b ON p.brand_id = b.id
                JOIN employees e ON a.employee_id = e.id
                WHERE
                    a.assignment_status = 'Active'
                    AND e.employment_status = 'Active'
                    AND a.start_date <= :today
                    AND (a.end_date IS NULL OR a.end_date >= :today)
                GROUP BY p.id, p.name, b.name
                ORDER BY employee_count DESC
                """
            ),
            {"today": today}
        )

        rows = result.fetchall()

    return pd.DataFrame(
        rows,
        columns=["Process", "Brand", "Employees"]
    )


# =========================================================
# PENDING APPROVALS
# =========================================================

def get_pending_approval_count():

    inspector = inspect(engine)

    if "roster_approvals" not in inspector.get_table_names():
        return 0

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM roster_approvals
                WHERE status = 'Pending'
                """
            )
        )

        return result.scalar() or 0


def get_pending_approvals_data():

    inspector = inspect(engine)

    if "roster_approvals" not in inspector.get_table_names():
        return pd.DataFrame()

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    ra.id AS "Approval ID",
                    ra.roster_id AS "Roster ID",
                    ra.status AS "Status",
                    ra.submitted_at AS "Submitted At",
                    e.full_name AS "Submitted By"
                FROM roster_approvals ra
                LEFT JOIN employees e
                    ON ra.submitted_by_employee_id = e.id
                WHERE ra.status = 'Pending'
                ORDER BY ra.submitted_at DESC
                """
            )
        )

        rows = result.fetchall()
        columns = result.keys()

    return pd.DataFrame(rows, columns=columns)


# =========================================================
# ROSTER HEALTH
# =========================================================

def get_latest_roster_health():

    db = None

    try:

        db = SessionLocal()

        latest_roster = (
            db.query(RosterRun)
            .order_by(
                RosterRun.year.desc(),
                RosterRun.month.desc(),
                RosterRun.id.desc()
            )
            .first()
        )

        if not latest_roster:

            return {
                "roster_id": None,
                "status": "No roster",
                "entries": 0,
                "conflicts": 0,
                "coverage_gaps": 0,
                "valid": False,
            }

        result = validate_roster(db, latest_roster.id)

        return {
            "roster_id": latest_roster.id,
            "status": latest_roster.status,
            "entries": result.get("total_entries", 0),
            "conflicts": result.get("conflict_count", 0),
            "coverage_gaps": result.get("coverage_gap_count", 0),
            "valid": result.get("is_valid", False),
        }

    except Exception as exc:

        return {
            "roster_id": None,
            "status": "Check required",
            "entries": 0,
            "conflicts": 0,
            "coverage_gaps": 0,
            "valid": False,
            "error": str(exc),
        }

    finally:

        if db:
            db.close()


# =========================================================
# UPCOMING LEAVE
# =========================================================

def get_upcoming_leave():

    today = date.today()
    next_30_days = today + timedelta(days=30)

    inspector = inspect(engine)

    if "leave_requests" not in inspector.get_table_names():
        return pd.DataFrame()

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    e.full_name AS "Employee",
                    e.employee_code AS "Employee Code",
                    l.leave_type AS "Leave Type",
                    l.start_date AS "Start Date",
                    l.end_date AS "End Date",
                    l.status AS "Status"
                FROM leave_requests l
                JOIN employees e ON l.employee_id = e.id
                WHERE
                    l.status = 'Approved'
                    AND l.end_date >= :today
                    AND l.start_date <= :next_30_days
                ORDER BY l.start_date ASC
                """
            ),
            {
                "today": today,
                "next_30_days": next_30_days,
            }
        )

        rows = result.fetchall()
        columns = result.keys()

    return pd.DataFrame(rows, columns=columns)


# =========================================================
# RECENT ROSTER ACTIVITY
# =========================================================

def get_recent_activity(limit=10):

    inspector = inspect(engine)

    if "roster_change_logs" not in inspector.get_table_names():
        return pd.DataFrame()

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    l.action AS "Action",
                    e.full_name AS "Changed By",
                    l.roster_id AS "Roster ID",
                    l.comments AS "Comments",
                    l.changed_at AS "Changed At"
                FROM roster_change_logs l
                LEFT JOIN employees e
                    ON l.changed_by_employee_id = e.id
                ORDER BY l.changed_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit}
        )

        rows = result.fetchall()
        columns = result.keys()

    return pd.DataFrame(rows, columns=columns)


# =========================================================
# DASHBOARD
# =========================================================

def render_dashboard():

    page_header(
        "Dashboard",
        "Workforce overview and scheduling intelligence"
    )

    # -----------------------------------------------------
    # KPI METRICS
    # -----------------------------------------------------

    employee_count = get_active_employee_count()
    pod_count = get_table_count("pods")
    process_count = get_table_count("processes")
    roster_count = get_table_count("roster_runs")
    assignment_count = get_table_count("assignments")
    pending_count = get_pending_approval_count()

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Active Employees", employee_count)
    col2.metric("Pods", pod_count)
    col3.metric("Processes", process_count)
    col4.metric("Rosters", roster_count)
    col5.metric("Assignments", assignment_count)
    col6.metric("Pending Approvals", pending_count)

    st.divider()

    # -----------------------------------------------------
    # ROSTER STATUS + ROSTER HEALTH
    # -----------------------------------------------------

    roster_df = get_roster_data()

    left, right = st.columns([1.2, 1])

    with left:

        section_title("Roster Status Overview")

        if not roster_df.empty:

            status_counts = (
                roster_df["Status"]
                .fillna("Unknown")
                .value_counts()
                .reset_index()
            )

            status_counts.columns = ["Status", "Count"]

            fig = px.pie(
                status_counts,
                names="Status",
                values="Count",
                hole=0.55,
            )

            fig.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=30, b=10),
                legend_title="Roster Status",
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

        else:

            st.info("No rosters available yet.")

    with right:

        section_title("Latest Roster Health")

        health = get_latest_roster_health()

        if health["roster_id"]:

            st.markdown(
                f"**Roster ID:** {health['roster_id']}"
            )

            st.markdown(
                f"**Status:** {health['status']}"
            )

            st.metric(
                "Roster Entries",
                health["entries"]
            )

            h1, h2 = st.columns(2)

            h1.metric(
                "Conflicts",
                health["conflicts"]
            )

            h2.metric(
                "Coverage Gaps",
                health["coverage_gaps"]
            )

            if health["valid"]:

                st.success("Roster validation passed.")

            else:

                st.warning("Roster needs attention.")

        else:

            st.info("No roster available for validation.")

            if health.get("error"):

                st.caption(health["error"])

    st.divider()

    # -----------------------------------------------------
    # EMPLOYEE DISTRIBUTION BY POD
    # -----------------------------------------------------

    section_title("Workforce Distribution by Pod")

    pod_df = get_pod_distribution()

    if not pod_df.empty:

        col1, col2 = st.columns([1.2, 1])

        with col1:

            fig = px.bar(
                pod_df,
                x="Pod",
                y="Employees",
                color="Pod",
                text="Employees",
            )

            fig.update_layout(
                height=350,
                showlegend=False,
                margin=dict(l=10, r=10, t=30, b=10),
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

        with col2:

            st.dataframe(
                pod_df,
                width="stretch",
                hide_index=True,
            )

    else:

        st.info("No workforce distribution data available.")

    st.divider()

    # -----------------------------------------------------
    # PROCESS STAFFING
    # -----------------------------------------------------

    section_title("Process Staffing Distribution")

    staffing_df = get_process_staffing()

    if not staffing_df.empty:

        fig = px.bar(
            staffing_df,
            x="Process",
            y="Employees",
            color="Brand",
            text="Employees",
        )

        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=30, b=10),
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

        st.dataframe(
            staffing_df,
            width="stretch",
            hide_index=True,
        )

    else:

        st.info("No active process staffing data available.")

    st.divider()

    # -----------------------------------------------------
    # PENDING APPROVALS
    # -----------------------------------------------------

    section_title("Pending Roster Approvals")

    approvals_df = get_pending_approvals_data()

    if not approvals_df.empty:

        st.dataframe(
            approvals_df,
            width="stretch",
            hide_index=True,
        )

    else:

        st.success("No pending roster approvals.")

    st.divider()

    # -----------------------------------------------------
    # UPCOMING LEAVE
    # -----------------------------------------------------

    section_title("Upcoming Approved Leave — Next 30 Days")

    leave_df = get_upcoming_leave()

    if not leave_df.empty:

        st.dataframe(
            leave_df,
            width="stretch",
            hide_index=True,
        )

    else:

        st.info("No upcoming approved leave.")

    st.divider()

    # -----------------------------------------------------
    # RECENT ROSTERS
    # -----------------------------------------------------

    section_title("Recent Rosters")

    if not roster_df.empty:

        recent = roster_df.head(10).copy()

        st.dataframe(
            recent,
            width="stretch",
            hide_index=True,
        )

    else:

        st.info("No roster records found.")

    st.divider()

    # -----------------------------------------------------
    # RECENT ACTIVITY
    # -----------------------------------------------------

    section_title("Recent Roster Activity")

    activity_df = get_recent_activity()

    if not activity_df.empty:

        st.dataframe(
            activity_df,
            width="stretch",
            hide_index=True,
        )

    else:

        st.info("No roster activity recorded yet.")

    st.divider()

    # -----------------------------------------------------
    # SYSTEM OVERVIEW
    # -----------------------------------------------------

    section_title("System Overview")

    overview_col1, overview_col2 = st.columns(2)

    with overview_col1:

        st.markdown(
            """
            **RosterIQ Modules**

            - Workforce management
            - Employee assignments
            - Leave and availability
            - Monthly roster generation
            - Roster validation
            - Approval workflow
            - Audit history
            """
        )

    with overview_col2:

        st.markdown(
            """
            **Scheduling Controls**

            - Employee eligibility
            - Process assignments
            - Operating calendars
            - Staffing coverage
            - Conflict detection
            - Backup recommendations
            - Controlled publishing
            """
        )
