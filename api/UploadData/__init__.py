"""Bulk CSV upload endpoint.

Accepts multi-part form file uploads, detects the target table from the file
name (household / product / transaction), normalises column names and values
the same way the initial Azure SQL loader did, and then truncates and inserts
the new data.
"""

import io
import logging
import re

import azure.functions as func
import pandas as pd

from shared_code.db import (
    clean_columns,
    cors_preflight,
    error_response,
    get_db_connection,
    json_response,
)

# Map filename hint -> (table name, required columns used to sanity-check the upload).
TABLE_MAP = {
    "transaction": ("dbo.Transactions", {"HSHD_NUM", "PRODUCT_NUM", "BASKET_NUM"}),
    "household":   ("dbo.Households",  {"HSHD_NUM"}),
    "product":     ("dbo.Products",    {"PRODUCT_NUM"}),
}

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _identify_table(filename: str):
    name = filename.lower()
    for key, (table, required) in TABLE_MAP.items():
        if key in name:
            return table, required
    return None, None


def _normalise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = clean_columns(df.columns)

    # Trim and null-ify heavily padded string values
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()
    df.replace({"null": None, "NULL": None, "Null": None, "": None}, inplace=True)

    if "PURCHASE_" in df.columns and "PURCHASE_DATE" not in df.columns:
        df.rename(columns={"PURCHASE_": "PURCHASE_DATE"}, inplace=True)

    df = df.where(pd.notnull(df), None)
    return df


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    logging.info("Executing UploadData function.")

    try:
        file = req.files.get("file") or req.files.get("csv-file")
        if not file:
            return error_response(
                "No file uploaded. Attach the CSV as 'file' or 'csv-file'.", 400
            )

        filename = file.filename or ""
        target_table, required = _identify_table(filename)
        if not target_table:
            return error_response(
                "Cannot determine target table. File name must contain "
                "'transaction', 'household', or 'product'.",
                400,
            )

        raw = file.read()
        if not raw:
            return error_response("Uploaded CSV file is empty.", 400)

        df = pd.read_csv(io.BytesIO(raw))
        df = _normalise_dataframe(df)

        missing = required - set(df.columns)
        if missing:
            return error_response(
                f"Uploaded CSV missing required columns: {sorted(missing)}", 400
            )

        # Guard against SQL-injection via column names (we build an INSERT dynamically)
        for c in df.columns:
            if not _IDENT_RE.match(c):
                return error_response(f"Invalid column name in CSV: {c!r}", 400)

        cols = list(df.columns)
        placeholders = ",".join(["%s"] * len(cols))
        col_list = ",".join(f"[{c}]" for c in cols)
        insert_sql = f"INSERT INTO {target_table} ({col_list}) VALUES ({placeholders})"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Disable FK constraints during bulk replacement so dependent loads succeed
        cursor.execute(f"ALTER TABLE {target_table} NOCHECK CONSTRAINT ALL")
        cursor.execute(f"TRUNCATE TABLE {target_table}")

        rows = list(df.itertuples(index=False, name=None))
        batch = 1000
        total = 0
        for i in range(0, len(rows), batch):
            cursor.executemany(insert_sql, rows[i : i + batch])
            total += len(rows[i : i + batch])

        cursor.execute(f"ALTER TABLE {target_table} WITH CHECK CHECK CONSTRAINT ALL")
        conn.commit()

        return json_response({
            "message": f"Successfully replaced {target_table} with {total:,} rows.",
            "table": target_table,
            "rows": total,
            "columns": cols,
        })

    except pd.errors.EmptyDataError:
        return error_response("Uploaded CSV file is empty.", 400)
    except Exception as exc:  # noqa: BLE001
        logging.exception("UploadData failed: %s", exc)
        return error_response(f"Upload failed: {exc}")
