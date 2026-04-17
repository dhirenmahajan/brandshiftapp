"""Demographic engagement analytics.

Answers: "How do factors like household size, presence of children,
location, and income affect customer engagement?"

Returns average spend per household bucketed by INCOME_RANGE, HH_SIZE,
HSHD_COMPOSITION, and CHILDREN. The dashboard uses this to explain
engagement differences across segments and to tune promotions.
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

FILTER_CLAUSES = {
    "region": "t.STORE_R = %s",
}


def _filter_sql(req: func.HttpRequest):
    """Optional store-region filter (other demographic filters would
    short-circuit the bucketing below, so we keep it targeted)."""
    clauses = []
    params = []
    for key, template in FILTER_CLAUSES.items():
        val = req.params.get(key)
        if val and val.lower() != "all":
            clauses.append(template)
            params.append(val)
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _bucket_sql(column: str, filter_sql: str) -> str:
    return f"""
    SELECT
        ISNULL(NULLIF(LTRIM(RTRIM(h.{column})), ''), 'Unknown') AS bucket,
        COUNT(DISTINCT t.HSHD_NUM) AS households,
        CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2)) AS total_spend,
        COUNT(DISTINCT t.BASKET_NUM) AS baskets
    FROM dbo.Transactions t
    JOIN dbo.Households h ON t.HSHD_NUM = h.HSHD_NUM
    WHERE h.{column} IS NOT NULL {filter_sql}
    GROUP BY ISNULL(NULLIF(LTRIM(RTRIM(h.{column})), ''), 'Unknown')
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

    filter_sql, params = _filter_sql(req)

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        def run(col):
            cur.execute(_bucket_sql(col, filter_sql), tuple(params))
            return _project(fetch_all_dicts(cur))

        payload = {
            "by_income":    run("INCOME_RANGE"),
            "by_size":      run("HH_SIZE"),
            "by_composition": run("HSHD_COMPOSITION"),
            "by_children":  run("CHILDREN"),
            "by_age":       run("AGE_RANGE"),
        }
        return json_response(payload)
    except Exception as exc:  # noqa: BLE001
        logging.exception("AnalyticsDemographics failed: %s", exc)
        return error_response("Failed to compute demographic engagement.")
