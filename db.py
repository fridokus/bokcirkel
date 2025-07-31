import psycopg2
from typing import Optional, Any, List, Tuple

DB_HOST = "127.0.0.1"
DB_USER = "botuser"
DB_PASSWORD = "123"
DB_NAME = "bokcirkel"

class Database:
    """
    Database handler for the book circle bot. Handles all DB operations.
    """
    def __init__(self, connection: Optional[psycopg2.extensions.connection] = None) -> None:
        """Initialize the database connection."""
        if connection:
            self.conn = connection
        else:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )

    def _execute(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch: bool = False) -> Optional[List[Tuple]]:
        """Helper to execute a query with error handling."""
        with self.conn.cursor() as cur:
            try:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                raise e
        return None

    def add_text(self, user_id: int, user_name: str, text: str) -> None:
        """Add a text entry to the database."""
        self._execute(
            "INSERT INTO texts (user_id, username, text) VALUES (%s, %s, %s)",
            (user_id, user_name, text)
        )

    def clear_texts(self) -> None:
        """Delete all text entries from the database."""
        self._execute("DELETE FROM texts;")

    def texts(self) -> List[Tuple[str, str, Any]]:
        """Get the 10 most recent text entries."""
        return self._execute(
            "SELECT username, text, timestamp FROM texts ORDER BY timestamp DESC LIMIT 10",
            fetch=True
        ) or []

    def get_book(self) -> str:
        """Get the current book, or a default if not set."""
        return self.get_setting("book") or "📚 Vilhelm Moberg: The Emigrants 🇸🇪"

    def set_book(self, text: str) -> None:
        """Set the current book."""
        self.set_setting("book", text)

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value by key."""
        result = self._execute(
            "SELECT value FROM settings WHERE key = %s;",
            (key,),
            fetch=True
        )
        return result[0][0] if result else None

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value by key."""
        self._execute(
            """
            INSERT INTO settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            """,
            (key, value)
        )

    def set_user_progress(self, user_id: int, user_name: str, progress: str) -> None:
        """Set or update a user's reading progress."""
        self._execute(
            """
            INSERT INTO user_progress (user_id, username, progress) VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, progress = EXCLUDED.progress;
            """,
            (user_id, user_name, progress)
        )

    def get_user_progress(self) -> List[Tuple[str, str]]:
        """Get all users' reading progress."""
        return self._execute(
            "SELECT username, progress FROM user_progress ORDER BY user_id",
            fetch=True
        ) or []