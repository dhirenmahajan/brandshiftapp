"""Seasonal spend patterns.

Returns average *weekly* spend for each calendar month so the dashboard
can surface peak inventory / promotion windows. Normalising by the
number of weeks observed in each month removes the bias from month
length and partial coverage at the start / end of the sample window.
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

SQL = """
SELECT
    DATEPART(MONTH, t.PURCHASE_DATE) AS month_num,
    COUNT(DISTINCT CONCAT(t.YEAR, '-', t.WEEK_NUM)) AS weeks_observed,
    CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2))  AS total_spend,
    COUNT(DISTINCT t.BASKET_NUM)                    AS baskets,
    COUNT(DISTINCT t.HSHD_NUM)                      AS households
FROM dbo.Transactions t
WHERE t.PURCHASE_DATE IS NOT NULL
GROUP BY DATEPART(MONTH, t.PURCHASE_DATE)
ORDER BY month_num;
"""

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(SQL)
        rows = fetch_all_dicts(cur)

        payload = []
        for r in rows:
            month = int(r["month_num"] or 0)
            weeks = int(r["weeks_observed"] or 0)
            total = float(r["total_spend"] or 0)
            baskets = int(r["baskets"] or 0)
            households = int(r["households"] or 0)
            payload.append({
                "month_num": month,
                "month_name": MONTH_NAMES[month - 1] if 1 <= month <= 12 else str(month),
                "weeks_observed": weeks,
                "total_spend": round(total, 2),
                "avg_weekly_spend": round(total / weeks, 2) if weeks else 0.0,
                "baskets": baskets,
                "active_households": households,
            })
        return json_response(payload)
    except Exception as exc:  # noqa: BLE001
        logging.exception("AnalyticsSeasonal failed: %s", exc)
        return error_response("Failed to compute seasonal spend.")
