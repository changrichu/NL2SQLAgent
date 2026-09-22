"""PostgreSQL connector — read-only with built-in safety guard."""
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

from ..config import settings
from ..sql.safety import SQLSafety
from .base import BaseConnector


class PostgresConnector(BaseConnector):
    name = "postgres"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.conn_params = {
            "host": host or settings.postgres_host,
            "port": port or settings.postgres_port,
            "dbname": db or settings.postgres_db,
            "user": user or settings.postgres_user,
            "password": password or settings.postgres_password,
        }

    @contextmanager
    def _connect(self):
        conn = psycopg2.connect(**self.conn_params)
        try:
            yield conn
        finally:
            conn.close()

    def execute_readonly(
        self, sql: str, params: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        # Guard runs before touching the database.
        if not SQLSafety.is_safe(sql):
            raise ValueError("❌ Refusing to execute unsafe SQL.")

        sql = SQLSafety.add_limit(sql, max_rows=settings.sql_max_rows)

        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or [])
                if cur.description is None:
                    return []
                return [dict(row) for row in cur.fetchall()]

    def get_schema(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
        """
        return self.execute_readonly(sql)
