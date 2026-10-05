# Customers are being paid twice, and the helpdesk can't see most of it

**To:** Arjun Mehta, Finance Controller · **From:** Abhishek Bidare · **Period:** Jan 2025 – Jun 2026 · **Detail:** `board_pack.xlsx`

**The headline:** about **80 customers a quarter get a refund *and* a replacement for the same order**, which Vireo's policy says must never happen. That's roughly **1 in 6 refunds**, and it costs at least **Rs 1.4 lakh a quarter (Rs 6.6 lakh over the last 18 months)**. **More than half of these cases don't show up in the helpdesk at all**; they're only written in the agents' notes. Stopping it would save about **Rs 1.2 lakh a quarter, around Rs 5 lakh a year**.

### 1. The double payouts

| | Q1 '25 | Q2 '25 | Q3 '25 | Q4 '25 | Q1 '26 | Q2 '26 |
|---|---|---|---|---|---|---|
| Refunds that also got a replacement | 29 | 38 | 57 | 78 | 82 | 78 |
| Share of all refunds | 14% | 15% | 14% | 14% | **18%** | **17%** |

- **It's growing.** The count has nearly tripled since early 2025, and in 2026 the share went up too.
- **The helpdesk misses most of it.** The "replacement issued" tick-box flags 166 of the 363 cases. The other 197 only appear in the agent's closing note, for example "credited full amount, new unit also going out tomorrow".
- **It's mostly two teams:** Logistics and Chat Frontline account for about 6 in 10 cases. Three agents alone account for a quarter.
- **It's usually deliberate.** The notes give the reasons: "customer threatened social media", "customer was very upset", "to avoid escalation". In at least 31 cases the note says a Team Lead was aware. The policy says these cases must reach both the Team Lead *and* Finance the same day.
- **How we counted the cost:** the customer was owed one remedy, so we count only the extra one (the cheaper of the refund or the replacement). The total paid out on these orders is about Rs 4 lakh a quarter, so Rs 1.4 lakh is the conservative figure.
- **There may be more.** We counted refund and replacement on the *same* ticket. Another 157 refunds had a replacement on a *different* ticket for the same order. Some of those are legitimate, so we haven't added them, but they're worth a look.

### 2. What we recommend
1. **Block refund + replacement on the same order** in the helpdesk unless a Team Lead and Finance both approve, and send Finance a **daily exception list**. The policy already requires same-day escalation; this makes it happen. **Goal: from 17% of refunds to under 2%, from about Rs 1.4 lakh to Rs 0.2 lakh a quarter, saving about Rs 1.2 lakh a quarter.**
2. **Make the replacement flag automatic** whenever a replacement order is raised, so the helpdesk stops under-reporting.
3. **Don't release a return refund until the item has been picked up.** We found 65 refunds paid while the pickup was missed or still pending, mostly on the Returns Desk.
4. **Clean up the dropdown:** remove "Goodwill / Other" as the default and add a "Wrong item shipped" code.

### 3. The refund total itself
Your export adds up to Rs 23 crore for 18 months, but that isn't real money. Old Freshdesk rows store amounts in **paise** (100× too big), and **638 tickets appear twice** from the migration. Fixing both gives **Rs 67.1 lakh, about Rs 12.6 lakh a quarter**, reconciled to the rupee and in line with the helpdesk's own figure of about Rs 11 lakh. For Finance's reconciliation: divide amounts on old Freshdesk rows by 100, and drop the duplicates.

Refunds rose from Rs 6.0 lakh (Q1 '25) to a Q4 '25 peak of Rs 16.7 lakh, around the time the frontline was asked to stop arguing with customers. **Mostly, ticket volume doubled**: about 1 in 5 tickets ends in a refund every quarter, and the average refund stayed at Rs 2,700–3,000.

### 4. Other things in the board pack
- **43% of refund money was coded "Goodwill / Other"**, the default dropdown option. Reading the notes, less than a third of that is really goodwill. The board pack shows the agents' codes and a corrected view side by side.
- **Goodwill above the Rs 500 cap** adds about Rs 0.5 lakh a quarter on top of the double payouts. Total paid against policy: about Rs 1.9 lakh a quarter.
- **Agent detail** is in the Excel, shown with each agent's team and refund rate, so teams that refund by design aren't penalised.

### How sure are we?
- **The totals** are checked automatically and match to the rupee.
- **Finding double payouts in the notes:** we used AI to read them, and tested it on 100 tickets we'd checked by hand first. It found every double payout with no false alarms. On 20 it found that the tick-box had missed, we checked each one by hand: 18 confirmed, 2 likely, none wrong.
- **Reason codes:** the AI matches hand-checked answers about 9 times in 10; the agents' own codes match about 4 in 10.
- **CSAT:** we couldn't find the +0.4 rise in this export; it's around 3.5 every quarter. Worth checking with Priya which measure she meant.
