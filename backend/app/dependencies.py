"""Legacy DB dependency (SQLAlchemy).

The backend has been migrated to CSV + DuckDB and should not require a DB session.
This module is kept as a stub for backward compatibility with any leftover imports.
"""

from typing import Iterator

from fastapi import HTTPException


def get_db() -> Iterator[None]:
    raise HTTPException(status_code=500, detail="SQLAlchemy is disabled (CSV-only mode)")
    yield None
