"""Step 7.1: score the Facebook answers against the answer key.

Only tests read the key (see scoring.py). Nothing in src/ ever does.
"""

from pathlib import Path

import pytest
from scoring import Score, score_results

from invoice_recon.loaders import ReferenceData, load_reference_data
from invoice_recon.readers import read_facebook_invoices
from invoice_recon.reconcile import reconcile_lines

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample"


@pytest.fixture(scope="module")
def ref() -> ReferenceData:
    return load_reference_data(SAMPLE)


@pytest.fixture(scope="module")
def score(ref: ReferenceData) -> Score:
    results = reconcile_lines(read_facebook_invoices(SAMPLE / "invoices"), ref)
    return score_results(results, "invoices/facebook")


def test_the_key_has_the_14_facebook_lines(score: Score) -> None:
    assert score.lines == 14


def test_every_facebook_line_is_fully_right(score: Score) -> None:
    assert score.mismatches == []
    assert score.all_four == score.lines


def test_the_scorer_notices_a_wrong_answer(ref: ReferenceData) -> None:
    results = reconcile_lines(read_facebook_invoices(SAMPLE / "invoices"), ref)
    broken = [results[0].model_copy(update={"matched_plan_line_id": "PL-999"}), *results[1:]]
    score = score_results(broken, "invoices/facebook")
    assert score.matched_plan_line == 13
    assert any("plan is wrong" in m for m in score.mismatches)


def test_the_scorer_notices_a_missing_result(ref: ReferenceData) -> None:
    results = reconcile_lines(read_facebook_invoices(SAMPLE / "invoices"), ref)
    score = score_results(results[1:], "invoices/facebook")
    assert any("no result for key row" in m for m in score.mismatches)
