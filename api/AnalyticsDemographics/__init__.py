"""Demographic engagement analytics.

Answers: "How do factors like household size, presence of children,
location, and income affect customer engagement?"

Returns average spend per household bucketed by INCOME_RANGE, HH_SIZE,
HSHD_COMPOSITION, CHILDREN, and AGE_RANGE.

Filters respected (from the dashboard sidebar):
    region      -> t.STORE_R
    income      -> h.INCOME_RANGE
    size        -> h.HH_SIZE
    children    -> h.CHILDREN

The filter for the column we are *currently bucketing by* is dropped so
the chart never collapses to a single bar when the user zooms in on a
segment – e.g. selecting "Income = 100-150K" filters every other chart
but still shows the whole Income breakdown so the user can compare.
"""

import logging
import azure.functions as func

from shared_code.db import (
    cors_preflight,
    error_response,
    fetch_all_dicts,
    get_db_connection,
    json_response,
)

# Map incoming query-string key -> (column the filter applies to, WHERE fragment)
FILTER_CLAUSES = {
    "region":   ("STORE_R",       "t.STORE_R = %s"),
    "income":   ("INCOME_RANGE",  "h.INCOME_RANGE = %s"),
    "size":     ("HH_SIZE",       "h.HH_SIZE = %s"),
    "children": ("CHILDREN",      "h.CHILDREN = %s"),
}


def _filter_sql(req: func.HttpRequest, skip_column: str | None = None):
    """Build an additional WHERE fragment.

    If ``skip_column`` is set (i.e. we're bucketing by that column), the
    corresponding filter is ignored so the resulting chart still has
    every bucket to compare against.
    """
    clauses = []
    params = []
    for key, (column, template) in FILTER_CLAUSES.items():
        if skip_column and column.upper() == skip_column.upper():
            continue
        val = req.params.get(key)
        if val and val.lower() != "all":
            clauses.append(template)
            params.append(val)
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _bucket_sql(column: str, filter_sql: str) -> str:
    return f"""
    SELECT
        ISNULL(NULLIF(LTRIM(RTRIM(CAST(h.{column} AS VARCHAR(80)))), ''), 'Unknown') AS bucket,
        COUNT(DISTINCT t.HSHD_NUM) AS households,
        CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2)) AS total_spend,
        COUNT(DISTINCT t.BASKET_NUM) AS baskets
    FROM dbo.Transactions t
    JOIN dbo.Households h ON t.HSHD_NUM = h.HSHD_NUM
    WHERE h.{column} IS NOT NULL {filter_sql}
    GROUP BY ISNULL(NULLIF(LTRIM(RTRIM(CAST(h.{column} AS VARCHAR(80)))), ''), 'Unknown')
    ORDER BY total_spend DESC;
    """


def _project(rows):
    out = []
    for r in rows:
        hshds = int(r.get("households") or 0)
        baskets = int(r.get("baskets") or 0)
        total_spend = float(r.get("total_spend") or 0)
        out.append({
            "bucket": (r.get("bucket") or "Unknown"),
            "households": hshds,
            "baskets": baskets,
            "total_spend": round(total_spend, 2),
            "avg_spend_per_hshd": round(total_spend / hshds, 2) if hshds else 0.0,
            "avg_basket_spend": round(total_spend / baskets, 2) if baskets else 0.0,
        })
    return out


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        def run(col):
            filter_sql, params = _filter_sql(req, skip_column=col)
            cur.execute(_bucket_sql(col, filter_sql), tuple(params))
            return _project(fetch_all_dicts(cur))

        payload = {
            "by_income":      run("INCOME_RANGE"),
            "by_size":        run("HH_SIZE"),
            "by_composition": run("HSHD_COMPOSITION"),
            "by_children":    run("CHILDREN"),
            "by_age":         run("AGE_RANGE"),
        }
        return json_response(payload)
    except Exception as exc:  # noqa: BLE001
        logging.exception("AnalyticsDemographics failed: %s", exc)
        return error_response(f"Failed to compute demographic engagement: {exc}")
