"""Basket / cross-sell analytics.

Computes top commodity co-occurrence pairs across baskets and returns
Lift + Confidence metrics – a lightweight version of market-basket
association rule mining, done inside Azure SQL so we don't have to pull
millions of rows into Python.

Formulas (standard association rule mining):
    support(A ∩ B)   = baskets_with_both / total_baskets
    support(A)       = baskets_with_a   / total_baskets
    support(B)       = baskets_with_b   / total_baskets
    confidence(A→B)  = support(A ∩ B) / support(A)
    lift(A, B)       = support(A ∩ B) / (support(A) * support(B))
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

TOTAL_BASKETS_SQL = "SELECT COUNT(DISTINCT BASKET_NUM) AS n FROM dbo.Transactions;"

# Distinct (basket, commodity) pairs so we only count a commodity once per basket.
BASKET_COMMODITY_CTE = """
WITH basket_commodity AS (
    SELECT DISTINCT t.BASKET_NUM AS basket_num, p.COMMODITY AS commodity
    FROM dbo.Transactions t
    JOIN dbo.Products   p ON t.PRODUCT_NUM = p.PRODUCT_NUM
    WHERE p.COMMODITY IS NOT NULL AND LTRIM(RTRIM(p.COMMODITY)) <> ''
)
"""

COMMODITY_SUPPORT_SQL = f"""
{BASKET_COMMODITY_CTE}
SELECT commodity, COUNT(*) AS basket_count
FROM basket_commodity
GROUP BY commodity
HAVING COUNT(*) >= %s;
"""

def _pair_sql(top_n: int) -> str:
    # top_n is integer-validated before we interpolate; no user input reaches the template.
    return f"""
    {BASKET_COMMODITY_CTE}
    SELECT TOP {int(top_n)}
        a.commodity AS commodity_a,
        b.commodity AS commodity_b,
        COUNT(*)    AS together
    FROM basket_commodity a
    JOIN basket_commodity b
        ON a.basket_num = b.basket_num
       AND a.commodity <  b.commodity
    GROUP BY a.commodity, b.commodity
    HAVING COUNT(*) >= %s
    ORDER BY together DESC;
    """


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    # Query knobs
    try:
        top_n = int(req.params.get("top", 15))
    except ValueError:
        top_n = 15
    top_n = max(1, min(top_n, 50))

    try:
        min_support = int(req.params.get("min_support", 15))
    except ValueError:
        min_support = 15

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(TOTAL_BASKETS_SQL)
        total_baskets = int((fetch_all_dicts(cur)[0] or {}).get("n") or 0)
        if total_baskets == 0:
            return json_response([])

        cur.execute(COMMODITY_SUPPORT_SQL, (min_support,))
        support_map = {r["commodity"]: int(r["basket_count"] or 0) for r in fetch_all_dicts(cur)}

        cur.execute(_pair_sql(top_n), (min_support,))
        pairs = fetch_all_dicts(cur)

        results = []
        for p in pairs:
            a = p["commodity_a"]
            b = p["commodity_b"]
            together = int(p["together"] or 0)
            sa = support_map.get(a, 0)
            sb = support_map.get(b, 0)
            if sa == 0 or sb == 0:
                continue
            support_ab = together / total_baskets
            support_a = sa / total_baskets
            support_b = sb / total_baskets
            lift = support_ab / (support_a * support_b) if support_a and support_b else 0
            confidence = (together / sa) * 100 if sa else 0
            results.append({
                "commodity_a": a,
                "commodity_b": b,
                "baskets_together": together,
                "lift": round(lift, 2),
                "confidence": round(confidence, 1),
            })

        # Sort by lift then frequency for better strategic insight
        results.sort(key=lambda r: (r["lift"], r["baskets_together"]), reverse=True)
        return json_response(results[:top_n])
    except Exception as exc:  # noqa: BLE001
        logging.exception("AnalyticsBasket failed: %s", exc)
        return error_response("Failed to compute basket analysis.")
