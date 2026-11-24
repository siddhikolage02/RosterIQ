
import streamlit as st
import pandas as pd

from src.database.connection import SessionLocal
from src.services.leave_service import (
    create_leave_request,
    get_employee_leave_requests,
    get_all_leave_requests,
    review_leave_request,
    set_employee_availability,
    get_employee_availability,
)


def _format_leave_requests(requests):
    return [
        {
            "Request ID": request.id,
            "Employee": request.employee.full_name,
            "Start Date": request.start_date,
            "End Date": request.end_date,
            "Leave Type": request.leave_type,
            "Status": request.status,
            "Reason": request.reason or "",
        }
        for request in requests
    ]


def _format_availability(records):
    return [
        {
            "Date": record.availability_date,
            "Status": record.status,
            "Reason": record.reason or "",
        }
        for record in records
    ]


def render_leave_availability():
    st.title("Leave & Availability")
    st.caption("Submit leave requests and manage your daily availability.")

    employee_id = st.session_state.get("employee_id")
    role = st.session_state.get("role", "Employee")

    if not employee_id:
        st.error("Your employee session could not be identified. Please log in again.")
        return

    # --------------------------------------------------
    # LEAVE REQUEST FORM
    # --------------------------------------------------
    st.subheader("Submit a Leave Request")

    with st.form("leave_request_form"):
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Leave Start Date",
                key="leave_start_date",
            )

        with col2:
            end_date = st.date_input(
                "Leave End Date",
                key="leave_end_date",
            )

        leave_type = st.selectbox(
            "Leave Type",
            ["Casual Leave", "Sick Leave", "Earned Leave", "Unpaid Leave", "Other"],
        )

        reason = st.text_area(
            "Reason (Optional)",
            placeholder="Enter the reason for your leave",
        )

        submit_leave = st.form_submit_button(
            "Submit Leave Request",
            width="stretch",
        )

    if submit_leave:
        if end_date < start_date:
            st.error("Leave end date cannot be before the start date.")
        else:
            db = SessionLocal()
            try:
                create_leave_request(
                    db=db,
                    employee_id=employee_id,
                    start_date=start_date,
                    end_date=end_date,
                    leave_type=leave_type,
                    reason=reason,
                )
                st.success("Leave request submitted successfully.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not submit leave request: {exc}")
            finally:
                db.close()

    st.divider()

    # --------------------------------------------------
    # AVAILABILITY FORM
    # --------------------------------------------------
    st.subheader("Update Your Availability")

    with st.form("availability_form"):
        availability_date = st.date_input(
            "Availability Date",
            key="availability_date",
        )

        availability_status = st.selectbox(
            "Availability Status",
            ["Available", "Unavailable"],
        )

        availability_reason = st.text_input(
            "Reason (Optional)",
            placeholder="Enter a reason if unavailable",
        )

        save_availability = st.form_submit_button(
            "Save Availability",
            width="stretch",
        )

    if save_availability:
        db = SessionLocal()
        try:
            set_employee_availability(
                db=db,
                employee_id=employee_id,
                availability_date=availability_date,
                status=availability_status,
                reason=availability_reason,
            )
            st.success("Availability updated successfully.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not update availability: {exc}")
        finally:
            db.close()

    st.divider()

    # --------------------------------------------------
    # LEAVE REQUEST HISTORY
    # --------------------------------------------------
    st.subheader("Leave Request History")

    db = SessionLocal()
    try:
        if role == "Manager":
            leave_requests = get_all_leave_requests(db)
        else:
            leave_requests = get_employee_leave_requests(db, employee_id)

        if leave_requests:
            st.dataframe(
                pd.DataFrame(_format_leave_requests(leave_requests)),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No leave requests found.")

        # --------------------------------------------------
        # MANAGER REVIEW
        # --------------------------------------------------
        if role == "Manager":
            st.divider()
            st.subheader("Review Pending Leave Requests")

            pending_requests = [
                request
                for request in leave_requests
                if request.status == "Pending"
            ]

            if not pending_requests:
                st.info("There are no pending leave requests.")
            else:
                request_options = {
                    (
                        f"Request #{request.id} — "
                        f"{request.employee.full_name} — "
                        f"{request.start_date} to {request.end_date}"
                    ): request.id
                    for request in pending_requests
                }

                selected_label = st.selectbox(
                    "Select a leave request",
                    list(request_options.keys()),
                )

                selected_request_id = request_options[selected_label]

                selected_request = next(
                    request
                    for request in pending_requests
                    if request.id == selected_request_id
                )

                st.write(f"**Leave Type:** {selected_request.leave_type}")
                st.write(f"**Reason:** {selected_request.reason or 'Not provided'}")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button(
                        "Approve Request",
                        type="primary",
                        width="stretch",
                    ):
                        review_leave_request(
                            db=db,
                            request_id=selected_request_id,
                            reviewer_id=employee_id,
                            decision="Approved",
                        )
                        st.success("Leave request approved.")
                        st.rerun()

                with col2:
                    if st.button(
                        "Reject Request",
                        width="stretch",
                    ):
                        review_leave_request(
                            db=db,
                            request_id=selected_request_id,
                            reviewer_id=employee_id,
                            decision="Rejected",
                        )
                        st.warning("Leave request rejected.")
                        st.rerun()

        # --------------------------------------------------
        # AVAILABILITY HISTORY
        # --------------------------------------------------
        st.divider()
        st.subheader("Your Availability History")

        availability_records = get_employee_availability(
            db,
            employee_id,
        )

        if availability_records:
            st.dataframe(
                pd.DataFrame(_format_availability(availability_records)),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No availability records found.")

    except Exception as exc:
        st.error(f"Could not load leave and availability data: {exc}")
    finally:
        db.close()
