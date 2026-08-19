from datetime import datetime, timezone

import streamlit as st

from clipboard_io import ClipboardError, read_clipboard, write_clipboard
from history_store import (
    add_learning_chat_exchange,
    create_translation,
    get_chat_messages,
    get_db_path,
    get_learning_chat_messages,
    get_revisions,
    get_translation,
    init_db,
    list_source_texts_for_export,
    list_translations,
    mark_source_texts_exported,
    update_clipboard_status,
    update_learning_suggestions,
    update_translation_from_chat,
)
from learning import (
    continue_learning_chat,
    generate_learning_suggestions,
)
from llm_client import DEFAULT_TARGET_LANGUAGE, get_model_name
from translator import (
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
        "warning": None,
        "draft_mode": False,
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
    export_marker = "exported " if item["source_exported_at"] else ""
    return (
        f"{export_marker}#{item['id']} {compact_time(item['updated_at'])} "
        f"{item['target_language']} - {snippet(item['source_text'])}"
    )


def build_source_export(items, generated_at: str) -> str:
    lines = [
        "SOURCE TEXT EXPORT",
        f"Generated: {generated_at}",
        f"Writings: {len(items)}",
        "",
    ]
    for item in items:
        lines.extend(
            [
                "=" * 80,
                f"Writing #{item['id']}",
                f"Created: {item['created_at']}",
                f"Target language: {item['target_language']}",
                "=" * 80,
                "",
                item["source_text"],
                "",
            ]
        )
    return "\n".join(lines)


def record_source_export(translation_ids) -> None:
    mark_source_texts_exported(translation_ids)
    st.session_state.notice = (
        f"Exported {len(translation_ids)} saved source "
        f"{'text' if len(translation_ids) == 1 else 'texts'}."
    )


def load_translation(translation_id: int, include_target_language: bool = True) -> bool:
    item = get_translation(translation_id)
    if item is None:
        return False

    st.session_state.selected_translation_id = item["id"]
    st.session_state.source_text = item["source_text"]
    st.session_state.translated_text = item["current_translation"]
    st.session_state.draft_mode = False
    if include_target_language:
        st.session_state.target_language = item["target_language"]
    return True


def save_new_translation(
    source_text: str,
    translated_text: str,
    target_language: str,
    origin: str,
    copied_to_clipboard: bool = False,
    learning_suggestions: str = "",
) -> int:
    translation_id = create_translation(
        source_text=source_text,
        translated_text=translated_text,
        target_language=target_language,
        model=get_model_name(),
        origin=origin,
        copied_to_clipboard=copied_to_clipboard,
        learning_suggestions=learning_suggestions,
    )
    st.session_state.selected_translation_id = translation_id
    st.session_state.source_text = source_text
    st.session_state.translated_text = translated_text
    st.session_state.draft_mode = False
    return translation_id


def translate_and_save(source_text: str, target_language: str, origin: str) -> int:
    translated_text = translate_text(source_text, target_language)
    translation_id = save_new_translation(
        source_text=source_text,
        translated_text=translated_text,
        target_language=target_language,
        origin=origin,
    )

    try:
        learning_suggestions = generate_learning_suggestions(
            source_text,
            translated_text,
            target_language,
        )
        update_learning_suggestions(translation_id, learning_suggestions)
    except Exception as exc:
        st.session_state.warning = (
            f"Translation #{translation_id} was saved, but learning suggestions "
            f"could not be generated: {exc}"
        )

    return translation_id


init_state()

history_items = list_translations(limit=50)
source_export_items = list_source_texts_for_export()
if (
    st.session_state.selected_translation_id is None
    and history_items
    and not st.session_state.draft_mode
):
    load_translation(history_items[0]["id"])

with st.sidebar:
    st.subheader("Export")
    export_table = [
        {
            "Status": "exported" if item["source_exported_at"] else "",
            "ID": item["id"],
            "Created": compact_time(item["created_at"]),
            "Source": snippet(item["source_text"], length=80),
        }
        for item in source_export_items
    ]
    export_selection = st.dataframe(
        export_table,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="source_export_selection",
        use_container_width=True,
        height=min(320, 36 + 35 * max(len(export_table), 1)),
    )
    selected_export_items = [
        source_export_items[index] for index in export_selection.selection.rows
    ]
    export_generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    export_ids = tuple(item["id"] for item in selected_export_items)
    st.download_button(
        f"Export selected ({len(selected_export_items)})",
        data=build_source_export(selected_export_items, export_generated_at),
        file_name=f"source-texts-{export_generated_at[:10]}.txt",
        mime="text/plain",
        disabled=not selected_export_items,
        on_click=record_source_export,
        args=(export_ids,),
        use_container_width=True,
    )
    st.caption(
        "Ctrl-click to select multiple rows, Shift-click to select a range, "
        "or use the header checkbox to select all."
    )
    exported_count = sum(
        item["source_exported_at"] is not None for item in source_export_items
    )
    st.caption(
        f"{len(source_export_items)} saved writings · {exported_count} marked exported"
    )
    if history_items:
        st.caption("“exported” means that source text was included in an export.")

    st.divider()
    st.header("History")

    if st.button("New draft", use_container_width=True):
        st.session_state.selected_translation_id = None
        st.session_state.source_text = ""
        st.session_state.translated_text = ""
        st.session_state.draft_mode = True
        st.rerun()

    if history_items:
        history_by_id = {item["id"]: item for item in history_items}
        history_ids = [item["id"] for item in history_items]
        if st.session_state.draft_mode:
            history_options = ["draft", *history_ids]
            current_option = "draft"
        else:
            history_options = history_ids
            current_option = st.session_state.selected_translation_id

        if current_option in history_options:
            selected_index = history_options.index(current_option)
        else:
            selected_index = 0

        chosen_id = st.radio(
            "Recent translations",
            history_options,
            index=selected_index,
            format_func=lambda item_id: (
                "New translation"
                if item_id == "draft"
                else format_history_item(history_by_id[item_id])
            ),
            label_visibility="collapsed",
        )
        if chosen_id == "draft":
            pass
        elif chosen_id != st.session_state.selected_translation_id:
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

if st.session_state.warning:
    st.warning(st.session_state.warning)
    st.session_state.warning = None

st.text_input(
    "Target language",
    key="target_language",
)

new_col, read_col, translate_col, copy_col = st.columns(4)

with new_col:
    new_translation_clicked = st.button("New translation", use_container_width=True)

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

if new_translation_clicked:
    st.session_state.selected_translation_id = None
    st.session_state.source_text = ""
    st.session_state.translated_text = ""
    st.session_state.draft_mode = True
    st.rerun()

if read_clipboard_clicked:
    with st.spinner("Translating and preparing learning suggestions..."):
        try:
            source_text = read_clipboard()
            translation_id = translate_and_save(
                source_text,
                st.session_state.target_language,
                "streamlit-clipboard",
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
        with st.spinner("Translating and preparing learning suggestions..."):
            try:
                translation_id = translate_and_save(
                    source_text,
                    st.session_state.target_language,
                    "streamlit-manual",
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

selected_id = st.session_state.selected_translation_id
if selected_id is None:
    st.text_area("Source text", height=180, key="source_text")
    st.caption("Translate text to start a history item and chat about it.")
else:
    selected_item = get_translation(selected_id)
    translation_tab, learning_tab = st.tabs(["Translation", "Learning"])

    with translation_tab:
        st.text_area("Source text", height=180, key="source_text")
        if selected_item and selected_item["source_exported_at"]:
            st.caption(
                "Source text last exported "
                f"{compact_time(selected_item['source_exported_at'])} UTC."
            )
        else:
            st.caption("Source text has not been exported yet.")

        if st.session_state.translated_text:
            st.text_area(
                "Current translation",
                value=st.session_state.translated_text,
                height=180,
            )

        st.subheader("Translation chat")
        messages = get_chat_messages(selected_id)
        if not messages:
            st.caption("Ask anything about the translation.")

        for message in messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        prompt = st.chat_input(
            "Ask anything about this translation...",
            key=f"translation_chat_input_{selected_id}",
        )
        if prompt:
            item = get_translation(selected_id)
            if item is None:
                st.error("Selected translation was not found.")
            else:
                with st.spinner("Preparing a reply..."):
                    try:
                        reply = refine_translation(
                            source_text=item["source_text"],
                            current_translation=item["current_translation"],
                            user_feedback=prompt,
                            target_language=item["target_language"],
                            chat_messages=messages,
                        )
                        update_translation_from_chat(
                            translation_id=selected_id,
                            user_message=prompt,
                            assistant_message=reply,
                        )
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

    with learning_tab:
        st.subheader("Learning suggestions")
        if selected_item and selected_item["learning_suggestions"]:
            with st.container(border=True):
                st.markdown(selected_item["learning_suggestions"])
        else:
            st.caption(
                "No suggestions are saved yet. For a new shortcut translation, "
                "refresh the page in a moment while generation finishes."
            )

        st.subheader("Learning chat")
        learning_messages = get_learning_chat_messages(selected_id)
        if not learning_messages:
            st.caption(
                "Ask for an explanation, more examples, an exercise, or feedback "
                "on your answer."
            )

        for message in learning_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        learning_prompt = st.chat_input(
            "Ask your language coach...",
            key=f"learning_chat_input_{selected_id}",
        )
        if learning_prompt:
            if selected_item is None:
                st.error("Selected translation was not found.")
            else:
                with st.spinner("Preparing a learning response..."):
                    try:
                        learning_response = continue_learning_chat(
                            source_text=selected_item["source_text"],
                            translated_text=selected_item["current_translation"],
                            learning_suggestions=selected_item[
                                "learning_suggestions"
                            ],
                            user_message=learning_prompt,
                            target_language=selected_item["target_language"],
                            chat_messages=learning_messages,
                        )
                        add_learning_chat_exchange(
                            translation_id=selected_id,
                            user_message=learning_prompt,
                            assistant_message=learning_response,
                        )
                        with st.chat_message("user"):
                            st.write(learning_prompt)
                        with st.chat_message("assistant"):
                            st.write(learning_response)
                    except Exception as exc:
                        st.error(f"Error: {exc}")
