"""Authenticate an existing analyst account."""

import json
import logging

import azure.functions as func

from shared_code.db import (
    cors_preflight,
    error_response,
    get_db_connection,
    json_response,
)
from shared_code.auth import ensure_users_table, find_user, verify_password


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

    if not password or (not username and not email):
        return error_response("username (or email) and password are required.", 400)

    try:
        ensure_users_table()
        conn = get_db_connection()
        cur = conn.cursor()

        user = find_user(cur, username=username or None, email=email or None)
        if not user or not verify_password(password, user["password_hash"]):
            return error_response("Invalid credentials.", 401)

        return json_response({
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
        })
    except Exception as exc:  # noqa: BLE001
        logging.exception("Login failed: %s", exc)
        return error_response("Could not sign in.")
