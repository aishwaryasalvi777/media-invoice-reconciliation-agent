# Media Invoice Reconciliation Agent

An agent that checks publisher bills for an ad agency. The client (Pepsi) pays the ad agency (GroupM), and the ad agency (GroupM) buys ads from publishers (Instagram, Facebook, YouTube, Hulu, TikTok). Each month the publishers send bills. For every bill line, the agent compares:

- **what was ordered**: the media plan
- **what was delivered**: the delivery counts
- **what the contract allows**: the billing rules
- **what was billed**: the invoice

It then decides one of: `approve`, `pay_less`, `dispute` or `send_to_human`.

## Status
Milestone 1 (thin version, Facebook only, no AI) is finished: the 14 Facebook bill lines are read, matched, checked against the contract, given a decision, and score 14 of 14 against the answer key. Next: Milestone 2 (all 10 bills, including PDF and Excel).

## Commands
- `uv sync`: install Python 3.12 and the exact library versions from `uv.lock`
- `uv run pytest`: run the tests
- `uv add <library>` / `uv add --dev <library>`: add a library (updates `pyproject.toml` and `uv.lock`)
- `uv run ruff check .` / `uv run ruff format .`: find mistakes / fix code layout
- `uv run mypy`: check data types (strict mode, covers `src/` and `tests/`)
- `uv run pre-commit run --all-files`: run every commit check by hand. They also run automatically on each `git commit`; a failure stops the commit.
- After cloning, run `uv run pre-commit install` once to switch the automatic checks on.
- `uv run jupyter lab`: open the walkthrough notebook in the browser (`notebooks/walkthrough.ipynb`).
- Settings: copy `.env.example` to `.env` (optional; the defaults work). All settings live in `src/invoice_recon/config.py` and start with `INVOICE_RECON_`.

## Layout
- `src/invoice_recon/`: the code
  - `config.py`: all settings
  - `models.py`: the 5 forms (PlanLine, DeliveryRecord, InvoiceLine, ContractTerms, Result). Money is always `Decimal`, never `float`.
  - `money.py`: the money rules. `to_cents()` rounds half up to whole cents, `cost_of_views()` = views × price per 1,000, `total()` adds lines that are already rounded. **All money math goes through these functions.**
  - `describe.py`: `blank_form(Form)` lists a form's fields, kinds, rules and meanings (used by the notebook). Every form field needs a one-line note in `models.py`; a test enforces it.
  - `loaders.py`: `load_reference_data()` reads the media plan, delivery files and contracts (every cell as text), checks the files agree, and returns a `ReferenceData` bundle with lookups. Raises `DataLoadError` listing every problem.
  - `matching.py`: `match_line()` finds the plan line a bill line was ordered on (PO narrows to a campaign, wording and ad type pick the line; no date or status filter). Facebook wording only so far.
  - `contract_math.py`: `payable()` = what should be paid for a plan line in a month (pick count, cap, multiply by the plan's price)
  - `causes.py`: `find_cause()` runs one check per cause and returns the cause with evidence
  - `decide.py`: `decide()` turns a cause into approve / pay_less / dispute / send_to_human, with guards
  - `reconcile.py`: `reconcile_lines(lines, ref)` runs the whole chain and returns one `Result` per line
  - `display.py`: small HTML drawing helpers (flow boxes, tiles, tables, badges, bars) for the notebook. Display only, no logic.
  - `readers/`: one file per publisher that reads its bill into `InvoiceLine` forms. `facebook.py` reads the Facebook CSVs: `read_facebook_invoice(path)` / `read_facebook_invoices(folder)`. The "Total" row is skipped and used as a check. Raises `InvoiceReadError` listing every problem.
- `tests/`: the tests. `tests/scoring.py` is the only code that reads `answer_key.csv` (scores the answers; never an input to the system).

## Data: `data/sample/`
Read [data/sample/README.md](data/sample/README.md) before working on anything that touches the data. It covers the files, the invoice formats, the contract rules and the 13 planted problems.

- `media_plan.xlsx`, `delivery/*.csv` and `contracts.json` are clean.
- `invoices/` holds 10 messy bills in PDF, CSV and Excel. Each publisher uses a different layout.
- The sample dataset is fixed. Don't regenerate it or edit it.

## Hard rules
- **The notebook holds no real logic.** `notebooks/walkthrough.ipynb` only calls code from `src/invoice_recon/` (plus small display code), keeps its outputs, and gets one new section per finished step. **Keep it visual and simple** (pictures, tiles, coloured tables, a dashboard; 1 to 2 sentences per step; input → blank form → filled).
- **Never write secrets (API keys, passwords) in code or in any committed file.** They go only in the private `.env` file or environment variables, read through `config.py`. `.env.example` holds placeholder values only.
- **The system must never read `data/sample/answer_key.csv`.** Only tests may use it, to score the agent's answers. Never use it as an input, a hint or a lookup.
- A purchase order number covers a whole campaign at one publisher, not a single plan line. Don't match bill lines using the purchase order number alone.
- An invoice that differs from the plan isn't automatically wrong. Some differences are allowed by the contract (for example, Hulu February over-delivery within the contract cap should be approved).

## Writing conventions
- Name each party by its role: client (Pepsi), ad agency (GroupM), publisher (Instagram, Facebook).
- Explain industry terms the first time they appear, for example "CPM (price per 1,000 views)".
