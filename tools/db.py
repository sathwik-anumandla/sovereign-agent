"""
tools/db.py (SIH PS 26117)
===========================
Centralized PostgreSQL database helper for Sovereign Workbench.
Provides connection management, port auto-detection, and query helpers using psycopg v3.
"""

import os
import socket
import logging
from typing import Any, List, Dict, Optional, Tuple, Union
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

POSTGRES_DB = os.getenv("POSTGRES_DB", "sovereign_workbench")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_sovereign_2026")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")


def get_postgres_port() -> int:
    """Auto-detects active PostgreSQL port (env POSTGRES_PORT, or tests ports 5432 & 5433)."""
    if "POSTGRES_PORT" in os.environ:
        return int(os.environ["POSTGRES_PORT"])
    
    # Attempt connecting with credentials to 5432 then 5433
    for test_port in [5432, 5433]:
        try:
            with psycopg.connect(
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                host=POSTGRES_HOST,
                port=test_port,
                connect_timeout=2
            ):
                return test_port
        except Exception:
            continue

    return 5432


def get_db_url() -> str:
    """Returns the PostgreSQL connection string URI."""
    port = get_postgres_port()
    return f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{port}/{POSTGRES_DB}"


def get_db_connection(row_factory_dict: bool = False) -> psycopg.Connection:
    """Establishes and returns a connection to PostgreSQL."""
    port = get_postgres_port()
    if row_factory_dict:
        return psycopg.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=port,
            row_factory=dict_row
        )
    return psycopg.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=port
    )


def execute_query(
    query: str,
    params: Optional[Union[Tuple[Any, ...], List[Any]]] = None,
    fetch_one: bool = False,
    fetch_all: bool = False,
    commit: bool = False,
    as_dict: bool = False
) -> Any:
    """Helper function to execute SQL queries on PostgreSQL safely."""
    with get_db_connection(row_factory_dict=as_dict) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            result = None
            if fetch_one:
                result = cur.fetchone()
            elif fetch_all:
                result = cur.fetchall()
            if commit:
                conn.commit()
            return result
