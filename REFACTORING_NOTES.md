# Refactoring Notes

## Known broken behavior: translation revisions

Translation chat does not currently update the saved translation.

`refine_translation()` returns a natural-language Markdown reply that may contain
a proposed revision. `update_translation_from_chat()` saves that reply in
`chat_messages`, but it only changes the translation row's `updated_at` value.
It does not:

- extract a revised translation from the reply;
- update `translations.current_translation`;
- append a row to `revisions`; or
- refresh `st.session_state.translated_text`.

As a result, the chat can suggest an improvement while the current translation
and revision history remain unchanged. This contradicts the workflow described
in the README.

The safe fix needs an explicit LLM response contract with two separate values:
the conversational reply and an optional revised translation. When a revision
is present, the chat messages, current translation, and revision row should be
written in one database transaction. The Streamlit session should then reload
the saved translation.

This behavior is intentionally documented rather than changed in the current
architecture-only refactor.

## Prioritized follow-up work

1. Fix translation revision persistence using structured model output and an
   atomic database update.
2. Decide whether translating edited text on an existing history item should
   update that item or create a new one. It currently always creates a new row.
3. Persist source-text edits for saved items, or make the source field read-only
   so edits cannot be lost silently.
4. Share one learning-generation workflow between Streamlit and the clipboard
   shortcut while keeping the desired synchronous/background behavior explicit.
5. Split the large, top-level Streamlit application into state, orchestration,
   and tab/sidebar rendering modules.
6. Bind Streamlit to localhost or add access control before exposing port 8501
   beyond the local machine; translation history and API usage are otherwise
   accessible to anyone who can reach it.
7. Reduce broad X11 access in `run_docker.sh` and align its setup instructions
   with the README.
8. Pin or lock runtime dependencies for reproducible Docker builds.
