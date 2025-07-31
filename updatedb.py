from db import Database

def execute_sql_from_file(conn, file_path):
    try:
        cursor = conn.cursor()

        with open(file_path, 'r') as sql_file:
            cursor.execute(sql_file.read())

        conn.commit()
        print("Schema updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    sql_file_path = 'bokcirkel_schema.sql'
    
    db = Database()

    execute_sql_from_file(db.conn, sql_file_path)
