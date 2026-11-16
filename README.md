# Media Invoice Reconciliation Agent

# Problem Statement

The finance team (accounts payable, the team that pays supplier bills) was checking supplier invoices manually. For every invoice line, someone compared it by hand with the purchase order, the delivery records and the contract terms, usually in Excel sheets. This took hours every month, didn't scale as invoice volume grew, and mistakes were common. Overbilling went through unnoticed, and some fair invoices were wrongly rejected. On top of that, every supplier used a different invoice format (PDF, Excel, CSV), which made the manual work even slower. So I built an agent that does this check automatically. It reads the invoices, matches each line to the order, delivery and contract, and decides whether to approve, pay less, dispute, or send it to a person for review.

Checks publisher bills for an ad agency. For every bill line it compares what
was **ordered** (the media plan), what was **delivered** (delivery counts) and
what was **invoiced** (the bill), applies the contract rules, finds the cause
of any difference, and decides: approve, pay less, dispute, or send to a human.

**Status:** early stage. The project setup and sample data are ready; the
reconciliation logic is not built yet.

## Setup

Needs [uv](https://docs.astral.sh/uv/) (installs Python and all libraries).

```bash
uv sync          # install Python 3.12 and the exact library versions from uv.lock
uv run pytest    # run the tests
uv run pre-commit install   # once: run code checks automatically before each commit
cp .env.example .env        # optional: your private settings (never committed)
```

## Layout

```
src/invoice_recon/   the code
tests/               the tests
data/sample/         fixed sample dataset (see data/sample/README.md)
```
