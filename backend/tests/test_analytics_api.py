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
