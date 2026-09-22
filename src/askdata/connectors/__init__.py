"""askdata.connectors — pluggable data-source connectors.

Heavy dependencies (psycopg2, pymysql, clickhouse_connect, …) are imported
lazily so the package can be imported in environments where only a subset of
drivers is installed (e.g. unit tests, Streamlit UI without a DB).
"""
from typing import Dict, Type

from .base import BaseConnector

__all__ = ["BaseConnector", "CONNECTOR_REGISTRY"]


def _load_postgres() -> Type[BaseConnector]:
    from .postgres import PostgresConnector

    return PostgresConnector


def _load_mysql() -> Type[BaseConnector]:
    from .mysql import MySQLConnector

    return MySQLConnector


def _load_clickhouse() -> Type[BaseConnector]:
    from .clickhouse import ClickHouseConnector

    return ClickHouseConnector


def _load_excel() -> Type[BaseConnector]:
    from .excel import ExcelConnector

    return ExcelConnector


def _load_api() -> Type[BaseConnector]:
    from .api import APIConnector

    return APIConnector


# Lazy registry: name -> loader. We only import the heavy driver the first
# time a connector is actually instantiated.
CONNECTOR_REGISTRY: Dict[str, callable] = {
    "postgres": _load_postgres,
    "mysql": _load_mysql,
    "clickhouse": _load_clickhouse,
    "excel": _load_excel,
    "api": _load_api,
}
