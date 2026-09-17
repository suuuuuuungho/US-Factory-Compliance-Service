"""Convert raw ECHO CSV values into typed pipeline values."""

from datetime import datetime, date
from decimal import Decimal, InvalidOperation


def is_missing(text: str) -> bool:
    """Return whether an ECHO missing-value marker was supplied."""

    return text.strip() in ("", "N/A", "-9999")


def parse_date(text: str) -> date | None:
    """Parse ECHO's accepted U.S. date formats, or return ``None``."""

    value = text.strip()
    for fmt in ("%m-%d-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def parse_amount(text: str) -> Decimal | None:
    """Parse a numeric ECHO amount while retaining exact decimal precision."""

    if is_missing(text):
        return None
    try:
        return Decimal(text.strip())
    except InvalidOperation as error:
        raise ValueError(f"Invalid ECHO amount: {text!r}") from error


def split_codes(text: str) -> list[str]:
    """Split whitespace-separated ECHO codes, omitting missing values."""

    return [] if is_missing(text) else text.split()
