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
    t.SPEND          AS Spend,
    t.UNITS          AS Units
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


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_preflight()

    logging.info("Executing GetHousehold10 function.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(QUERY, (10,))
        return json_response(fetch_all_dicts(cursor))
    except Exception as exc:  # noqa: BLE001
        logging.exception("GetHousehold10 failed: %s", exc)
        return error_response("An error occurred while fetching Household 10 data.")
