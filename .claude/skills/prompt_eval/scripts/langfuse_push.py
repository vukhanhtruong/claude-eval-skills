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


def push_run_case(
    client,
    dataset_name: str,
    item_index: int,
    run_id: str,
    version: str,
    prompt_name: str,
    rendered_prompt: str,
    output: str,
    score: int,
    reasoning: str,
    model: str,
    latency_ms: int,
) -> None:
    """Create a span + score for one evaluated case and link to its dataset run.

    Uses the v4 Langfuse SDK pattern:
      1. ``start_as_current_observation`` opens a span (trace) with the case's
         input/output and metadata.
      2. ``api.dataset_run_items.create`` links the trace to a dataset run;
         this also lazily creates the dataset run on first call by ``run_name``.
      3. ``create_score`` attaches the GEval score to the trace.

    The 1-10 integer score is normalized to 0.0-1.0 (Langfuse convention);
    the raw int is preserved in span metadata under ``raw_score``.
    """
    item_id = f"{prompt_name}-{run_id}-item-{item_index}"

    # Look up the dataset item to get its server-assigned id. (We use the
    # deterministic id we set when the item was created via push_dataset.)
    dataset = client.get_dataset(dataset_name)
    item = next((i for i in dataset.items if i.id == item_id), None)
    if item is None:
        raise ValueError(
            f"Dataset item {item_id} not found in {dataset_name}"
        )

    span_metadata = {
        "model": model,
        "latency_ms": latency_ms,
        "version": version,
        "raw_score": score,
    }

    with client.start_as_current_observation(
        name=f"{prompt_name}/{run_id}/{version}/case-{item_index}",
        as_type="span",
        input=rendered_prompt,
        output=output,
        metadata=span_metadata,
    ) as span:
        trace_id = span.trace_id
        observation_id = span.id

    # Link the trace to a dataset run (creates the run on first call).
    client.api.dataset_run_items.create(
        run_name=version,
        run_description=f"test_model={model}",
        metadata={
            "prompt_name": prompt_name,
            "run_id": run_id,
            "version": version,
            "test_model": model,
        },
        dataset_item_id=item.id,
        trace_id=trace_id,
        observation_id=observation_id,
    )

    # Attach the GEval score to the trace.
    client.create_score(
        name="Task Quality",
        value=score / 10.0,
        trace_id=trace_id,
        comment=reasoning,
        data_type="NUMERIC",
    )
