# Sample dataset

A fixed, hand-designed dataset. It is created once and never regenerated.

**Story:** the client (Pepsi) gave the ad agency (GroupM) about $3M for three
campaigns running January to March 2026. The ad agency (GroupM) bought ads from
5 publishers: Instagram, Facebook, YouTube, Hulu and TikTok. It is now early
March, and the ad agency (GroupM) must check the January and February bills
from the publishers.

## Files

| File | What it is | Clean or messy |
|---|---|---|
| `media_plan.xlsx` | What was **ordered**: 40 plan lines (8 per publisher) | Clean |
| `delivery/delivery_2026-01.csv`, `delivery_2026-02.csv` | What was **delivered**: views per plan line per month, counted by the publisher and by the ad agency's (GroupM's) ad server | Clean |
| `contracts.json` | Billing rules agreed with each publisher | Clean |
| `invoices/` | What was **invoiced**: 10 bills (5 publishers × 2 months), 73 lines | **Messy on purpose** |
| `answer_key.csv` | The correct answer for every invoice line. **Used only for testing. The system must never read it.** | — |

### Invoice formats (each publisher has its own style)

| Publisher | Format | What makes it tricky |
|---|---|---|
| Instagram | PDF (landscape table) | Short codes in descriptions ("PZS \| Reels \| JAN26") |
| Facebook | CSV export | Campaign and ad name in separate columns; a "Total" row at the end |
| YouTube | Excel | Header block above the table; table starts on row 8; total row at the bottom |
| Hulu | PDF (portrait "statement") | Different column names ("Delivered Imps", "Net Cost"); dollar signs |
| TikTok | Excel | Numbers stored as text ("2,152,202", "$22,060.07"); merged title cell; extra "Notes" sheet |

About 75% of invoice lines carry the purchase order number. The rest must be
matched using the publisher's wording only.

## Key terms

- **Impression / view:** one time the ad is shown to someone.
- **Price per 1,000 views** (the industry calls this "CPM"): $10 means $10 for every 1,000 views, so 1 cent per view.
- **Purchase order number:** the number on the official order the ad agency (GroupM) sent to the publisher. One purchase order covers all lines of one campaign at one publisher, so it does **not** identify a single plan line by itself.
- **Ad server count:** views counted by the ad agency's (GroupM's) own tool, used to check the publisher's count.

## Contract rules (from `contracts.json`)

The amount the ad agency (GroupM) should pay for a plan line in a month is:

1. **Pick the count.** If `bill_on` is `publisher_count`, use the publisher's count, unless it is more than `allowed_difference_percent` above the ad server count. In that case use the ad server count. If `bill_on` is `ad_server_count`, always use the ad server count.
2. **Cap it.** Never pay for more than that month's planned views plus `pay_for_extra_views_up_to_percent`.
3. **Multiply** by the plan's price per view.

That month's planned views are the plan line's total views split by the number of flight days in each month.

## Planted problems (13 of 73 lines)

| Cause | Where | Expected decision |
|---|---|---|
| `over_delivery_billed` | Instagram Jan | pay_less |
| `outside_flight_dates` | Instagram Jan | dispute |
| `duplicate_line` (same invoice) | Instagram Feb | dispute |
| `count_mismatch_beyond_tolerance` | Facebook Jan | pay_less |
| `cancelled_line_billed` | Facebook Feb | dispute |
| `math_error` (two digits swapped) | YouTube Jan | dispute |
| `rate_mismatch` | YouTube Feb, TikTok Jan | send_to_human |
| `no_matching_order` | YouTube Feb | send_to_human |
| `billed_on_wrong_count` | Hulu Jan | pay_less |
| `over_delivery_within_contract` | Hulu Feb | **approve** (a trap: the bill differs from the plan but is correct) |
| `over_delivery_beyond_contract` | Hulu Feb | pay_less |
| `duplicate_line` (January billed again in February) | TikTok Feb | dispute |

Another trap: a TikTok plan line was cancelled on Feb 1 and correctly does
**not** appear on the February bill. The system should not flag it.

All other lines have cause `none` and decision `approve`.

## Simplifications (worth mentioning in an interview)

- The over-delivery cap is checked per month, not over the whole campaign.
- No taxes, currency conversion, agency fees or credit notes.
- Rate changes are never approved here, so every rate mismatch goes to a human. Email evidence of agreed rate changes is a planned later addition.
