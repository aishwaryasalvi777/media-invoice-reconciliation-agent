"""Step 4.4: turn a cause into a decision, with safety guards.

    cause                                   decision
    none, over_delivery_within_contract     approve        (the bill is right)
    over_delivery_billed / _beyond_contract,
    billed_on_wrong_count,
    count_mismatch_beyond_tolerance         pay_less       (pay the expected amount)
    outside_flight_dates, duplicate_line,
    cancelled_line_billed, math_error       dispute        (the bill shouldn't have been sent)
    rate_mismatch, no_matching_order,
    unexplained_difference                  send_to_human  (we can't be sure)

Guards (D-038): wrongly approving a bad bill costs far more than asking a person.
- "approve" only when the billed amount equals the expected amount.
- "pay_less" only when the bill is higher than the expected amount (an under-bill is not a
  case for paying less).
Anything failing a guard goes to a human.
"""

from decimal import Decimal

from invoice_recon.models import Cause, Decision

DECISION_BY_CAUSE: dict[Cause, Decision] = {
    Cause.NONE: Decision.APPROVE,
    Cause.OVER_DELIVERY_WITHIN_CONTRACT: Decision.APPROVE,
    Cause.OVER_DELIVERY_BILLED: Decision.PAY_LESS,
    Cause.OVER_DELIVERY_BEYOND_CONTRACT: Decision.PAY_LESS,
    Cause.BILLED_ON_WRONG_COUNT: Decision.PAY_LESS,
    Cause.COUNT_MISMATCH_BEYOND_TOLERANCE: Decision.PAY_LESS,
    Cause.OUTSIDE_FLIGHT_DATES: Decision.DISPUTE,
    Cause.DUPLICATE_LINE: Decision.DISPUTE,
    Cause.CANCELLED_LINE_BILLED: Decision.DISPUTE,
    Cause.MATH_ERROR: Decision.DISPUTE,
    Cause.RATE_MISMATCH: Decision.SEND_TO_HUMAN,
    Cause.NO_MATCHING_ORDER: Decision.SEND_TO_HUMAN,
    Cause.UNEXPLAINED_DIFFERENCE: Decision.SEND_TO_HUMAN,
}


def decide(cause: Cause, invoiced: Decimal, expected: Decimal) -> Decision:
    """The decision for a cause, unless a guard sends it to a human."""
    decision = DECISION_BY_CAUSE[cause]
    if decision is Decision.APPROVE and invoiced != expected:
        return Decision.SEND_TO_HUMAN
    if decision is Decision.PAY_LESS and invoiced <= expected:
        return Decision.SEND_TO_HUMAN
    return decision
