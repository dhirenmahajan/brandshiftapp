"""Shared DB helpers for the BrandShift Azure Functions app."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterable

import azure.functions as func
import pymssql


def _parse_conn_str(conn_str: str) -> dict:
    parts = {}
    for segment in conn_str.split(";"):
        if "=" not in segment:
            continue
        key, _, value = segment.partition("=")
        parts[key.strip()] = value.strip()
    return parts


def get_db_connection():
    """Return a pymssql connection using the SqlConnectionString env var."""
    conn_str = os.environ.get("SqlConnectionString", "")
    if not conn_str:
        logging.error("SqlConnectionString environment variable is not set.")
        raise ValueError("Database connection string is missing.")

    parts = _parse_conn_str(conn_str)
    server = parts.get("Server", "").replace("tcp:", "").split(",")[0]
    database = parts.get("Database", "")
    user = parts.get("Uid") or parts.get("User Id") or parts.get("UserId") or ""
    password = parts.get("Pwd") or parts.get("Password") or ""

    if not all([server, database, user, password]):
        raise ValueError("Incomplete SqlConnectionString: need Server, Database, Uid, Pwd.")

    return pymssql.connect(
        server=server,
        user=user,
        password=password,
        database=database,
        login_timeout=30,
        timeout=60,
    )


_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
}


def cors_preflight() -> func.HttpResponse:
    return func.HttpResponse(status_code=204, headers=_CORS_HEADERS)


def json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload, default=str),
        mimetype="application/json",
        status_code=status_code,
        headers=_CORS_HEADERS,
    )


def error_response(message: str, status_code: int = 500) -> func.HttpResponse:
    return json_response({"error": message}, status_code=status_code)


def fetch_all_dicts(cursor) -> list[dict]:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def clean_columns(columns: Iterable[str]) -> list[str]:
    """Mirror the normalisation used by the initial azure_insert.py loader."""
    import re

    cleaned = []
    for c in columns:
        c2 = str(c).strip()
        c2 = re.sub(r"\s+", "_", c2)
        c2 = c2.replace("-", "_").replace("/", "_")
        cleaned.append(c2)
    return cleaned
