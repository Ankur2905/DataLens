from io import StringIO
from pathlib import Path
from uuid import uuid4

import sqlite3
import pandas as pd

DATABASE_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "datalens.db"
)

def _get_connection() -> sqlite3.Connection:
    """Create a connection to the persistent dataset database."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection

def _initialize_database() -> None:
    """Create the datasets table if it does not exist."""
    with _get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                original_json TEXT NOT NULL,
                working_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

def _serialize_dataframe(df: pd.DataFrame) -> str:
    """Serialize a DataFrame to JSON while retaining its schema."""
    return df.to_json(orient="table", date_format="iso")

def _deserialize_dataframe(payload: str) -> pd.DataFrame:
    """Restore a DataFrame from stored JSON."""
    return pd.read_json(
        StringIO(payload),
        orient="table",
    )

def store_dataset(df: pd.DataFrame) -> str:
    """Persist an original dataset and its working copy."""
    dataset_id = str(uuid4())
    original_json = _serialize_dataframe(df.copy(deep=True))
    working_json = _serialize_dataframe(df.copy(deep=True))

    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO datasets (
                dataset_id,
                original_json,
                working_json
            )
            VALUES (?, ?, ?)
            """,
            (dataset_id, original_json, working_json),
        )

    return dataset_id

def get_dataset(dataset_id: str) -> pd.DataFrame | None:
    """Retrieve the current working dataset."""
    with _get_connection() as connection:
        row = connection.execute(
            """
            SELECT working_json
            FROM datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

    if row is None:
        return None

    return _deserialize_dataframe(row["working_json"])

def get_original_dataset(dataset_id: str) -> pd.DataFrame | None:
    """Retrieve the unchanged original dataset."""
    with _get_connection() as connection:
        row = connection.execute(
            """
            SELECT original_json
            FROM datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

    if row is None:
        return None

    return _deserialize_dataframe(row["original_json"])

def update_working_dataset(
    dataset_id: str,
    df: pd.DataFrame,
) -> None:
    """Persist an updated working dataset after cleaning."""
    working_json = _serialize_dataframe(df.copy(deep=True))

    with _get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE datasets
            SET working_json = ?
            WHERE dataset_id = ?
            """,
            (working_json, dataset_id),
        )

        if cursor.rowcount == 0:
            raise KeyError(f"Dataset not found: {dataset_id}")

_initialize_database()
