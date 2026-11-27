import re
from datetime import date


def format_date(d: date, pattern: str) -> str:
    """Render a date with the company's Day.js-style pattern (DD, MM, YYYY, ...)."""
    tokens = {
        "YYYY": f"{d.year:04d}",
        "YY": f"{d.year % 100:02d}",
        "MM": f"{d.month:02d}",
        "DD": f"{d.day:02d}",
        "M": str(d.month),
        "D": str(d.day),
    }
    return re.sub(r"YYYY|YY|MM|DD|M|D", lambda m: tokens[m.group()], pattern)
