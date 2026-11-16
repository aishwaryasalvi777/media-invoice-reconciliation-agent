# Project-Specific Interview Prep: Media Invoice Reconciliation Agent

Use this version when the interviewer asks about the actual project setup (advertising).

## Goal
Build an agent (a program that makes decisions on its own) that checks the monthly bills from publishers (Instagram, Facebook, YouTube, Hulu, TikTok) for the ad agency (GroupM), who buys ads for the client (Pepsi).

## Problem
Every month each publisher sends bills in a different layout (PDF, CSV, Excel). Someone has to check each bill line by hand against four things:
- **What was ordered:** the media plan
- **What was delivered:** the delivery counts
- **What the contract allows:** the billing rules
- **What was billed:** the invoice

That is slow and easy to get wrong. Overbilling costs money. Wrongly rejecting a fair bill upsets the publisher. A bill that differs from the plan isn't automatically wrong. For example, Hulu delivering extra views in February is fine if it stays within the contract's limit.

## How we solve it
1. Read the 10 messy sample bills and turn them into one clean, common format.
2. Match each bill line to the right plan line. We can't use the purchase order number alone, because it covers a whole campaign.
3. Compare the line against delivery and contract rules.
4. Decide one of four outcomes: `approve`, `pay_less`, `dispute`, or `send_to_human` (when unsure).
5. Test it on the sample data, which has 13 planted problems. Only the tests may read the answer key, never the agent.

## Status
Right now only the sample data exists, and the code is just starting.

## Interview angle
Say it as "an invoice reconciliation agent: it extracts messy documents into one format, matches them to the plan, applies contract rules, and escalates to a human when unsure." This shows you understand real finance operations and know when to keep a human involved.

## In simple terms
The project builds a program that checks publisher bills against what was ordered, delivered and allowed by the contract. It pays correct bills, cuts or disputes wrong ones, and asks a person when it is unsure.
