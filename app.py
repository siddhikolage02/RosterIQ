
import streamlit as st

from src.ui.theme import apply_theme
from src.views.layout import render_sidebar
from src.views.dashboard import render_dashboard
from src.views.employees import render_employees
from src.views.roster_calendar import render_roster_calendar

from src.database.connection import SessionLocal
from src.auth.auth_service import authenticate_user

from src.views.leave_availability import render_leave_availability

from src.views.approvals import render_approvals

from src.views.pods_processes import render_pods_processes

from src.views.reports import render_reports

from src.views.ai_assistant import render_ai_assistant


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="RosterIQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()


# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------

def render_login():

    st.markdown("<br><br>", unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.5, 1])

    with center:

        st.markdown(
            """
            <div style="text-align:center;">
                <h1>RosterIQ</h1>
                <p>Workforce Intelligence & Scheduling</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        st.subheader("Login to your account")

        with st.form("login_form"):

            email = st.text_input(
                "Email Address",
                placeholder="Enter your registered email",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            login_button = st.form_submit_button(
                "Login",
                width="stretch",
            )

        if login_button:

            if not email.strip() or not password:

                st.error("Please enter both email and password.")

            else:

                db = SessionLocal()

                try:

                    employee = authenticate_user(
                        db,
                        email.strip(),
                        password,
                    )

                    if employee:

                        st.session_state["authenticated"] = True
                        st.session_state["employee_id"] = employee.id
                        st.session_state["full_name"] = employee.full_name
                        st.session_state["email"] = employee.email
                        st.session_state["role"] = employee.role

                        st.success("Login successful!")

                        st.rerun()

                    else:

                        st.error("Invalid email or password.")

                finally:

                    db.close()


# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------

def main():

    if not st.session_state.get("authenticated", False):

        render_login()

        return

    selected_page = render_sidebar()

    # ----------------------------------------------
    # DASHBOARD
    # ----------------------------------------------

    if selected_page == "Dashboard":

        render_dashboard()

    # ----------------------------------------------
    # EMPLOYEE MANAGEMENT
    # ----------------------------------------------

    elif selected_page == "Employees":

        render_employees()

    elif selected_page == "Roster Calendar":

        render_roster_calendar()

    elif selected_page == "Leave & Availability":
        render_leave_availability()

    elif selected_page == "Approvals":
        render_approvals()

    elif selected_page == "Pods & Processes":
        render_pods_processes()
    
    elif selected_page == "Reports":
        render_reports()

    elif selected_page == "AI Assistant":
        render_ai_assistant()

    # ----------------------------------------------
    # OTHER MODULES
    # ----------------------------------------------

    else:

        st.title(selected_page)

        st.info(
            f"{selected_page} module will be implemented "
            "in the upcoming development phases."
        )


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    main()
