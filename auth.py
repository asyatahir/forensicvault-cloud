
"""ForensicVault cloud research-prototype authentication."""

import argparse
import getpass
import hashlib
import hmac
import re
import secrets
import psycopg2

from contextlib import closing
from datetime import datetime, timezone
from database import get_connection

ITERATIONS = 600_000


def initialize_auth():
    # Tables are already created in Supabase.
    pass


def _valid_email(email):
    return (
        bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email))
        and len(email) <= 254
    )


def create_user(
    name, email, password, role='victim',
    *, authorized=False, staff_id=None
):

    name = name.strip()
    email = email.strip().lower()

    if role not in ('victim', 'investigator'):
        raise ValueError('Invalid role.')

    if role == 'investigator' and not authorized:
        raise ValueError(
            'Investigator accounts cannot be publicly registered.'
        )

    if not (2 <= len(name) <= 100) or not _valid_email(email):
        raise ValueError('Enter a valid name and email.')

    if not 12 <= len(password) <= 128:
        raise ValueError('Password must contain 12–128 characters.')

    if role == 'investigator':
        if not staff_id or not re.fullmatch(
            r'[A-Za-z0-9_-]{12,32}', staff_id.strip()
        ):
            raise ValueError('Invalid Staff ID.')

        staff_id = staff_id.strip().upper()
    else:
        staff_id = None

    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        'sha256', password.encode(), salt, ITERATIONS
    )

    try:
        with closing(get_connection()) as conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO public.users (
                            email, full_name, role, salt,
                            password_hash, created_at, staff_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        email, name, role, salt.hex(),
                        digest.hex(),
                        datetime.now(timezone.utc),
                        staff_id
                    ))

                    return cursor.fetchone()['id']

    except psycopg2.errors.UniqueViolation:
        raise ValueError(
            'Email or Staff ID already exists.'
        ) from None



def _allow_login_attempt(identifier, role):

    normalized = identifier.strip().lower()

    attempt_key = hashlib.sha256(
        f"{role}:{normalized}".encode()
    ).hexdigest()

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO public.login_attempts (
                        attempt_key,
                        attempt_count,
                        window_started_at,
                        updated_at
                    )
                    VALUES (%s, 1, NOW(), NOW())

                    ON CONFLICT (attempt_key)
                    DO UPDATE SET
                        attempt_count = CASE
                            WHEN login_attempts.window_started_at
                                <= NOW() - INTERVAL '5 minutes'
                            THEN 1
                            ELSE LEAST(
                                login_attempts.attempt_count + 1, 6
                            )
                        END,

                        window_started_at = CASE
                            WHEN login_attempts.window_started_at
                                <= NOW() - INTERVAL '5 minutes'
                            THEN NOW()
                            ELSE login_attempts.window_started_at
                        END,

                        updated_at = NOW()

                    RETURNING attempt_count
                """, (attempt_key,))

                return cursor.fetchone()['attempt_count'] <= 5


def authenticate(identifier, password, role='victim'):

    if role not in ('victim', 'investigator'):
        return None

    if len(identifier) > 254 or len(password) > 128:
        return None

    if not _allow_login_attempt(identifier, role):
        return None

    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:

            if role == 'victim':
                cursor.execute("""
                    SELECT * FROM public.users
                    WHERE LOWER(email) = LOWER(%s)
                    AND role = %s
                """, (identifier.strip(), role))

            else:
                cursor.execute("""
                    SELECT * FROM public.users
                    WHERE staff_id = %s AND role = %s
                """, (identifier.strip().upper(), role))

            row = cursor.fetchone()

    salt = (
        bytes.fromhex(row['salt'])
        if row else b'\x00' * 16
    )

    expected = (
        bytes.fromhex(row['password_hash'])
        if row else b'\x00' * 32
    )

    actual = hashlib.pbkdf2_hmac(
        'sha256', password.encode(), salt, ITERATIONS
    )

    if not row or not hmac.compare_digest(expected, actual):
        return None

    return {
        'id': row['id'],
        'email': row['email'],
        'name': row['full_name'],
        'role': row['role'],
        'staff_id': row['staff_id']
    }


def get_user(user_id):

    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, email, full_name, role, staff_id
                FROM public.users WHERE id = %s
            """, (user_id,))

            row = cursor.fetchone()

    if not row:
        return None

    return {
        'id': row['id'],
        'email': row['email'],
        'name': row['full_name'],
        'role': row['role'],
        'staff_id': row['staff_id']
    }


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Manage authorized investigator accounts'
    )

    parser.add_argument(
        'command',
        choices=['create-investigator', 'set-staff-id']
    )

    args = parser.parse_args()

    if args.command == 'set-staff-id':

        email = input('Existing investigator email: ').strip()
        staff_id = input('New Staff ID: ').strip().upper()

        if not re.fullmatch(r'[A-Za-z0-9_-]{12,32}', staff_id):
            raise SystemExit('Invalid Staff ID.')

        try:
            with closing(get_connection()) as conn:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE public.users
                            SET staff_id = %s
                            WHERE LOWER(email) = LOWER(%s)
                            AND role = 'investigator'
                        """, (staff_id, email))

                        if not cursor.rowcount:
                            raise SystemExit(
                                'Investigator account not found.'
                            )

        except psycopg2.errors.UniqueViolation:
            raise SystemExit('Staff ID already exists.') from None

        print('Staff ID assigned successfully.')
        raise SystemExit(0)

    print('Create authorized cloud investigator account')

    name = input('Full name: ')
    email = input('Email: ')
    staff_id = input('Staff ID (12–32 characters): ')

    password = getpass.getpass('Password (12+ characters): ')
    confirm = getpass.getpass('Confirm password: ')

    if password != confirm:
        raise SystemExit('Passwords do not match.')

    try:
        create_user(
            name, email, password,
            role='investigator',
            authorized=True,
            staff_id=staff_id
        )

        print('Cloud investigator account created successfully!')

    except ValueError as exc:
        raise SystemExit(str(exc))
