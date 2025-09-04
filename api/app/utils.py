"""Utility functions for the application."""

from datetime import datetime, date, timezone
from typing import Optional, Union


def format_datetime(dt: Optional[Union[datetime, date]]) -> Optional[str]:
    """
    Format datetime or date to ISO string with consistent timezone format.

    Always returns UTC datetimes with 'Z' suffix for consistency across environments.
    For date objects, returns the ISO date string without timezone.
    Returns None if input is None.
    """
    if dt is None:
        return None

    # Handle date objects (no timezone info)
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()

    # Handle datetime objects
    iso_string = dt.isoformat()

    # If it already ends with 'Z', return as-is
    if iso_string.endswith("Z"):
        return iso_string

    # If it ends with '+00:00', replace with 'Z'
    if iso_string.endswith("+00:00"):
        return iso_string[:-6] + "Z"

    # If it's a naive datetime (no timezone info), assume UTC and add 'Z'
    if dt.tzinfo is None:
        return iso_string + "Z"

    # For other timezone formats, convert to UTC first
    if dt.tzinfo is not None:
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.isoformat().replace("+00:00", "Z")

    return iso_string
