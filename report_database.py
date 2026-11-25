
from pathlib import Path
from contextlib import closing
from datetime import datetime, timezone
from database import get_connection

# Keep local database path for backup compatibility
DATABASE_PATH = Path("local_vault") / "victim_reports.db"


def initialize_database():
    # Tables are already created in Supabase.
    pass


def save_report(
    victim_name, victim_email, platform,
    scam_url, description, user_id=None
):

    if user_id is None:
        raise ValueError(
            "Authenticated victim account is required."
        )

    if platform not in ("Carousell", "Telegram", "IIUM Souq"):
        raise ValueError("Unsupported platform.")

    submitted_at = datetime.now(timezone.utc)

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO public.victim_reports (
                        victim_name, victim_email,
                        platform, scam_url, description,
                        submitted_at, user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    victim_name, victim_email,
                    platform, scam_url, description,
                    submitted_at, user_id
                ))

                return cursor.fetchone()["id"]


def format_record(row):

    record = dict(row)

    for key, value in record.items():
        if isinstance(value, datetime):
            record[key] = value.isoformat()

    return record


def get_all_reports():

    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT * FROM public.victim_reports
                ORDER BY id DESC
            """)

            return [
                format_record(row)
                for row in cursor.fetchall()
            ]


def get_reports_for_user(user_id):

    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT * FROM public.victim_reports
                WHERE user_id = %s
                ORDER BY id DESC
            """, (user_id,))

            return [
                format_record(row)
                for row in cursor.fetchall()
            ]


def save_report_evidence(report_id, evidence_data):

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    INSERT INTO public.report_evidence (
                        report_id, file_path,
                        original_filename,
                        sha256, captured_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    report_id,
                    evidence_data["file_path"],
                    evidence_data["original_filename"],
                    evidence_data["sha256"],
                    evidence_data["captured_at"]
                ))


def get_report_evidence(report_id):

    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT * FROM public.report_evidence
                WHERE report_id = %s
                ORDER BY id DESC
            """, (report_id,))

            return [
                format_record(row)
                for row in cursor.fetchall()
            ]


def update_report_status(report_id, new_status):

    if new_status not in (
        "Pending",
        "Under Investigation",
        "Resolved"
    ):
        raise ValueError("Invalid report status.")

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    UPDATE public.victim_reports
                    SET status = %s
                    WHERE id = %s
                """, (new_status, report_id))

                return cursor.rowcount > 0
