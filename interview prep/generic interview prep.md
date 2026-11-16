# Generic Interview Prep: Invoice Reconciliation Agent

Use this version in any interview, in any industry (supply chain, retail, manufacturing, healthcare, logistics and so on).

## Goal
Build an agent (a program that makes decisions on its own) that checks supplier invoices before the company pays them.

## Problem
Every company buys from suppliers, and each supplier sends invoices in its own format (PDF, spreadsheet, CSV file). Before paying, someone must check each invoice line by hand against three records:
- **What we ordered:** the purchase order or plan
- **What we received:** the delivery or receipt records
- **What the contract allows:** agreed prices, limits and terms

This is often called "three-way matching". It is slow, repetitive and easy to get wrong. Overbilling means lost money. Wrongly rejecting a fair invoice damages the supplier relationship. Also, an invoice that differs from the order isn't automatically wrong. The contract may allow some differences, such as extra quantity within an agreed limit.

## How we solve it
1. **Extract:** read invoices in any format and turn them into one clean structure.
2. **Match:** link each invoice line to the right order line. A purchase order number alone is not enough, because one order can cover many items.
3. **Compare:** check quantity, price and contract rules for each line.
4. **Decide:** choose one of four outcomes:
   - `approve`: pay in full
   - `pay_less`: pay only the correct amount
   - `dispute`: reject and challenge the supplier
   - `send_to_human`: ask a person when unsure
5. **Test:** run it on sample data with known planted errors and score how many it catches.

## How to say it in one line
"I built an agent that automates invoice checking. It reads messy supplier invoices, matches them to orders, receipts and contract terms, and decides whether to pay, reduce, dispute or escalate to a person."

## Interview angle
This works for supply chain, retail, manufacturing, healthcare, logistics and any other industry that pays suppliers. The core skills are the same everywhere:
- Extracting data from messy documents
- Matching records that don't line up exactly
- Applying business rules
- Knowing when to hand a decision to a human

If they ask "why not just use rules?", say invoice formats vary too much for fixed rules, and judgment calls need a person's review.

## In simple terms
This is a program that checks supplier bills against what was ordered, received and promised in the contract. It pays the right amount, flags wrong bills, and asks a person when it is unsure.
