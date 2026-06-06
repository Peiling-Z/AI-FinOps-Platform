"""CSV loader for manual transaction imports."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"date", "amount"}
OPTIONAL_COLUMNS = {"merchant", "category", "description"}


def load_csv(file_path: str | Path) -> list[dict]:
    """Load transactions from a CSV file."""
    df = pd.read_csv(file_path)
    return _normalize_dataframe(df)


def load_csv_string(content: str) -> list[dict]:
    """Load transactions from CSV string content."""
    df = pd.read_csv(StringIO(content))
    return _normalize_dataframe(df)


def _normalize_dataframe(df: pd.DataFrame) -> list[dict]:
    df.columns = [c.strip().lower() for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    records = []
    for _, row in df.iterrows():
        record = {
            "date": str(row["date"]),
            "amount": float(row["amount"]),
        }
        for col in OPTIONAL_COLUMNS:
            if col in df.columns and pd.notna(row[col]):
                record[col] = str(row[col])
        records.append(record)
    return records
