import os
import pymssql
import logging

def get_db_connection():
    """
    Creates and returns a pymssql connection to Azure SQL Database.
    Parses the standard SqlConnectionString format.
    """
    conn_str = os.environ.get('SqlConnectionString', '')
    if not conn_str:
        logging.error("SqlConnectionString environment variable is not set.")
        raise ValueError("Database connection string is missing.")
        
    try:
        # Mini-parser for connection string
        parts = {p.split('=')[0]: p.split('=')[1] for p in conn_str.split(';') if '=' in p}
        
        server = parts.get('Server', '').replace('tcp:', '').split(',')[0]
        database = parts.get('Database', '')
        user = parts.get('Uid', '')
        password = parts.get('Pwd', '')
        
        conn = pymssql.connect(
            server=server,
            user=user,
            password=password,
            database=database
        )
        return conn
    except Exception as e:
        logging.error(f"Failed to connect using pymssql: {e}")
        raise
