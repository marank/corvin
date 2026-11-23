from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django import template
from django.template import Context
from django.utils import timezone

register = template.Library()

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "CHF": "CHF",
    "INR": "₹",
    "KRW": "₩",
    "PLN": "zł",
    "RUB": "₽",
    "TRY": "₺",
    "UAH": "₴",
}


def _company(context: Context) -> Any:
    return context.get("company")


def _date_pattern(pattern: str) -> str:
    result = pattern
    for source, target in (
        ("YYYY", "%Y"),
        ("YY", "%y"),
        ("MM", "%m"),
        ("DD", "%d"),
        ("HH", "%H"),
        ("mm", "%M"),
        ("ss", "%S"),
    ):
        result = result.replace(source, target)
    return result


def _number(value: Any, company: Any, minimum: int = 0, maximum: int = 2) -> str:
    try:
        number = Decimal(str(value))
    except InvalidOperation, TypeError, ValueError:
        return "—"
    text = f"{number:,.{maximum}f}"
    integer, _, decimals = text.partition(".")
    while len(decimals) > minimum and decimals.endswith("0"):
        decimals = decimals[:-1]
    decimal_separator = getattr(company, "decimal_separator", ",")
    thousands_separator = getattr(company, "thousands_separator", ".")
    integer = integer.replace(",", "\0").replace("\0", thousands_separator)
    return integer + (decimal_separator + decimals if decimals else "")


@register.simple_tag(takes_context=True)
def display_date(context: Context, value: date | None, pattern: str | None = None) -> str:
    if not value:
        return "—"
    company = _company(context)
    default: str = getattr(company, "date_format", "DD.MM.YYYY")
    fmt = pattern or default
    return value.strftime(_date_pattern(fmt))


@register.simple_tag(takes_context=True)
def display_time(context: Context, value: datetime | None, pattern: str | None = None) -> str:
    if not value:
        return "—"
    company = _company(context)
    default: str = getattr(company, "time_format", "HH:mm")
    fmt = pattern or default
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime(_date_pattern(fmt))


@register.simple_tag(takes_context=True)
def display_number(
    context: Context, value: Any, minimum: int | str = 0, maximum: int | str = 2
) -> str:
    return _number(value, _company(context), int(minimum), int(maximum))


@register.simple_tag(takes_context=True)
def display_money(context: Context, value: Any, currency: str | None = None) -> str:
    company = _company(context)
    default: str = getattr(company, "currency", "EUR")
    code = currency or default
    marker = (
        CURRENCY_SYMBOLS.get(code, code)
        if getattr(company, "currency_display", "symbol") == "symbol"
        else code
    )
    amount = _number(value, company, 2, 2)
    space = " " if getattr(company, "currency_space", True) else ""
    if getattr(company, "currency_position", "after") == "before":
        return f"{marker}{space}{amount}"
    return f"{amount}{space}{marker}"
