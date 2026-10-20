import io
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)

def upload_csv(content: str) -> str:
    """Upload a CSV and return its dataset ID."""
    response = client.post(
        "/api/v1/datasets/profile",
        files={
            "file": (
                "analytics_test.csv",
                io.BytesIO(content.encode("utf-8")),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    return response.json()["dataset_id"]

def test_dataset_analytics_returns_numerical_summary():
    dataset_id = upload_csv(
        "category,amount,quantity\n"
        "A,10,1\n"
        "A,20,2\n"
        "B,40,4\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/analytics"
    )

    assert response.status_code == 200

    result = response.json()

    assert result["total_rows"] == 3
    assert result["total_columns"] == 3
    assert "amount" in result["numeric_columns"]
    assert "quantity" in result["numeric_columns"]

    amount = next(
        item
        for item in result["numerical_summary"]
        if item["column"] == "amount"
    )

    assert amount["mean"] == 70 / 3
    assert amount["min"] == 10
    assert amount["max"] == 40

def test_dataset_analytics_returns_correlation_matrix():
    dataset_id = upload_csv(
        "first,second\n"
        "1,2\n"
        "2,4\n"
        "3,6\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/analytics"
    )

    assert response.status_code == 200

    correlation = response.json()["correlation"]

    assert correlation["columns"] == ["first", "second"]
    assert correlation["matrix"][0][1] > 0.99

def test_group_by_analytics_returns_mean():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
        "A,20\n"
        "B,40\n"
    )

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/analytics/group-by",
        json={
            "group_by": "category",
            "aggregation": "mean",
            "metric": "amount",
        },
    )

    assert response.status_code == 200

    assert response.json()["results"] == [
        {"category": "A", "mean": 15.0},
        {"category": "B", "mean": 40.0},
    ]

def test_group_by_analytics_counts_rows():
    dataset_id = upload_csv(
        "category\n"
        "A\n"
        "A\n"
        "B\n"
    )

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/analytics/group-by",
        json={
            "group_by": "category",
            "aggregation": "count",
        },
    )

    assert response.status_code == 200

    assert response.json()["results"] == [
        {"category": "A", "count": 2},
        {"category": "B", "count": 1},
    ]

def test_group_by_analytics_rejects_unknown_column():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
    )

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/analytics/group-by",
        json={
            "group_by": "unknown",
            "aggregation": "count",
        },
    )

    assert response.status_code == 400

def test_analytics_rejects_unknown_dataset():
    response = client.get(
        "/api/v1/datasets/unknown-id/analytics"
    )

    assert response.status_code == 404


def test_chart_api_returns_bar_chart_data():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
        "A,20\n"
        "B,40\n"
    )

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/analytics/chart",
        json={
            "chart_type": "bar",
            "x_column": "category",
            "y_column": "amount",
            "aggregation": "sum",
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["chart_type"] == "bar"
    assert result["data"] == [
        {"x": "A", "y": 30},
        {"x": "B", "y": 40},
    ]

def test_chart_api_returns_scatter_data():
    dataset_id = upload_csv(
        "height,weight\n"
        "150,50\n"
        "160,60\n"
        "170,70\n"
    )

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/analytics/chart",
        json={
            "chart_type": "scatter",
            "x_column": "height",
            "y_column": "weight",
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["chart_type"] == "scatter"
    assert result["data"] == [
        {"x": 150, "y": 50},
        {"x": 160, "y": 60},
        {"x": 170, "y": 70},
    ]


def test_chart_api_rejects_unknown_column():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
    )

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/analytics/chart",
        json={
            "chart_type": "bar",
            "x_column": "unknown",
            "y_column": "amount",
            "aggregation": "sum",
        },
    )

    assert response.status_code == 400


def test_preview_filters_by_minimum_value():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
        "B,20\n"
        "C,40\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={"filter_column": "amount", "min_value": 20},
    )

    assert response.status_code == 200
    assert [row["amount"] for row in response.json()["rows"]] == [20, 40]


def test_preview_filters_by_maximum_value():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
        "B,20\n"
        "C,40\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={"filter_column": "amount", "max_value": 20},
    )

    assert response.status_code == 200
    assert [row["amount"] for row in response.json()["rows"]] == [10, 20]


def test_preview_filters_by_numeric_range():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
        "B,20\n"
        "C,40\n"
        "D,60\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={
            "filter_column": "amount",
            "min_value": 20,
            "max_value": 40,
        },
    )

    assert response.status_code == 200
    assert [row["amount"] for row in response.json()["rows"]] == [20, 40]


def test_preview_rejects_numeric_range_on_text_column():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
        "B,20\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={"filter_column": "category", "min_value": 1},
    )

    assert response.status_code == 400

def test_preview_rejects_minimum_greater_than_maximum():
    dataset_id = upload_csv(
        "category,amount\n"
        "A,10\n"
        "B,20\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={
            "filter_column": "amount",
            "min_value": 30,
            "max_value": 10,
        },
    )

    assert response.status_code == 400


def test_preview_text_filter_still_works():
    dataset_id = upload_csv(
        "category,amount\n"
        "Engineering,10\n"
        "Sales,20\n"
        "Engineering,30\n"
    )

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={
            "filter_column": "category",
            "filter_value": "Engineering",
        },
    )

    assert response.status_code == 200
    assert [row["category"] for row in response.json()["rows"]] == [
        "Engineering",
        "Engineering",
    ]
