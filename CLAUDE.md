# Media Invoice Reconciliation Agent

An agent that checks publisher bills for an ad agency. The client (Pepsi) pays the ad agency (GroupM), and the ad agency (GroupM) buys ads from publishers (Instagram, Facebook, YouTube, Hulu, TikTok). Each month the publishers send bills. For every bill line, the agent compares:

- **what was ordered**: the media plan
- **what was delivered**: the delivery counts
- **what the contract allows**: the billing rules
- **what was billed**: the invoice

It then decides one of: `approve`, `pay_less`, `dispute` or `send_to_human`.

## Status
Early stage. Only the sample data exists. There is no code yet, so there are no build, test or run commands.

## Data: `data/sample/`
Read [data/sample/README.md](data/sample/README.md) before working on anything that touches the data. It covers the files, the invoice formats, the contract rules and the 13 planted problems.

- `media_plan.xlsx`, `delivery/*.csv` and `contracts.json` are clean.
- `invoices/` holds 10 messy bills in PDF, CSV and Excel. Each publisher uses a different layout.
- The sample dataset is fixed. Don't regenerate it or edit it.

## Hard rules
- **The system must never read `data/sample/answer_key.csv`.** Only tests may use it, to score the agent's answers. Never use it as an input, a hint or a lookup.
- A purchase order number covers a whole campaign at one publisher, not a single plan line. Don't match bill lines using the purchase order number alone.
- An invoice that differs from the plan isn't automatically wrong. Some differences are allowed by the contract (for example, Hulu February over-delivery within the contract cap should be approved).

## Writing conventions
- Name each party by its role: client (Pepsi), ad agency (GroupM), publisher (Instagram, Facebook).
- Explain industry terms the first time they appear, for example "CPM (price per 1,000 views)".
