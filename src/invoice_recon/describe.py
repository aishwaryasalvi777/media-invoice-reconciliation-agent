"""Describe a form as a "blank form": one row per field with its kind of value and rules.

Built from the forms in models.py themselves, so the description can never go out
of date. Used by the walkthrough notebook to show each blank form.
"""

import types
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Union, get_args, get_origin

from annotated_types import Ge, Le
from pydantic.functional_validators import BeforeValidator

from invoice_recon.models import Form, _refuse_float

_KINDS: dict[Any, str] = {
    str: "text",
    int: "whole number",
    float: "number",
    Decimal: "exact decimal",
    date: "date",
}


def _unwrap(annotation: Any) -> tuple[Any, bool, list[Any]]:
    """Strip "or nothing" (optional) and attached rules off a field's type.
    Returns the bare type, whether it is optional, and the rules found on the way."""
    optional = False
    rules: list[Any] = []
    if get_origin(annotation) in (Union, types.UnionType):
        parts = [a for a in get_args(annotation) if a is not type(None)]
        optional = len(parts) < len(get_args(annotation))
        annotation = parts[0]
    if get_origin(annotation) is Annotated:
        annotation, *rules = get_args(annotation)
    return annotation, optional, rules


def _kind(annotation: Any) -> str:
    """A plain-words name for a kind of value."""
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return "one of: " + ", ".join(str(m.value) for m in annotation)
    if get_origin(annotation) is tuple:
        return "list of text"
    return _KINDS.get(annotation, getattr(annotation, "__name__", str(annotation)))


def _rules(metadata: list[Any]) -> list[str]:
    rules = []
    for item in metadata:
        if isinstance(item, Ge):
            rules.append(f">= {item.ge}")
        elif isinstance(item, Le):
            rules.append(f"<= {item.le}")
        elif isinstance(item, BeforeValidator) and item.func is _refuse_float:
            rules.append("never a float")
        if getattr(item, "decimal_places", None) is not None:
            rules.append(f"at most {item.decimal_places} decimal places")
        if getattr(item, "pattern", None) == r"^\d{4}-(0[1-9]|1[0-2])$":
            rules.append("month as YYYY-MM")
        if getattr(item, "min_length", None) == 1:
            rules.append("can't be empty")
    return rules


def blank_form(form: type[Form]) -> list[dict[str, str]]:
    """One row per field: name, kind of value, required or optional, rules, meaning."""
    rows = []
    for name, field in form.model_fields.items():
        bare, optional, inner_rules = _unwrap(field.annotation)
        required = field.is_required() and not optional
        rows.append(
            {
                "field": name,
                "kind of value": _kind(bare),
                "required": "yes" if required else "no",
                "rules": ", ".join(_rules([*field.metadata, *inner_rules])) or "-",
                "meaning": (field.description or "").replace("\n", " "),
            }
        )
    return rows
