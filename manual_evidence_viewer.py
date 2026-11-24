import streamlit as st

from manual_evidence import preserve_manual_evidence

from url_validator import (
    valid_case_id,
    normalize_carousell_url,
    normalize_telegram_target
)


def show_manual_upload():

    st.subheader("Manual Evidence Upload")

    st.caption(
        "Preserve manually obtained evidence when "
        "automatic collection is unavailable."
    )

    with st.form("manual_collection_form"):

        platform = st.selectbox(
            "Evidence Source", ["Carousell", "Telegram"]
        )

        case_id = st.text_input(
            "Case ID", placeholder="CASE-2026-001"
        )

        target = st.text_input("Original Source URL")

        uploaded_file = st.file_uploader(
            "Upload Evidence (Max 10 MB)",
            type=["png", "jpg", "jpeg", "pdf", "txt", "html"]
        )

        notes = st.text_area(
            "Investigation Notes",
            placeholder="Describe how the evidence was obtained..."
        )

        confirmed = st.checkbox(
            "I am authorized to collect and preserve this evidence."
        )

        submitted = st.form_submit_button(
            "Preserve & Register Evidence",
            type="primary",
            width="stretch"
        )

    if submitted:

        case_id = case_id.strip()
        target = target.strip()

        if not valid_case_id(case_id):
            st.error("Invalid Case ID.")
            return

        if not target or uploaded_file is None:
            st.error("Please provide the source URL and evidence file.")
            return

        if not notes.strip():
            st.error("Please document how the evidence was obtained.")
            return

        if not confirmed:
            st.error("Please confirm your authorization.")
            return

        try:
            if platform == "Carousell":
                target = normalize_carousell_url(target)
            else:
                target = normalize_telegram_target(target)

            with st.spinner("Preserving manual evidence..."):
                result = preserve_manual_evidence(
                    uploaded_file,
                    case_id,
                    platform,
                    target,
                    notes.strip()
                )

            if result["blockchain_status"] == "Registered":
                st.success("Evidence preserved and registered successfully!")
            else:
                st.warning(
                    "Evidence preserved. Blockchain registration "
                    "requires confirmation."
                )

            st.write("Case ID:", case_id)
            st.write("Collection Method: Manual")
            st.write("Storage: Supabase Cloud")

            st.write("SHA-256 Hash")
            st.code(result["sha256"], language=None)

            if result["transaction_hash"]:
                st.write("Transaction Hash")
                st.code(result["transaction_hash"], language=None)

        except Exception as exc:
            st.error("Unable to preserve evidence.")
