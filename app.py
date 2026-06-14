import streamlit as st

from clipboard_io import ClipboardError, read_clipboard, write_clipboard
from history_store import (
    create_translation,
    get_chat_messages,
    get_db_path,
    get_revisions,
    get_translation,
    init_db,
    list_translations,
    update_clipboard_status,
    update_translation_from_chat,
)
from translator import (
    DEFAULT_TARGET_LANGUAGE,
    get_model_name,
    refine_translation,
    translate_text,
)


st.set_page_config(page_title="Clipboard Translator")
init_db()


def init_state() -> None:
    defaults = {
        "selected_translation_id": None,
        "source_text": "",
        "translated_text": "",
        "target_language": DEFAULT_TARGET_LANGUAGE,
        "notice": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def snippet(text: str, length: int = 64) -> str:
    compact = " ".join(text.split())
    if len(compact) <= length:
        return compact
    return compact[: length - 3] + "..."


def compact_time(value: str) -> str:
    return value.replace("T", " ")[:16]


def format_history_item(item) -> str:
    return (
        f"#{item['id']} {compact_time(item['updated_at'])} "
        f"{item['target_language']} - {snippet(item['source_text'])}"
    )


def load_translation(translation_id: int, include_target_language: bool = True) -> bool:
    item = get_translation(translation_id)
    if item is None:
        return False

    st.session_state.selected_translation_id = item["id"]
    st.session_state.source_text = item["source_text"]
    st.session_state.translated_text = item["current_translation"]
    if include_target_language:
        st.session_state.target_language = item["target_language"]
    return True


def save_new_translation(
    source_text: str,
    translated_text: str,
    target_language: str,
    origin: str,
    copied_to_clipboard: bool = False,
) -> int:
    translation_id = create_translation(
        source_text=source_text,
        translated_text=translated_text,
        target_language=target_language,
        model=get_model_name(),
        origin=origin,
        copied_to_clipboard=copied_to_clipboard,
    )
    st.session_state.selected_translation_id = translation_id
    st.session_state.source_text = source_text
    st.session_state.translated_text = translated_text
    return translation_id


init_state()

history_items = list_translations(limit=50)
if st.session_state.selected_translation_id is None and history_items:
    load_translation(history_items[0]["id"])

with st.sidebar:
    st.header("History")

    if st.button("New draft", use_container_width=True):
        st.session_state.selected_translation_id = None
        st.session_state.source_text = ""
        st.session_state.translated_text = ""
        st.rerun()

    if history_items:
        history_by_id = {item["id"]: item for item in history_items}
        history_ids = [item["id"] for item in history_items]
        current_id = st.session_state.selected_translation_id
        selected_index = history_ids.index(current_id) if current_id in history_ids else 0
        chosen_id = st.radio(
            "Recent translations",
            history_ids,
            index=selected_index,
            format_func=lambda item_id: format_history_item(history_by_id[item_id]),
            label_visibility="collapsed",
        )
        if chosen_id != current_id:
            load_translation(chosen_id)
            st.rerun()
    else:
        st.caption("No saved translations yet.")

    st.divider()
    st.caption(f"Database: {get_db_path()}")

st.title("Clipboard Translator")

if st.session_state.notice:
    st.success(st.session_state.notice)
    st.session_state.notice = None

st.text_input(
    "Target language",
    key="target_language",
)

read_col, translate_col, copy_col = st.columns(3)

with read_col:
    read_clipboard_clicked = st.button("Read + translate", use_container_width=True)

with translate_col:
    translate_clicked = st.button("Translate current text", use_container_width=True)

with copy_col:
    copy_clicked = st.button(
        "Copy result",
        disabled=not st.session_state.translated_text,
        use_container_width=True,
    )

if read_clipboard_clicked:
    with st.spinner("Reading clipboard and translating..."):
        try:
            source_text = read_clipboard()
            translated_text = translate_text(source_text, st.session_state.target_language)
            translation_id = save_new_translation(
                source_text=source_text,
                translated_text=translated_text,
                target_language=st.session_state.target_language,
                origin="streamlit-clipboard",
            )
            st.session_state.notice = f"Saved translation #{translation_id}."
            st.rerun()
        except ClipboardError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Error: {exc}")

if translate_clicked:
    source_text = st.session_state.source_text
    if not source_text.strip():
        st.warning("Source text is empty.")
    else:
        with st.spinner("Translating..."):
            try:
                translated_text = translate_text(source_text, st.session_state.target_language)
                translation_id = save_new_translation(
                    source_text=source_text,
                    translated_text=translated_text,
                    target_language=st.session_state.target_language,
                    origin="streamlit-manual",
                )
                st.session_state.notice = f"Saved translation #{translation_id}."
                st.rerun()
            except Exception as exc:
                st.error(f"Error: {exc}")

if copy_clicked:
    try:
        write_clipboard(st.session_state.translated_text)
        if st.session_state.selected_translation_id is not None:
            update_clipboard_status(st.session_state.selected_translation_id, True)
        st.session_state.notice = "Copied translation to clipboard."
        st.rerun()
    except ClipboardError as exc:
        st.error(str(exc))

st.text_area("Source text", height=180, key="source_text")

if st.session_state.translated_text:
    st.text_area(
        "Current translation",
        value=st.session_state.translated_text,
        height=180,
    )

selected_id = st.session_state.selected_translation_id
if selected_id is not None:
    st.subheader("Chat refinement")

    messages = get_chat_messages(selected_id)
    if not messages:
        st.caption("No feedback yet for this translation.")

    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("Tell the translator what to change...")
    if prompt:
        item = get_translation(selected_id)
        if item is None:
            st.error("Selected translation was not found.")
        else:
            with st.spinner("Revising translation..."):
                try:
                    revised_translation = refine_translation(
                        source_text=item["source_text"],
                        current_translation=item["current_translation"],
                        user_feedback=prompt,
                        target_language=item["target_language"],
                        chat_messages=messages,
                    )
                    update_translation_from_chat(
                        translation_id=selected_id,
                        user_message=prompt,
                        assistant_message=revised_translation,
                        revised_translation=revised_translation,
                    )
                    st.session_state.translated_text = revised_translation
                    st.session_state.notice = "Saved revised translation."
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error: {exc}")

    revisions = get_revisions(selected_id)
    if revisions:
        with st.expander("Revisions"):
            for revision in revisions:
                st.caption(
                    f"{compact_time(revision['created_at'])} - {revision['note']}"
                )
                st.text(revision["translation_text"])
else:
    st.caption("Translate text to start a history item and chat about it.")
