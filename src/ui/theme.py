import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        /* Main application */
        .stApp {
            background-color: #F5F7FB;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #10243E;
        }

        [data-testid="stSidebar"] * {
            color: #FFFFFF;
        }

        /* Main headings */
        h1, h2, h3 {
            color: #10243E;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #E5EAF1;
            padding: 18px;
            border-radius: 12px;
        }

        /* Buttons */
        .stButton button {
            border-radius: 8px;
            font-weight: 600;
        }

        /* Login card */
        .login-card {
            background-color: white;
            padding: 30px;
            border-radius: 16px;
            border: 1px solid #E5EAF1;
        }

        /* Input fields */
        input, textarea {
            border-radius: 8px !important;
        }

        /* Dataframes */
        [data-testid="stDataFrame"] {
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )