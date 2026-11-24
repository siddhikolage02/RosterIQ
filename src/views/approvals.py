
import streamlit as st
import pandas as pd

from src.database.connection import SessionLocal
from src.database.models import Employee, RosterRun, RosterApproval
from src.scheduling.validation_service import validate_roster
from src.services.approval_service import (
    submit_roster_for_approval,
    get_pending_approvals,
    approve_roster,
    reject_roster,
    publish_approved_roster,
)


def _employee_name(db, employee_id):
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )
    return employee.full_name if employee else "Unknown employee"


def _roster_label(roster):
    month_name = pd.Timestamp(
        year=roster.year,
        month=roster.month,
        day=1,
    ).strftime("%B")

    return f"{month_name} {roster.year} — Roster #{roster.id}"


def render_approvals():
    st.title("Roster Approvals")
    st.caption("Submit, review and publish workforce rosters.")

    actor_id = st.session_state.get("employee_id")

    if not actor_id:
        st.error("Employee session not found. Please log in again.")
        return

    db = SessionLocal()

    try:
        actor = (
            db.query(Employee)
            .filter(Employee.id == actor_id)
            .first()
        )

        if not actor or actor.employment_status != "Active":
            st.error("An active employee account is required.")
            return

        is_manager = actor.role == "Manager"
        can_submit = actor.role in ("Manager", "Pod Lead")

        # =================================================
        # SUBMIT DRAFT ROSTER
        # =================================================

        st.subheader("Submit a Roster")

        if can_submit:
            draft_rosters = (
                db.query(RosterRun)
                .filter(RosterRun.status == "Draft")
                .order_by(
                    RosterRun.year.desc(),
                    RosterRun.month.desc(),
                )
                .all()
            )

            if draft_rosters:
                roster_options = {
                    _roster_label(roster): roster.id
                    for roster in draft_rosters
                }

                with st.form("submit_roster_approval_form"):
                    selected_label = st.selectbox(
                        "Select Draft Roster",
                        list(roster_options.keys()),
                    )

                    submit_clicked = st.form_submit_button(
                        "Submit for Approval",
                        width="stretch",
                    )

                if submit_clicked:
                    try:
                        result = submit_roster_for_approval(
                            db,
                            roster_options[selected_label],
                            actor_id,
                        )

                        st.success(
                            f"Roster #{result.roster_id} submitted for approval."
                        )
                        st.rerun()

                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))

            else:
                st.info("There are no Draft rosters available to submit.")
        else:
            st.info(
                "Only Managers and Pod Leads can submit rosters for approval."
            )

        st.divider()

        # =================================================
        # PENDING APPROVALS
        # =================================================

        st.subheader("Pending Approval Requests")

        pending_approvals = get_pending_approvals(db)

        if pending_approvals:
            for approval in pending_approvals:
                roster = (
                    db.query(RosterRun)
                    .filter(RosterRun.id == approval.roster_id)
                    .first()
                )

                if not roster:
                    continue

                submitter_name = _employee_name(
                    db,
                    approval.submitted_by_employee_id,
                )

                with st.container(border=True):
                    st.markdown(
                        f"**{_roster_label(roster)}**"
                    )
                    st.write(f"Submitted by: {submitter_name}")
                    st.write(f"Submitted at: {approval.submitted_at}")
                    st.write(f"Status: {approval.status}")

                    try:
                        validation = validate_roster(db, roster.id)

                        col1, col2, col3 = st.columns(3)

                        col1.metric(
                            "Roster Entries",
                            validation.get("total_entries", 0),
                        )
                        col2.metric(
                            "Conflicts",
                            len(validation.get("conflicts", [])),
                        )
                        col3.metric(
                            "Coverage Gaps",
                            len(validation.get("coverage_gaps", [])),
                        )

                        if validation.get("is_valid"):
                            st.success("Roster validation passed.")
                        else:
                            st.warning(
                                "Roster validation currently has issues."
                            )

                        if validation.get("conflicts"):
                            with st.expander("View Conflicts"):
                                for conflict in validation["conflicts"]:
                                    st.write(f"- {conflict}")

                        if validation.get("coverage_gaps"):
                            with st.expander("View Coverage Gaps"):
                                for gap in validation["coverage_gaps"]:
                                    st.write(f"- {gap}")

                    except Exception as exc:
                        st.warning(f"Could not load validation details: {exc}")

                    if is_manager:
                        if approval.submitted_by_employee_id == actor_id:
                            st.warning(
                                "You submitted this roster and cannot review your own submission."
                            )
                        else:
                            approve_col, reject_col = st.columns(2)

                            with approve_col:
                                with st.form(
                                    f"approve_form_{approval.id}"
                                ):
                                    approve_clicked = st.form_submit_button(
                                        "Approve Roster",
                                        type="primary",
                                        width="stretch",
                                    )

                                if approve_clicked:
                                    try:
                                        approve_roster(
                                            db,
                                            approval.id,
                                            actor_id,
                                            comments="Approved by Manager.",
                                        )
                                        st.success("Roster approved.")
                                        st.rerun()
                                    except (ValueError, PermissionError) as exc:
                                        st.error(str(exc))

                            with reject_col:
                                with st.form(
                                    f"reject_form_{approval.id}"
                                ):
                                    rejection_comments = st.text_area(
                                        "Rejection Comments",
                                        key=f"reject_comments_{approval.id}",
                                        placeholder="Explain what needs to be corrected...",
                                    )

                                    reject_clicked = st.form_submit_button(
                                        "Reject Roster",
                                        width="stretch",
                                    )

                                if reject_clicked:
                                    try:
                                        reject_roster(
                                            db,
                                            approval.id,
                                            actor_id,
                                            rejection_comments,
                                        )
                                        st.success(
                                            "Roster rejected and returned to Draft."
                                        )
                                        st.rerun()
                                    except (ValueError, PermissionError) as exc:
                                        st.error(str(exc))
                    else:
                        st.info(
                            "Only Managers can approve or reject roster submissions."
                        )
        else:
            st.info("There are no pending roster approvals.")

        st.divider()

        # =================================================
        # PUBLISH APPROVED ROSTERS
        # =================================================

        st.subheader("Publish Approved Rosters")

        if is_manager:
            approved_rosters = (
                db.query(RosterRun)
                .filter(RosterRun.status == "Approved")
                .order_by(
                    RosterRun.year.desc(),
                    RosterRun.month.desc(),
                )
                .all()
            )

            if approved_rosters:
                approved_options = {
                    _roster_label(roster): roster.id
                    for roster in approved_rosters
                }

                with st.form("publish_roster_form"):
                    selected_approved = st.selectbox(
                        "Select Approved Roster",
                        list(approved_options.keys()),
                    )

                    publish_clicked = st.form_submit_button(
                        "Publish Roster",
                        type="primary",
                        width="stretch",
                    )

                if publish_clicked:
                    try:
                        published = publish_approved_roster(
                            db,
                            approved_options[selected_approved],
                            actor_id,
                        )
                        st.success(
                            f"Roster #{published.id} published successfully."
                        )
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))
            else:
                st.info("There are no approved rosters waiting to be published.")
        else:
            st.info("Only Managers can publish approved rosters.")

        st.divider()

        # =================================================
        # APPROVAL HISTORY
        # =================================================

        st.subheader("Approval History")

        history = (
            db.query(RosterApproval)
            .order_by(RosterApproval.submitted_at.desc())
            .limit(25)
            .all()
        )

        if history:
            history_rows = []

            for record in history:
                roster = (
                    db.query(RosterRun)
                    .filter(RosterRun.id == record.roster_id)
                    .first()
                )

                history_rows.append({
                    "Approval ID": record.id,
                    "Roster ID": record.roster_id,
                    "Period": (
                        _roster_label(roster)
                        if roster else "Roster unavailable"
                    ),
                    "Submitted By": _employee_name(
                        db,
                        record.submitted_by_employee_id,
                    ),
                    "Reviewed By": (
                        _employee_name(db, record.reviewed_by_employee_id)
                        if record.reviewed_by_employee_id
                        else "Not reviewed"
                    ),
                    "Status": record.status,
                    "Submitted At": record.submitted_at,
                    "Reviewed At": record.reviewed_at,
                    "Comments": record.comments or "",
                })

            st.dataframe(
                pd.DataFrame(history_rows),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No approval history is available yet.")

    finally:
        db.close()
