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
