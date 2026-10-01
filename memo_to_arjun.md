# Refunds: what the numbers really say

**To:** Arjun Mehta, Finance Controller · **From:** Abhishek Bidare · **Period:** Jan 2025 – Jun 2026 · **Detail:** `board_pack.xlsx`

**The short version:** refunds are running at about **Rs 12.6 lakh a quarter, not over a crore**. They did roughly double during 2025, mostly because the number of support tickets doubled. And about **Rs 1.9 lakh a quarter goes out against Vireo's own refund policy**, most of it customers getting a refund *and* a replacement for the same order.

### 1. Why your export said a crore
Your export adds up to Rs 23 crore for 18 months. That isn't real money. Two things in the data inflate it:
- Tickets from the old Freshdesk system store amounts in **paise**, so they look 100 times bigger than they are (−Rs 18.7 crore).
- **638 tickets appear twice** because of the migration re-import (−Rs 3.6 crore).

Fix both and you get **Rs 67.1 lakh**, with every rupee of the export accounted for. That lines up with the helpdesk's own report of about Rs 11 lakh a quarter.

### 2. What actually happened

| | Q1 '25 | Q2 '25 | Q3 '25 | Q4 '25 | Q1 '26 | Q2 '26 |
|---|---|---|---|---|---|---|
| Refunds (Rs lakh) | 6.0 | 7.2 | 11.7 | **16.7** | 12.6 | 12.6 |

Refunds climbed all through 2025, peaked in Q4, around the same time the frontline was asked to stop arguing with customers, and have settled at around Rs 12.6 lakh a quarter since.

**Why did they go up?** Mostly because support volume more than doubled: tickets went from about 1,050 a quarter to about 2,300. The share of tickets ending in a refund stayed at about 1 in 5, and the average refund stayed at Rs 2,700–3,000. Within that, genuine goodwill grew fastest, from Rs 0.5 lakh to about Rs 1.8 lakh a quarter, and refunds for returns grew from Rs 1.5 lakh to Rs 3.2 lakh.

### 3. Why "by reason" was hard to read
**43% of refund money was booked as "Goodwill / Other"**, which is simply the first option in the agents' dropdown. We had AI read the agents' notes on those tickets. Less than a third of that money is really goodwill. The rest is ordinary returns, failed payments, delivery problems and cancellations that were never coded properly. The board pack shows the agents' codes and the corrected view side by side.

### 4. Where money is leaking

**a) Refund and replacement together: about Rs 1.4 lakh a quarter.** Policy says a customer should never get both. In 2026, **17% of refunds (around 80 a quarter) also came with a replacement**. The helpdesk's "replacement issued" tick-box only catches fewer than half of them; the rest are only visible in the agents' notes. We count only the extra remedy, not both, so this is a conservative figure. Most of it comes from **Logistics and Chat Frontline**, and the notes often say why: "customer threatened social media", "customer was very upset".

**b) Goodwill above the Rs 500 cap: about Rs 0.5 lakh a quarter.** This counts only the part above Rs 500, and not tickets already counted in (a). The biggest pattern here: **65 refunds were paid even though the pickup had been missed or was still pending**, so the product had not come back when the money was paid. Most of those are on the **Returns Desk**.

Both look like process gaps rather than a few individuals. Agent-level detail, shown alongside each agent's team and refund rate, is in the Excel.

### 5. What we recommend
1. **Report refunds at about Rs 12.6 lakh a quarter.** For Finance's own reconciliation: divide amounts on rows from the old Freshdesk system by 100, and drop the duplicate tickets.
2. **Stop double payouts.** Block a refund and a replacement on the same order unless a Team Lead and Finance both approve, and send a daily exception list. The policy already requires same-day escalation of these cases; this makes it happen. **Goal: bring it down from 17% of refunds to under 2%, from about Rs 1.4 lakh to Rs 0.2 lakh a quarter, saving about Rs 1.2 lakh a quarter (around Rs 5 lakh a year).**
3. **Tighten the basics.** Don't release a return refund until the item is picked up. Remove "Goodwill / Other" as the dropdown default and add a "Wrong item shipped" code. Set the replacement flag automatically whenever a replacement order is raised.

### How sure are we?
- **Totals:** checked automatically. The raw export, the corrections and the true total match to the rupee.
- **AI reading the notes:** it matched hand-checked answers on **89 of 100 test tickets** (about 9 in 10). The codes agents picked matched about 4 times in 10. It found every refund-plus-replacement case in our test tickets, and when we checked 20 of the ones the tick-box had missed, 18 were confirmed, 2 likely, and none wrong.
- **The double payout count is a minimum:** we only re-read the refunds most likely to hide one.
- **CSAT:** we couldn't find the +0.4 rise in this export; it sits around 3.5 every quarter. Worth checking with Priya which measure she meant before the board meets.
