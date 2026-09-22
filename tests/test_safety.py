"""Tests for the SQL safety guard — these run without any LLM or DB."""
from askdata.sql.safety import SQLSafety


def test_select_is_safe():
    assert SQLSafety.is_safe("SELECT * FROM users LIMIT 10")


def test_with_cte_is_safe():
    sql = """
    WITH active AS (
      SELECT id FROM users WHERE active = TRUE
    )
    SELECT COUNT(*) FROM active
    """
    assert SQLSafety.is_safe(sql)


def test_insert_blocked():
    assert not SQLSafety.is_safe("INSERT INTO users (name) VALUES ('x')")


def test_update_blocked():
    assert not SQLSafety.is_safe("UPDATE users SET name = 'x'")


def test_delete_blocked():
    assert not SQLSafety.is_safe("DELETE FROM users WHERE id = 1")


def test_drop_blocked():
    assert not SQLSafety.is_safe("DROP TABLE users")


def test_sql_comment_blocked():
    assert not SQLSafety.is_safe("SELECT * FROM users -- evil")


def test_stacked_statement_blocked():
    assert not SQLSafety.is_safe("SELECT 1; DROP TABLE users")


def test_or_injection_blocked():
    assert not SQLSafety.is_safe("SELECT * FROM users WHERE name = '' OR 1=1")


def test_add_limit_when_missing():
    sql = "SELECT * FROM users"
    out = SQLSafety.add_limit(sql, max_rows=100)
    assert "LIMIT 100" in out.upper()


def test_add_limit_keeps_existing():
    sql = "SELECT * FROM users LIMIT 5"
    out = SQLSafety.add_limit(sql, max_rows=100)
    assert out.upper().count("LIMIT") == 1


def test_empty_sql_blocked():
    assert not SQLSafety.is_safe("")
    assert not SQLSafety.is_safe("   ")
