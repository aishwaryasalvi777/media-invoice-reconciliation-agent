"""Tests for matching, contract math, cause checks, decisions and the whole pipeline.

Small made-up cases are built from the real Facebook plan lines and contract, with one
thing changed at a time. The answer key is not used here (it is used only in test_scoring.py).
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from invoice_recon.contract_math import flight_days_in_month, payable, planned_views_in_month
from invoice_recon.decide import decide
from invoice_recon.loaders import ReferenceData, load_reference_data
from invoice_recon.matching import facebook_ad_type, match_line
from invoice_recon.models import (
    BillOn,
    Cause,
    ContractTerms,
    Decision,
    DeliveryRecord,
    InvoiceLine,
    PlanLine,
    PlanStatus,
    Result,
)
from invoice_recon.readers import read_facebook_invoices
from invoice_recon.reconcile import reconcile_lines

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample"


@pytest.fixture(scope="module")
def ref() -> ReferenceData:
    return load_reference_data(SAMPLE)


@pytest.fixture(scope="module")
def bills() -> list[InvoiceLine]:
    return read_facebook_invoices(SAMPLE / "invoices")


def make_line(**changes: object) -> InvoiceLine:
    """A clean January bill line for PL-009 (Feed video, PO-5011); change what you need."""
    base = InvoiceLine(
        invoice_number="T-1",
        invoice_line_number=1,
        publisher="Facebook",
        service_month="2026-01",
        purchase_order_number="PO-5011",
        line_description="Pepsi_WildCherry_Spring_2026 | FB Feed Video",
        billed_impressions=4_577_110,
        rate_per_1000_views=Decimal("10.25"),
        amount=Decimal("46915.38"),
        source_file="t.csv",
        source_location="row 2",
    )
    return base.model_copy(update=changes)


def with_contract(ref: ReferenceData, **changes: object) -> ReferenceData:
    contract = ref.contracts["Facebook"].model_copy(update=changes)
    return replace(ref, contracts={**ref.contracts, "Facebook": contract})


def with_delivery(ref: ReferenceData, publisher: int, ad_server: int) -> ReferenceData:
    record = DeliveryRecord(
        plan_line_id="PL-009",
        publisher="Facebook",
        month="2026-01",
        publisher_count=publisher,
        ad_server_count=ad_server,
    )
    return replace(ref, deliveries={**ref.deliveries, ("PL-009", "2026-01"): record})


def one(line: InvoiceLine, ref: ReferenceData) -> Result:
    return reconcile_lines([line], ref)[0]


# ---------- 3.1 matching ----------


def test_all_14_real_lines_match_one_plan_line(
    ref: ReferenceData, bills: list[InvoiceLine]
) -> None:
    ids = [match_line(b, ref).plan_line_id for b in bills]
    assert ids == [
        *("PL-009", "PL-010", "PL-011", "PL-012", "PL-013", "PL-014", "PL-016"),
        *("PL-009", "PL-010", "PL-011", "PL-013", "PL-014", "PL-015", "PL-016"),
    ]


def test_lines_without_a_po_are_matched_by_wording_with_lower_confidence(
    ref: ReferenceData, bills: list[InvoiceLine]
) -> None:
    for line in bills:
        match = match_line(line, ref)
        assert match.confidence == (0.9 if line.purchase_order_number is None else 1.0)


def test_cancelled_line_is_still_matched(ref: ReferenceData, bills: list[InvoiceLine]) -> None:
    assert match_line(bills[8], ref).plan_line_id == "PL-010"
    assert ref.plan_lines["PL-010"].status is PlanStatus.CANCELLED


def test_po_alone_is_not_enough(ref: ReferenceData) -> None:
    """PO-5011 covers 4 plan lines. A bill line whose ad type can't be read isn't matched."""
    line = make_line(line_description="Pepsi_WildCherry_Spring_2026 | Something else")
    match = match_line(line, ref)
    assert match.plan_line_id is None
    assert "can't read" in match.reason


def test_po_and_wording_pointing_to_different_campaigns_is_not_matched(ref: ReferenceData) -> None:
    match = match_line(make_line(purchase_order_number="PO-5012"), ref)
    assert match.plan_line_id is None
    assert "different campaigns" in match.reason


def test_unknown_po_is_not_matched(ref: ReferenceData) -> None:
    match = match_line(make_line(purchase_order_number="PO-9999"), ref)
    assert match.plan_line_id is None
    assert "PO-9999 is not in the media plan" in match.reason


def test_unknown_campaign_without_po_is_not_matched(ref: ReferenceData) -> None:
    line = make_line(
        purchase_order_number=None, line_description="Mystery_Brand_2026 | FB Feed Video"
    )
    assert match_line(line, ref).plan_line_id is None


def test_other_publishers_are_not_matched_yet(ref: ReferenceData) -> None:
    match = match_line(make_line(publisher="Hulu"), ref)
    assert match.plan_line_id is None
    assert "no wording rules for Hulu" in match.reason


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("FB Feed Video", "feed video"),
        ("Facebook Feed video", "feed video"),
        ("FB Feed Image", "feed image"),
        ("In-Stream", "in-stream"),
        ("Facebook In-stream video", "in-stream"),
        ("Marketplace", "marketplace"),
        ("Marketplace image", "marketplace"),
        ("Banner", None),
    ],
)
def test_ad_type_wording(text: str, expected: str | None) -> None:
    assert facebook_ad_type(text) == expected


# ---------- 4.1 contract math ----------


def small_plan(**changes: object) -> PlanLine:
    """9,000 views over 90 days (Jan 1 - Mar 31) at $10 per 1,000 views."""
    base = PlanLine(
        plan_line_id="PL-X",
        purchase_order_number="PO-X",
        publisher="Facebook",
        description="Test - Facebook Feed video",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        planned_impressions=9000,
        price_per_1000_views=Decimal("10"),
        planned_cost=Decimal("90.00"),
        status=PlanStatus.ACTIVE,
    )
    return base.model_copy(update=changes)


def small_delivery(publisher: int, ad_server: int) -> DeliveryRecord:
    return DeliveryRecord(
        plan_line_id="PL-X",
        publisher="Facebook",
        month="2026-01",
        publisher_count=publisher,
        ad_server_count=ad_server,
    )


def contract(**changes: object) -> ContractTerms:
    base = ContractTerms(
        publisher="Facebook",
        agency="GroupM",
        client="Pepsi",
        bill_on=BillOn.PUBLISHER_COUNT,
        allowed_difference_percent=Decimal("10"),
        pay_for_extra_views_up_to_percent=Decimal("0"),
    )
    return base.model_copy(update=changes)


def test_month_plan_is_split_by_flight_days() -> None:
    plan = small_plan()
    assert flight_days_in_month(plan, "2026-01") == 31
    assert planned_views_in_month(plan, "2026-01") == Decimal("3100")  # 9,000 x 31 / 90


def test_pays_publisher_count_when_close_to_ad_server() -> None:
    pay = payable(small_plan(), small_delivery(3000, 2900), contract(), "2026-01")
    assert (pay.count_used, pay.payable_views, pay.expected_amount) == (
        "publisher_count",
        3000,
        Decimal("30.00"),
    )


def test_pays_ad_server_count_when_publisher_is_too_far_above() -> None:
    pay = payable(small_plan(), small_delivery(3000, 2500), contract(), "2026-01")  # 20% above
    assert (pay.count_used, pay.payable_views) == ("ad_server_count", 2500)


def test_exactly_at_the_tolerance_is_still_allowed() -> None:
    pay = payable(small_plan(), small_delivery(2750, 2500), contract(), "2026-01")  # exactly 10%
    assert pay.count_used == "publisher_count"


def test_contract_on_ad_server_always_uses_ad_server() -> None:
    pay = payable(
        small_plan(),
        small_delivery(3000, 2990),
        contract(bill_on=BillOn.AD_SERVER_COUNT),
        "2026-01",
    )
    assert (pay.count_used, pay.payable_views) == ("ad_server_count", 2990)


def test_cap_is_planned_views_when_no_extra_is_paid() -> None:
    pay = payable(small_plan(), small_delivery(3500, 3400), contract(), "2026-01")
    assert (pay.cap_views, pay.payable_views) == (3100, 3100)


def test_cap_allows_extra_views_up_to_the_percent() -> None:
    allow = contract(pay_for_extra_views_up_to_percent=Decimal("10"))
    pay = payable(small_plan(), small_delivery(3500, 3400), allow, "2026-01")
    assert (pay.cap_views, pay.payable_views) == (3410, 3410)


def test_no_flight_days_means_nothing_is_payable() -> None:
    plan = small_plan(
        start_date=date(2026, 2, 1), planned_impressions=5900, planned_cost=Decimal("59.00")
    )
    pay = payable(plan, small_delivery(3000, 2900), contract(), "2026-01")
    assert pay.expected_amount == Decimal("0.00")


def test_missing_delivery_means_nothing_is_payable() -> None:
    pay = payable(small_plan(), None, contract(), "2026-01")
    assert pay.expected_amount == Decimal("0.00")
    assert not pay.delivery_found


def test_cancelled_line_stops_the_day_before_it_was_cancelled() -> None:
    plan = small_plan(status=PlanStatus.CANCELLED, cancelled_effective_date=date(2026, 2, 1))
    assert flight_days_in_month(plan, "2026-01") == 31
    assert flight_days_in_month(plan, "2026-02") == 0


def test_real_over_tolerance_line_expected_amount(ref: ReferenceData) -> None:
    """PL-012 in January: the publisher's count is 18% above the ad server's."""
    pay = payable(
        ref.plan_lines["PL-012"],
        ref.delivery_for("PL-012", "2026-01"),
        ref.contracts["Facebook"],
        "2026-01",
    )
    assert pay.count_used == "ad_server_count"
    assert pay.expected_amount == Decimal("26718.89")  # 2,544,656 views x $10.50 per 1,000


# ---------- 4.2 causes and 4.4 decisions, one change at a time ----------


def test_clean_line_has_no_cause_and_is_approved(ref: ReferenceData) -> None:
    result = one(make_line(), ref)
    assert (result.cause, result.decision) == (Cause.NONE, Decision.APPROVE)
    assert result.difference == 0


def test_no_matching_order_goes_to_a_human(ref: ReferenceData) -> None:
    result = one(make_line(purchase_order_number="PO-9999"), ref)
    assert (result.cause, result.decision) == (Cause.NO_MATCHING_ORDER, Decision.SEND_TO_HUMAN)
    assert result.matched_plan_line_id is None
    assert result.expected_amount == Decimal("0.00")


def test_cancelled_line_billed_is_disputed(ref: ReferenceData, bills: list[InvoiceLine]) -> None:
    result = one(bills[8], ref)
    assert (result.cause, result.decision) == (Cause.CANCELLED_LINE_BILLED, Decision.DISPUTE)
    assert result.expected_amount == Decimal("0.00")
    assert any("PL-010" in e and "cancelled" in e for e in result.evidence)


def test_billing_a_month_with_no_flight_days_is_disputed(ref: ReferenceData) -> None:
    """PL-012 (Marketplace) runs in January only."""
    line = make_line(
        service_month="2026-02",
        purchase_order_number="PO-5011",
        line_description="Pepsi_WildCherry_Spring_2026 | Marketplace",
    )
    result = one(line, ref)
    assert (result.cause, result.decision) == (Cause.OUTSIDE_FLIGHT_DATES, Decision.DISPUTE)


def test_same_line_billed_twice_disputes_only_the_second(ref: ReferenceData) -> None:
    first, second = reconcile_lines([make_line(), make_line(invoice_line_number=2)], ref)
    assert (first.cause, first.decision) == (Cause.NONE, Decision.APPROVE)
    assert (second.cause, second.decision) == (Cause.DUPLICATE_LINE, Decision.DISPUTE)
    assert second.expected_amount == Decimal("0.00")


def test_digits_swapped_in_amount_is_a_math_error(ref: ReferenceData) -> None:
    result = one(make_line(amount=Decimal("46915.83")), ref)
    assert (result.cause, result.decision) == (Cause.MATH_ERROR, Decision.DISPUTE)


def test_different_price_goes_to_a_human(ref: ReferenceData) -> None:
    line = make_line(rate_per_1000_views=Decimal("11.00"), amount=Decimal("50348.21"))
    result = one(line, ref)
    assert (result.cause, result.decision) == (Cause.RATE_MISMATCH, Decision.SEND_TO_HUMAN)


def test_publisher_count_far_above_ad_server_is_pay_less(
    ref: ReferenceData, bills: list[InvoiceLine]
) -> None:
    result = one(bills[3], ref)
    assert (result.cause, result.decision) == (
        Cause.COUNT_MISMATCH_BEYOND_TOLERANCE,
        Decision.PAY_LESS,
    )
    assert (result.invoiced_amount, result.expected_amount) == (
        Decimal("31528.29"),
        Decimal("26718.89"),
    )
    assert result.difference == Decimal("4809.40")


def test_over_delivery_with_no_extra_allowed_is_pay_less(ref: ReferenceData) -> None:
    """Delivered 5,000,000 against 4,700,633 planned; the contract pays no extra."""
    rich = with_delivery(ref, 5_000_000, 4_950_000)
    line = make_line(billed_impressions=5_000_000, amount=Decimal("51250.00"))
    result = one(line, rich)
    assert (result.cause, result.decision) == (Cause.OVER_DELIVERY_BILLED, Decision.PAY_LESS)
    assert result.expected_amount == Decimal("48181.49")  # capped at 4,700,633 views


def test_over_delivery_within_the_contract_cap_is_approved(ref: ReferenceData) -> None:
    contract_with_extra = with_contract(ref, pay_for_extra_views_up_to_percent=Decimal("10"))
    rich = with_delivery(contract_with_extra, 4_900_000, 4_850_000)
    line = make_line(billed_impressions=4_900_000, amount=Decimal("50225.00"))
    result = one(line, rich)
    assert (result.cause, result.decision) == (
        Cause.OVER_DELIVERY_WITHIN_CONTRACT,
        Decision.APPROVE,
    )
    assert result.difference == 0


def test_over_delivery_beyond_the_contract_cap_is_pay_less(ref: ReferenceData) -> None:
    contract_with_extra = with_contract(ref, pay_for_extra_views_up_to_percent=Decimal("10"))
    rich = with_delivery(contract_with_extra, 5_400_000, 5_350_000)
    line = make_line(billed_impressions=5_400_000, amount=Decimal("55350.00"))
    result = one(line, rich)
    assert (result.cause, result.decision) == (
        Cause.OVER_DELIVERY_BEYOND_CONTRACT,
        Decision.PAY_LESS,
    )
    assert result.expected_amount == Decimal("52999.63")  # capped at 5,170,696 views


def test_billing_on_the_wrong_count_is_pay_less(ref: ReferenceData) -> None:
    on_ad_server = with_contract(ref, bill_on=BillOn.AD_SERVER_COUNT)
    result = one(
        make_line(), on_ad_server
    )  # billed the publisher's 4,577,110, not ad server's 4,445,680
    assert (result.cause, result.decision) == (Cause.BILLED_ON_WRONG_COUNT, Decision.PAY_LESS)


def test_a_difference_no_rule_explains_goes_to_a_human(ref: ReferenceData) -> None:
    """Billed below what is owed: not an over-bill, and no rule covers it."""
    result = one(make_line(amount=Decimal("46915.37")), ref)
    # 4,577,110 x $10.25 per 1,000 = 46,915.3775 -> 46,915.38, so a cent less is a math error
    assert result.cause is Cause.MATH_ERROR
    short = make_line(
        billed_impressions=4_000_000, amount=Decimal("41000.00")
    )  # consistent, but low
    result = one(short, ref)
    assert (result.cause, result.decision) == (Cause.UNEXPLAINED_DIFFERENCE, Decision.SEND_TO_HUMAN)


def test_guards_never_approve_a_wrong_amount() -> None:
    assert decide(Cause.NONE, Decimal("10.00"), Decimal("10.00")) is Decision.APPROVE
    assert decide(Cause.NONE, Decimal("11.00"), Decimal("10.00")) is Decision.SEND_TO_HUMAN
    assert (
        decide(Cause.OVER_DELIVERY_BILLED, Decimal("9.00"), Decimal("10.00"))
        is Decision.SEND_TO_HUMAN
    )
    assert (
        decide(Cause.OVER_DELIVERY_BILLED, Decimal("11.00"), Decimal("10.00")) is Decision.PAY_LESS
    )


def test_every_cause_has_a_decision() -> None:
    for cause in Cause:
        assert isinstance(decide(cause, Decimal("1.00"), Decimal("1.00")), Decision)


# ---------- the whole pipeline on the real bills ----------


def test_real_facebook_bills_end_to_end(ref: ReferenceData, bills: list[InvoiceLine]) -> None:
    results = reconcile_lines(bills, ref)
    assert len(results) == 14
    odd = {
        (r.invoice_number, r.invoice_line_number): (r.cause, r.decision)
        for r in results
        if r.decision is not Decision.APPROVE
    }
    assert odd == {
        ("FBADS-26-01-7731", 4): (Cause.COUNT_MISMATCH_BEYOND_TOLERANCE, Decision.PAY_LESS),
        ("FBADS-26-02-8094", 2): (Cause.CANCELLED_LINE_BILLED, Decision.DISPUTE),
    }
    for r in results:
        if r.decision is Decision.APPROVE:
            assert r.difference == 0
        if r.cause is not Cause.NONE:
            assert r.evidence  # every flagged line carries evidence
