"""Create a new analyst account."""

import json
import logging
import re

import azure.functions as func

from shared_code.db import (
    cors_preflight,
    error_response,
    get_db_connection,
    json_response,
)
from shared_code.auth import ensure_users_table, find_user, hash_password

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _parse_body(req: func.HttpRequest):
    try:
        return req.get_json() or {}
    except ValueError:
        try:
            return json.loads(req.get_body() or b"{}")
        except Exception:  # noqa: BLE001
            return {}


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    body = _parse_body(req)
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not username or not email or not password:
        return error_response("username, email, and password are required.", 400)
    if not USERNAME_RE.match(username):
        return error_response("Username must be 3-40 chars, alphanumeric / _ . - only.", 400)
    if not EMAIL_RE.match(email):
        return error_response("Please provide a valid email address.", 400)
    if len(password) < 6:
        return error_response("Password must be at least 6 characters.", 400)

    try:
        ensure_users_table()
        conn = get_db_connection()
        cur = conn.cursor()

        if find_user(cur, username=username, email=None):
            return error_response("That username is already taken.", 409)
        if find_user(cur, username=None, email=email):
            return error_response("That email is already registered.", 409)

        cur.execute(
            "INSERT INTO dbo.Users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, hash_password(password)),
        )
        conn.commit()

        return json_response({"username": username, "email": email}, status_code=201)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Register failed: %s", exc)
        return error_response("Could not create the account.")
