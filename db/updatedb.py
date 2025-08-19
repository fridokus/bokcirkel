from .db import Database
from pathlib import Path

_schema_file = "bokcirkel_schema.sql"

def execute_sql_from_file(conn, file_path = Path(__file__).parent / _schema_file):
    try:
        cursor = conn.cursor()

        with open(file_path, 'r') as sql_file:
            cursor.execute(sql_file.read())

        conn.commit()
        print("Schema updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
