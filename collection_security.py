"""Server-side automatic collection protection."""

from contextlib import closing
from database import get_connection


def allow_collection_attempt(user_id):

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    SELECT role FROM public.users
                    WHERE id = %s
                    FOR SHARE
                """, (user_id,))

                user = cursor.fetchone()

                if not user or user["role"] != "investigator":
                    return False

                cursor.execute("""
                    INSERT INTO public.collection_attempts (
                        user_id,
                        attempt_count,
                        window_started_at,
                        updated_at
                    )
                    VALUES (%s, 1, NOW(), NOW())

                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        attempt_count = CASE
                            WHEN collection_attempts.window_started_at
                                <= NOW() - INTERVAL '5 minutes'
                            THEN 1
                            ELSE LEAST(
                                collection_attempts.attempt_count + 1, 4
                            )
                        END,

                        window_started_at = CASE
                            WHEN collection_attempts.window_started_at
                                <= NOW() - INTERVAL '5 minutes'
                            THEN NOW()
                            ELSE collection_attempts.window_started_at
                        END,

                        updated_at = NOW()

                    RETURNING attempt_count
                """, (user_id,))

                return cursor.fetchone()["attempt_count"] <= 3


from contextlib import contextmanager

COLLECTION_LOCK_ID = 4311202601


@contextmanager
def collection_lock():

    with closing(get_connection()) as conn:

        conn.autocommit = True

        with conn.cursor() as cursor:

            cursor.execute(
                "SELECT pg_try_advisory_lock(%s) AS acquired",
                (COLLECTION_LOCK_ID,)
            )

            acquired = cursor.fetchone()["acquired"]

            try:
                yield acquired

            finally:
                if acquired:
                    cursor.execute(
                        "SELECT pg_advisory_unlock(%s)",
                        (COLLECTION_LOCK_ID,)
                    )
