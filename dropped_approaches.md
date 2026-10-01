# Approaches we dropped or replaced

Things I tried or planned, and why I changed course.

| Dropped / replaced | Why | What replaced it |
|---|---|---|
| **Streamlit dashboard** | Arjun needs something for a board pack, and that's Excel. A web app also adds setup risk on a clean machine. | `run.py` writes `output/board_pack.xlsx` directly |
| **Shifting legacy timestamps from UTC to IST** | The policy says the legacy event log is UTC, so I first shifted them. A test showed legacy and helpdesk tickets have the same resolution-hour pattern and the same handle time, so the export is already IST. The shift would have made every legacy ticket look 5.5 hours slower. | No shift. The date format is now checked strictly, so an Excel-mangled file fails loudly |
| **Double payout cost of Rs 8.7 lakh** (refund + full replacement cost) | Overstated. The customer was owed one remedy, so only the extra one is lost money. | Conservative cost: the cheaper of the refund or the replacement (unit cost + Rs 340) |
| **Adding the two leaks together** (double payouts + goodwill above the cap) | 150 tickets were in both, so the first total counted the same money twice. | An overlap-free total |
| **Counting refunds in the month the ticket was created** | Finance counts a refund when the money goes out. | Month resolved; month created only if not yet resolved |
| **One ticket per API call** | Slow and wasteful on the rate limit. | 20 tickets per call, so the whole project ran on the Gemini free tier |
| **A single 120-ticket gold set** | Too many to label carefully in the time. | A 60-ticket gold set plus two fresh 20-ticket holdouts, which also makes the test fairer |
| **Accepting whatever code the model returns** | It once invented a code ("WTY-BUYBUY"). | Codes outside the 9 valid ones are re-asked, or treated as UNCLEAR |
| **Using the model's confidence score to route tickets to human review** | Not calibrated: it said "high" for almost everything, including wrong answers. | Not used. Every answer carries an evidence quote instead |
| **Claude Haiku as the labelling model** | No key available. | Gemini 3.5 Flash-Lite (free tier) |

## Prompt versions (kept, not dropped)

| Version | What changed | Score on unseen tickets |
|---|---|---|
| v1 | Plain: "here are the codes, pick one" | 60% (gold set) |
| v2 | Policy definitions, "never refund and replace" rule with a yes/no field, shorthand glossary, UNCLEAR option, evidence quote | 82% gold · 70% on fresh holdout 2 |
| **v3 (final)** | One change: a return only counts once the item is back | 85% gold · **90% on fresh holdout 2** |

v3 was chosen with a rule written before running it: it had to be at least as good on 20 fresh tickets that played no part in writing it.

## Left out on purpose

SLA breach credits, repeat-contact and transfer costs, product/lot-code defect analysis, refund and replacement on *different* tickets for the same order, and a fourth prompt version. The reasons are in `submission-form.md`.
