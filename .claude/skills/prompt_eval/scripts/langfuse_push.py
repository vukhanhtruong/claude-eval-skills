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
