
import pandas as pd


_original_datasets: dict[str, pd.DataFrame] = {}
_working_datasets: dict[str, pd.DataFrame] = {}


def store_dataset(df: pd.DataFrame) -> str:
    """Store an original dataset and create its working copy."""
    from uuid import uuid4

    dataset_id = str(uuid4())

    _original_datasets[dataset_id] = df.copy(deep=True)
    _working_datasets[dataset_id] = df.copy(deep=True)

    return dataset_id


def get_dataset(dataset_id: str) -> pd.DataFrame | None:
    """Retrieve the current working dataset."""
    return _working_datasets.get(dataset_id)


def get_original_dataset(dataset_id: str) -> pd.DataFrame | None:
    """Retrieve the unchanged original dataset."""
    return _original_datasets.get(dataset_id)


def update_working_dataset(
    dataset_id: str,
    df: pd.DataFrame,
) -> None:
    """Replace the working dataset with a cleaned copy."""
    if dataset_id not in _working_datasets:
        raise KeyError(f"Dataset not found: {dataset_id}")

    _working_datasets[dataset_id] = df.copy(deep=True)
