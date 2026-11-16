"""The 5 forms: the exact shape of every record in the system.

A record that doesn't fit its form is rejected the moment it is created, so bad
data never reaches the money math. All forms are frozen (can't be changed once
created) and reject unknown fields.

1. PlanLine        one row of the media plan the ad agency (GroupM) built for the client (Pepsi)
2. DeliveryRecord  views delivered for one plan line in one month
3. InvoiceLine     one line of a publisher's bill (Instagram, Facebook), after reading
4. ContractTerms   the billing rules agreed with one publisher
5. Result          our answer for one bill line
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    model_validator,
)

# ---------- shared building blocks ----------


def _refuse_float(value: Any) -> Any:
    """Money must never be a float: 0.1 + 0.2 = 0.30000000000000004 in float.
    Accept Decimal, whole numbers, or text like "12170.52"."""
    if isinstance(value, float):
        raise ValueError("money must be a Decimal or text like '12.50', never a float")
    return value


Money = Annotated[Decimal, BeforeValidator(_refuse_float), Field(ge=0, decimal_places=2)]
"""An amount in US dollars, exact to the cent. Example: Decimal("12170.52")."""

Rate = Annotated[Decimal, BeforeValidator(_refuse_float), Field(ge=0, decimal_places=4)]
"""Price per 1,000 views (the industry calls this CPM). Example: Decimal("8.25")."""

Percent = Annotated[Decimal, BeforeValidator(_refuse_float), Field(ge=0, le=100)]

Month = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
"""A calendar month written as YYYY-MM. Example: "2026-01"."""

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
"""Text that can't be empty."""

Views = Annotated[int, Field(ge=0)]
"""A count of views (impressions). Never negative."""


class Form(BaseModel):
    """Settings shared by all 5 forms."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)


# ---------- fixed lists ----------


class PlanStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class BillOn(StrEnum):
    """Whose view count the contract says is used for billing."""

    PUBLISHER_COUNT = "publisher_count"
    AD_SERVER_COUNT = "ad_server_count"


class Cause(StrEnum):
    """Why a bill line differs from what should be paid."""

    NONE = "none"
    OVER_DELIVERY_BILLED = "over_delivery_billed"
    OVER_DELIVERY_WITHIN_CONTRACT = "over_delivery_within_contract"
    OVER_DELIVERY_BEYOND_CONTRACT = "over_delivery_beyond_contract"
    OUTSIDE_FLIGHT_DATES = "outside_flight_dates"
    DUPLICATE_LINE = "duplicate_line"
    COUNT_MISMATCH_BEYOND_TOLERANCE = "count_mismatch_beyond_tolerance"
    BILLED_ON_WRONG_COUNT = "billed_on_wrong_count"
    CANCELLED_LINE_BILLED = "cancelled_line_billed"
    MATH_ERROR = "math_error"
    RATE_MISMATCH = "rate_mismatch"
    NO_MATCHING_ORDER = "no_matching_order"


class Decision(StrEnum):
    APPROVE = "approve"
    PAY_LESS = "pay_less"
    DISPUTE = "dispute"
    SEND_TO_HUMAN = "send_to_human"


# ---------- 1. PlanLine ----------


class PlanLine(Form):
    plan_line_id: Text
    """Unique ID of this plan row, e.g. PL-001."""
    purchase_order_number: Text
    """Covers a whole campaign at one publisher, not a single plan line."""
    publisher: Text
    """Who runs the ad, e.g. Instagram."""
    description: Text
    """What is being bought: campaign, publisher and ad type."""
    start_date: date
    """First day the ad runs."""
    end_date: date
    """Last day the ad runs. Not before start_date."""
    planned_impressions: Views
    """Views ordered for the whole run."""
    price_per_1000_views: Rate
    """Agreed price for every 1,000 views (CPM)."""
    planned_cost: Money
    """Must equal views x price per view, to the cent."""
    status: PlanStatus
    """Active, or cancelled from cancelled_effective_date."""
    cancelled_effective_date: date | None = None
    """Only for a cancelled line: the day it stopped."""

    @model_validator(mode="after")
    def _check(self) -> "PlanLine":
        if self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        cancelled = self.status is PlanStatus.CANCELLED
        if cancelled != (self.cancelled_effective_date is not None):
            raise ValueError("a cancelled line needs a cancelled_effective_date, and only then")
        expected = (self.planned_impressions * self.price_per_1000_views / 1000).quantize(
            Decimal("0.01")
        )
        if self.planned_cost != expected:
            raise ValueError(
                f"planned_cost {self.planned_cost} doesn't equal views x price = {expected}"
            )
        return self


# ---------- 2. DeliveryRecord ----------


class DeliveryRecord(Form):
    plan_line_id: Text
    """Which plan line these views belong to."""
    publisher: Text
    """Must be the same publisher as on the plan line."""
    month: Month
    """Which month the views were delivered in."""
    publisher_count: Views
    """Views counted by the publisher (Instagram, Facebook)."""
    ad_server_count: Views
    """Views counted by the ad agency's (GroupM's) own ad server."""


# ---------- 3. InvoiceLine ----------


class InvoiceLine(Form):
    """One bill line, as read from the publisher's file.

    Deliberately accepts an amount that doesn't equal views x price: bills can be
    wrong, and spotting that is the job of the cause checks, not this form.
    """

    invoice_number: Text
    """The bill's number, e.g. IG-INV-2026-0142."""
    invoice_line_number: Annotated[int, Field(ge=1)]
    """Line position on the bill, starting at 1."""
    publisher: Text
    """Who sent the bill."""
    service_month: Month
    """Which month this line charges for."""
    purchase_order_number: Text | None = None
    """Missing on about a quarter of lines."""
    line_description: Text
    """The publisher's own wording, e.g. "PZS | Reels | JAN26"."""
    billed_impressions: Views
    """Views the publisher is charging for."""
    rate_per_1000_views: Rate
    """Price per 1,000 views used on the bill."""
    amount: Money
    """Money charged. May be wrong; checked later."""
    source_file: Text
    """The bill file this line was read from."""
    source_location: Text
    """Where in the file this line came from, e.g. "page 1, row 3"."""


# ---------- 4. ContractTerms ----------


class ContractTerms(Form):
    publisher: Text
    """The publisher these rules apply to."""
    agency: Text
    """The ad agency that pays, e.g. GroupM."""
    client: Text
    """The brand the ads are for, e.g. Pepsi."""
    bill_on: BillOn
    """Whose view count is used for billing."""
    allowed_difference_percent: Percent
    """How far the publisher's count may be above the ad server count."""
    pay_for_extra_views_up_to_percent: Percent
    """0 = extra views are never paid. 10 = up to 10% extra views are paid."""


# ---------- 5. Result ----------


class Result(Form):
    invoice_number: Text
    """The bill this result is for."""
    invoice_line_number: Annotated[int, Field(ge=1)]
    """The line on that bill."""
    matched_plan_line_id: Text | None
    """None when no plan line matches."""
    match_confidence: Annotated[float, Field(ge=0, le=1)]
    """How sure the match is: 1.0 = certain."""
    expected_amount: Money
    """What the ad agency (GroupM) should pay under the contract."""
    invoiced_amount: Money
    """What the publisher billed."""
    cause: Cause
    """Why the bill differs, from the fixed list of causes."""
    evidence: tuple[Text, ...] = ()
    """Short facts that prove the cause, each naming its source."""
    decision: Decision
    """What to do: approve, pay less, dispute or send to a human."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def difference(self) -> Decimal:
        """Billed minus expected. Positive = the publisher billed too much."""
        return self.invoiced_amount - self.expected_amount

    @model_validator(mode="after")
    def _check(self) -> "Result":
        if self.difference != 0 and self.cause is Cause.NONE:
            raise ValueError("a line with a difference needs a cause other than 'none'")
        return self
