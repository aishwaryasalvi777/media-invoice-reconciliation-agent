"""Tests for loading the clean reference files.

Broken-file tests work on a temporary copy of the sample data, so the real
sample files are never changed. The answer key is never copied or read.
"""

import json
import shutil
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from invoice_recon.loaders import DataLoadError, ReferenceData, load_reference_data

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample"


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    """A throwaway copy of the 3 clean inputs: media plan, delivery, contracts."""
    shutil.copy(SAMPLE / "media_plan.xlsx", tmp_path)
    shutil.copy(SAMPLE / "contracts.json", tmp_path)
    shutil.copytree(SAMPLE / "delivery", tmp_path / "delivery")
    return tmp_path


def problems_after(folder: Path) -> list[str]:
    with pytest.raises(DataLoadError) as caught:
        load_reference_data(folder)
    return caught.value.problems


# ---------- the real files ----------


@pytest.fixture(scope="module")
def reference() -> ReferenceData:
    return load_reference_data(SAMPLE)


def test_real_files_load(reference: ReferenceData) -> None:
    assert len(reference.plan_lines) == 40
    assert len(reference.deliveries) == 68
    assert sorted(reference.contracts) == ["Facebook", "Hulu", "Instagram", "TikTok", "YouTube"]


def test_money_is_exact_decimal_never_float(reference: ReferenceData) -> None:
    for plan in reference.plan_lines.values():
        assert type(plan.price_per_1000_views) is Decimal
        assert type(plan.planned_cost) is Decimal
    assert reference.plan_lines["PL-001"].price_per_1000_views == Decimal("8.25")


def test_lookups(reference: ReferenceData) -> None:
    assert reference.plan_lines["PL-001"].publisher == "Instagram"
    assert reference.contracts["Hulu"].pay_for_extra_views_up_to_percent == 10

    january = reference.delivery_for("PL-001", "2026-01")
    assert january is not None
    assert january.publisher == "Instagram"

    # PL-007 starts on Feb 1, so nothing was delivered in January.
    assert reference.delivery_for("PL-007", "2026-01") is None


def test_cancelled_lines_are_loaded_with_their_date(reference: ReferenceData) -> None:
    cancelled = [p for p in reference.plan_lines.values() if p.status == "cancelled"]

    assert len(cancelled) == 2
    assert all(p.cancelled_effective_date is not None for p in cancelled)


# ---------- broken copies: each problem is caught ----------


def edit_plan(folder: Path, row: int, column: int, value: int | str) -> None:
    book = openpyxl.load_workbook(folder / "media_plan.xlsx")
    sheet = book.active
    assert sheet is not None
    sheet.cell(row, column, value)
    book.save(folder / "media_plan.xlsx")


def add_delivery_row(folder: Path, row: str) -> None:
    with (folder / "delivery" / "delivery_2026-01.csv").open("a") as f:
        f.write(row + "\n")


def drop_contract(folder: Path, publisher: str) -> None:
    path = folder / "contracts.json"
    contracts = [c for c in json.loads(path.read_text()) if c["publisher"] != publisher]
    path.write_text(json.dumps(contracts))


BREAKAGES: list[tuple[str, Callable[[Path], None], str]] = [
    (
        "a bad value in one row",
        lambda f: edit_plan(f, 2, 7, -100),  # row 2 = PL-001, column 7 = planned_impressions
        "media_plan.xlsx row 2: planned_impressions",
    ),
    (
        "two plan lines with the same ID",
        lambda f: edit_plan(f, 3, 1, "PL-001"),
        "plan line PL-001 appears more than once",
    ),
    (
        "delivery for a plan line that doesn't exist",
        lambda f: add_delivery_row(f, "PL-999,Instagram,2026-01,100,98"),
        "plan line PL-999 is not in the media plan",
    ),
    (
        "delivery says the wrong publisher",
        lambda f: add_delivery_row(f, "PL-007,Facebook,2026-01,100,98"),
        "PL-007 says Facebook, but the media plan says Instagram",
    ),
    (
        "the same month delivered twice",
        lambda f: add_delivery_row(f, "PL-001,Instagram,2026-01,100,98"),
        "PL-001 has more than one delivery record",
    ),
    (
        "a publisher with no contract",
        lambda f: drop_contract(f, "TikTok"),
        "no contract for publisher TikTok",
    ),
]


@pytest.mark.parametrize(
    ("breakage", "expected"), [(b, e) for _, b, e in BREAKAGES], ids=[n for n, _, _ in BREAKAGES]
)
def test_each_problem_is_caught(
    data_copy: Path, breakage: Callable[[Path], None], expected: str
) -> None:
    breakage(data_copy)

    problems = problems_after(data_copy)

    assert any(expected in p for p in problems), problems


def test_every_problem_is_listed_at_once(data_copy: Path) -> None:
    for _, breakage, _ in BREAKAGES:
        breakage(data_copy)

    problems = problems_after(data_copy)

    for _, _, expected in BREAKAGES:
        assert any(expected in p for p in problems), (expected, problems)


def test_a_rejected_plan_row_causes_no_extra_problems(data_copy: Path) -> None:
    """PL-001's row is rejected (views = -100), but PL-001 is still in the file.
    Its deliveries must not also be reported as "not in the media plan"."""
    edit_plan(data_copy, 2, 7, -100)

    problems = problems_after(data_copy)

    assert problems == [
        "media_plan.xlsx row 2: planned_impressions: Input should be greater than or equal to 0"
    ]


def test_the_real_sample_files_were_not_changed() -> None:
    load_reference_data(SAMPLE)  # still loads cleanly after all the broken-copy tests
