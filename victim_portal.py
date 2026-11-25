
import hashlib
from pathlib import Path
import streamlit as st

from url_validator import (
    validate_carousell_url,
    normalize_souq_url
)
from report_database import (
    save_report,
    save_report_evidence,
    get_reports_for_user,
    get_report_evidence
)
from victim_evidence import save_victim_evidence
from evidence_reader import read_evidence


def render_victim_portal(user):

    if not user or user.get("role") != "victim":
        st.error("Victim login required.")
        st.stop()

    st.title("🛡️ Victim Portal")

    st.caption(
        "Report suspected Carousell, Telegram or IIUM Souq fraud "
        "and track your own reports."
    )

    st.info(
        "Report status: Pending → Under Investigation "
        "→ Resolved. Only investigators can update it."
    )

    tab_submit, tab_reports = st.tabs([
        "Submit Fraud Report", "My Reports"
    ])

    with tab_submit:

        platform = st.selectbox(
            "Platform",
            ["Carousell", "Telegram", "IIUM Souq"],
            key="victim_report_platform"
        )

        platform_placeholders = {
            "Carousell": "https://www.carousell.com.my/...",
            "Telegram": "https://t.me/channelname",
            "IIUM Souq": "https://souq.iium.edu.my/...",
        }

        with st.form("fraud_report_form"):

            scam_url = st.text_input(
                "Scam Listing or Channel URL (optional)",
                placeholder=platform_placeholders[platform],
                key=f"victim_url_{platform}"
            )

            description = st.text_area(
                "Describe What Happened"
            )

            evidence_files = st.file_uploader(
                "Supporting Evidence",
                type=["png", "jpg", "jpeg", "pdf", "txt"],
                accept_multiple_files=True,
                help="Upload multiple files. Combined maximum: 10 MB."
            )

            total_size = sum(
                file.size for file in evidence_files
            )

            st.caption(
                f"Total evidence size: "
                f"{total_size / (1024 * 1024):.2f} / 10 MB"
            )

            consent = st.checkbox(
                "I confirm this report is accurate "
                "to the best of my knowledge."
            )

            submitted = st.form_submit_button(
                "Submit Fraud Report", type="primary"
            )

        if submitted:

            url_error = None
            scam_url = scam_url.strip()

            if platform == "IIUM Souq" and scam_url:
                try:
                    scam_url = normalize_souq_url(scam_url)
                except ValueError:
                    url_error = (
                        "Please enter a valid HTTPS "
                        "IIUM Souq listing URL."
                    )

            if url_error:
                st.error(url_error)

            elif not description.strip():
                st.error("Please describe the incident.")

            elif not consent:
                st.error("Please confirm the declaration.")

            elif (
                platform == "Carousell"
                and scam_url.strip()
                and not validate_carousell_url(scam_url)
            ):
                st.error(
                    "Please enter a valid HTTPS Carousell listing URL."
                )

            elif total_size > 10 * 1024 * 1024:
                st.error(
                    "Combined evidence size must not exceed 10 MB."
                )

            elif any(file.size == 0 for file in evidence_files):
                st.error("Please remove empty evidence files.")

            else:

                try:
                    report_id = save_report(
                        user["name"],
                        user["email"],
                        platform,
                        scam_url.strip(),
                        description.strip(),
                        user_id=user["id"]
                    )

                    st.success(
                        f"Report REPORT-{report_id:04d} submitted."
                    )

                    if evidence_files:
                        successful_uploads = 0
                        failed_uploads = []

                        for evidence_file in evidence_files:
                            try:
                                data = save_victim_evidence(
                                    evidence_file
                                )

                                save_report_evidence(
                                    report_id, data
                                )

                                successful_uploads += 1

                            except Exception:
                                failed_uploads.append(
                                    evidence_file.name
                                )

                        if successful_uploads:
                            st.success(
                                f"{successful_uploads} evidence "
                                "file(s) successfully uploaded "
                                "with individual SHA-256 hashes."
                            )

                        if failed_uploads:
                            st.warning(
                                "Report saved, but the following "
                                "files could not be uploaded or linked: "
                                + ", ".join(failed_uploads)
                            )

                except Exception:
                    st.error(
                        "Unable to save report. Please try again."
                    )

    with tab_reports:

        reports = get_reports_for_user(user["id"])

        if not reports:
            st.info(
                "You have not submitted any reports "
                "with this account."
            )

        for report in reports:

            with st.expander(
                f"REPORT-{report['id']:04d} · "
                f"{report['platform']} · {report['status']}"
            ):

                st.write("**Submitted:**", report["submitted_at"])
                st.write("**Status:**", report["status"])
                st.write("**Description:**", report["description"])

                if report.get("scam_url"):
                    st.write("**Source URL:**", report["scam_url"])

                for evidence in get_report_evidence(report["id"]):

                    st.write(
                        "**File:**", evidence["original_filename"]
                    )

                    is_test = evidence["original_filename"].startswith(
                        f"report_{report['id']}_"
                    )

                    if is_test:
                        st.warning(
                            "SIMULATED TEST EVIDENCE — "
                            "not a real website capture."
                        )

                    try:
                        data = read_evidence(
                            evidence["file_path"]
                        )

                    except Exception:
                        st.error("Unable to retrieve evidence.")
                        continue

                    current_hash = hashlib.sha256(
                        data
                    ).hexdigest()

                    if current_hash != evidence["sha256"]:
                        st.error(
                            "Evidence integrity mismatch. "
                            "File cannot be trusted."
                        )
                        continue

                    st.caption(
                        "SHA-256 evidence integrity check passed."
                    )

                    extension = Path(
                        evidence["original_filename"]
                    ).suffix.lower()

                    if extension in (".png", ".jpg", ".jpeg"):
                        st.image(data, width=400)

                    st.download_button(
                        "Download Evidence",
                        data=data,
                        file_name=evidence["original_filename"],
                        mime="application/octet-stream",
                        key=f"victim_download_{evidence['id']}"
                    )


if __name__ == "__main__":

    st.set_page_config(
        page_title="ForensicVault | Victim Portal",
        page_icon="🛡️"
    )

    st.warning(
        "For secure role-based login, launch the unified "
        "portal with: python -m streamlit run app.py"
    )
