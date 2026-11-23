"""Tests for reading the Facebook bills.

Broken-file tests work on a temporary copy of a bill, so the real sample files are
never changed. The answer key is never read.
"""

import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from invoice_recon.models import InvoiceLine
from invoice_recon.readers import InvoiceReadError, read_facebook_invoice, read_facebook_invoices

INVOICES = Path(__file__).resolve().parent.parent / "data" / "sample" / "invoices"
JAN = INVOICES / "facebook_2026-01.csv"
FEB = INVOICES / "facebook_2026-02.csv"


@pytest.fixture(scope="module")
def all_lines() -> list[InvoiceLine]:
    return read_facebook_invoices(INVOICES)


@pytest.fixture
def jan_copy(tmp_path: Path) -> Path:
    return Path(shutil.copy(JAN, tmp_path / "facebook_2026-01.csv"))


def problems_in(path: Path) -> list[str]:
    with pytest.raises(InvoiceReadError) as caught:
        read_facebook_invoice(path)
    return caught.value.problems


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new, 1))


# ---------- the real files ----------


def test_both_files_read_with_7_lines_each(all_lines: list[InvoiceLine]) -> None:
    assert len(all_lines) == 14
    assert len(read_facebook_invoice(JAN)) == 7
    assert len(read_facebook_invoice(FEB)) == 7


def test_total_row_is_not_a_line(all_lines: list[InvoiceLine]) -> None:
    assert all("Total" not in line.line_description for line in all_lines)
    assert all(line.invoice_number for line in all_lines)


def test_lines_add_up_to_the_total_row() -> None:
    jan = read_facebook_invoice(JAN)
    assert sum(line.billed_impressions for line in jan) == 22_317_327
    assert sum((line.amount for line in jan), Decimal(0)) == Decimal("192703.88")


def test_first_line_is_filled_as_expected() -> None:
    line = read_facebook_invoice(JAN)[0]
    assert line.invoice_number == "FBADS-26-01-7731"
    assert line.invoice_line_number == 1
    assert line.publisher == "Facebook"
    assert line.service_month == "2026-01"
    assert line.purchase_order_number == "PO-5011"
    assert line.line_description == "Pepsi_WildCherry_Spring_2026 | FB Feed Video"
    assert line.billed_impressions == 4_577_110
    assert line.rate_per_1000_views == Decimal("10.25")
    assert line.amount == Decimal("46915.38")
    assert line.source_file == "facebook_2026-01.csv"
    assert line.source_location == "row 2"


def test_line_numbers_count_from_1_on_each_bill(all_lines: list[InvoiceLine]) -> None:
    assert [line.invoice_line_number for line in all_lines[:7]] == list(range(1, 8))
    assert [line.invoice_line_number for line in all_lines[7:]] == list(range(1, 8))


def test_missing_po_becomes_none(all_lines: list[InvoiceLine]) -> None:
    missing = [line for line in all_lines if line.purchase_order_number is None]
    assert len(missing) == 4  # 1 in January, 3 in February: blank cells in the files
    assert all(line.purchase_order_number for line in all_lines if line not in missing)


def test_money_is_exact_decimal_never_float(all_lines: list[InvoiceLine]) -> None:
    for line in all_lines:
        assert isinstance(line.amount, Decimal)
        assert isinstance(line.rate_per_1000_views, Decimal)


def test_months_come_from_reporting_start(all_lines: list[InvoiceLine]) -> None:
    assert {line.service_month for line in all_lines[:7]} == {"2026-01"}
    assert {line.service_month for line in all_lines[7:]} == {"2026-02"}


# ---------- broken copies ----------


def test_text_in_impressions_is_reported_with_its_row(jan_copy: Path) -> None:
    edit(jan_copy, "4577110", "lots")
    problems = problems_in(jan_copy)
    assert len(problems) == 1
    assert "facebook_2026-01.csv row 2: billed_impressions" in problems[0]


def test_lines_not_adding_up_to_total_are_reported(jan_copy: Path) -> None:
    edit(jan_copy, "46915.38", "46915.39")
    problems = problems_in(jan_copy)
    assert len(problems) == 1
    assert "amounts on the lines add up to" in problems[0]
    assert "Total row says 192703.88" in problems[0]


def test_missing_total_row_is_reported(jan_copy: Path) -> None:
    lines = jan_copy.read_text().splitlines()
    jan_copy.write_text("\n".join(lines[:-1]) + "\n")
    assert "no Total row" in problems_in(jan_copy)[0]


def test_missing_column_is_reported(jan_copy: Path) -> None:
    edit(jan_copy, "PO Reference", "PO Ref")
    assert "missing column(s): PO Reference" in problems_in(jan_copy)[0]


def test_bad_date_is_reported(jan_copy: Path) -> None:
    edit(jan_copy, "2026-01-01", "01/01/2026")
    assert "row 2: Reporting starts" in problems_in(jan_copy)[0]


def test_every_problem_is_listed_at_once(jan_copy: Path) -> None:
    edit(jan_copy, "4577110", "lots")
    edit(jan_copy, "24216.49", "twenty")
    problems = problems_in(jan_copy)
    assert len(problems) == 2
    assert any("row 2" in p for p in problems)
    assert any("row 3" in p for p in problems)


def test_an_amount_that_is_not_whole_cents_is_reported(jan_copy: Path) -> None:
    edit(jan_copy, "46915.38", "46915.385")
    assert "amount" in problems_in(jan_copy)[0]
