"""Smoke tests for the notebook's drawing helpers (display only, no business logic)."""

from decimal import Decimal

from invoice_recon import display as vz
from invoice_recon.models import Cause, Decision


def test_every_cause_and_decision_has_plain_words() -> None:
    assert set(vz.CAUSE_WORDS) == set(Cause)
    assert set(vz.DECISION_WORDS) == set(Decision) == set(vz.DECISION_TONE)


def test_text_is_escaped_but_raw_html_is_kept() -> None:
    html = vz.table(["a"], [["<script>"], [vz.badge("ok", "good")]])
    assert "&lt;script&gt;" in html
    assert 'class="badge"' in html


def test_money_pair_and_stacked_do_not_divide_by_zero() -> None:
    assert "bar" in vz.money_pair(Decimal("0"), Decimal("0"), Decimal("0"))
    assert vz.stacked([("a", 0, "good")]).startswith('<div class="stack">')


def test_usd_formats_thousands_and_cents() -> None:
    assert vz.usd(Decimal("1234.5")) == "$1,234.50"
