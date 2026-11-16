"""Exact money rules, used everywhere money is calculated.

1. Money is always a Decimal. A float raises an error (0.1 + 0.2 isn't 0.3 in float).
2. Every amount is rounded to whole cents with "round half up": a half cent goes away
   from zero. Example: $10.125 -> $10.13, and -$10.125 -> -$10.13.
3. Each line is rounded first; totals add lines that are already whole cents.

Small example: 100 views at $1 each ($1,000 per 1,000 views) = $100.00.
Real example: 1,475,215 views x $8.25 per 1,000 = $12,170.52375 -> $12,170.52.
"""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def _require_decimal(value: object, name: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal, not {type(value).__name__}")


def to_cents(amount: Decimal) -> Decimal:
    """Round to whole cents, half up. Example: Decimal("12170.52375") -> Decimal("12170.52")."""
    _require_decimal(amount, "amount")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def cost_of_views(views: int, price_per_1000_views: Decimal) -> Decimal:
    """What a number of views costs at a price per 1,000 views, rounded to cents."""
    if isinstance(views, bool) or not isinstance(views, int):
        raise TypeError(f"views must be a whole number, not {type(views).__name__}")
    _require_decimal(price_per_1000_views, "price_per_1000_views")
    return to_cents(Decimal(views) * price_per_1000_views / 1000)


def total(amounts: Iterable[Decimal]) -> Decimal:
    """Add line amounts that are already rounded to whole cents.

    Refuses an unrounded amount, so a total can never hide rounding that should
    have happened line by line."""
    result = Decimal("0.00")
    for amount in amounts:
        if to_cents(amount) != amount:
            raise ValueError(f"round each line to cents before adding: got {amount}")
        result += amount
    return result
