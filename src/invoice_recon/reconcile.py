"""The whole thin pipeline: bill lines in, one Result per line out. No AI.

    InvoiceLine -> match -> plan line -> contract math -> expected amount
                                      -> find cause -> cause + evidence -> decide -> decision

Bill lines must be given in bill order (earliest invoice first), because a later line
for the same plan line and month is the duplicate, not the first one.
"""

from decimal import Decimal

from invoice_recon.causes import LineContext, find_cause
from invoice_recon.contract_math import Payable, payable
from invoice_recon.decide import decide
from invoice_recon.loaders import ReferenceData
from invoice_recon.matching import match_line
from invoice_recon.models import Cause, InvoiceLine, Result


def reconcile_lines(lines: list[InvoiceLine], ref: ReferenceData) -> list[Result]:
    """Check every bill line against the plan, the delivery and the contract."""
    seen: dict[tuple[str, str, str], InvoiceLine] = {}
    results: list[Result] = []

    for line in lines:
        match = match_line(line, ref)
        plan = ref.plan_lines[match.plan_line_id] if match.plan_line_id else None
        contract = ref.contracts.get(line.publisher)
        pay: Payable | None = None
        earlier: InvoiceLine | None = None
        if plan is not None and contract is not None:
            pay = payable(
                plan,
                ref.delivery_for(plan.plan_line_id, line.service_month),
                contract,
                line.service_month,
            )
            key = (line.publisher, plan.plan_line_id, line.service_month)
            earlier = seen.get(key)
            seen.setdefault(key, line)

        cause, evidence = find_cause(
            LineContext(
                line=line,
                match=match,
                plan=plan,
                pay=pay,
                contract=contract,
                earlier_duplicate=earlier,
            )
        )

        # A duplicate is paid once, on its first occurrence; no match means nothing to pay.
        expected = Decimal("0.00")
        if pay is not None and cause is not Cause.DUPLICATE_LINE:
            expected = pay.expected_amount

        results.append(
            Result(
                invoice_number=line.invoice_number,
                invoice_line_number=line.invoice_line_number,
                matched_plan_line_id=match.plan_line_id,
                match_confidence=match.confidence,
                expected_amount=expected,
                invoiced_amount=line.amount,
                cause=cause,
                evidence=evidence,
                decision=decide(cause, line.amount, expected),
            )
        )
    return results
