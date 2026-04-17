import logging
import json
import azure.functions as func

from shared_code.db import get_db_connection

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Executing SearchData function.')

    hshd_num = req.params.get('hshd_num')
    if not hshd_num:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            hshd_num = req_body.get('hshd_num')

    if not hshd_num:
        return func.HttpResponse(
             "Please pass a hshd_num on the query string or in the request body",
             status_code=400
        )

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
        t.Hshd_num = %d
    ORDER BY 
        t.Hshd_num ASC, 
        t.Basket_num ASC, 
        t.PURCHASE_DATE ASC, 
        t.Product_num ASC, 
        p.Department ASC, 
        p.Commodity ASC;
    """

    try:
        # Convert to int to validate safety
        hshd_num_int = int(hshd_num)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (hshd_num_int,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
            
        return func.HttpResponse(
            json.dumps(results, default=str),
            mimetype="application/json",
            status_code=200
        )

    except ValueError:
       return func.HttpResponse("hshd_num must be an integer.", status_code=400)
    except Exception as e:
        logging.error(f"Error querying database: {e}")
        return func.HttpResponse(
            "An error occurred while fetching search data.",
            status_code=500
        )
