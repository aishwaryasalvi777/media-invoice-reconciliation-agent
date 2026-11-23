"""Read Facebook bills (CSV) into InvoiceLine forms.

    facebook_2026-01.csv  ->  InvoiceLine  (one per bill line)

Every cell is read as text, so money goes straight from text such as "46915.38" to an
exact Decimal and is never a float. The final "Total" row is not a bill line: it is
skipped, then used as a control total (the lines must add up to it). If anything is
wrong, reading stops and lists every problem at once, naming the file and row.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from invoice_recon.models import InvoiceLine
from invoice_recon.readers.errors import InvoiceReadError

PUBLISHER = "Facebook"

# Facebook column name -> what we call it here.
COLUMNS = {
    "Invoice ID": "invoice_id",
    "Campaign name": "campaign",
    "Ad set name": "ad_set",
    "Reporting starts": "starts",
    "Impressions": "impressions",
    "CPM (cost per 1,000 impressions) (USD)": "rate",
    "Amount spent (USD)": "amount",
    "PO Reference": "po",
}


def _read_one(path: Path, problems: list[str]) -> list[InvoiceLine]:
    """Read one Facebook bill. Adds every problem found to `problems`."""
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [name for name in COLUMNS if name not in table.columns]
    if missing:
        problems.append(f"{path.name}: missing column(s): {', '.join(missing)}")
        return []

    lines: list[InvoiceLine] = []
    total_row: dict[str, str] | None = None
    new_problems: list[str] = []

    # Spreadsheet row numbers: row 1 is the header, so the first data row is row 2.
    for number, raw in enumerate(table.to_dict("records"), start=2):
        row = {COLUMNS[k]: str(raw[k]).strip() for k in COLUMNS}
        where = f"{path.name} row {number}"

        if row["campaign"] == "Total" and row["invoice_id"] == "":
            total_row = row
            continue

        try:
            service_month = date.fromisoformat(row["starts"]).strftime("%Y-%m")
        except ValueError:
            new_problems.append(f"{where}: Reporting starts: '{row['starts']}' is not a date")
            continue

        try:
            lines.append(
                InvoiceLine.model_validate(
                    {
                        "invoice_number": row["invoice_id"],
                        "invoice_line_number": len(lines) + 1,
                        "publisher": PUBLISHER,
                        "service_month": service_month,
                        "purchase_order_number": row["po"] or None,
                        "line_description": f"{row['campaign']} | {row['ad_set']}",
                        "billed_impressions": row["impressions"],
                        "rate_per_1000_views": row["rate"],
                        "amount": row["amount"],
                        "source_file": path.name,
                        "source_location": f"row {number}",
                    }
                )
            )
        except ValidationError as error:
            for e in error.errors():
                field = ".".join(str(part) for part in e["loc"]) or "row"
                new_problems.append(f"{where}: {field}: {e['msg']}")

    problems += new_problems
    if total_row is None:
        problems.append(f"{path.name}: no Total row found, so the lines can't be checked")
    elif not new_problems:
        problems += _check_total(path.name, lines, total_row)
    return lines


def _check_total(file_name: str, lines: list[InvoiceLine], total_row: dict[str, str]) -> list[str]:
    """The lines must add up to the publisher's own Total row."""
    try:
        total_views = int(total_row["impressions"])
        total_amount = Decimal(total_row["amount"])
    except (ValueError, InvalidOperation):
        return [f"{file_name}: the Total row has an unreadable impressions or amount"]

    problems = []
    views = sum(line.billed_impressions for line in lines)
    if views != total_views:
        problems.append(
            f"{file_name}: impressions on the lines add up to {views:,}, "
            f"but the Total row says {total_views:,}"
        )
    amount = sum((line.amount for line in lines), Decimal("0"))
    if amount != total_amount:
        problems.append(
            f"{file_name}: amounts on the lines add up to {amount}, "
            f"but the Total row says {total_amount}"
        )
    return problems


def read_facebook_invoice(path: Path) -> list[InvoiceLine]:
    """Read one Facebook bill. Raises InvoiceReadError listing every problem."""
    problems: list[str] = []
    lines = _read_one(path, problems)
    if problems:
        raise InvoiceReadError(problems)
    return lines


def read_facebook_invoices(folder: Path) -> list[InvoiceLine]:
    """Read every facebook_*.csv in a folder. Raises InvoiceReadError listing every
    problem from every file."""
    problems: list[str] = []
    lines: list[InvoiceLine] = []
    for path in sorted(folder.glob("facebook_*.csv")):
        lines += _read_one(path, problems)
    if problems:
        raise InvoiceReadError(problems)
    return lines
