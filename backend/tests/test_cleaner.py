import pandas as pd
import pytest

from app.analytics.cleaner import apply_cleaning_operation

def test_fill_missing_with_mean():
    df = pd.DataFrame({"price": [10.0, None, 30.0]})

    result, summary = apply_cleaning_operation(
        df,
        {
            "type": "fill_missing",
            "columns": ["price"],
            "strategy": "mean",
        },
    )

    assert result["price"].tolist() == [10.0, 20.0, 30.0]
    assert summary["filled_counts"] == {"price": 1}
    assert df["price"].isna().sum() == 1

def test_fill_missing_with_constant():
    df = pd.DataFrame({"city": ["Delhi", None, "Pune"]})

    result, _ = apply_cleaning_operation(
        df,
        {
            "type": "fill_missing",
            "columns": ["city"],
            "strategy": "constant",
            "value": "Unknown",
        },
    )

    assert result["city"].tolist() == ["Delhi", "Unknown", "Pune"]

def test_drop_missing_rows():
    df = pd.DataFrame({
        "name": ["A", "B", "C"],
        "score": [10, None, 30],
    })

    result, summary = apply_cleaning_operation(
        df,
        {"type": "drop_missing"},
    )

    assert len(result) == 2
    assert summary["rows_removed"] == 1

def test_remove_duplicates():
    df = pd.DataFrame({
        "product": ["Laptop", "Phone", "Laptop"],
        "price": [100, 200, 100],
    })

    result, summary = apply_cleaning_operation(
        df,
        {"type": "remove_duplicates"},
    )

    assert len(result) == 2
    assert summary["rows_removed"] == 1

def test_drop_columns():
    df = pd.DataFrame({
        "name": ["A", "B"],
        "age": [20, 30],
    })

    result, _ = apply_cleaning_operation(
        df,
        {"type": "drop_columns", "columns": ["age"]},
    )

    assert list(result.columns) == ["name"]

def test_rename_columns():
    df = pd.DataFrame({"old_name": [1, 2]})

    result, _ = apply_cleaning_operation(
        df,
        {
            "type": "rename_columns",
            "mapping": {"old_name": "new_name"},
        },
    )

    assert list(result.columns) == ["new_name"]

def test_convert_column_type():
    df = pd.DataFrame({"quantity": ["10", "20", None]})

    result, _ = apply_cleaning_operation(
        df,
        {
            "type": "convert_type",
            "column": "quantity",
            "dtype": "integer",
        },
    )

    assert str(result["quantity"].dtype) == "Int64"
    assert result["quantity"].iloc[0] == 10
    assert pd.isna(result["quantity"].iloc[2])

def test_reject_mean_for_string_column():
    df = pd.DataFrame({"city": ["Delhi", None]})

    with pytest.raises(ValueError, match="must be numeric"):
        apply_cleaning_operation(
            df,
            {
                "type": "fill_missing",
                "columns": ["city"],
                "strategy": "mean",
            },
        )

def test_reject_unknown_column():
    df = pd.DataFrame({"price": [10, 20]})

    with pytest.raises(ValueError, match="Unknown columns"):
        apply_cleaning_operation(
            df,
            {
                "type": "drop_columns",
                "columns": ["unknown"],
            },
        )

def test_reject_unsupported_operation():
    df = pd.DataFrame({"price": [10, 20]})

    with pytest.raises(ValueError, match="Unsupported"):
        apply_cleaning_operation(
            df,
            {"type": "delete_everything"},
        )
