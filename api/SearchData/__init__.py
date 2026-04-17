import logging
import azure.functions as func

from shared_code.db import (
    cors_preflight,
    error_response,
    fetch_all_dicts,
    get_db_connection,
    json_response,
)

QUERY = """
SELECT
    t.HSHD_NUM       AS Hshd_num,
    t.BASKET_NUM     AS Basket_num,
    t.PURCHASE_DATE  AS [Date],
    t.PRODUCT_NUM    AS Product_num,
    p.DEPARTMENT     AS Department,
    p.COMMODITY      AS Commodity,
    p.BRAND_TY       AS Brand_type,
    p.NATURAL_ORGANIC_FLAG AS Organic_flag,
    t.SPEND          AS Spend,
    t.UNITS          AS Units,
    t.STORE_R        AS Store_region,
    t.WEEK_NUM       AS Week_num,
    t.YEAR           AS Year_num
FROM dbo.Transactions t
LEFT JOIN dbo.Households h ON t.HSHD_NUM = h.HSHD_NUM
LEFT JOIN dbo.Products   p ON t.PRODUCT_NUM = p.PRODUCT_NUM
WHERE t.HSHD_NUM = %s
ORDER BY
    t.HSHD_NUM ASC,
    t.BASKET_NUM ASC,
    t.PURCHASE_DATE ASC,
    t.PRODUCT_NUM ASC,
    p.DEPARTMENT ASC,
    p.COMMODITY ASC;
"""

HOUSEHOLD_QUERY = """
SELECT TOP 1
    HSHD_NUM          AS Hshd_num,
    L                 AS Loyalty_flag,
    AGE_RANGE         AS Age_range,
    MARITAL           AS Marital_status,
    INCOME_RANGE      AS Income_range,
    HOMEOWNER         AS Homeowner_desc,
    HSHD_COMPOSITION  AS Hshd_composition,
    HH_SIZE           AS Hshd_size,
    CHILDREN          AS Children
FROM dbo.Households
WHERE HSHD_NUM = %s;
"""


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    logging.info("Executing SearchData function.")

    hshd_num = req.params.get("hshd_num")
    if not hshd_num:
        try:
            body = req.get_json()
            hshd_num = body.get("hshd_num") if body else None
        except ValueError:
            hshd_num = None

    if hshd_num is None or str(hshd_num).strip() == "":
        return error_response("Please pass a hshd_num on the query string or in the request body.", 400)

    try:
        hshd_num_int = int(str(hshd_num).strip())
    except ValueError:
        return error_response("hshd_num must be an integer.", 400)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(HOUSEHOLD_QUERY, (hshd_num_int,))
        household_rows = fetch_all_dicts(cursor)
        household = household_rows[0] if household_rows else None

        cursor.execute(QUERY, (hshd_num_int,))
        transactions = fetch_all_dicts(cursor)

        return json_response({
            "hshd_num": hshd_num_int,
            "household": household,
            "transactions": transactions,
            "count": len(transactions),
        })
    except Exception as exc:  # noqa: BLE001
        logging.exception("SearchData failed: %s", exc)
        return error_response("An error occurred while fetching search data.")
