import streamlit as st


def render_sidebar():

    with st.sidebar:

        st.markdown(
            """
            # RosterIQ
            ### Workforce Intelligence
            """
        )

        st.divider()

        st.markdown("### Logged In User")

        st.write(st.session_state.get("full_name", "User"))

        st.caption(st.session_state.get("role", "Employee"))

        st.divider()

        selected_page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Employees",
                "Roster Calendar",
                "Approvals",
                "Pods & Processes",
                "Leave & Availability",
                "Reports",
                "AI Assistant",
            ],
        )

        st.divider()

        if st.button("Logout", width="stretch"):

            st.session_state.clear()

            st.rerun()

    return selected_page