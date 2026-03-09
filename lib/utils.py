def format_minutes_short(minutes: int) -> str:
    """Format minutes to a human-readable string like 'Xh Ym'."""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"

def format_minutes_long(minutes: int) -> str:
    """Format minutes to a human-readable string like '06 hours 17 minutes'."""
    hours = minutes // 60
    mins = minutes % 60
    # Use zero padding for hours as in the example '06 hours'
    return f"{hours:02} hours {mins:02} minutes"
