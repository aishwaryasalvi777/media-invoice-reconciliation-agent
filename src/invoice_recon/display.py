"""Small helpers that draw things as HTML for the walkthrough notebook.

Display only: no business logic lives here. Each function returns an HTML string; the
notebook shows it with IPython's HTML(). Colours are fixed (light fill, dark text) so
everything is readable in a light or a dark Jupyter theme.
"""

from collections.abc import Sequence
from decimal import Decimal
from html import escape

from invoice_recon.models import Cause, Decision


class Raw(str):
    """Text that is already HTML and must not be escaped."""


_TONES = {  # tone -> (background, border, text)
    "good": ("#e3f4e8", "#7cc592", "#14532d"),
    "warn": ("#fdf0d5", "#e8b84b", "#6b4a00"),
    "bad": ("#fbe3e3", "#e08a8a", "#7f1d1d"),
    "info": ("#e4eefb", "#8fb4e8", "#12365f"),
    "plain": ("#f1f1f1", "#c9c9c9", "#222222"),
}

STYLE = """
<style>
.vz{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#222;font-size:14px}
.vz *{box-sizing:border-box}
.vz table{border-collapse:collapse;width:100%;background:#fff;color:#222}
.vz th{background:#eef1f5;text-align:left;padding:6px 10px;border-bottom:2px solid #cfd6df;
       font-weight:600}
.vz td{padding:6px 10px;border-bottom:1px solid #e5e8ec;vertical-align:middle}
.vz th,.vz td{text-align:left !important;overflow-wrap:anywhere}
.vz td.num{text-align:right !important}
.vz tr.dim td{color:#888;background:#fafafa;font-style:italic}
.vz tr.hot td{background:#fff6e5}
.vz .num{font-variant-numeric:tabular-nums}
.vz .row{display:flex;flex-wrap:wrap;gap:12px;margin:8px 0}
.vz .tile{flex:1;min-width:150px;border:1px solid;border-radius:10px;padding:10px 14px}
.vz .tile b{display:block;font-size:24px;line-height:1.2}
.vz .tile span{font-size:12px;opacity:.85}
.vz .badge{display:inline-block;border:1px solid;border-radius:999px;padding:2px 10px;
           font-size:12px;font-weight:600;white-space:nowrap}
.vz .flow{display:flex;align-items:stretch;gap:6px;margin:10px 0;flex-wrap:wrap}
.vz .box{flex:1;min-width:130px;border:1px solid;border-radius:10px;padding:8px 12px}
.vz .box b{display:block}
.vz .arrow{align-self:center;font-size:22px;color:#777}
.vz .bar{height:14px;border-radius:4px;margin:2px 0}
.vz .card{border:1px solid;border-radius:10px;padding:10px 14px;margin:8px 0}
.vz .card ul{margin:6px 0 0 18px;padding:0}
.vz .row .card{flex:1;min-width:200px;margin:0}
.vz .stack{display:flex;height:26px;border-radius:6px;overflow:hidden;margin:6px 0}
.vz .stack div{display:flex;align-items:center;justify-content:center;font-size:12px;
               font-weight:600;color:#fff}
</style>
"""

CAUSE_WORDS: dict[Cause, str] = {
    Cause.NONE: "Nothing wrong",
    Cause.OVER_DELIVERY_BILLED: "Billed extra views the contract doesn't pay",
    Cause.OVER_DELIVERY_WITHIN_CONTRACT: "Extra views, but the contract allows them",
    Cause.OVER_DELIVERY_BEYOND_CONTRACT: "Extra views beyond what the contract allows",
    Cause.OUTSIDE_FLIGHT_DATES: "Billed a month the ad wasn't scheduled",
    Cause.DUPLICATE_LINE: "Same line billed twice",
    Cause.COUNT_MISMATCH_BEYOND_TOLERANCE: "Publisher counted too many views",
    Cause.BILLED_ON_WRONG_COUNT: "Billed on the wrong view count",
    Cause.CANCELLED_LINE_BILLED: "Billed an order that was cancelled",
    Cause.MATH_ERROR: "The bill's own maths is wrong",
    Cause.RATE_MISMATCH: "Price differs from the plan",
    Cause.NO_MATCHING_ORDER: "No order in the plan fits this line",
    Cause.UNEXPLAINED_DIFFERENCE: "Amount is wrong and no rule explains it",
}

DECISION_TONE = {
    Decision.APPROVE: "good",
    Decision.PAY_LESS: "warn",
    Decision.DISPUTE: "bad",
    Decision.SEND_TO_HUMAN: "info",
}
DECISION_WORDS = {
    Decision.APPROVE: "Approve",
    Decision.PAY_LESS: "Pay less",
    Decision.DISPUTE: "Dispute",
    Decision.SEND_TO_HUMAN: "Ask a person",
}


def usd(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _cell(value: object) -> str:
    return str(value) if isinstance(value, Raw) else escape(str(value))


def wrap(*parts: str) -> str:
    return f'{STYLE}<div class="vz">{"".join(parts)}</div>'


def badge(text: str, tone: str = "plain") -> Raw:
    bg, border, color = _TONES[tone]
    return Raw(
        f'<span class="badge" style="background:{bg};border-color:{border};color:{color}">'
        f"{escape(text)}</span>"
    )


def decision_badge(decision: Decision) -> Raw:
    return badge(DECISION_WORDS[decision], DECISION_TONE[decision])


def tiles(items: Sequence[tuple[str, str, str]]) -> str:
    """Big-number tiles: (label, value, tone)."""
    boxes = []
    for label, value, tone in items:
        bg, border, color = _TONES[tone]
        boxes.append(
            f'<div class="tile" style="background:{bg};border-color:{border};color:{color}">'
            f"<b>{escape(value)}</b><span>{escape(label)}</span></div>"
        )
    return f'<div class="row">{"".join(boxes)}</div>'


def flow(steps: Sequence[tuple[str, str]], tones: Sequence[str] | None = None) -> str:
    """Boxes joined by arrows: (title, small text)."""
    parts = []
    for i, (title, small) in enumerate(steps):
        bg, border, color = _TONES[tones[i] if tones else "info"]
        if i:
            parts.append('<div class="arrow">→</div>')
        parts.append(
            f'<div class="box" style="background:{bg};border-color:{border};color:{color}">'
            f"<b>{escape(title)}</b>{escape(small)}</div>"
        )
    return f'<div class="flow">{"".join(parts)}</div>'


def table(
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    numeric: Sequence[str] = (),
    dim: Sequence[int] = (),
    hot: Sequence[int] = (),
) -> str:
    """A table. `numeric` columns are right-aligned; `dim` / `hot` are row numbers
    (from 0) to grey out or highlight."""
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = []
    for n, row in enumerate(rows):
        cls = "dim" if n in dim else "hot" if n in hot else ""
        cells = "".join(
            f'<td class="{"num" if headers[i] in numeric else ""}">{_cell(v)}</td>'
            for i, v in enumerate(row)
        )
        body.append(f'<tr class="{cls}">{cells}</tr>')
    return f"<table><tr>{head}</tr>{''.join(body)}</table>"


def card(title: str, bullets: Sequence[str], tone: str = "plain") -> str:
    bg, border, color = _TONES[tone]
    items = "".join(f"<li>{escape(b)}</li>" for b in bullets)
    return (
        f'<div class="card" style="background:{bg};border-color:{border};color:{color}">'
        f"<b>{escape(title)}</b><ul>{items}</ul></div>"
    )


def bars(values: Sequence[tuple[str, int | Decimal, str]], width_of: int | Decimal) -> str:
    """Horizontal bars sharing one scale: (label, value, tone). Longest = `width_of`."""
    out = []
    for label, value, tone in values:
        pct = max(1.0, float(value) / float(width_of) * 100) if value else 0.0
        _, border, _ = _TONES[tone]
        out.append(
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<div style="width:120px;font-size:12px">{escape(label)}</div>'
            f'<div class="bar" style="width:{pct:.1f}%;background:{border}"></div>'
            f'<div style="font-size:12px">{value:,}</div></div>'
        )
    return "".join(out)


def money_pair(billed: Decimal, expected: Decimal, biggest: Decimal) -> Raw:
    """Two small bars: what was billed, and what should be paid."""
    b = float(billed / biggest * 100) if biggest else 0
    e = float(expected / biggest * 100) if biggest else 0
    over = billed > expected
    return Raw(
        f'<div class="bar" style="width:{b:.1f}%;background:{_TONES["bad" if over else "info"][1]}"'
        f' title="billed"></div>'
        f'<div class="bar" style="width:{e:.1f}%;background:{_TONES["good"][1]}"'
        f' title="should pay"></div>'
    )


def stacked(parts: Sequence[tuple[str, int, str]]) -> str:
    """One bar split in coloured parts: (label, count, tone). Zero-size parts are skipped."""
    solid = {"good": "#2e9e5b", "warn": "#d99a1b", "bad": "#d64545", "info": "#3b79c9"}
    total = sum(n for _, n, _ in parts) or 1
    cells = "".join(
        f'<div style="width:{n / total * 100:.1f}%;background:{solid[tone]}">'
        f"{escape(label)} {n}</div>"
        for label, n, tone in parts
        if n
    )
    return f'<div class="stack">{cells}</div>'
