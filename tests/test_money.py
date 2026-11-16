"""Tests for the money rules: Decimal only, whole cents, round half up, per line."""

from decimal import Decimal

import pytest

from invoice_recon.loaders import load_reference_data
from invoice_recon.money import cost_of_views, to_cents, total

D = Decimal


@pytest.mark.parametrize(
    ("exact", "rounded"),
    [
        (D("12170.52375"), D("12170.52")),  # less than half a cent: down
        (D("10.125"), D("10.13")),  # exactly half: up
        (D("10.135"), D("10.14")),
        (D("10.124999"), D("10.12")),
        (D("-10.125"), D("-10.13")),  # half goes away from zero
        (D("100"), D("100.00")),
    ],
)
def test_round_to_cents_half_up(exact: Decimal, rounded: Decimal) -> None:
    assert to_cents(exact) == rounded
    assert str(to_cents(exact)) == str(rounded)  # always exactly 2 decimal places


def test_half_up_differs_from_pythons_default_bankers_rounding() -> None:
    assert to_cents(D("10.125")) == D("10.13")
    assert D("10.125").quantize(D("0.01")) == D("10.12")  # banker's: half to even


def test_float_rounding_gets_some_amounts_wrong() -> None:
    """1.005 can't be stored exactly as a float (it is really 1.00499999...)."""
    assert round(1.005, 2) == 1.0  # float: wrong
    assert to_cents(D("1.005")) == D("1.01")  # Decimal: right


def test_cost_of_views() -> None:
    assert cost_of_views(100, D("1000")) == D("100.00")  # 100 views at $1 each
    assert cost_of_views(1_475_215, D("8.25")) == D("12170.52")  # PL-001, January
    assert cost_of_views(0, D("8.25")) == D("0.00")


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: to_cents(0.1), "amount must be a Decimal"),  # type: ignore[arg-type]
        (lambda: cost_of_views(100, 8.25), "must be a Decimal"),  # type: ignore[arg-type]
        (lambda: cost_of_views(100.0, D("8.25")), "whole number"),  # type: ignore[arg-type]
    ],
)
def test_floats_are_refused(call: object, message: str) -> None:
    with pytest.raises(TypeError, match=message):
        call()  # type: ignore[operator]


def test_each_line_is_rounded_before_adding() -> None:
    """3 lines of 1 view at $5 per 1,000 = $0.005 each.
    Per line: $0.01 + $0.01 + $0.01 = $0.03. Rounding only the total would give $0.02."""
    lines = [cost_of_views(1, D("5")) for _ in range(3)]

    assert lines == [D("0.01")] * 3
    assert total(lines) == D("0.03")


def test_total_refuses_an_unrounded_line() -> None:
    with pytest.raises(ValueError, match="round each line"):
        total([D("0.01"), D("0.005")])


def test_total_of_nothing_is_zero() -> None:
    assert total([]) == D("0.00")


def test_every_real_plan_cost_matches_the_money_rule() -> None:
    plans = load_reference_data().plan_lines.values()

    for p in plans:
        assert p.planned_cost == cost_of_views(p.planned_impressions, p.price_per_1000_views)
