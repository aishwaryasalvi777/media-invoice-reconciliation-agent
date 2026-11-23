"""Step 4.2: find the cause when a bill line differs from what should be paid.

One small rule check per cause, tried in a fixed order. The first check that fires wins,
and it returns evidence: short facts that each name their source, so a person can verify
the answer. If the amount is wrong but no check fires, the cause is
"unexplained_difference", and the line goes to a human (see D-038).

Order (most basic problem first):
 1 no_matching_order            no plan line fits
 2 cancelled_line_billed        the plan line was cancelled before this month
 3 outside_flight_dates         the ad wasn't scheduled to run this month
 4 duplicate_line               the same plan line and month was billed earlier
 5 math_error                   the bill's own views x price doesn't equal its amount
 6 rate_mismatch                the bill's price differs from the plan's price
 7 billed_on_wrong_count        billed on the other count than the contract names
 8 count_mismatch_beyond_tolerance  the publisher's count is too far above the ad server's
 9 over_delivery_*              more views than planned: billed, within or beyond the contract
10 none                         the amount is what should be paid
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from invoice_recon.contract_math import Payable, flight_days_in_month, month_bounds
from invoice_recon.matching import Match
from invoice_recon.models import BillOn, Cause, ContractTerms, InvoiceLine, PlanLine, PlanStatus
from invoice_recon.money import cost_of_views


@dataclass(frozen=True)
class LineContext:
    """Everything a cause check may look at for one bill line."""

    line: InvoiceLine
    match: Match
    plan: PlanLine | None
    pay: Payable | None
    contract: ContractTerms | None
    earlier_duplicate: InvoiceLine | None
    """The earlier bill line for the same plan line and month, if there is one."""


Evidence = tuple[str, ...]
Check = Callable[[LineContext], Evidence | None]


def _where(line: InvoiceLine) -> str:
    return f"{line.source_file} {line.source_location}"


def check_no_matching_order(c: LineContext) -> Evidence | None:
    if c.plan is not None:
        return None
    return (f"{_where(c.line)}: {c.match.reason}",)


def check_cancelled_line_billed(c: LineContext) -> Evidence | None:
    plan = c.plan
    if (
        plan is None
        or plan.status is not PlanStatus.CANCELLED
        or plan.cancelled_effective_date is None
    ):
        return None
    first_day, _ = month_bounds(c.line.service_month)
    if plan.cancelled_effective_date > first_day:
        return None
    return (
        f"media_plan.xlsx {plan.plan_line_id}: cancelled from {plan.cancelled_effective_date}",
        f"{_where(c.line)}: bills {c.line.service_month} (${c.line.amount})",
    )


def check_outside_flight_dates(c: LineContext) -> Evidence | None:
    plan = c.plan
    if plan is None or flight_days_in_month(plan, c.line.service_month) > 0:
        return None
    return (
        f"media_plan.xlsx {plan.plan_line_id}: runs {plan.start_date} to {plan.end_date}",
        f"{_where(c.line)}: bills {c.line.service_month}, a month with no flight days",
    )


def check_duplicate_line(c: LineContext) -> Evidence | None:
    first = c.earlier_duplicate
    if first is None:
        return None
    return (
        f"{_where(c.line)}: same plan line and month ({c.match.plan_line_id}, "
        f"{c.line.service_month}) as {_where(first)}",
    )


def check_math_error(c: LineContext) -> Evidence | None:
    line = c.line
    correct = cost_of_views(line.billed_impressions, line.rate_per_1000_views)
    if line.amount == correct:
        return None
    return (
        f"{_where(line)}: {line.billed_impressions:,} views x ${line.rate_per_1000_views} "
        f"per 1,000 = ${correct}, but the bill says ${line.amount}",
    )


def check_rate_mismatch(c: LineContext) -> Evidence | None:
    plan = c.plan
    if plan is None or c.line.rate_per_1000_views == plan.price_per_1000_views:
        return None
    return (
        f"{_where(c.line)}: price per 1,000 views ${c.line.rate_per_1000_views}",
        f"media_plan.xlsx {plan.plan_line_id}: price per 1,000 views ${plan.price_per_1000_views}",
    )


def check_billed_on_wrong_count(c: LineContext) -> Evidence | None:
    pay, contract = c.pay, c.contract
    if pay is None or contract is None or contract.bill_on is not BillOn.AD_SERVER_COUNT:
        return None
    if (
        c.line.billed_impressions == pay.ad_server_views
        or c.line.billed_impressions != pay.publisher_views
    ):
        return None
    return (
        f"contracts.json {contract.publisher}: bill on the ad server count",
        f"{_where(c.line)}: billed {c.line.billed_impressions:,} views, the publisher's count "
        f"(ad server count is {pay.ad_server_views:,})",
    )


def check_count_mismatch_beyond_tolerance(c: LineContext) -> Evidence | None:
    pay, contract = c.pay, c.contract
    if pay is None or contract is None or contract.bill_on is not BillOn.PUBLISHER_COUNT:
        return None
    if pay.count_used != "ad_server_count" or c.line.billed_impressions == pay.ad_server_views:
        return None
    return (
        f"delivery {c.line.service_month} {c.match.plan_line_id}: publisher count "
        f"{pay.publisher_views:,}, ad server count {pay.ad_server_views:,} "
        f"({pay.publisher_above_ad_server_percent:.1f}% above)"
        if pay.publisher_above_ad_server_percent is not None
        else "ad server count is 0",
        f"contracts.json {contract.publisher}: allowed difference "
        f"{contract.allowed_difference_percent}%",
        f"{_where(c.line)}: billed {c.line.billed_impressions:,} views",
    )


def check_over_delivery(c: LineContext) -> tuple[Cause, Evidence] | None:
    """More views billed than the month's plan. Which cause depends on the contract."""
    pay, contract = c.pay, c.contract
    if pay is None or contract is None or Decimal(c.line.billed_impressions) <= pay.planned_views:
        return None
    extra = contract.pay_for_extra_views_up_to_percent
    facts = (
        f"{_where(c.line)}: billed {c.line.billed_impressions:,} views",
        f"media_plan.xlsx {c.match.plan_line_id}: {pay.planned_views:,.0f} views planned for "
        f"{c.line.service_month}",
        f"contracts.json {contract.publisher}: extra views paid up to {extra}% "
        f"(at most {pay.cap_views:,} views)",
    )
    if extra == 0:
        return Cause.OVER_DELIVERY_BILLED, facts
    if c.line.billed_impressions > pay.cap_views:
        return Cause.OVER_DELIVERY_BEYOND_CONTRACT, facts
    if c.line.amount == pay.expected_amount:
        return Cause.OVER_DELIVERY_WITHIN_CONTRACT, facts
    return None


_CHECKS: tuple[tuple[Cause, Check], ...] = (
    (Cause.NO_MATCHING_ORDER, check_no_matching_order),
    (Cause.CANCELLED_LINE_BILLED, check_cancelled_line_billed),
    (Cause.OUTSIDE_FLIGHT_DATES, check_outside_flight_dates),
    (Cause.DUPLICATE_LINE, check_duplicate_line),
    (Cause.MATH_ERROR, check_math_error),
    (Cause.RATE_MISMATCH, check_rate_mismatch),
    (Cause.BILLED_ON_WRONG_COUNT, check_billed_on_wrong_count),
    (Cause.COUNT_MISMATCH_BEYOND_TOLERANCE, check_count_mismatch_beyond_tolerance),
)


def find_cause(c: LineContext) -> tuple[Cause, Evidence]:
    """The cause of any difference on this line, with the evidence for it."""
    for cause, check in _CHECKS:
        evidence = check(c)
        if evidence is not None:
            return cause, evidence

    over = check_over_delivery(c)
    if over is not None:
        return over

    if c.pay is not None and c.line.amount == c.pay.expected_amount:
        return Cause.NONE, ()
    expected = c.pay.expected_amount if c.pay else "unknown"
    return Cause.UNEXPLAINED_DIFFERENCE, (
        f"{_where(c.line)}: billed ${c.line.amount}, expected ${expected}, and no rule explains it",
    )
