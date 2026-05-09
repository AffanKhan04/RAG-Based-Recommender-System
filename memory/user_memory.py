"""
Persistent chat history and preferences in Supabase (PostgREST via supabase-py).
"""

from __future__ import annotations

from typing import Dict, List, Union

from langchain_core.messages import AIMessage, HumanMessage

from auth.supabase_auth import get_supabase_client

LcMessage = Union[HumanMessage, AIMessage]


def _format_storage_error(exc: BaseException, fallback: str) -> str:
    msg = str(exc).strip() or fallback
    low = msg.lower()
    if "permission denied" in low or "401" in msg or "403" in msg:
        return (
            "Supabase refused the request. Verify SUPABASE_URL and your service_role key."
        )
    return msg[:500] if len(msg) > 500 else msg


def save_message(user_id: str, role: str, content: str) -> None:
    """
    Persist one chat turn to ``public.chat_history``.

    Args:
        user_id: UUID string of the user.
        role: ``'user'`` or ``'assistant'``.
        content: Message text.

    Raises:
        ValueError: Invalid role or empty content.
        RuntimeError: On Supabase errors.
    """
    if role not in ("user", "assistant"):
        raise ValueError("role must be 'user' or 'assistant'.")
    if not content or not str(content).strip():
        raise ValueError("content must be non-empty.")
    try:
        sb = get_supabase_client()
        sb.table("chat_history").insert(
            {
                "user_id": user_id,
                "role": role,
                "content": content,
            }
        ).execute()
    except BaseException as e:
        raise RuntimeError(_format_storage_error(e, "Failed to save message.")) from e


def load_history(user_id: str, limit: int = 20) -> List[LcMessage]:
    """
    Load recent messages for the user (newest-first query, reversed to chronological).

    Returns:
        LangChain ``HumanMessage`` / ``AIMessage`` objects oldest → newest.

    Raises:
        RuntimeError: On Supabase errors.
    """
    if limit < 1:
        limit = 1
    try:
        sb = get_supabase_client()
        result = (
            sb.table("chat_history")
            .select("role", "content", "timestamp")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        rows = list(reversed(getattr(result, "data", None) or []))
        out: List[LcMessage] = []
        for row in rows:
            r = row.get("role")
            c = row.get("content", "")
            if r == "user":
                out.append(HumanMessage(content=c))
            elif r == "assistant":
                out.append(AIMessage(content=c))
        return out
    except BaseException as e:
        raise RuntimeError(_format_storage_error(e, "Failed to load chat history.")) from e


def delete_all_chat_history(user_id: str) -> None:
    """
    Remove every ``chat_history`` row for ``user_id`` (fresh conversation in DB).

    Does not alter ``user_preferences``.

    Raises:
        RuntimeError: On Supabase errors.
    """
    if not user_id or not str(user_id).strip():
        raise ValueError("user_id is required.")
    try:
        sb = get_supabase_client()
        sb.table("chat_history").delete().eq("user_id", user_id).execute()
    except BaseException as e:
        raise RuntimeError(_format_storage_error(e, "Failed to delete chat history.")) from e


def update_preference(user_id: str, key: str, value: str) -> None:
    """
    Upsert a preference (`public.user_preferences` unique on ``user_id`` + ``preference_key``).

    Raises:
        ValueError: Missing key/value.
        RuntimeError: On Supabase errors.
    """
    pref_key = (key or "").strip()
    pref_val = (value or "").strip()
    if not pref_key:
        raise ValueError("preference_key is required.")
    if not pref_val:
        raise ValueError("preference_value is required.")
    try:
        sb = get_supabase_client()
        updated = (
            sb.table("user_preferences")
            .update({"preference_value": pref_val})
            .eq("user_id", user_id)
            .eq("preference_key", pref_key)
            .select("id")
            .execute()
        )
        changed = getattr(updated, "data", None) or []
        if not changed:
            sb.table("user_preferences").insert(
                {
                    "user_id": user_id,
                    "preference_key": pref_key,
                    "preference_value": pref_val,
                }
            ).execute()
    except BaseException as e:
        raise RuntimeError(_format_storage_error(e, "Failed to update preference.")) from e


def get_preferences(user_id: str) -> Dict[str, str]:
    """
    Return all preferences for the user as ``{key: value}``.

    Raises:
        RuntimeError: On Supabase errors.
    """
    try:
        sb = get_supabase_client()
        result = (
            sb.table("user_preferences")
            .select("preference_key", "preference_value")
            .eq("user_id", user_id)
            .execute()
        )
        rows = getattr(result, "data", None) or []
        prefs: Dict[str, str] = {}
        for row in rows:
            k = row.get("preference_key")
            v = row.get("preference_value")
            if k is not None and v is not None:
                prefs[str(k)] = str(v)
        return prefs
    except BaseException as e:
        raise RuntimeError(_format_storage_error(e, "Failed to load preferences.")) from e


def build_memory_context(user_id: str) -> str:
    """
    Build a short string of stored preferences for system-prompt injection.

    Returns empty string when there are no preferences.
    """
    try:
        prefs = get_preferences(user_id)
    except RuntimeError:
        return ""
    if not prefs:
        return ""
    lines = [f"- {k}: {v}" for k, v in sorted(prefs.items())]
    body = "\n".join(lines)
    return (
        "\nKnown user preferences (honor these when relevant):\n"
        + body
        + "\n"
    )
