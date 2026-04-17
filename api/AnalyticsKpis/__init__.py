"""Return high-level KPI numbers used on the Executive Dashboard."""

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
    # Frontend value -> WHERE fragment joined on dbo.Households h
    "region": "t.STORE_R = %s",
    "income": "h.INCOME_RANGE = %s",
    "size":   "h.HH_SIZE = %s",
    "children": "h.CHILDREN = %s",
}


def _build_where(req: func.HttpRequest):
    clauses = []
    params = []
    for key, template in FILTER_CLAUSES.items():
        val = req.params.get(key)
        if val and val.lower() != "all":
            clauses.append(template)
            params.append(val)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    where, params = _build_where(req)

    # Total spend, baskets, unique households, avg basket size, loyalty share
    summary_sql = f"""
    SELECT
        CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2))           AS total_spend,
        COUNT(DISTINCT t.BASKET_NUM)                             AS total_baskets,
        COUNT(DISTINCT t.HSHD_NUM)                               AS active_households,
        CAST(ISNULL(SUM(t.SPEND)/NULLIF(COUNT(DISTINCT t.BASKET_NUM),0), 0) AS DECIMAL(18,2)) AS avg_basket_spend,
        CAST(ISNULL(SUM(t.UNITS), 0) AS BIGINT)                  AS total_units
    FROM dbo.Transactions t
    LEFT JOIN dbo.Households h ON t.HSHD_NUM = h.HSHD_NUM
    {where};
    """

    # Private label share
    brand_sql = f"""
    SELECT
        CAST(ISNULL(SUM(CASE WHEN p.BRAND_TY = 'PRIVATE' THEN t.SPEND ELSE 0 END), 0) AS DECIMAL(18,2)) AS private_spend,
        CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2))                                                AS all_spend
    FROM dbo.Transactions t
    LEFT JOIN dbo.Households h ON t.HSHD_NUM = h.HSHD_NUM
    LEFT JOIN dbo.Products   p ON t.PRODUCT_NUM = p.PRODUCT_NUM
    {where};
    """

    # Loyalty share
    loyalty_sql = f"""
    SELECT
        CAST(ISNULL(SUM(CASE WHEN h.L = 'Y' THEN t.SPEND ELSE 0 END), 0) AS DECIMAL(18,2)) AS loyal_spend,
        CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2))                                    AS all_spend
    FROM dbo.Transactions t
    LEFT JOIN dbo.Households h ON t.HSHD_NUM = h.HSHD_NUM
    {where};
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(summary_sql, tuple(params))
        summary = fetch_all_dicts(cur)[0]

        cur.execute(brand_sql, tuple(params))
        brand = fetch_all_dicts(cur)[0]

        cur.execute(loyalty_sql, tuple(params))
        loyalty = fetch_all_dicts(cur)[0]

        def _pct(num, denom):
            try:
                num = float(num or 0)
                denom = float(denom or 0)
                return round((num / denom) * 100, 1) if denom else 0.0
            except Exception:  # noqa: BLE001
                return 0.0

        payload = {
            "total_spend": float(summary["total_spend"] or 0),
            "total_baskets": int(summary["total_baskets"] or 0),
            "active_households": int(summary["active_households"] or 0),
            "avg_basket_spend": float(summary["avg_basket_spend"] or 0),
            "total_units": int(summary["total_units"] or 0),
            "private_label_pct": _pct(brand["private_spend"], brand["all_spend"]),
            "loyalty_spend_pct": _pct(loyalty["loyal_spend"], loyalty["all_spend"]),
        }
        return json_response(payload)
    except Exception as exc:  # noqa: BLE001
        logging.exception("AnalyticsKpis failed: %s", exc)
        return error_response("Failed to compute KPIs.")
