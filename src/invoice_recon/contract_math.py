"""Step 4.1: what the ad agency (GroupM) should pay for one plan line in one month.

The rules come from the contract (see data/sample/README.md):
1. Pick the count. If the contract bills on the publisher's count, use it, unless it is more
   than `allowed_difference_percent` above the ad server count; then use the ad server count.
   If the contract bills on the ad server count, always use that.
2. Cap it. Never pay for more than that month's planned views plus the extra percent the
   contract allows. The cap is cut down to whole views.
3. Multiply by the plan's price per 1,000 views (not the price on the bill), rounded half up.

A month's planned views = the plan line's total views x (flight days in that month) /
(flight days in the whole run). A cancelled line has no flight days from its cancelled date.

Small example: 9,000 views planned over 90 days; January has 31 flight days, so January's
plan is 9,000 x 31 / 90 = 3,100 views. At $10 per 1,000 views, 3,100 views cost $31.00.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from math import floor

from invoice_recon.models import BillOn, ContractTerms, DeliveryRecord, PlanLine, PlanStatus
from invoice_recon.money import cost_of_views


def month_bounds(month: str) -> tuple[date, date]:
    """First and last day of a month written "YYYY-MM"."""
    year, number = int(month[:4]), int(month[5:])
    return date(year, number, 1), date(year, number, calendar.monthrange(year, number)[1])


def flight_days_in_month(plan: PlanLine, month: str) -> int:
    """Days of this month on which the ad could run. A cancelled line stops the day
    before its cancelled date."""
    first, last = month_bounds(month)
    end = plan.end_date
    if plan.status is PlanStatus.CANCELLED and plan.cancelled_effective_date is not None:
        end = min(end, plan.cancelled_effective_date - timedelta(days=1))
    start = max(first, plan.start_date)
    stop = min(last, end)
    return max(0, (stop - start).days + 1)


def planned_views_in_month(plan: PlanLine, month: str) -> Decimal:
    """That month's share of the plan line's total views (may have decimals)."""
    whole_run = (plan.end_date - plan.start_date).days + 1
    return Decimal(plan.planned_impressions) * flight_days_in_month(plan, month) / whole_run


@dataclass(frozen=True)
class Payable:
    """What should be paid for one plan line in one month, and how it was worked out."""

    expected_amount: Decimal
    """The correct amount, in dollars and cents."""
    payable_views: int
    """The views we pay for after steps 1 and 2."""
    count_used: str
    """Which count step 1 picked: "publisher_count" or "ad_server_count"."""
    count_used_views: int
    """That count's number of views."""
    publisher_views: int
    ad_server_views: int
    planned_views: Decimal
    """That month's planned views."""
    cap_views: int
    """Most views we pay for this month (planned + allowed extra, cut to whole views)."""
    publisher_above_ad_server_percent: Decimal | None
    """How far the publisher's count is above the ad server's, in percent.
    None if the ad server count is 0."""
    delivery_found: bool


def payable(
    plan: PlanLine, delivery: DeliveryRecord | None, contract: ContractTerms, month: str
) -> Payable:
    """The contract math for one plan line in one month."""
    publisher_views = delivery.publisher_count if delivery else 0
    ad_server_views = delivery.ad_server_count if delivery else 0

    above: Decimal | None = None
    if ad_server_views > 0:
        above = (Decimal(publisher_views) - ad_server_views) * 100 / ad_server_views

    use_ad_server = contract.bill_on is BillOn.AD_SERVER_COUNT or (
        above is not None and above > contract.allowed_difference_percent
    )
    count_used = "ad_server_count" if use_ad_server else "publisher_count"
    count_views = ad_server_views if use_ad_server else publisher_views

    planned = planned_views_in_month(plan, month)
    cap = floor(planned * (100 + contract.pay_for_extra_views_up_to_percent) / 100)
    views = min(count_views, cap)

    return Payable(
        expected_amount=cost_of_views(views, plan.price_per_1000_views),
        payable_views=views,
        count_used=count_used,
        count_used_views=count_views,
        publisher_views=publisher_views,
        ad_server_views=ad_server_views,
        planned_views=planned,
        cap_views=cap,
        publisher_above_ad_server_percent=above,
        delivery_found=delivery is not None,
    )
