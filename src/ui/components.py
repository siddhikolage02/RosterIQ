import streamlit as st
def page_header(title, subtitle=None):
    st.title(title)
    if subtitle:
        st.markdown(
            f'<p class="rosteriq-subtitle">{subtitle}</p>',
            unsafe_allow_html=True,
        )
def metric_card(label, value, help_text=None):
    st.metric(
        label=label,
        value=value,
        help=help_text,
    )
def section_title(title):
    st.subheader(title)
