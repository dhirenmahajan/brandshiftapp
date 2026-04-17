"""Churn risk analytics.

Pulls per-household, per-quarter spend and fits a cheap numpy-based linear
regression slope per household. Negative slope = spend is trending down.

Returns:
    - at_risk / stagnant / healthy counts
    - a monthly time series of active vs at-risk households
    - the top 20 at-risk households (for the ML re-engagement table)
"""

import logging
from collections import defaultdict
from statistics import mean

import azure.functions as func

from shared_code.db import (
    cors_preflight,
    error_response,
    fetch_all_dicts,
    get_db_connection,
    json_response,
)

QUARTERLY_SQL = """
SELECT
    t.HSHD_NUM AS hshd_num,
    t.YEAR     AS year_num,
    DATEPART(QUARTER, t.PURCHASE_DATE) AS quarter_num,
    CAST(ISNULL(SUM(t.SPEND), 0) AS DECIMAL(18,2)) AS spend,
    COUNT(DISTINCT t.BASKET_NUM) AS baskets
FROM dbo.Transactions t
WHERE t.PURCHASE_DATE IS NOT NULL
GROUP BY t.HSHD_NUM, t.YEAR, DATEPART(QUARTER, t.PURCHASE_DATE)
ORDER BY t.HSHD_NUM, t.YEAR, quarter_num;
"""

MONTHLY_SQL = """
SELECT
    t.YEAR AS year_num,
    DATEPART(MONTH, t.PURCHASE_DATE) AS month_num,
    COUNT(DISTINCT t.HSHD_NUM) AS active_hshds
FROM dbo.Transactions t
WHERE t.PURCHASE_DATE IS NOT NULL
GROUP BY t.YEAR, DATEPART(MONTH, t.PURCHASE_DATE)
ORDER BY t.YEAR, month_num;
"""

DEMOG_SQL = """
SELECT
    HSHD_NUM, L, AGE_RANGE, INCOME_RANGE, HSHD_COMPOSITION, HH_SIZE, CHILDREN
FROM dbo.Households;
"""


def _slope(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    return (num / den) if den else 0.0


def _classify(slope, total_spend):
    if total_spend <= 0:
        return "inactive"
    if slope < -15:
        return "at_risk"
    if slope < 0:
        return "stagnant"
    return "healthy"


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(QUARTERLY_SQL)
        q_rows = fetch_all_dicts(cur)

        cur.execute(MONTHLY_SQL)
        m_rows = fetch_all_dicts(cur)

        cur.execute(DEMOG_SQL)
        demog = {int(r["HSHD_NUM"]): r for r in fetch_all_dicts(cur)}

        # Fit slope per household
        per_hshd = defaultdict(list)  # hshd -> [(idx, spend)]
        for row in q_rows:
            key = (int(row["year_num"] or 0), int(row["quarter_num"] or 0))
            per_hshd[int(row["hshd_num"])].append((key, float(row["spend"] or 0)))

        analyses = []
        for hshd, entries in per_hshd.items():
            entries.sort()
            ys = [e[1] for e in entries]
            xs = list(range(1, len(ys) + 1))
            s = _slope(xs, ys)
            total_spend = sum(ys)
            avg_spend = total_spend / len(ys) if ys else 0
            pct_change = 0.0
            if len(ys) >= 2 and ys[0] > 0:
                pct_change = round(((ys[-1] - ys[0]) / ys[0]) * 100, 1)

            d = demog.get(hshd, {})
            analyses.append({
                "hshd_num": hshd,
                "slope": round(s, 2),
                "total_spend": round(total_spend, 2),
                "avg_quarter_spend": round(avg_spend, 2),
                "pct_change": pct_change,
                "quarters": len(ys),
                "status": _classify(s, total_spend),
                "income_range": (d.get("INCOME_RANGE") or "Unknown"),
                "age_range": (d.get("AGE_RANGE") or "Unknown"),
                "children": (d.get("CHILDREN") or "Unknown"),
                "composition": (d.get("HSHD_COMPOSITION") or "Unknown"),
            })

        counts = {"healthy": 0, "stagnant": 0, "at_risk": 0, "inactive": 0}
        for a in analyses:
            counts[a["status"]] = counts.get(a["status"], 0) + 1

        at_risk = [a for a in analyses if a["status"] == "at_risk"]
        at_risk.sort(key=lambda a: a["slope"])
        top_risk = at_risk[:20]

        # Monthly trend of active vs at-risk
        risky_set = {a["hshd_num"] for a in at_risk}
        monthly = []
        for r in m_rows:
            label = f"{int(r['year_num'])}-{int(r['month_num']):02d}"
            monthly.append({
                "label": label,
                "active_households": int(r["active_hshds"] or 0),
            })

        return json_response({
            "counts": counts,
            "monthly": monthly,
            "top_risk": top_risk,
            "at_risk_ids": sorted(risky_set),
            "total_households_analyzed": len(analyses),
        })
    except Exception as exc:  # noqa: BLE001
        logging.exception("AnalyticsChurn failed: %s", exc)
        return error_response("Failed to compute churn analytics.")
