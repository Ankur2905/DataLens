from io import StringIO
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

import sqlite3
import pandas as pd
import json

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
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cleaning_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dataset_id)
                    REFERENCES datasets(dataset_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dataset_versions (
                version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id TEXT NOT NULL,
                dataframe_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (dataset_id)
                    REFERENCES datasets(dataset_id)
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

def record_cleaning_operation(
    dataset_id: str,
    operation: dict,
    summary: dict,
    previous_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
) -> None:
    """Atomically save history and update the working dataset."""
    timestamp = datetime.now(timezone.utc).isoformat()

    operation_json = json.dumps(operation, default=str)
    summary_json = json.dumps(summary, default=str)
    previous_json = _serialize_dataframe(previous_df)
    cleaned_json = _serialize_dataframe(cleaned_df)

    with _get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE datasets
            SET working_json = ?
            WHERE dataset_id = ?
            """,
            (cleaned_json, dataset_id),
        )

        if cursor.rowcount == 0:
            raise KeyError(f"Dataset not found: {dataset_id}")

        connection.execute(
            """
            INSERT INTO dataset_versions (
                dataset_id,
                dataframe_json,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (dataset_id, previous_json, timestamp),
        )

        connection.execute(
            """
            INSERT INTO cleaning_history (
                dataset_id,
                operation,
                summary,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                dataset_id,
                operation_json,
                summary_json,
                timestamp,
            ),
        )

def get_cleaning_history(dataset_id: str) -> list[dict]:
    """Retrieve cleaning operations, newest first."""
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT history_id, operation, summary, created_at
            FROM cleaning_history
            WHERE dataset_id = ?
            ORDER BY history_id DESC
            """,
            (dataset_id,),
        ).fetchall()

    return [
        {
            "history_id": row["history_id"],
            "operation": json.loads(row["operation"]),
            "summary": json.loads(row["summary"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]

def undo_last_cleaning(dataset_id: str) -> dict | None:
    """Restore the dataset to the state before its latest cleaning."""
    with _get_connection() as connection:
        history = connection.execute(
            """
            SELECT history_id
            FROM cleaning_history
            WHERE dataset_id = ?
            ORDER BY history_id DESC
            LIMIT 1
            """,
            (dataset_id,),
        ).fetchone()

        if history is None:
            return None

        version = connection.execute(
            """
            SELECT version_id, dataframe_json
            FROM dataset_versions
            WHERE dataset_id = ?
            ORDER BY version_id DESC
            LIMIT 1
            """,
            (dataset_id,),
        ).fetchone()

        if version is None:
            raise RuntimeError(
                "Cannot undo: previous dataset version is missing."
            )

        connection.execute(
            """
            UPDATE datasets
            SET working_json = ?
            WHERE dataset_id = ?
            """,
            (version["dataframe_json"], dataset_id),
        )

        connection.execute(
            """
            DELETE FROM cleaning_history
            WHERE history_id = ?
            """,
            (history["history_id"],),
        )

        connection.execute(
            """
            DELETE FROM dataset_versions
            WHERE version_id = ?
            """,
            (version["version_id"],),
        )

    return {
        "undone_history_id": history["history_id"],
        "message": "Last cleaning operation undone successfully.",
    }

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
