import logging
import json
import azure.functions as func

from shared_code.db import get_db_connection

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Executing GetHousehold10 function.')

    query = """
    SELECT 
        t.Hshd_num, 
        t.Basket_num, 
        t.PURCHASE_DATE as Date, 
        t.Product_num, 
        p.Department, 
        p.Commodity
    FROM 
        dbo.Transactions t
    LEFT JOIN 
        dbo.Households h ON t.Hshd_num = h.Hshd_num
    LEFT JOIN 
        dbo.Products p ON t.Product_num = p.Product_num
    WHERE 
        t.Hshd_num = 10
    ORDER BY 
        t.Hshd_num ASC, 
        t.Basket_num ASC, 
        t.PURCHASE_DATE ASC, 
        t.Product_num ASC, 
        p.Department ASC, 
        p.Commodity ASC;
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
            
        return func.HttpResponse(
            json.dumps(results, default=str),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error querying database: {e}")
        return func.HttpResponse(
            "An error occurred while fetching Household 10 data.",
            status_code=500
        )
