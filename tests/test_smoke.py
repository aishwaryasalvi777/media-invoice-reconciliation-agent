"""Smoke tests: quick checks that the project setup works.

They test no business logic. They only prove that Python, the folder layout
and the libraries are ready. These tests never read answer_key.csv.
"""

import json
import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "sample"


def test_package_can_be_loaded() -> None:
    import invoice_recon

    assert invoice_recon.__doc__


def test_python_version_is_3_12() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_libraries_can_read_sample_data() -> None:
    media_plan = pd.read_excel(DATA / "media_plan.xlsx")
    assert len(media_plan) == 40

    contracts = json.loads((DATA / "contracts.json").read_text())
    publishers = {c["publisher"] for c in contracts}
    assert publishers == {"Instagram", "Facebook", "YouTube", "Hulu", "TikTok"}
