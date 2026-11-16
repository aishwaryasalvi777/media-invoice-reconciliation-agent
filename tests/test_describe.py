"""Tests for the blank-form descriptions shown in the notebook."""

import pytest

from invoice_recon.describe import blank_form
from invoice_recon.models import (
    ContractTerms,
    DeliveryRecord,
    Form,
    InvoiceLine,
    PlanLine,
    Result,
)

ALL_FORMS = [PlanLine, DeliveryRecord, InvoiceLine, ContractTerms, Result]


def row(form: type[Form], field: str) -> dict[str, str]:
    return next(r for r in blank_form(form) if r["field"] == field)


def test_one_row_per_field() -> None:
    assert [r["field"] for r in blank_form(PlanLine)] == list(PlanLine.model_fields)


def test_kinds_and_rules_are_read_from_the_form() -> None:
    assert row(PlanLine, "planned_impressions")["rules"] == ">= 0"
    assert "never a float" in row(PlanLine, "planned_cost")["rules"]
    assert row(PlanLine, "status")["kind of value"] == "one of: active, cancelled"
    assert row(DeliveryRecord, "month")["rules"] == "month as YYYY-MM"


def test_optional_fields_are_marked() -> None:
    assert row(InvoiceLine, "purchase_order_number")["required"] == "no"
    assert row(Result, "matched_plan_line_id")["kind of value"] == "text"
    assert row(Result, "matched_plan_line_id")["required"] == "no"


@pytest.mark.parametrize("form", ALL_FORMS, ids=[f.__name__ for f in ALL_FORMS])
def test_every_field_has_a_plain_words_meaning(form: type[Form]) -> None:
    missing = [r["field"] for r in blank_form(form) if not r["meaning"]]

    assert missing == [], f"add a one-line note under these fields in models.py: {missing}"
