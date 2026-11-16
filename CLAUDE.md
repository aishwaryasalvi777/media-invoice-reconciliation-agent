# Media Invoice Reconciliation Agent

An agent that checks publisher bills for an ad agency. The client (Pepsi) pays the ad agency (GroupM), and the ad agency (GroupM) buys ads from publishers (Instagram, Facebook, YouTube, Hulu, TikTok). Each month the publishers send bills. For every bill line, the agent compares:

- **what was ordered**: the media plan
- **what was delivered**: the delivery counts
- **what the contract allows**: the billing rules
- **what was billed**: the invoice

It then decides one of: `approve`, `pay_less`, `dispute` or `send_to_human`.

## Status
Early stage. Project setup and sample data are ready. No reconciliation logic yet.

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
  - `describe.py`: `blank_form(Form)` lists a form's fields, kinds, rules and meanings (used by the notebook). Every form field needs a one-line note in `models.py`; a test enforces it.
  - `loaders.py`: `load_reference_data()` reads the media plan, delivery files and contracts (every cell as text), checks the files agree, and returns a `ReferenceData` bundle with lookups. Raises `DataLoadError` listing every problem.
- `tests/`: the tests

## Data: `data/sample/`
Read [data/sample/README.md](data/sample/README.md) before working on anything that touches the data. It covers the files, the invoice formats, the contract rules and the 13 planted problems.

- `media_plan.xlsx`, `delivery/*.csv` and `contracts.json` are clean.
- `invoices/` holds 10 messy bills in PDF, CSV and Excel. Each publisher uses a different layout.
- The sample dataset is fixed. Don't regenerate it or edit it.

## Hard rules
- **The notebook holds no real logic.** `notebooks/walkthrough.ipynb` only calls code from `src/invoice_recon/` (plus small display code), keeps its outputs, and gets one new section per finished step.
- **Never write secrets (API keys, passwords) in code or in any committed file.** They go only in the private `.env` file or environment variables, read through `config.py`. `.env.example` holds placeholder values only.
- **The system must never read `data/sample/answer_key.csv`.** Only tests may use it, to score the agent's answers. Never use it as an input, a hint or a lookup.
- A purchase order number covers a whole campaign at one publisher, not a single plan line. Don't match bill lines using the purchase order number alone.
- An invoice that differs from the plan isn't automatically wrong. Some differences are allowed by the contract (for example, Hulu February over-delivery within the contract cap should be approved).

## Writing conventions
- Name each party by its role: client (Pepsi), ad agency (GroupM), publisher (Instagram, Facebook).
- Explain industry terms the first time they appear, for example "CPM (price per 1,000 views)".
