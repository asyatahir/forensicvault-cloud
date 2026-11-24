
import hashlib
import streamlit as st

from collection_database import get_collected_evidence
from evidence_reader import read_evidence


def show_cloud_evidence():

    try:
        records = get_collected_evidence()
    except Exception:
        st.error("Unable to retrieve cloud evidence.")
        return

    if not records:
        st.info("No collected evidence found.")
        return

    registered = sum(
        r["blockchain_status"] == "Registered"
        for r in records
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Files", len(records))
    col2.metric("Registered", registered)
    col3.metric("Pending / Other", len(records) - registered)

    search = st.text_input(
        "Search by Case ID",
        placeholder="Enter case ID...",
        key="cloud_case_search"
    )

    platform = st.selectbox(
        "Filter by Platform",
        ["All", "Carousell", "Telegram"],
        key="cloud_platform_filter"
    )

    method = st.selectbox(
        "Filter by Collection Method",
        ["All", "Automatic", "Manual"],
        key="cloud_method_filter"
    )

    filtered = [
        record for record in records
        if search.lower() in record["case_id"].lower()
        and (
            platform == "All"
            or record["platform"] == platform
        )
        and (
            method == "All"
            or record.get("collection_method") == method
        )
    ]

    if not filtered:
        st.info("No matching evidence found.")
        return

    cases = {}

    for record in filtered:
        cases.setdefault(
            record["case_id"], []
        ).append(record)

    for case_id, items in cases.items():

        with st.expander(
            f"{case_id} — {len(items)} Evidence File(s)"
        ):

            for item in items:

                evidence_id = item["id"]

                st.markdown(
                    "**" + item["original_filename"] + "**"
                )

                st.write("Platform:", item["platform"])
                st.write("Source URL:", item["target_url"])
                method_label = item.get(
                    "collection_method", "Unknown"
                )

                st.write("Collection Method:", method_label)

                if method_label == "Manual":
                    st.write("Preserved at:", item["captured_at"])
                else:
                    st.write("Captured at:", item["captured_at"])

                capture_status = item.get(
                    "capture_status", "Unreviewed"
                )

                if capture_status == "Invalid":
                    st.error(
                        "Invalid capture: Do not rely on this "
                        "file as evidence of the reported content."
                    )
                elif capture_status == "Reviewed":
                    st.info("Capture Status: Reviewed")
                else:
                    st.warning("Capture Status: Unreviewed")

                notes = item.get("investigation_notes")

                if notes:
                    st.write("Investigation Notes:")
                    st.text(notes)

                st.write("SHA-256 Hash")
                st.code(item["sha256"], language=None)

                status = item["blockchain_status"]

                if status == "Registered":
                    st.success("Blockchain status: Registered")
                else:
                    st.warning(f"Blockchain status: {status}")

                if item["transaction_hash"]:
                    st.write("Transaction Hash")
                    st.code(
                        item["transaction_hash"],
                        language=None
                    )

                if st.checkbox(
                    "Retrieve & Verify Evidence",
                    key=f"retrieve_{evidence_id}"
                ):

                    try:
                        file_bytes = read_evidence(
                            item["file_path"]
                        )

                        actual_hash = hashlib.sha256(
                            file_bytes
                        ).hexdigest()

                        if actual_hash != item["sha256"]:
                            st.error(
                                "Integrity verification failed."
                            )
                        else:
                            st.success(
                                "File integrity verified: SHA-256 matches stored hash."
                            )

                            filename = item["original_filename"]

                            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                                st.image(file_bytes)

                            elif filename.lower().endswith(".txt"):
                                st.text_area(
                                    "Evidence Preview",
                                    file_bytes.decode(
                                        "utf-8",
                                        errors="replace"
                                    ),
                                    height=250,
                                    disabled=True,
                                    key=f"preview_{evidence_id}"
                                )

                            st.download_button(
                                "Download Original Evidence",
                                data=file_bytes,
                                file_name=filename,
                                mime="application/octet-stream",
                                key=f"download_cloud_{evidence_id}"
                            )

                    except Exception:
                        st.error("Unable to retrieve evidence file.")

                st.divider()
