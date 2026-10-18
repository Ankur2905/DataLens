import pandas as pd
import pytest

from app.analytics.profiler import profile_dataframe


def test_basic_dataset_profile():
    df = pd.DataFrame({
        "product": ["Laptop", "Phone", "Laptop", "Phone"],
        "price": [1000, 500, 1000, 20000],
        "quantity": [1, 2, 1, 3],
    })

    result = profile_dataframe(df)

    assert result["dataset"]["total_rows"] == 4
    assert result["dataset"]["total_columns"] == 3
    assert result["data_quality"]["duplicate_rows"] == 1
    assert result["data_quality"]["missing_values"] == 0
    assert result["columns"]["price"]["outlier_count"] == 1


def test_missing_values():
    df = pd.DataFrame({
        "price": [100, None, 300],
        "quantity": [1, 2, None],
    })

    result = profile_dataframe(df)

    assert result["data_quality"]["missing_values"] == 2
    assert result["columns"]["price"]["missing_count"] == 1
    assert result["columns"]["quantity"]["missing_count"] == 1
    assert result["data_quality"]["quality_score"] < 100


def test_empty_dataframe():
    df = pd.DataFrame()

    result = profile_dataframe(df)

    assert result["dataset"]["total_rows"] == 0
    assert result["dataset"]["total_columns"] == 0
    assert result["data_quality"]["quality_score"] == 100


def test_non_dataframe_input():
    with pytest.raises(TypeError):
        profile_dataframe([1, 2, 3])
