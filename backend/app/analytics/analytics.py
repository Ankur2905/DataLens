import pandas as pd
import json

SUPPORTED_AGGREGATIONS = {
    "sum",
    "mean",
    "median",
    "min",
    "max",
    "count",
}

def generate_analytics(df: pd.DataFrame) -> dict:
    """Generate numerical summaries and correlations for a dataset."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    numeric_df = df.select_dtypes(include="number")
    numeric_df = numeric_df.loc[
        :, ~numeric_df.columns.isin([])
    ]

    summary = []

    for column in numeric_df.columns:
        values = numeric_df[column].dropna()

        summary.append(
            {
                "column": column,
                "count": int(values.count()),
                "mean": (
                    float(values.mean())
                    if not values.empty
                    else None
                ),
                "median": (
                    float(values.median())
                    if not values.empty
                    else None
                ),
                "std": (
                    float(values.std())
                    if len(values) > 1
                    else None
                ),
                "min": (
                    float(values.min())
                    if not values.empty
                    else None
                ),
                "max": (
                    float(values.max())
                    if not values.empty
                    else None
                ),
            }
        )

    correlation_df = numeric_df.corr()
    correlation_df = correlation_df.fillna(0)

    return {
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "numeric_columns": list(numeric_df.columns),
        "numerical_summary": summary,
        "correlation": {
            "columns": list(correlation_df.columns),
            "matrix": correlation_df.values.tolist(),
        },
    }

def group_by_aggregate(
    df: pd.DataFrame,
    group_by: str,
    aggregation: str,
    metric: str | None = None,
) -> dict:
    """Group dataset records and calculate an aggregation."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if group_by not in df.columns:
        raise ValueError(f"Unknown grouping column: {group_by}")

    if aggregation not in SUPPORTED_AGGREGATIONS:
        raise ValueError(
            f"Unsupported aggregation: {aggregation}"
        )

    if aggregation == "count" and metric is None:
        grouped = (
            df.groupby(group_by, dropna=False)
            .size()
            .reset_index(name="count")
        )
    else:
        if metric is None:
            raise ValueError(
                "A metric column is required for this aggregation."
            )

        if metric not in df.columns:
            raise ValueError(f"Unknown metric column: {metric}")

        if aggregation in {"sum", "mean", "median"}:
            if not pd.api.types.is_numeric_dtype(df[metric]):
                raise ValueError(
                    f"Aggregation '{aggregation}' requires "
                    "a numeric metric column."
                )

        grouped = (
            df.groupby(group_by, dropna=False)[metric]
            .agg(aggregation)
            .reset_index(name=aggregation)
        )

    records = pd.DataFrame(grouped).to_json(
        orient="records",
        date_format="iso",
    )

    return {
        "group_by": group_by,
        "aggregation": aggregation,
        "metric": metric,
        "results": json.loads(records),
    }
