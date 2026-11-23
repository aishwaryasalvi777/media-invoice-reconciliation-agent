"""Score the pipeline's answers against the answer key.

This is the ONLY place that reads data/sample/answer_key.csv. It lives in tests/ on
purpose: the system itself must never read the key (project hard rule), so the key is
never an input, a hint or a lookup. The scorer only compares answers after the fact.
"""

import csv
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from invoice_recon.models import Result

ANSWER_KEY = Path(__file__).resolve().parent.parent / "data" / "sample" / "answer_key.csv"


@dataclass(frozen=True)
class Score:
    """How many lines were right, per field, and every mismatch spelled out."""

    lines: int
    matched_plan_line: int
    cause: int
    decision: int
    expected_amount: int
    all_four: int
    """Lines where all four fields were right."""
    mismatches: list[str] = field(default_factory=list)


def score_results(
    results: list[Result], invoice_file_prefix: str, key_path: Path = ANSWER_KEY
) -> Score:
    """Compare results with the key rows whose invoice file starts with the prefix,
    for example "invoices/facebook". Every key row must have a result, and the other way round."""
    with key_path.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["invoice_file"].startswith(invoice_file_prefix)]
    key = {(r["invoice_number"], int(r["invoice_line_number"])): r for r in rows}
    got = {(r.invoice_number, r.invoice_line_number): r for r in results}

    mismatches = [f"no result for key row {k}" for k in key if k not in got]
    mismatches += [f"result {k} has no key row" for k in got if k not in key]

    counts = dict.fromkeys(("plan", "cause", "decision", "amount", "all"), 0)
    for k in key.keys() & got.keys():
        row, result = key[k], got[k]
        checks = {
            "plan": result.matched_plan_line_id == row["true_plan_line_id"],
            "cause": result.cause.value == row["planted_cause"],
            "decision": result.decision.value == row["expected_decision"],
            "amount": result.expected_amount == Decimal(row["expected_amount"]),
        }
        for name, ok in checks.items():
            counts[name] += ok
            if not ok:
                mismatches.append(
                    f"{k[0]} line {k[1]}: {name} is wrong ({row['planted_cause']}, "
                    f"{row['expected_decision']}, expected ${row['expected_amount']})"
                )
        counts["all"] += all(checks.values())

    return Score(
        lines=len(key),
        matched_plan_line=counts["plan"],
        cause=counts["cause"],
        decision=counts["decision"],
        expected_amount=counts["amount"],
        all_four=counts["all"],
        mismatches=mismatches,
    )
