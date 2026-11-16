"""Tests for the 5 forms: good records are accepted, bad ones are stopped at the door."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from invoice_recon.models import (
    Cause,
    ContractTerms,
    Decision,
    DeliveryRecord,
    InvoiceLine,
    PlanLine,
    Result,
)

DATA = Path(__file__).resolve().parent.parent / "data" / "sample"

# Small-number examples: 100 views at $1 each ($1,000 per 1,000 views) = $100.
GOOD_PLAN: dict[str, Any] = {
    "plan_line_id": "PL-001",
    "purchase_order_number": "PO-5000",
    "publisher": "Instagram",
    "description": "Pepsi Zero Sugar Big Game - Instagram Stories video",
    "start_date": "2026-01-01",
    "end_date": "2026-03-31",
    "planned_impressions": 100,
    "price_per_1000_views": Decimal("1000"),
    "planned_cost": Decimal("100.00"),
    "status": "active",
}
GOOD_DELIVERY: dict[str, Any] = {
    "plan_line_id": "PL-001",
    "publisher": "Instagram",
    "month": "2026-01",
    "publisher_count": 107,
    "ad_server_count": 105,
}
GOOD_INVOICE: dict[str, Any] = {
    "invoice_number": "IG-INV-2026-0142",
    "invoice_line_number": 1,
    "publisher": "Instagram",
    "service_month": "2026-01",
    "purchase_order_number": "PO-5000",
    "line_description": "PZS | IG Stories Vid | JAN26",
    "billed_impressions": 107,
    "rate_per_1000_views": Decimal("1000"),
    "amount": Decimal("107.00"),
    "source_file": "invoices/instagram_2026-01.pdf",
    "source_location": "page 1, row 1",
}
GOOD_CONTRACT: dict[str, Any] = {
    "publisher": "Instagram",
    "agency": "GroupM",
    "client": "Pepsi",
    "bill_on": "publisher_count",
    "allowed_difference_percent": 10,
    "pay_for_extra_views_up_to_percent": 0,
}
GOOD_RESULT: dict[str, Any] = {
    "invoice_number": "IG-INV-2026-0142",
    "invoice_line_number": 1,
    "matched_plan_line_id": "PL-001",
    "match_confidence": 1.0,
    "expected_amount": Decimal("100.00"),
    "invoiced_amount": Decimal("107.00"),
    "cause": "over_delivery_billed",
    "evidence": ("delivery: 107 views delivered, 100 ordered",),
    "decision": "pay_less",
}


def changed(record: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return {**record, **changes}


# ---------- good records are accepted ----------


@pytest.mark.parametrize(
    ("form", "record"),
    [
        (PlanLine, GOOD_PLAN),
        (DeliveryRecord, GOOD_DELIVERY),
        (InvoiceLine, GOOD_INVOICE),
        (ContractTerms, GOOD_CONTRACT),
        (Result, GOOD_RESULT),
    ],
)
def test_a_good_record_is_accepted(form: type[Any], record: dict[str, Any]) -> None:
    form(**record)


def test_all_five_real_contracts_fit_the_form() -> None:
    contracts = json.loads((DATA / "contracts.json").read_text())

    assert len([ContractTerms(**c) for c in contracts]) == 5


# ---------- bad records are stopped at the door ----------


@pytest.mark.parametrize(
    ("form", "record", "why"),
    [
        (PlanLine, changed(GOOD_PLAN, planned_impressions=-100), "views can't be negative"),
        (PlanLine, changed(GOOD_PLAN, end_date="2025-12-31"), "end is before start"),
        (PlanLine, changed(GOOD_PLAN, status="maybe"), "status not in the fixed list"),
        (PlanLine, changed(GOOD_PLAN, status="cancelled"), "cancelled without a date"),
        (PlanLine, changed(GOOD_PLAN, planned_cost=Decimal("99.00")), "cost != views x price"),
        (PlanLine, changed(GOOD_PLAN, planned_cost=100.0), "money given as a float"),
        (PlanLine, changed(GOOD_PLAN, colour="blue"), "unknown extra field"),
        (DeliveryRecord, changed(GOOD_DELIVERY, month="2026-13"), "month 13 doesn't exist"),
        (InvoiceLine, changed(GOOD_INVOICE, amount=Decimal("107.001")), "fraction of a cent"),
        (InvoiceLine, changed(GOOD_INVOICE, line_description="  "), "empty description"),
        (ContractTerms, changed(GOOD_CONTRACT, bill_on="whoever"), "bill_on not in the list"),
        (Result, changed(GOOD_RESULT, decision="pay later"), "decision not in the list"),
        (Result, changed(GOOD_RESULT, cause="none"), "a $7 difference with cause 'none'"),
        (Result, changed(GOOD_RESULT, match_confidence=1.5), "confidence above 100%"),
    ],
)
def test_a_bad_record_is_rejected(form: type[Any], record: dict[str, Any], why: str) -> None:
    with pytest.raises(ValidationError):
        form(**record)


# ---------- other rules ----------


def test_a_record_cant_be_changed_after_creation() -> None:
    plan = PlanLine(**GOOD_PLAN)

    with pytest.raises(ValidationError):
        plan.planned_cost = Decimal("1.00")  # type: ignore[misc]


def test_decimal_money_is_exact_where_float_is_not() -> None:
    assert 0.1 + 0.2 != 0.3
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")


def test_an_invoice_with_wrong_math_is_still_accepted() -> None:
    """Bills can be wrong. The form keeps them, and the cause checks find the error."""
    line = InvoiceLine(**changed(GOOD_INVOICE, amount=Decimal("701.00")))

    assert line.amount == Decimal("701.00")


def test_a_missing_purchase_order_number_is_allowed() -> None:
    line = InvoiceLine(**changed(GOOD_INVOICE, purchase_order_number=None))

    assert line.purchase_order_number is None


def test_result_works_out_the_difference() -> None:
    result = Result(**GOOD_RESULT)

    assert result.difference == Decimal("7.00")
    assert result.cause is Cause.OVER_DELIVERY_BILLED
    assert result.decision is Decision.PAY_LESS
