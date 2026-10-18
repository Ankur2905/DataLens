import numpy as np
import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> dict:
    """
    Generate a data-quality profile and statistical summary
    for a pandas DataFrame.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    total_rows, total_columns = df.shape
    total_cells = total_rows * total_columns

    missing_total = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    missing_percentage = (
        (missing_total / total_cells) * 100
        if total_cells > 0
        else 0.0
    )

    duplicate_percentage = (
        (duplicate_rows / total_rows) * 100
        if total_rows > 0
        else 0.0
    )

    # Quality score: penalize missing cells and duplicate rows.
    completeness_score = (
        100 * (1 - missing_total / total_cells)
        if total_cells > 0
        else 100.0
    )

    uniqueness_score = (
        100 * (1 - duplicate_rows / total_rows)
        if total_rows > 0
        else 100.0
    )

    quality_score = round(
        completeness_score * uniqueness_score / 100, 2
    )

    columns = {}

    for column in df.columns:
        series = df[column]
        missing_count = int(series.isna().sum())

        column_info = {
            "dtype": str(series.dtype),
            "missing_count": missing_count,
            "missing_percentage": round(
                missing_count / total_rows * 100, 2
            ) if total_rows > 0 else 0.0,
            "unique_count": int(series.nunique()),
            "sample_values": [
                None if pd.isna(value) else str(value)
                for value in series.dropna().head(5).tolist()
            ],
        }

        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            numeric = series.dropna()

            column_info["statistics"] = {
                "mean": float(numeric.mean()) if not numeric.empty else None,
                "median": float(numeric.median()) if not numeric.empty else None,
                "std": float(numeric.std()) if len(numeric) > 1 else None,
                "min": float(numeric.min()) if not numeric.empty else None,
                "max": float(numeric.max()) if not numeric.empty else None,
            }

            if not numeric.empty:
                q1 = numeric.quantile(0.25)
                q3 = numeric.quantile(0.75)
                iqr = q3 - q1

                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                outlier_mask = (
                    (numeric < lower_bound)
                    | (numeric > upper_bound)
                )

                column_info["outlier_count"] = int(
                    outlier_mask.sum()
                )
            else:
                column_info["outlier_count"] = 0

        columns[str(column)] = column_info

    return {
        "dataset": {
            "total_rows": total_rows,
            "total_columns": total_columns,
            "total_cells": total_cells,
        },
        "data_quality": {
            "missing_values": missing_total,
            "missing_percentage": round(missing_percentage, 2),
            "duplicate_rows": duplicate_rows,
            "duplicate_percentage": round(duplicate_percentage, 2),
            "quality_score": quality_score,
        },
        "columns": columns,
    }
