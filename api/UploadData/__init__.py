import logging
import json
import io
import pandas as pd
import azure.functions as func

from shared_code.db import get_db_connection

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Executing UploadData function.')

    try:
        # Check if the file is embedded in the form data
        file = req.files.get('file') or req.files.get('csv-file')
        if not file:
             return func.HttpResponse(
                json.dumps({"error": "No file uploaded in the request. Use 'file' or 'csv-file' field."}),
                mimetype="application/json",
                status_code=400
             )
        
        filename = file.filename.lower()
        file_contents = file.read()
        df = pd.read_csv(io.BytesIO(file_contents))

        # Determine which table to upload to based on typical file namings
        target_table = None
        if 'transaction' in filename:
            target_table = 'dbo.Transactions'
        elif 'household' in filename:
            target_table = 'dbo.Households'
        elif 'product' in filename:
            target_table = 'dbo.Products'
        else:
             return func.HttpResponse(
                json.dumps({"error": "Cannot determine target table. File name must contain 'transaction', 'household', or 'product'."}),
                mimetype="application/json",
                status_code=400
             )
        
        # Connect to DB
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build dynamic INSERT statement depending on the target table.
        # This is generic fast-insert using pyodbc executemany
        # Limit to 10k rows for class project constraint performance unless needed otherwise.
        # df = df.head(10000) 
        
        # Note: In a production environment with pandas, we typically use sqlalchemy `to_sql`
        # for simplicity, but pyodbc parameterized execute many is also extremely fast.
        
        columns = list(df.columns)
        placeholders = ','.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO {target_table} ({','.join(columns)}) VALUES ({placeholders})"
        
        # Convert df to list of tuples, handle NaN as None for SQL DB Nulls
        df = df.where(pd.notnull(df), None)
        data_tuples = list(df.itertuples(index=False, name=None))
        
        # Use executemany for batch insertion
        # cursor.fast_executemany = True # If supported by driver
        cursor.executemany(insert_query, data_tuples)
        conn.commit()

        return func.HttpResponse(
            json.dumps({"message": f"Successfully uploaded {len(df)} records to {target_table}."}),
            mimetype="application/json",
            status_code=200
        )

    except pd.errors.EmptyDataError:
        return func.HttpResponse(
            json.dumps({"error": "Uploaded CSV file is empty."}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error during file upload and parsing: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"An error occurred: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )
