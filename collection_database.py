from contextlib import closing
from database import get_connection


def save_collected_evidence(
    case_id,
    platform,
    target_url,
    title,
    evidence,
    collection_method="Automatic",
    investigation_notes=None
):

    if collection_method not in {"Automatic", "Manual"}:
        raise ValueError("Invalid collection method.")

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    INSERT INTO public.collected_evidence (
                        case_id,
                        platform,
                        target_url,
                        title,
                        original_filename,
                        file_path,
                        sha256,
                        captured_at,
                        collection_method,
                        investigation_notes,
                        capture_status
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    RETURNING id
                """, (
                    case_id,
                    platform,
                    target_url,
                    title,
                    evidence["original_filename"],
                    evidence["file_path"],
                    evidence["sha256"],
                    evidence["captured_at"],
                    collection_method,
                    investigation_notes,
                    "Unreviewed"
                ))

                return cursor.fetchone()["id"]


def get_collected_evidence():

    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT *
                FROM public.collected_evidence
                ORDER BY id DESC
            """)

            return cursor.fetchall()


def update_blockchain_status(
    evidence_id,
    status,
    transaction_hash=None
):

    if status not in {"Pending", "Registered", "Failed"}:
        raise ValueError("Invalid blockchain status.")

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    UPDATE public.collected_evidence
                    SET blockchain_status = %s,
                        transaction_hash = %s,
                        registered_at = CASE
                            WHEN %s = 'Registered' THEN NOW()
                            ELSE NULL
                        END
                    WHERE id = %s
                """, (
                    status,
                    transaction_hash,
                    status,
                    evidence_id
                ))

                return cursor.rowcount > 0
