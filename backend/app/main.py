from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.responses import JSONResponse, StreamingResponse
from app.analytics.profiler import profile_dataframe
from app.analytics.dataset_store import get_dataset, store_dataset, get_original_dataset, record_cleaning_operation, update_working_dataset, get_cleaning_history, undo_last_cleaning
from fastapi.middleware.cors import CORSMiddleware
from math import ceil
from app.analytics.cleaner import apply_cleaning_operation
from app.analytics.dataset_store import (
    get_dataset,
    get_original_dataset,
    store_dataset,
    update_working_dataset,
)
from app.analytics.analytics import (
    generate_analytics,
    generate_chart_data,
    group_by_aggregate,
    detect_outliers,
)

import pandas as pd
import json

app = FastAPI(
    title="DataLens API",
    description="API for dataset profiling and data quality analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

def _serialize_rows(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame rows into JSON-compatible records."""
    return json.loads(
        df.head(10).to_json(
            orient="records",
            date_format="iso",
        )
    )

@app.get("/health")
def health_check():
    """Check whether the API is running."""
    return {
        "status": "healthy",
        "application": "DataLens API",
        "version": app.version,
    }

@app.post("/api/v1/datasets/profile")
async def profile_dataset(file: UploadFile = File(...)):
    """Upload a CSV or Excel file and return its data profile."""

    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a CSV or XLSX file.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB upload limit.",
        )

    try:
        file_buffer = BytesIO(content)

        if extension == ".csv":
            df = pd.read_csv(file_buffer)
        else:
            df = pd.read_excel(file_buffer, engine="openpyxl")

        if len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="The dataset must contain at least one column.",
            )

        dataset_id = store_dataset(df)
        profile = profile_dataframe(df)
        profile["dataset_id"] = dataset_id

        return JSONResponse(content=profile)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to read or analyze the uploaded file.",
        ) from exc
    finally:
        await file.close()


@app.get("/api/v1/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = None,
    sort_by: str | None = None,
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    filter_column: str | None = None,
    filter_value: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
):
    """Search, filter, sort, and paginate a stored dataset."""

    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    result = df

    if search:
        search_mask = result.astype("string").apply(
            lambda column: column.str.contains(
                search,
                case=False,
                na=False,
                regex=False,
            )
        ).any(axis=1)

        result = result.loc[search_mask]

    if filter_column is not None:
        if filter_column not in result.columns:
            raise HTTPException(
                status_code=400,
                detail="Unknown filter column.",
            )

        has_numeric_filter = min_value is not None or max_value is not None

        if has_numeric_filter:
            if filter_value is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot combine filter_value with numeric range filters.",
                )

            if not pd.api.types.is_numeric_dtype(result[filter_column]):
                raise HTTPException(
                    status_code=400,
                    detail="Numeric range filtering requires a numeric column.",
                )

            if (
                min_value is not None
                and max_value is not None
                and min_value > max_value
            ):
                raise HTTPException(
                    status_code=400,
                    detail="min_value cannot be greater than max_value.",
                )

            numeric_column = result[filter_column]

            filter_mask = numeric_column.notna()

            if min_value is not None:
                filter_mask &= numeric_column >= min_value

            if max_value is not None:
                filter_mask &= numeric_column <= max_value

        else:
            if filter_value is None:
                raise HTTPException(
                    status_code=400,
                    detail="filter_value is required with filter_column.",
                )

            filter_mask = result[filter_column].astype("string").str.contains(
                filter_value,
                case=False,
                na=False,
                regex=False,
            )

        result = result.loc[filter_mask]

    elif min_value is not None or max_value is not None:
        raise HTTPException(
            status_code=400,
            detail="filter_column is required for numeric range filtering.",
        )
    
    if sort_by is not None:
        if sort_by not in result.columns:
            raise HTTPException(
                status_code=400,
                detail="Unknown sort column.",
            )

        result = result.sort_values(
            by=sort_by,
            ascending=(sort_order == "asc"),
            na_position="last",
        )

    total_rows = len(result)
    total_pages = ceil(total_rows / page_size)
    start = (page - 1) * page_size

    page_df = result.iloc[start:start + page_size]

    # Convert missing values to JSON null and dates to ISO strings.
    rows = json.loads(
        page_df.to_json(orient="records", date_format="iso")
    )

    return {
        "dataset_id": dataset_id,
        "columns": [str(column) for column in df.columns],
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": total_pages,
        "rows": rows,
    }

@app.post("/api/v1/datasets/{dataset_id}/clean/preview")
def preview_cleaning(dataset_id: str, operation: dict):
    """Preview a cleaning operation without changing stored data."""

    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    try:
        cleaned_df, summary = apply_cleaning_operation(df, operation)

        return {
            "dataset_id": dataset_id,
            "summary": summary,
            "before": {
                "rows": len(df),
                "columns": list(df.columns),
                "preview": _serialize_rows(df),
            },
            "after": {
                "rows": len(cleaned_df),
                "columns": list(cleaned_df.columns),
                "preview": _serialize_rows(cleaned_df),
                "profile": profile_dataframe(cleaned_df),
            },
        }

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/api/v1/datasets/{dataset_id}/clean/apply")
def apply_cleaning(dataset_id: str, operation: dict):
    """Apply a cleaning operation to the working dataset."""

    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    try:
        cleaned_df, summary = apply_cleaning_operation(df, operation)
        record_cleaning_operation(
            dataset_id=dataset_id,
            operation=operation,
            summary=summary,
            previous_df=df,
            cleaned_df=cleaned_df
            )

        return {
            "dataset_id": dataset_id,
            "message": "Cleaning operation applied successfully.",
            "summary": summary,
            "profile": profile_dataframe(cleaned_df),
        }

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.get("/api/v1/datasets/{dataset_id}/clean/history")
def get_dataset_cleaning_history(dataset_id: str):
    """Return the cleaning history for a dataset."""

    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    return {
        "dataset_id": dataset_id,
        "history": get_cleaning_history(dataset_id),
    }    

@app.post("/api/v1/datasets/{dataset_id}/clean/undo")
def undo_cleaning(dataset_id: str):
    """Undo the most recently applied cleaning operation."""

    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    result = undo_last_cleaning(dataset_id)

    if result is None:
        raise HTTPException(
            status_code=400,
            detail="There is no cleaning operation to undo.",
        )

    restored_df = get_dataset(dataset_id)

    return {
        "dataset_id": dataset_id,
        **result,
        "profile": profile_dataframe(restored_df),
    }

@app.get("/api/v1/datasets/{dataset_id}/analytics")
def get_dataset_analytics(dataset_id: str):
    """Return numerical summaries and correlations for a dataset."""
    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    return {
        "dataset_id": dataset_id,
        **generate_analytics(df),
    }

@app.post("/api/v1/datasets/{dataset_id}/analytics/group-by")
def get_group_by_analytics(
    dataset_id: str,
    request: dict,
):
    """Aggregate dataset records by a selected column."""
    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    try:
        result = group_by_aggregate(
            df=df,
            group_by=request.get("group_by", ""),
            aggregation=request.get("aggregation", ""),
            metric=request.get("metric"),
        )

        return {
            "dataset_id": dataset_id,
            **result,
        }

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.post("/api/v1/datasets/{dataset_id}/analytics/chart")
def get_chart_data(
    dataset_id: str,
    request: dict,
):
    """Generate chart-ready data for a dataset."""
    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    try:
        result = generate_chart_data(
            df=df,
            chart_type=request.get("chart_type", ""),
            x_column=request.get("x_column"),
            y_column=request.get("y_column"),
            aggregation=request.get("aggregation", "sum"),
            bins=request.get("bins", 10),
        )

        return {
            "dataset_id": dataset_id,
            **result,
        }

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.get("/api/v1/datasets/{dataset_id}/insights/outliers")
def get_dataset_outliers(dataset_id: str):
    """Return potential numeric outliers for a dataset."""
    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    try:
        return {
            "dataset_id": dataset_id,
            **detect_outliers(df),
        }

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.get("/api/v1/datasets/{dataset_id}/export")
def export_dataset(
    dataset_id: str,
    export_format: str = Query(
        default="csv",
        pattern="^(csv|xlsx)$",
    ),
):
    """Export the current working dataset as CSV or Excel."""

    df = get_dataset(dataset_id)

    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Upload the file again.",
        )

    buffer = BytesIO()

    if export_format == "csv":
        content = df.to_csv(index=False).encode("utf-8-sig")
        buffer.write(content)
        media_type = "text/csv"
        filename = f"datalens-cleaned-{dataset_id}.csv"
    else:
        df.to_excel(
            buffer,
            index=False,
            engine="openpyxl",
        )
        media_type = (
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        )
        filename = f"datalens-cleaned-{dataset_id}.xlsx"

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
        },
    )
