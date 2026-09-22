"""SQL safety guard — keyword whitelist + forbidden pattern check + auto LIMIT."""
import re

from loguru import logger


class SQLSafety:
    """Static analyzer that decides if a SQL string is safe to execute read-only."""

    FORBIDDEN_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
        "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
        "COPY", "VACUUM", "REINDEX",
    }

    DANGEROUS_PATTERNS = [
        r";\s*\w",          # stacked statements
        r"--",              # SQL comment (injection vector)
        r"/\*",             # block comment start
        r"\bOR\s+1\s*=\s*1",  # classic auth bypass
        r"\bUNION\s+SELECT\s+.*--",  # union-based injection
    ]

    @classmethod
    def is_safe(cls, sql: str) -> bool:
        if not sql or not sql.strip():
            return False

        sql_upper = sql.upper()

        for kw in cls.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{kw}\b", sql_upper):
                logger.warning(f"SQL blocked: forbidden keyword '{kw}'")
                return False

        for pat in cls.DANGEROUS_PATTERNS:
            if re.search(pat, sql, re.IGNORECASE):
                logger.warning(f"SQL blocked: dangerous pattern '{pat}'")
                return False

        first_token = sql_upper.strip().split()[0]
        if first_token not in {"SELECT", "WITH"}:
            logger.warning(f"SQL blocked: must start with SELECT/WITH, got '{first_token}'")
            return False

        return True

    @classmethod
    def add_limit(cls, sql: str, max_rows: int = 10000) -> str:
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + f"\nLIMIT {max_rows}"
        return sql
