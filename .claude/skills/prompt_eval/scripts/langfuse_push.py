"""Optional Langfuse push for datasets and evaluation runs.

All Langfuse SDK use lives in this module so the rest of the skill stays
decoupled. Functions return None / False on missing config; callers check.
"""
import os
from typing import Optional

from langfuse import Langfuse


REQUIRED_ENV = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")


def is_configured() -> bool:
    """Return True iff all three Langfuse env vars are present and non-empty."""
    return all(os.environ.get(k) for k in REQUIRED_ENV)


def get_client() -> Optional[Langfuse]:
    """Return a Langfuse client if env vars are set, else None.

    The SDK auto-reads LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
    from the environment, so we don't pass them explicitly.
    """
    if not is_configured():
        return None
    return Langfuse()


def _dataset_exists(client, name: str) -> bool:
    """Return True if the named dataset exists in Langfuse.

    The SDK doesn't expose a `head`-style check; we treat any exception from
    `get_dataset` as "not found." Matches the SDK's NotFoundError convention.
    """
    try:
        client.get_dataset(name)
        return True
    except Exception:
        return False


def push_dataset(
    client,
    prompt_name: str,
    run_id: str,
    dataset: list,
    task_description: str,
    inputs_spec: dict,
) -> str:
    """Create-or-upsert the Langfuse dataset and its items.

    Uses deterministic item IDs ``<prompt_name>-<run_id>-item-<index>`` so
    re-pushes are idempotent and prior dataset runs in Langfuse retain their
    item links.
    """
    name = f"{prompt_name}-{run_id}"

    if _dataset_exists(client, name):
        print(f"⚠ Dataset {name} exists in Langfuse — upserting items from local")
    else:
        client.create_dataset(
            name=name,
            description=task_description,
            metadata={
                "prompt_name": prompt_name,
                "run_id": run_id,
                "dataset_size": len(dataset),
                "inputs_spec": inputs_spec,
            },
        )

    for i, case in enumerate(dataset):
        client.create_dataset_item(
            dataset_name=name,
            id=f"{prompt_name}-{run_id}-item-{i}",
            input=case["prompt_inputs"],
            expected_output=case["solution_criteria"],
            metadata={
                "scenario": case.get("scenario"),
                "task_description": case.get("task_description"),
            },
        )

    return name
