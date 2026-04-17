"""Time-series: National vs Private Label and Organic vs Conventional spend per year/week bucket."""

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
    t.YEAR AS year_num,
    DATEPART(QUARTER, t.PURCHASE_DATE) AS quarter_num,
    CAST(ISNULL(SUM(CASE WHEN p.BRAND_TY = 'NATIONAL' THEN t.SPEND ELSE 0 END), 0) AS DECIMAL(18,2)) AS national_spend,
    CAST(ISNULL(SUM(CASE WHEN p.BRAND_TY = 'PRIVATE'  THEN t.SPEND ELSE 0 END), 0) AS DECIMAL(18,2)) AS private_spend,
    CAST(ISNULL(SUM(CASE WHEN p.NATURAL_ORGANIC_FLAG = 'Y' THEN t.SPEND ELSE 0 END), 0) AS DECIMAL(18,2)) AS organic_spend,
    CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2))                                                     AS total_spend
FROM dbo.Transactions t
LEFT JOIN dbo.Products p ON t.PRODUCT_NUM = p.PRODUCT_NUM
WHERE t.PURCHASE_DATE IS NOT NULL
GROUP BY t.YEAR, DATEPART(QUARTER, t.PURCHASE_DATE)
ORDER BY t.YEAR, quarter_num;
"""


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(SQL)
        rows = fetch_all_dicts(cur)
        for r in rows:
            r["label"] = f"Q{r['quarter_num']} {r['year_num']}"
            for k in ("national_spend", "private_spend", "organic_spend", "total_spend"):
                r[k] = float(r[k] or 0)
        return json_response(rows)
    except Exception as exc:  # noqa: BLE001
        logging.exception("AnalyticsSpendTrends failed: %s", exc)
        return error_response("Failed to compute spend trends.")
