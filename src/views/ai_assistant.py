import streamlit as st

from src.database.connection import SessionLocal
from src.services.ai_assistant_service import (
    build_ai_context,
    ask_bedrock,
)


def render_ai_assistant():

    st.title("AI Assistant")
    st.caption(
        "Ask questions about workforce data, assignments, "
        "leave and roster operations."
    )

    st.info(
        "The assistant is read-only. It can explain information "
        "but cannot modify application records."
    )

    # -------------------------------------------------
    # CHAT HISTORY
    # -------------------------------------------------

    if "ai_chat_history" not in st.session_state:
        st.session_state["ai_chat_history"] = []

    history = st.session_state["ai_chat_history"]

    # -------------------------------------------------
    # SUGGESTED QUESTIONS
    # -------------------------------------------------

    with st.expander("Example questions", expanded=not history):

        st.markdown(
            """
            **Workforce**
            - How many active employees are there?
            - Give me a summary of workforce information.

            **Scheduling**
            - Which processes have staffing gaps?
            - Explain the current roster information.

            **Leave**
            - How many leave requests are pending?
            - Show me the status of my leave requests.
            """
        )

    # -------------------------------------------------
    # DISPLAY EXISTING MESSAGES
    # -------------------------------------------------

    for message in history:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # -------------------------------------------------
    # USER INPUT
    # -------------------------------------------------

    question = st.chat_input(
        "Ask RosterIQ Assistant..."
    )

    if question:

        question = question.strip()

        if not question:
            return

        history.append({
            "role": "user",
            "content": question,
        })

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner("Analyzing RosterIQ data..."):

                db = SessionLocal()

                try:

                    actor_id = st.session_state.get("employee_id")

                    if not actor_id:
                        raise ValueError(
                            "Your login session has expired. Please log in again."
                        )

                    context = build_ai_context(
                        db,
                        actor_id,
                    )

                    # Exclude the current question from previous history.
                    previous_history = history[:-1]

                    answer = ask_bedrock(
                        question=question,
                        context=context,
                        history=previous_history,
                    )

                    st.markdown(answer)

                    history.append({
                        "role": "assistant",
                        "content": answer,
                    })

                except Exception as exc:

                    error_message = str(exc)

                    st.error(error_message)

                    history.append({
                        "role": "assistant",
                        "content": (
                            f"I couldn't complete that request. "
                            f"{error_message}"
                        ),
                    })

                finally:
                    db.close()

        st.rerun()

    # -------------------------------------------------
    # CHAT CONTROLS
    # -------------------------------------------------

    if history:

        if st.button(
            "Clear conversation",
            key="clear_ai_conversation",
        ):
            st.session_state["ai_chat_history"] = []
            st.rerun()