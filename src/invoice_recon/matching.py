"""Step 3.1: find the plan line each bill line was ordered on. Exact rules, no AI.

    bill line (publisher's wording)                 plan line (ad agency's wording)
    "Pepsi_WildCherry_Spring_2026 | In-Stream"  ->  PL-011 (Facebook In-stream video)
    PO-5011 (or blank)                              PO-5011

How a line is matched (see D-037):
1. Candidates are the plan lines of the same publisher. Dates and cancelled status are
   NOT used here: they are cause checks later, and filtering would hide those problems.
2. Narrow to one campaign. A purchase order number (PO) covers a whole campaign, so it
   only narrows the choice. The campaign wording narrows it too. If both are available
   and point to different campaigns, nothing is matched (a person must look).
3. Within the campaign, pick the plan line with the same ad type (for example "feed video").
4. Exactly one plan line fits -> matched. None, or more than one -> no match, with a reason.

Only Facebook wording rules exist so far. Other publishers get "no match" until their
rules are added.
"""

import re

from pydantic import Field

from invoice_recon.loaders import ReferenceData
from invoice_recon.models import Form, InvoiceLine, PlanLine, Text


class Match(Form):
    invoice_number: Text
    """The bill this match is for."""
    invoice_line_number: int = Field(ge=1)
    """The line on that bill."""
    plan_line_id: Text | None
    """The plan line this bill line was ordered on. None when no single plan line fits."""
    confidence: float = Field(ge=0, le=1)
    """1.0 = the PO and the wording agree. 0.9 = only one of them was available. 0 = no match."""
    reason: Text
    """Plain words: how the match was made, or why there is none."""


# ---------- reading the wording ----------


def _words(text: str) -> list[str]:
    """Split text into lowercase words. Splits on punctuation and on camelCase,
    drops 4-digit years. "DietPepsi_NewYear_2026" -> ["diet", "pepsi", "new", "year"]."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    words = re.findall(r"[A-Za-z0-9]+", spaced.lower())
    return [w for w in words if not re.fullmatch(r"20\d\d", w)]


_PUBLISHER_WORDS = {"fb", "facebook"}


def facebook_ad_type(text: str) -> str | None:
    """The kind of ad in Facebook's or the plan's wording. "FB Feed Video" and
    "Facebook Feed video" are both "feed video"; "In-Stream" is "in-stream video"."""
    words = {w for w in _words(text) if w not in _PUBLISHER_WORDS}
    if "marketplace" in words:
        return "marketplace"
    if "stream" in words or "instream" in words:
        return "in-stream"
    if "feed" in words and "video" in words:
        return "feed video"
    if "feed" in words and "image" in words:
        return "feed image"
    return None


def _plan_campaign_and_ad(plan: PlanLine) -> tuple[list[str], str | None]:
    """Plan descriptions look like "Pepsi Wild Cherry Spring - Facebook Feed video"."""
    if " - " not in plan.description:
        return [], None
    campaign, ad = plan.description.split(" - ", 1)
    return _words(campaign), facebook_ad_type(ad)


def _bill_campaign_and_ad(line: InvoiceLine) -> tuple[list[str], str | None]:
    """Bill descriptions look like "Pepsi_WildCherry_Spring_2026 | FB Feed Video"."""
    if " | " not in line.line_description:
        return [], None
    campaign, ad = line.line_description.split(" | ", 1)
    return _words(campaign), facebook_ad_type(ad)


# ---------- matching ----------


def _no_match(line: InvoiceLine, reason: str) -> Match:
    return Match(
        invoice_number=line.invoice_number,
        invoice_line_number=line.invoice_line_number,
        plan_line_id=None,
        confidence=0,
        reason=reason,
    )


def match_line(line: InvoiceLine, ref: ReferenceData) -> Match:
    """Find the one plan line this bill line was ordered on, or say why none fits."""
    if line.publisher != "Facebook":
        return _no_match(line, f"no wording rules for {line.publisher} yet")

    candidates = [p for p in ref.plan_lines.values() if p.publisher == line.publisher]
    bill_words, bill_ad = _bill_campaign_and_ad(line)
    if bill_ad is None or not bill_words:
        return _no_match(
            line, f"can't read the campaign and ad type from '{line.line_description}'"
        )

    # Route 1: the PO number narrows to a campaign.
    by_po = (
        [p for p in candidates if p.purchase_order_number == line.purchase_order_number]
        if line.purchase_order_number
        else None
    )
    if by_po is not None and not by_po:
        return _no_match(line, f"{line.purchase_order_number} is not in the media plan")

    # Route 2: the campaign wording narrows to a campaign. The bill's campaign words must
    # be the start of the plan's campaign words ("Diet Pepsi New Year" starts "... Refresh").
    by_wording = [
        p for p in candidates if _plan_campaign_and_ad(p)[0][: len(bill_words)] == bill_words
    ]

    if (
        by_po is not None
        and by_wording
        and {p.plan_line_id for p in by_po} != {p.plan_line_id for p in by_wording}
    ):
        return _no_match(
            line,
            f"the PO {line.purchase_order_number} and the campaign wording "
            "point to different campaigns",
        )

    pool = by_po if by_po is not None else by_wording
    if not pool:
        return _no_match(line, f"no campaign in the plan fits '{line.line_description}'")

    both = by_po is not None and bool(by_wording)
    fits = [p for p in pool if _plan_campaign_and_ad(p)[1] == bill_ad]
    if len(fits) == 1:
        how = "PO and wording agree" if both else ("PO only" if by_po else "wording only (no PO)")
        return Match(
            invoice_number=line.invoice_number,
            invoice_line_number=line.invoice_line_number,
            plan_line_id=fits[0].plan_line_id,
            confidence=1.0 if both else 0.9,
            reason=f"campaign + ad type '{bill_ad}' fit {fits[0].plan_line_id}; {how}",
        )
    if not fits:
        return _no_match(line, f"the campaign has no '{bill_ad}' plan line")
    ids = ", ".join(p.plan_line_id for p in fits)
    return _no_match(line, f"more than one plan line fits ({ids})")


def match_lines(lines: list[InvoiceLine], ref: ReferenceData) -> list[Match]:
    return [match_line(line, ref) for line in lines]
