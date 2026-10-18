from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_profile_csv():
    csv_content = (
        b"product,price,quantity\n"
        b"Laptop,50000,1\n"
        b"Phone,20000,2\n"
        b"Laptop,,1\n"
    )

    response = client.post(
        "/api/v1/datasets/profile",
        files={
            "file": (
                "sales.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["dataset"]["total_rows"] == 3
    assert result["dataset"]["total_columns"] == 3
    assert result["data_quality"]["missing_values"] == 1
    assert "price" in result["columns"]

def test_reject_unsupported_file():
    response = client.post(
        "/api/v1/datasets/profile",
        files={
            "file": (
                "notes.txt",
                b"some text",
                "text/plain",
            )
        },
    )
    assert response.status_code == 400


def test_preview_dataset():
    csv_content = (
        b"product,price,quantity\n"
        b"Laptop,50000,1\n"
        b"Phone,20000,2\n"
        b"Tablet,30000,1\n"
    )

    upload_response = client.post(
        "/api/v1/datasets/profile",
        files={
            "file": (
                "sales.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert upload_response.status_code == 200
    dataset_id = upload_response.json()["dataset_id"]

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={"page": 1, "page_size": 2},
    )

    assert response.status_code == 200

    result = response.json()

    assert result["total_rows"] == 3
    assert result["total_pages"] == 2
    assert len(result["rows"]) == 2


def test_preview_search():
    csv_content = (
        b"product,price\n"
        b"Laptop,50000\n"
        b"Phone,20000\n"
        b"Tablet,30000\n"
    )

    upload_response = client.post(
        "/api/v1/datasets/profile",
        files={
            "file": (
                "sales.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    dataset_id = upload_response.json()["dataset_id"]

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={"search": "phone"},
    )

    assert response.status_code == 200
    assert response.json()["total_rows"] == 1
    assert response.json()["rows"][0]["product"] == "Phone"


def test_preview_unknown_dataset():
    response = client.get(
        "/api/v1/datasets/unknown-id/preview"
    )

    assert response.status_code == 404


def test_preview_sorting():
    csv_content = (
        b"product,price\n"
        b"Laptop,50000\n"
        b"Phone,20000\n"
        b"Tablet,30000\n"
    )

    upload_response = client.post(
        "/api/v1/datasets/profile",
        files={
            "file": (
                "sales.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    dataset_id = upload_response.json()["dataset_id"]

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        params={
            "sort_by": "price",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 200

    prices = [
        row["price"]
        for row in response.json()["rows"]
    ]

    assert prices == [50000, 30000, 20000]


def test_clean_preview_does_not_modify_dataset():
    csv_content = (
        b"product,price\n"
        b"Laptop,100\n"
        b"Phone,\n"
        b"Tablet,300\n"
    )

    upload = client.post(
        "/api/v1/datasets/profile",
        files={"file": ("sales.csv", csv_content, "text/csv")},
    )

    dataset_id = upload.json()["dataset_id"]

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/clean/preview",
        json={
            "type": "fill_missing",
            "columns": ["price"],
            "strategy": "constant",
            "value": 200,
        },
    )

    assert response.status_code == 200
    assert response.json()["after"]["rows"] == 3
    assert response.json()["summary"]["filled_counts"]["price"] == 1

    current = client.get(
        f"/api/v1/datasets/{dataset_id}/preview"
    ).json()

    assert current["rows"][1]["price"] is None


def test_apply_cleaning_updates_working_dataset():
    csv_content = (
        b"product,price\n"
        b"Laptop,100\n"
        b"Phone,\n"
        b"Tablet,300\n"
    )

    upload = client.post(
        "/api/v1/datasets/profile",
        files={"file": ("sales.csv", csv_content, "text/csv")},
    )

    dataset_id = upload.json()["dataset_id"]

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/clean/apply",
        json={
            "type": "fill_missing",
            "columns": ["price"],
            "strategy": "constant",
            "value": 200,
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Cleaning operation applied successfully."
    )

    current = client.get(
        f"/api/v1/datasets/{dataset_id}/preview"
    ).json()

    assert current["rows"][1]["price"] == 200


def test_cleaning_rejects_unknown_dataset():
    response = client.post(
        "/api/v1/datasets/unknown-id/clean/apply",
        json={
            "type": "remove_duplicates",
        },
    )

    assert response.status_code == 404


def test_cleaning_rejects_invalid_operation():
    upload = client.post(
        "/api/v1/datasets/profile",
        files={
            "file": (
                "sales.csv",
                b"price\n100\n200\n",
                "text/csv",
            )
        },
    )

    dataset_id = upload.json()["dataset_id"]

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/clean/apply",
        json={"type": "invalid_operation"},
    )

    assert response.status_code == 400
