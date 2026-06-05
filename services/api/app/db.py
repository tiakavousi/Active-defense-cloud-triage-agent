"""Postgres connection pool."""
from __future__ import annotations

import os
from psycopg_pool import ConnectionPool

DSN = (
    f"host={os.environ['POSTGRES_HOST']} port={os.environ['POSTGRES_PORT']} "
    f"user={os.environ['POSTGRES_USER']} password={os.environ['POSTGRES_PASSWORD']} "
    f"dbname={os.environ['POSTGRES_DB']}"
)

pool = ConnectionPool(DSN, min_size=2, max_size=10, kwargs={"autocommit": True}, open=False)


def open_pool() -> None:
    pool.open()
    pool.wait()


def close_pool() -> None:
    pool.close()
