"""Shared authentication helpers.

We keep a tiny Users table in the same Azure SQL database so we don't
need an extra service for a course project while still avoiding plain
text credentials. Passwords are stored as salted PBKDF2-HMAC-SHA256
hashes (100k iterations) using only the Python stdlib.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets

from shared_code.db import get_db_connection

_ITERATIONS = 100_000
_ALGO = "pbkdf2_sha256"

_CREATE_USERS_SQL = """
CREATE TABLE dbo.Users (
    user_id       INT IDENTITY(1,1) PRIMARY KEY,
    username      VARCHAR(40)  NOT NULL,
    email         VARCHAR(120) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    created_at    DATETIME2    NOT NULL CONSTRAINT DF_Users_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_Users_username UNIQUE (username),
    CONSTRAINT UQ_Users_email    UNIQUE (email)
)
"""


def ensure_users_table() -> None:
    """Create the Users table on first use (idempotent).

    Avoids the `IF NOT EXISTS ... BEGIN ... END` batch shape because some
    pymssql / TDS driver combinations surface it as a prepare-time syntax
    error. Instead we poll `OBJECT_ID` first and run a plain CREATE when
    the object is missing.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT OBJECT_ID('dbo.Users', 'U')")
        row = cur.fetchone()
        if row and row[0]:
            return

        try:
            cur.execute(_CREATE_USERS_SQL)
            conn.commit()
        except Exception:  # noqa: BLE001
            # Another worker may have raced us; re-check to confirm.
            cur.execute("SELECT OBJECT_ID('dbo.Users', 'U')")
            row = cur.fetchone()
            if not (row and row[0]):
                raise
            logging.info("dbo.Users was created concurrently; continuing.")
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(derived).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        return False
    if algo != _ALGO:
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
    return hmac.compare_digest(expected, derived)


def find_user(cur, username: str | None, email: str | None):
    if username and email:
        cur.execute(
            "SELECT TOP 1 user_id, username, email, password_hash FROM dbo.Users "
            "WHERE username = %s AND email = %s",
            (username.strip(), email.strip().lower()),
        )
    elif username:
        cur.execute(
            "SELECT TOP 1 user_id, username, email, password_hash FROM dbo.Users "
            "WHERE username = %s",
            (username.strip(),),
        )
    elif email:
        cur.execute(
            "SELECT TOP 1 user_id, username, email, password_hash FROM dbo.Users "
            "WHERE email = %s",
            (email.strip().lower(),),
        )
    else:
        return None
    row = cur.fetchone()
    if not row:
        return None
    return {
        "user_id": row[0],
        "username": row[1],
        "email": row[2],
        "password_hash": row[3],
    }
