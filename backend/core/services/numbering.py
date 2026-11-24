import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from django.template import Variable, VariableDoesNotExist
from django.utils import timezone

from core.models import (
    Customer,
    Invoice,
    NumberSequence,
    OnSiteVisit,
    Project,
    SupportContract,
    Task,
)
from core.models.base import OwnedModel
from core.models.company_settings import NUMBERING_SCHEMES

TOKEN_PATTERN = re.compile(r"\{([^{}]+)\}")
# The model whose `number` each numbering scheme fills.
NUMBERED_MODELS: dict[str, type[OwnedModel]] = {
    "customer": Customer,
    "project": Project,
    "invoice": Invoice,
    "contract": SupportContract,
    "visit": OnSiteVisit,
    "task": Task,
}


@dataclass
class RenderContext:
    counter: int
    today: date
    values: dict[str, Any]


def _width(param: str | None, default: int) -> int:
    try:
        return max(1, int(param)) if param else default
    except ValueError:
        return default


def _counter(param: str | None, ctx: RenderContext) -> str:
    return f"{ctx.counter:0{_width(param, 1)}d}"


def _year(param: str | None, ctx: RenderContext) -> str:
    value = str(ctx.today.year)
    digits = _width(param, 4)
    return value[-digits:].zfill(digits)


def _month(param: str | None, ctx: RenderContext) -> str:
    return f"{ctx.today.month:0{_width(param, 2)}d}"


def _day(param: str | None, ctx: RenderContext) -> str:
    return f"{ctx.today.day:0{_width(param, 2)}d}"


Resolver = Callable[[str | None, RenderContext], str]
RESOLVERS: dict[str, Resolver] = {
    "counter": _counter,
    "year": _year,
    "month": _month,
    "day": _day,
}


def render_number(
    format_string: str,
    counter: int,
    values: dict[str, Any] | None = None,
    today: date | None = None,
) -> str:
    ctx = RenderContext(counter, today or timezone.localdate(), values or {})

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        name, separator, param = token.partition(":")
        param = param if separator else None
        resolver = RESOLVERS.get(name)
        if resolver:
            return resolver(param, ctx)
        try:
            value = Variable(name).resolve(ctx.values)
        except VariableDoesNotExist, AttributeError, KeyError, TypeError:
            return ""
        if value is None:
            return ""
        if param:
            try:
                return format(value, param)
            except TypeError, ValueError:
                return str(value)
        return str(value)

    return TOKEN_PATTERN.sub(replace, format_string)


def get_scheme(owner: User, entity: str) -> dict[str, Any]:
    default = NUMBERING_SCHEMES[entity]
    company = getattr(owner, "company_settings", None)
    configured = (company.numbering_schemes or {}).get(entity, {}) if company else {}
    return {**default, **configured}


def normalize_scope(scope: Any) -> list[str]:
    legacy = {
        "global": [],
        "year": ["year"],
        "customer": ["customer"],
        "customer_year": ["customer", "year"],
        "project": ["project"],
        "project_year": ["project", "year"],
    }
    if isinstance(scope, str):
        return legacy.get(scope, [])
    if isinstance(scope, list):
        return [value for value in ("customer", "project", "year") if value in scope]
    return []


def _scope_key(scope: Any, values: dict[str, Any], today: date) -> str:
    dimensions = normalize_scope(scope)
    if dimensions == ["year"]:
        return str(today.year)
    parts = []
    for dimension in dimensions:
        if dimension == "year":
            parts.append(f"year:{today.year}")
            continue
        obj = values.get(dimension)
        value = obj.pk if obj and getattr(obj, "pk", None) else "missing"
        parts.append(f"{dimension}:{value}")
    return ":".join(parts) or "global"


def _is_taken(owner: User, entity: str, number: str) -> bool:
    manager = NUMBERED_MODELS[entity]._default_manager
    return manager.filter(**{"owner": owner, "number": number}).exists()


def _next_free(
    owner: User,
    entity: str,
    format_string: str,
    sequence: NumberSequence,
    values: dict[str, Any],
    today: date,
) -> str:
    """Advance the counter past numbers already given by hand."""
    previous: str | None = None
    while True:
        sequence.last_number += 1
        result = render_number(format_string, sequence.last_number, values, today)
        # A format without {counter} renders the same number every time; skipping cannot help.
        if result == previous or not _is_taken(owner, entity, result):
            return result
        previous = result


def next_number(owner: User, entity: str, values: dict[str, Any] | None = None) -> str:
    values = values or {}
    scheme = get_scheme(owner, entity)
    today = timezone.localdate()
    start = max(1, int(scheme.get("start", 1)))
    scope_key = _scope_key(scheme.get("scope", "global"), values, today)
    with transaction.atomic():
        sequence, _ = NumberSequence.objects.select_for_update().get_or_create(
            owner=owner,
            entity=entity,
            scope_key=scope_key,
            defaults={"last_number": start - 1},
        )
        result = _next_free(owner, entity, scheme["format"], sequence, values, today)
        if len(result) > 50:
            raise ValueError(f"Generated {entity} number exceeds 50 characters.")
        sequence.save(update_fields=["last_number"])
        return result


def preview_number(
    format_string: str,
    start: int,
    values: dict[str, Any] | None = None,
) -> str:
    return render_number(format_string, max(1, start), values)
