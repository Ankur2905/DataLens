import numpy as np
import pandas as pd

SUPPORTED_STRATEGIES = {"mean", "median", "mode", "constant"}
SUPPORTED_DTYPES = {"integer", "float", "string", "datetime"}

def _validate_columns(
    df: pd.DataFrame,
    columns: list[str] | None,
) -> list[str]:
    """Validate and normalize a list of column names."""

    if columns is None:
        return list(df.columns)

    if not isinstance(columns, list) or not columns:
        raise ValueError("Columns must be a non-empty list.")

    if not all(isinstance(column, str) for column in columns):
        raise ValueError("Column names must be strings.")

    if len(columns) != len(set(columns)):
        raise ValueError("Duplicate column names are not allowed.")

    missing = [column for column in columns if column not in df.columns]

    if missing:
        raise ValueError(f"Unknown columns: {missing}")

    return columns

def _fill_missing(
    df: pd.DataFrame,
    operation: dict,
) -> tuple[pd.DataFrame, dict]:
    columns = _validate_columns(df, operation.get("columns"))
    strategy = operation.get("strategy")

    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(
            f"Strategy must be one of {sorted(SUPPORTED_STRATEGIES)}."
        )

    if strategy in {"mean", "median"}:
        for column in columns:
            if not pd.api.types.is_numeric_dtype(df[column]):
                raise ValueError(
                    f"Column '{column}' must be numeric for {strategy}."
                )
            if pd.api.types.is_bool_dtype(df[column]):
                raise ValueError(
                    f"Column '{column}' cannot use {strategy}."
                )

    if strategy == "constant" and "value" not in operation:
        raise ValueError("A value is required for constant filling.")

    result = df.copy()
    filled_counts = {}

    for column in columns:
        missing_count = int(result[column].isna().sum())

        if strategy == "mean":
            fill_value = result[column].mean()
        elif strategy == "median":
            fill_value = result[column].median()
        elif strategy == "mode":
            modes = result[column].mode(dropna=True)
            if modes.empty:
                continue
            fill_value = modes.iloc[0]
        else:
            fill_value = operation["value"]

        if pd.isna(fill_value):
            continue

        result[column] = result[column].fillna(fill_value)
        filled_counts[column] = missing_count - int(
            result[column].isna().sum()
        )

    return result, {
        "operation": "fill_missing",
        "strategy": strategy,
        "filled_counts": filled_counts,
        "rows_before": len(df),
        "rows_after": len(result),
    }

def _drop_missing(
    df: pd.DataFrame,
    operation: dict,
) -> tuple[pd.DataFrame, dict]:
    columns = operation.get("columns")
    subset = _validate_columns(df, columns) if columns is not None else None

    result = df.dropna(subset=subset).copy()

    return result, {
        "operation": "drop_missing",
        "rows_removed": len(df) - len(result),
        "rows_before": len(df),
        "rows_after": len(result),
    }

def _remove_duplicates(
    df: pd.DataFrame,
    operation: dict,
) -> tuple[pd.DataFrame, dict]:
    columns = operation.get("columns")
    subset = _validate_columns(df, columns) if columns is not None else None

    keep = operation.get("keep", "first")

    if keep not in {"first", "last"}:
        raise ValueError("keep must be 'first' or 'last'.")

    result = df.drop_duplicates(
        subset=subset,
        keep=keep,
    ).copy()

    return result, {
        "operation": "remove_duplicates",
        "rows_removed": len(df) - len(result),
        "rows_before": len(df),
        "rows_after": len(result),
    }

def _drop_columns(
    df: pd.DataFrame,
    operation: dict,
) -> tuple[pd.DataFrame, dict]:
    columns = operation.get("columns")

    if not isinstance(columns, list) or not columns:
        raise ValueError("Provide a non-empty columns list.")

    columns = _validate_columns(df, columns)
    result = df.drop(columns=columns).copy()

    return result, {
        "operation": "drop_columns",
        "columns_removed": columns,
        "rows_before": len(df),
        "rows_after": len(result),
    }

def _rename_columns(
    df: pd.DataFrame,
    operation: dict,
) -> tuple[pd.DataFrame, dict]:
    mapping = operation.get("mapping")

    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Provide a non-empty column mapping.")

    if not all(
        isinstance(old, str)
        and isinstance(new, str)
        and new.strip()
        for old, new in mapping.items()
    ):
        raise ValueError("Column names must be non-empty strings.")

    unknown = [column for column in mapping if column not in df.columns]

    if unknown:
        raise ValueError(f"Unknown columns: {unknown}")

    new_names = [
        mapping.get(column, column)
        for column in df.columns
    ]

    if len(new_names) != len(set(new_names)):
        raise ValueError("Renaming would create duplicate column names.")

    result = df.rename(columns=mapping).copy()

    return result, {
        "operation": "rename_columns",
        "mapping": mapping,
        "rows_before": len(df),
        "rows_after": len(result),
    }

def _convert_type(
    df: pd.DataFrame,
    operation: dict,
) -> tuple[pd.DataFrame, dict]:
    column = operation.get("column")
    target_type = operation.get("dtype")

    if not isinstance(column, str) or column not in df.columns:
        raise ValueError("Provide a valid column name.")

    if target_type not in SUPPORTED_DTYPES:
        raise ValueError(
            f"dtype must be one of {sorted(SUPPORTED_DTYPES)}."
        )

    result = df.copy()
    series = result[column]

    if target_type == "integer":
        numeric = pd.to_numeric(series, errors="raise")

        if numeric.dropna().mod(1).ne(0).any():
            raise ValueError(
                f"Column '{column}' contains non-integer values."
            )

        result[column] = numeric.astype("Int64")

    elif target_type == "float":
        result[column] = pd.to_numeric(
            series,
            errors="raise",
        ).astype(float)

    elif target_type == "string":
        result[column] = series.astype("string")

    else:
        result[column] = pd.to_datetime(
            series,
            errors="raise",
        )

    return result, {
        "operation": "convert_type",
        "column": column,
        "dtype": target_type,
        "rows_before": len(df),
        "rows_after": len(result),
    }

def apply_cleaning_operation(
    df: pd.DataFrame,
    operation: dict,
) -> tuple[pd.DataFrame, dict]:
    """
    Apply one cleaning operation without mutating the input DataFrame.

    Returns the cleaned DataFrame and an operation summary.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if not isinstance(operation, dict):
        raise ValueError("Operation must be a dictionary.")

    if df.columns.has_duplicates:
        raise ValueError("Dataset contains duplicate column names.")

    operation_type = operation.get("type")

    handlers = {
        "fill_missing": _fill_missing,
        "drop_missing": _drop_missing,
        "remove_duplicates": _remove_duplicates,
        "drop_columns": _drop_columns,
        "rename_columns": _rename_columns,
        "convert_type": _convert_type,
    }

    handler = handlers.get(operation_type)

    if handler is None:
        raise ValueError(f"Unsupported cleaning operation: {operation_type}")

    return handler(df, operation)
