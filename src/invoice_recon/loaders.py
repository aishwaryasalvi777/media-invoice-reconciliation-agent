"""Load the clean reference files into the forms, and check they agree with each other.

    media_plan.xlsx  ->  PlanLine        (what the ad agency (GroupM) ordered for Pepsi)
    delivery/*.csv   ->  DeliveryRecord  (views delivered per plan line per month)
    contracts.json   ->  ContractTerms   (billing rules per publisher (Instagram, Facebook))

Every cell is read as text, so money goes straight from text such as "8.25" to an
exact Decimal and is never a float. If anything is wrong, loading stops and lists
every problem at once. Bills are not loaded here; they are messy and have their own
readers.
"""

import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from invoice_recon.config import get_settings
from invoice_recon.models import ContractTerms, DeliveryRecord, Form, PlanLine


class DataLoadError(Exception):
    """The reference files have problems. `problems` lists every one of them."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        listed = "\n".join(f"- {p}" for p in problems)
        super().__init__(f"{len(problems)} problem(s) in the data files:\n{listed}")


@dataclass(frozen=True)
class ReferenceData:
    """All trusted reference data, with quick lookups for the later steps."""

    plan_lines: dict[str, PlanLine]
    """Plan line by its ID, e.g. plan_lines["PL-001"]."""
    deliveries: dict[tuple[str, str], DeliveryRecord]
    """Delivery by (plan line ID, month), e.g. deliveries["PL-001", "2026-01"]."""
    contracts: dict[str, ContractTerms]
    """Contract by publisher, e.g. contracts["Hulu"]."""

    def delivery_for(self, plan_line_id: str, month: str) -> DeliveryRecord | None:
        """The delivery for one plan line in one month, or None if nothing was delivered."""
        return self.deliveries.get((plan_line_id, month))


# ---------- reading files into forms ----------


def _fill_forms[F: Form](
    form: type[F], rows: Iterable[tuple[str, dict[str, Any]]], problems: list[str]
) -> list[F]:
    """Turn raw rows into form records. A row that doesn't fit becomes a problem,
    labelled with where it came from, e.g. "media_plan.xlsx row 5"."""
    records = []
    for where, row in rows:
        cleaned = {key: (None if value == "" else value) for key, value in row.items()}
        try:
            records.append(form(**cleaned))
        except ValidationError as error:
            for e in error.errors():
                field = ".".join(str(part) for part in e["loc"]) or "row"
                problems.append(f"{where}: {field}: {e['msg']}")
    return records


def _table_rows(table: pd.DataFrame, file_name: str) -> list[tuple[str, dict[str, Any]]]:
    # Spreadsheet row numbers: row 1 is the header, so the first data row is row 2.
    return [
        (f"{file_name} row {number}", {str(k): v for k, v in row.items()})
        for number, row in enumerate(table.to_dict("records"), start=2)
    ]


def read_media_plan(path: Path, problems: list[str]) -> tuple[list[PlanLine], list[str]]:
    """Returns the valid plan lines, plus every plan line ID written in the file,
    including rows that were rejected. The cross-file checks need all the IDs, so that
    one broken row can't hide a duplicate ID or cause false "not in the plan" problems."""
    table = pd.read_excel(path, dtype=str, keep_default_na=False)
    ids_in_file = [str(i) for i in table["plan_line_id"]] if "plan_line_id" in table else []
    return _fill_forms(PlanLine, _table_rows(table, path.name), problems), ids_in_file


def read_deliveries(folder: Path, problems: list[str]) -> list[DeliveryRecord]:
    records: list[DeliveryRecord] = []
    for path in sorted(folder.glob("delivery_*.csv")):
        table = pd.read_csv(path, dtype=str, keep_default_na=False)
        records += _fill_forms(DeliveryRecord, _table_rows(table, path.name), problems)
    return records


def read_contracts(path: Path, problems: list[str]) -> list[ContractTerms]:
    raw = json.loads(path.read_text())
    rows = [(f"{path.name} item {number}", item) for number, item in enumerate(raw, start=1)]
    return _fill_forms(ContractTerms, rows, problems)


# ---------- checks across files ----------


def _repeats(values: Iterable[Any]) -> list[Any]:
    return [value for value, count in Counter(values).items() if count > 1]


def check_files_agree(
    plans: list[PlanLine],
    plan_ids_in_file: list[str],
    deliveries: list[DeliveryRecord],
    contracts: list[ContractTerms],
) -> list[str]:
    """Problems that only show up when the files are compared with each other.

    `plan_ids_in_file` holds every ID in the media plan, including rejected rows.
    """
    problems = [
        f"media_plan.xlsx: plan line {i} appears more than once" for i in _repeats(plan_ids_in_file)
    ]
    plan_by_id = {p.plan_line_id: p for p in plans}
    known_ids = set(plan_ids_in_file)

    for d in deliveries:
        plan = plan_by_id.get(d.plan_line_id)
        if d.plan_line_id not in known_ids:
            problems.append(
                f"delivery {d.month}: plan line {d.plan_line_id} is not in the media plan"
            )
        elif plan is None:
            continue  # the plan row exists but was rejected; that problem is already listed
        elif d.publisher != plan.publisher:
            problems.append(
                f"delivery {d.month}: {d.plan_line_id} says {d.publisher}, "
                f"but the media plan says {plan.publisher}"
            )
    problems += [
        f"delivery {month}: {plan_id} has more than one delivery record"
        for plan_id, month in _repeats((d.plan_line_id, d.month) for d in deliveries)
    ]

    problems += [
        f"contracts.json: {p} has more than one contract"
        for p in _repeats(c.publisher for c in contracts)
    ]
    with_contract = {c.publisher for c in contracts}
    problems += [
        f"contracts.json: no contract for publisher {publisher}"
        for publisher in sorted({p.publisher for p in plans} - with_contract)
    ]
    return problems


# ---------- the one function the rest of the system calls ----------


def load_reference_data(data_folder: Path | None = None) -> ReferenceData:
    """Load and check the media plan, delivery files and contracts.

    Raises DataLoadError listing every problem if any record or cross-file check fails.
    """
    folder = data_folder or get_settings().data_folder
    problems: list[str] = []

    plans, plan_ids_in_file = read_media_plan(folder / "media_plan.xlsx", problems)
    deliveries = read_deliveries(folder / "delivery", problems)
    contracts = read_contracts(folder / "contracts.json", problems)
    problems += check_files_agree(plans, plan_ids_in_file, deliveries, contracts)

    if problems:
        raise DataLoadError(problems)

    return ReferenceData(
        plan_lines={p.plan_line_id: p for p in plans},
        deliveries={(d.plan_line_id, d.month): d for d in deliveries},
        contracts={c.publisher: c for c in contracts},
    )
