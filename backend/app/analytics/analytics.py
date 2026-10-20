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


def generate_chart_data(
    df,
    chart_type,
    x_column=None,
    y_column=None,
    aggregation="sum",
    bins=10,
):
    """Generate chart-ready data from a complete DataFrame."""
    import json

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    if chart_type not in {"bar", "line", "scatter", "histogram"}:
        raise ValueError(
            "chart_type must be one of: bar, line, scatter, histogram"
        )

    if df.empty:
        raise ValueError("Cannot generate a chart from an empty dataset")

    def require_column(column, argument_name):
        if not column:
            raise ValueError(f"{argument_name} is required")

        if column not in df.columns:
            raise ValueError(f"Column '{column}' does not exist")

    def require_numeric(column):
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"Column '{column}' must be numeric")

    if chart_type in {"bar", "line"}:
        require_column(x_column, "x_column")

        if aggregation not in {
            "count", "sum", "mean", "median", "min", "max"
        }:
            raise ValueError("Unsupported aggregation")

        if aggregation == "count":
            grouped = df.groupby(x_column, dropna=False).size()
        else:
            require_column(y_column, "y_column")
            require_numeric(y_column)

            grouped = df.groupby(x_column, dropna=False)[y_column].agg(
                aggregation
            )

        result = grouped.reset_index(name="value")
        records = json.loads(
            result.to_json(orient="records", date_format="iso")
        )

        data = [
            {"x": record[x_column], "y": record["value"]}
            for record in records
        ]

        return {
            "chart_type": chart_type,
            "x_column": x_column,
            "y_column": y_column,
            "aggregation": aggregation,
            "data": data,
        }

    if chart_type == "scatter":
        require_column(x_column, "x_column")
        require_column(y_column, "y_column")
        require_numeric(x_column)
        require_numeric(y_column)

        result = df[[x_column, y_column]].dropna()
        records = json.loads(
            result.to_json(orient="records", date_format="iso")
        )

        data = [
            {"x": record[x_column], "y": record[y_column]}
            for record in records
        ]

        return {
            "chart_type": chart_type,
            "x_column": x_column,
            "y_column": y_column,
            "data": data,
        }

    require_column(x_column, "x_column")
    require_numeric(x_column)

    if not isinstance(bins, int) or isinstance(bins, bool) or not 5 <= bins <= 50:
        raise ValueError("bins must be an integer between 5 and 50")

    values = df[x_column].dropna()

    if values.empty:
        raise ValueError(
            f"Column '{x_column}' has no numeric values to plot"
        )

    intervals = pd.cut(values, bins=bins, include_lowest=True)
    counts = intervals.value_counts(sort=False)

    data = [
        {"x": str(interval), "y": int(count)}
        for interval, count in counts.items()
    ]

    return {
        "chart_type": chart_type,
        "x_column": x_column,
        "bins": bins,
        "data": data,
    }

def detect_outliers(df: pd.DataFrame) -> dict:
    """Detect potential numeric outliers using the IQR method."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if df.empty:
        raise ValueError("Cannot detect outliers in an empty dataset.")

    numeric_df = df.select_dtypes(include="number")
    results = []

    for column in numeric_df.columns:
        # Exclude missing and infinite values from the calculation.
        values = numeric_df[column].dropna()
        values = values[values.map(lambda value: pd.notna(value) and abs(value) != float("inf"))]

        if values.empty:
            results.append({
                "column": str(column),
                "valid_count": 0,
                "outlier_count": 0,
                "outlier_percentage": 0.0,
                "lower_bound": None,
                "upper_bound": None,
                "outlier_values": [],
            })
            continue

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = values[
            (values < lower_bound) | (values > upper_bound)
        ]

        results.append({
            "column": str(column),
            "valid_count": int(len(values)),
            "outlier_count": int(len(outliers)),
            "outlier_percentage": round(
                float(len(outliers) / len(values) * 100), 2
            ),
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
            "outlier_values": [
                float(value) for value in outliers.tolist()
            ],
        })

    return {
        "total_rows": int(len(df)),
        "numeric_columns_analyzed": len(results),
        "outliers": results,
    }
