import pandas as pd
import pytest

from app.analytics.analytics import (
    generate_analytics,
    generate_chart_data,
    group_by_aggregate,
)

def test_generate_analytics_returns_numeric_summary():
    df = pd.DataFrame(
        {
            "product": ["A", "B", "C"],
            "price": [10, 20, 30],
        }
    )

    result = generate_analytics(df)

    assert result["total_rows"] == 3
    assert result["total_columns"] == 2
    assert result["numeric_columns"] == ["price"]

    price = result["numerical_summary"][0]

    assert price["mean"] == 20
    assert price["median"] == 20
    assert price["min"] == 10
    assert price["max"] == 30

def test_generate_analytics_handles_missing_values():
    df = pd.DataFrame({"value": [10.0, None, 30.0]})

    result = generate_analytics(df)

    assert result["numerical_summary"][0]["count"] == 2
    assert result["numerical_summary"][0]["mean"] == 20

def test_generate_analytics_returns_correlation_matrix():
    df = pd.DataFrame(
        {
            "first": [1, 2, 3],
            "second": [2, 4, 6],
        }
    )

    result = generate_analytics(df)

    assert result["correlation"]["columns"] == [
        "first",
        "second",
    ]
    assert len(result["correlation"]["matrix"]) == 2
    assert result["correlation"]["matrix"][0][1] == pytest.approx(1)

def test_group_by_aggregate_calculates_mean():
    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "amount": [10, 20, 40],
        }
    )

    result = group_by_aggregate(
        df,
        group_by="category",
        aggregation="mean",
        metric="amount",
    )

    assert result["results"] == [
        {"category": "A", "mean": 15.0},
        {"category": "B", "mean": 40.0},
    ]

def test_group_by_aggregate_counts_rows():
    df = pd.DataFrame(
        {"category": ["A", "A", "B"]}
    )

    result = group_by_aggregate(
        df,
        group_by="category",
        aggregation="count",
    )

    assert result["results"] == [
        {"category": "A", "count": 2},
        {"category": "B", "count": 1},
    ]

def test_group_by_aggregate_rejects_unknown_column():
    df = pd.DataFrame({"category": ["A"]})

    with pytest.raises(ValueError, match="Unknown grouping column"):
        group_by_aggregate(
            df,
            group_by="unknown",
            aggregation="count",
        )

def test_group_by_aggregate_rejects_invalid_aggregation():
    df = pd.DataFrame({"category": ["A"]})

    with pytest.raises(ValueError, match="Unsupported aggregation"):
        group_by_aggregate(
            df,
            group_by="category",
            aggregation="invalid",
        )

def test_group_by_aggregate_rejects_mean_for_strings():
    df = pd.DataFrame(
        {
            "category": ["A", "B"],
            "label": ["one", "two"],
        }
    )

    with pytest.raises(ValueError, match="requires a numeric"):
        group_by_aggregate(
            df,
            group_by="category",
            aggregation="mean",
            metric="label",
        )

        
def test_generate_chart_data_creates_bar_chart():
    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "amount": [10, 20, 40],
        }
    )

    result = generate_chart_data(
        df,
        chart_type="bar",
        x_column="category",
        y_column="amount",
        aggregation="sum",
    )

    assert result["chart_type"] == "bar"
    assert result["data"] == [
        {"x": "A", "y": 30},
        {"x": "B", "y": 40},
    ]


def test_generate_chart_data_creates_scatter_plot():
    df = pd.DataFrame(
        {
            "height": [150, 160, 170],
            "weight": [50, 60, 70],
        }
    )

    result = generate_chart_data(
        df,
        chart_type="scatter",
        x_column="height",
        y_column="weight",
    )

    assert result["chart_type"] == "scatter"
    assert result["data"] == [
        {"x": 150, "y": 50},
        {"x": 160, "y": 60},
        {"x": 170, "y": 70},
    ]


def test_generate_chart_data_creates_histogram():
    df = pd.DataFrame({"score": list(range(1, 11))})

    result = generate_chart_data(
        df,
        chart_type="histogram",
        x_column="score",
        bins=5,
    )

    assert result["chart_type"] == "histogram"
    assert len(result["data"]) == 5
    assert sum(item["y"] for item in result["data"]) == 10


def test_generate_chart_data_rejects_non_numeric_scatter_column():
    df = pd.DataFrame(
        {
            "category": ["A", "B"],
            "amount": [10, 20],
        }
    )

    with pytest.raises(ValueError, match="must be numeric"):
        generate_chart_data(
            df,
            chart_type="scatter",
            x_column="category",
            y_column="amount",
        )
