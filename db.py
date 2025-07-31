import psycopg2

DB_HOST = "127.0.0.1"
DB_USER = "botuser"
DB_PASSWORD = "123"
DB_NAME = "bokcirkel"

class Database():

    def __init__(self, connection=None):
        if connection:
            self.conn = connection
        else:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )

    def add_text(self, user_id, user_name, text: str):
        with self.conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO texts (user_id, username, text) VALUES (%s, %s, %s)",
                        (user_id, user_name, text))
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
    
    def clear_texts(self):
        with self.conn.cursor() as cur:
            try:
                cur.execute("DELETE FROM texts;")
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def texts(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT username, text, timestamp FROM texts ORDER BY timestamp DESC LIMIT 10")
            results = cur.fetchall()
        return results

    def get_book(self):
        return self.get_setting("book") or "📚 Vilhelm Moberg: Utvandrarna 🇸🇪"

    def set_book(self, text: str):
        self.set_setting("book", text)

    def get_setting(self, key: str):
        with self.conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s;", (key,))
            result = cur.fetchone()

        return result[0] if result else None

    def set_setting(self, key: str, value: str):
        with self.conn.cursor as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO settings (key, value) VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
                    """,
                    (key, value),
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def set_user_progress(self, user_id: int, user_name: str, progress: str):
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO user_progress (user_id, username, progress) VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, progress = EXCLUDED.progress;
                    """,
                    (user_id, user_name, progress),
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def get_user_progress(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT username, progress FROM user_progress ORDER BY user_id")
            results = cur.fetchall()
        return results