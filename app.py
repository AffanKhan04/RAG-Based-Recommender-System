import os
from pathlib import Path

from dotenv import load_dotenv

_project_dir = Path(__file__).resolve().parent
load_dotenv(_project_dir / ".env")
load_dotenv()

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from auth.supabase_auth import (
    get_current_user_id,
    issue_session_after_sign_in,
    sign_in,
    sign_out,
    sign_up,
)
from agent.graph import create_recommender_agent, invoke_recommender_with_memory
from memory.user_memory import delete_all_chat_history, load_history

_DEFAULT_MODEL = "qwen2.5:3b"


def _populate_messages_from_database(user_id: str) -> None:
    """Load recent chat turns from Supabase into session display state."""
    st.session_state.messages = []
    try:
        for msg in load_history(user_id, limit=100):
            if isinstance(msg, HumanMessage):
                st.session_state.messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                st.session_state.messages.append(
                    {"role": "assistant", "content": msg.content}
                )
    except RuntimeError as re:
        st.session_state.messages = []
        st.warning(f"Could not load chat history: {re}")


st.set_page_config(page_title="Electronics Recommender", layout="centered")


def _ensure_session_defaults() -> None:
    """Initialize mutable session defaults when missing."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    # Radio mode is stored under this key (avoids st.toggle + value/rerun glitches).
    if "auth_mode_select" not in st.session_state:
        st.session_state.auth_mode_select = "Sign in"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "auth_error" not in st.session_state:
        st.session_state.auth_error = None


def _render_auth_screen() -> None:
    """Login / Sign up form before chat is available."""
    st.title("Electronics Recommender")
    st.caption(
        "Sign in to keep your preferences and conversations across sessions (Supabase)."
    )

    if st.session_state.auth_error:
        st.error(st.session_state.auth_error)
        st.session_state.auth_error = None

    st.markdown("**Choose mode**")
    st.radio(
        "Authentication mode",
        ["Sign in", "Create account"],
        horizontal=True,
        key="auth_mode_select",
        label_visibility="collapsed",
    )
    mode_signup = st.session_state.auth_mode_select == "Create account"

    with st.form("auth_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(
            "Create account" if mode_signup else "Sign in"
        )

        if submitted:
            try:
                if mode_signup:
                    new_uid = sign_up(email, password)
                    issue_session_after_sign_in(new_uid)
                    st.success("Account created. You are logged in.")
                else:
                    info = sign_in(email, password)
                    issue_session_after_sign_in(info["user_id"])
                    st.success(f"Signed in as {info.get('email', email)}")
                _populate_messages_from_database(get_current_user_id() or "")
                st.rerun()
            except ValueError as ve:
                st.session_state.auth_error = str(ve)
                st.rerun()
            except RuntimeError as rte:
                st.session_state.auth_error = str(rte)
                st.rerun()


def _render_chat_logged_in(user_id: str) -> None:
    """Chat UI shown after authentication."""
    if st.session_state.pop("show_chat_cleared_banner", False):
        st.success("Chat history deleted. You are starting a new conversation.")

    st.title("Electronics Recommender Assistant")
    st.write(
        "Ask me to find laptops, mice, headphones, or any other electronics. "
        "Your recent history and saved preferences inform recommendations."
    )

    agent = get_agent()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("What are you looking for today?"):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("Searching the catalog..."):
                try:
                    final_answer = invoke_recommender_with_memory(
                        agent, user_id=user_id, user_input=user_input
                    )
                    st.markdown(final_answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": final_answer}
                    )
                except Exception as exc_chat:
                    st.error(
                        f"Error connecting to chat or persistence: {exc_chat}. "
                        "Is Ollama running?"
                    )


@st.cache_resource
def get_agent():
    """Return singleton LangGraph agent (Chroma-backed tools unchanged)."""
    model = os.getenv("OLLAMA_MODEL", "").strip() or _DEFAULT_MODEL
    return create_recommender_agent(model_name=model)


_ensure_session_defaults()


with st.sidebar:
    st.markdown("### Account")
    if st.session_state.get("authenticated"):
        uid = get_current_user_id()
        tok = st.session_state.get("access_token", "")
        st.caption(f"User id: `{uid}`" if uid else "")
        if tok:
            st.caption(f"Session token: `{tok[:12]}…`")
        st.markdown("### Chat")
        if uid and st.button(
            "Clear chat / delete history",
            help="Removes all saved messages for this account in Supabase; preferences stay.",
        ):
            try:
                delete_all_chat_history(uid)
                st.session_state.messages = []
                st.session_state.show_chat_cleared_banner = True
                st.rerun()
            except RuntimeError as e_del:
                st.session_state.chat_history_delete_error = str(e_del)
        err_del = st.session_state.pop("chat_history_delete_error", None)
        if err_del:
            st.error(err_del)
        if st.button("Log out"):
            sign_out()
            st.rerun()


if not st.session_state.get("authenticated") or not get_current_user_id():
    _render_auth_screen()
else:
    _render_chat_logged_in(get_current_user_id() or "")
