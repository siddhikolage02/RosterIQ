
import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import date

from src.ui.components import page_header, section_title
from src.services.report_service import (
    get_workforce_report,
    get_pod_summary_report,
    get_process_staffing_report,
    get_assignment_report,
    get_leave_report,
    get_roster_report,
    get_roster_entries_report,
    get_approval_report,
)


def _download_csv(dataframe: pd.DataFrame, filename: str, key: str):
    """Display a CSV download button for a report."""
    if dataframe.empty:
        st.caption("No data available to export.")
        return

    csv_data = dataframe.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
        key=key,
        width="content",
    )


def _show_dataframe(dataframe: pd.DataFrame):
    if dataframe.empty:
        st.info("No records found for the selected filters.")
    else:
        st.dataframe(
            dataframe,
            width="stretch",
            hide_index=True,
        )


def _date_range(label: str, key: str):
    """Return a validated start/end date selection."""
    today = date.today()
    first_day = today.replace(day=1)

    selected = st.date_input(
        label,
        value=(first_day, today),
        key=key,
    )

    if isinstance(selected, (tuple, list)) and len(selected) == 2:
        start_date, end_date = selected
        if start_date and end_date:
            return start_date, end_date

    return None, None


def render_reports():

    page_header(
        "Reports & Analytics",
        "Workforce, assignments, leave and roster reporting"
    )

    st.caption(
        "Use the report tabs to explore records, apply filters and export results."
    )

    workforce_tab, assignment_tab, leave_tab, roster_tab, approval_tab = st.tabs(
        [
            "Workforce",
            "Assignments",
            "Leave",
            "Rosters",
            "Approvals",
        ]
    )

    # =====================================================
    # WORKFORCE REPORT
    # =====================================================

    with workforce_tab:

        section_title("Workforce Overview")

        workforce_df = get_workforce_report()

        if workforce_df.empty:
            st.info("No employee records are available.")
        else:
            active_count = (
                workforce_df["Employment Status"] == "Active"
            ).sum()

            inactive_count = len(workforce_df) - active_count
            pod_count = workforce_df["Pod"].nunique()

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Employees", len(workforce_df))
            col2.metric("Active Employees", int(active_count))
            col3.metric("Pods / Groups", int(pod_count))

            st.divider()

            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:
                employment_filter = st.selectbox(
                    "Employment Status",
                    ["All", "Active", "Inactive"],
                    key="report_workforce_status",
                )

            with filter_col2:
                pod_options = ["All"] + sorted(
                    workforce_df["Pod"].dropna().unique().tolist()
                )

                pod_filter = st.selectbox(
                    "Pod",
                    pod_options,
                    key="report_workforce_pod",
                )

            filtered_workforce = workforce_df.copy()

            if employment_filter != "All":
                filtered_workforce = filtered_workforce[
                    filtered_workforce["Employment Status"]
                    == employment_filter
                ]

            if pod_filter != "All":
                filtered_workforce = filtered_workforce[
                    filtered_workforce["Pod"] == pod_filter
                ]

            section_title("Employee Records")
            _show_dataframe(filtered_workforce)

            _download_csv(
                filtered_workforce,
                "rosteriq_workforce_report.csv",
                "download_workforce_report",
            )

            st.divider()

            section_title("Employee Distribution by Pod")

            pod_df = get_pod_summary_report()

            if not pod_df.empty:
                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    fig = px.bar(
                        pod_df,
                        x="Pod",
                        y="Active Employees",
                        text="Active Employees",
                        title="Active Employees by Pod",
                    )
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, width="stretch")

                with chart_col2:
                    fig = px.pie(
                        pod_df,
                        names="Pod",
                        values="Total Employees",
                        hole=0.5,
                        title="Total Workforce Distribution",
                    )
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, width="stretch")

                st.dataframe(
                    pod_df,
                    width="stretch",
                    hide_index=True,
                )

                _download_csv(
                    pod_df,
                    "rosteriq_pod_summary.csv",
                    "download_pod_summary",
                )

            st.divider()

            section_title("Process Staffing")

            staffing_date = st.date_input(
                "Staffing as of date",
                value=date.today(),
                key="report_staffing_date",
            )

            staffing_df = get_process_staffing_report(staffing_date)

            if not staffing_df.empty:
                covered = (
                    staffing_df["Staffing Status"] == "Covered"
                ).sum()

                understaffed = (
                    staffing_df["Staffing Status"] == "Understaffed"
                ).sum()

                col1, col2 = st.columns(2)
                col1.metric("Covered Processes", int(covered))
                col2.metric("Understaffed Processes", int(understaffed))

                fig = px.bar(
                    staffing_df,
                    x="Process",
                    y="Assigned Employees",
                    color="Staffing Status",
                    hover_data=["Brand", "Minimum Staff"],
                    title="Process Staffing vs Assigned Employees",
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, width="stretch")

                _show_dataframe(staffing_df)

                _download_csv(
                    staffing_df,
                    "rosteriq_process_staffing.csv",
                    "download_process_staffing",
                )
            else:
                st.info("No active processes are available.")

    # =====================================================
    # ASSIGNMENT REPORT
    # =====================================================

    with assignment_tab:

        section_title("Employee Assignment Report")

        start_date, end_date = _date_range(
            "Assignment date range",
            "report_assignment_dates",
        )

        assignment_status = st.selectbox(
            "Assignment Status",
            ["All", "Active", "Inactive"],
            key="report_assignment_status",
        )

        assignment_df = get_assignment_report(
            start_date=start_date,
            end_date=end_date,
            assignment_status=assignment_status,
        )

        if not assignment_df.empty:
            col1, col2, col3 = st.columns(3)

            col1.metric("Assignments", len(assignment_df))
            col2.metric(
                "Employees",
                assignment_df["Employee Code"].nunique(),
            )
            col3.metric(
                "Processes",
                assignment_df["Process"].nunique(),
            )

            st.divider()

            status_counts = (
                assignment_df["Assignment Status"]
                .fillna("Unknown")
                .value_counts()
                .reset_index()
            )
            status_counts.columns = ["Status", "Count"]

            fig = px.pie(
                status_counts,
                names="Status",
                values="Count",
                hole=0.5,
                title="Assignment Status Distribution",
            )
            st.plotly_chart(fig, width="stretch")

        _show_dataframe(assignment_df)

        _download_csv(
            assignment_df,
            "rosteriq_assignment_report.csv",
            "download_assignment_report",
        )

    # =====================================================
    # LEAVE REPORT
    # =====================================================

    with leave_tab:

        section_title("Employee Leave Report")

        start_date, end_date = _date_range(
            "Leave date range",
            "report_leave_dates",
        )

        leave_status = st.selectbox(
            "Leave Status",
            ["All", "Pending", "Approved", "Rejected", "Cancelled"],
            key="report_leave_status",
        )

        leave_df = get_leave_report(
            start_date=start_date,
            end_date=end_date,
            leave_status=leave_status,
        )

        if not leave_df.empty:
            col1, col2, col3 = st.columns(3)

            col1.metric("Leave Requests", len(leave_df))
            col2.metric(
                "Pending",
                int((leave_df["Status"] == "Pending").sum()),
            )
            col3.metric(
                "Approved",
                int((leave_df["Status"] == "Approved").sum()),
            )

            st.divider()

            leave_chart = (
                leave_df["Status"]
                .fillna("Unknown")
                .value_counts()
                .reset_index()
            )
            leave_chart.columns = ["Status", "Requests"]

            fig = px.pie(
                leave_chart,
                names="Status",
                values="Requests",
                hole=0.5,
                title="Leave Request Status",
            )
            st.plotly_chart(fig, width="stretch")

        _show_dataframe(leave_df)

        _download_csv(
            leave_df,
            "rosteriq_leave_report.csv",
            "download_leave_report",
        )

    # =====================================================
    # ROSTER REPORT
    # =====================================================

    with roster_tab:

        section_title("Monthly Roster Report")

        all_rosters = get_roster_report()

        if all_rosters.empty:
            st.info("No roster records are available.")
        else:
            year_options = sorted(
                all_rosters["Year"].dropna().astype(int).unique().tolist(),
                reverse=True,
            )

            month_options = ["All"] + list(range(1, 13))

            filter_col1, filter_col2, filter_col3 = st.columns(3)

            with filter_col1:
                selected_year = st.selectbox(
                    "Year",
                    ["All"] + year_options,
                    key="report_roster_year",
                )

            with filter_col2:
                selected_month = st.selectbox(
                    "Month",
                    month_options,
                    format_func=lambda value: (
                        "All Months" if value == "All"
                        else date(2000, value, 1).strftime("%B")
                    ),
                    key="report_roster_month",
                )

            with filter_col3:
                selected_roster_status = st.selectbox(
                    "Roster Status",
                    [
                        "All",
                        "Draft",
                        "Pending Approval",
                        "Approved",
                        "Published",
                        "Archived",
                    ],
                    key="report_roster_status",
                )

            roster_df = get_roster_report(
                year=None if selected_year == "All" else selected_year,
                month=None if selected_month == "All" else selected_month,
                roster_status=selected_roster_status,
            )

            if not roster_df.empty:
                col1, col2 = st.columns(2)

                col1.metric("Rosters", len(roster_df))
                col2.metric(
                    "Total Roster Entries",
                    int(roster_df["Roster Entries"].sum()),
                )

                st.divider()

                roster_status_counts = (
                    roster_df["Roster Status"]
                    .fillna("Unknown")
                    .value_counts()
                    .reset_index()
                )
                roster_status_counts.columns = ["Status", "Count"]

                fig = px.pie(
                    roster_status_counts,
                    names="Status",
                    values="Count",
                    hole=0.5,
                    title="Roster Status Distribution",
                )
                st.plotly_chart(fig, width="stretch")

            section_title("Roster Records")
            _show_dataframe(roster_df)

            _download_csv(
                roster_df,
                "rosteriq_roster_report.csv",
                "download_roster_report",
            )

            st.divider()

            section_title("Roster Entry Details")

            roster_ids = sorted(
                all_rosters["Roster ID"].dropna().astype(int).tolist(),
                reverse=True,
            )

            selected_roster_id = st.selectbox(
                "Select Roster ID",
                roster_ids,
                key="report_roster_entry_id",
            )

            entries_df = get_roster_entries_report(
                roster_id=selected_roster_id
            )

            _show_dataframe(entries_df)

            _download_csv(
                entries_df,
                f"rosteriq_roster_{selected_roster_id}_entries.csv",
                "download_roster_entries",
            )

    # =====================================================
    # APPROVAL REPORT
    # =====================================================

    with approval_tab:

        section_title("Roster Approval History")

        start_date, end_date = _date_range(
            "Approval submission date range",
            "report_approval_dates",
        )

        approval_status = st.selectbox(
            "Approval Status",
            ["All", "Pending", "Approved", "Rejected"],
            key="report_approval_status",
        )

        approval_df = get_approval_report(
            start_date=start_date,
            end_date=end_date,
            approval_status=approval_status,
        )

        if not approval_df.empty:
            col1, col2, col3 = st.columns(3)

            col1.metric("Approval Requests", len(approval_df))
            col2.metric(
                "Approved",
                int((approval_df["Approval Status"] == "Approved").sum()),
            )
            col3.metric(
                "Pending",
                int((approval_df["Approval Status"] == "Pending").sum()),
            )

            st.divider()

            approval_counts = (
                approval_df["Approval Status"]
                .fillna("Unknown")
                .value_counts()
                .reset_index()
            )
            approval_counts.columns = ["Status", "Count"]

            fig = px.bar(
                approval_counts,
                x="Status",
                y="Count",
                text="Count",
                title="Roster Approval Summary",
            )
            st.plotly_chart(fig, width="stretch")

        _show_dataframe(approval_df)

        _download_csv(
            approval_df,
            "rosteriq_approval_report.csv",
            "download_approval_report",
        )
