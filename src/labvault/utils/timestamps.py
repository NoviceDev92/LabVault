from datetime import datetime, timezone

def get_current_timestamp() -> str:
    """Return the current time as an ISO 8601 string in UTC."""
    return datetime.now(timezone.utc).isoformat()
