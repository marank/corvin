from decimal import Decimal, InvalidOperation

from django import template
from django.utils import timezone

register = template.Library()

CURRENCY_SYMBOLS = {
    "EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CNY": "¥",
    "CHF": "CHF", "INR": "₹", "KRW": "₩", "PLN": "zł", "RUB": "₽",
    "TRY": "₺", "UAH": "₴",
}


def _company(context):
    return context.get("company")


def _date_pattern(pattern):
    result = pattern
    for source, target in (
        ("YYYY", "%Y"), ("YY", "%y"), ("MM", "%m"), ("DD", "%d"),
        ("HH", "%H"), ("mm", "%M"), ("ss", "%S"),
    ):
        result = result.replace(source, target)
    return result


def _number(value, company, minimum=0, maximum=2):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
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
def display_date(context, value, pattern=None):
    if not value:
        return "—"
    company = _company(context)
    pattern = pattern or getattr(company, "date_format", "DD.MM.YYYY")
    return value.strftime(_date_pattern(pattern))


@register.simple_tag(takes_context=True)
def display_time(context, value, pattern=None):
    if not value:
        return "—"
    company = _company(context)
    pattern = pattern or getattr(company, "time_format", "HH:mm")
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime(_date_pattern(pattern))


@register.simple_tag(takes_context=True)
def display_number(context, value, minimum=0, maximum=2):
    return _number(value, _company(context), int(minimum), int(maximum))


@register.simple_tag(takes_context=True)
def display_money(context, value, currency=None):
    company = _company(context)
    code = currency or getattr(company, "currency", "EUR")
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
