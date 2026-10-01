# Work log — Vireo Audio refund analysis (Task 1, Set C)

A running record of what we read, what we understood, what we built, what we found and what we threw away. Numbers here are taken from the notebook outputs.

---

## 0. The brief, in our own words

**What Arjun (Finance Controller) asked for:** a monthly summary of refunds by reason code and by agent — "who is giving away money and for what" — for the board pack, and "I want the total to reconcile".

**What is actually going on (from the email thread):**
- Arjun's own sum of the export says refunds are **well over Rs 1 crore a quarter**.
- The helpdesk's built-in report says **~Rs 11 lakh a quarter**.
- Both come from the same data, so one of them is reading it wrong.

**So the real job, in order:**
1. **Fix the number:** clean the export and get one true refund total that reconciles, step by step.
2. **Explain the number:** by month, reason and agent, with reason codes we can actually trust.
3. **Act on it:** find refunds that break Vireo's own policy and put a rupee figure on them (the business goal).

**What the deliverables need:** a working AI-assisted tool that runs from a README, a business goal as a number, proof it works (and how often it doesn't), a one-page memo, a ≤3 min screen recording and the submission form. About 5 hours, and scope choices are judged.

---

## 1. Files we were given and what each one told us

| File | What we took from it |
|---|---|
| `tickets.csv` | 12,238 rows, Jan 2025 – Jun 2026. Refund amount, reason code, replacement flag, customer message, agent note, source system |
| `agents.csv` | 44 agents, one roster row each (code still handles from/to dates) |
| `orders.csv`, `customers.csv`, `products.csv` | Reference data. `products.unit_cost_inr` is needed for the replacement cost |
| `support-policy.pdf` | The rules: replacement cost = unit cost + Rs 340, goodwill capped at Rs 500, **never refund + replacement on the same order**, Returns Desk should do the "large majority" of refunds, legacy tool stored money "in its own native unit", legacy event log in UTC, CSAT blanks excluded |
| `EMAIL_THREAD.txt` | The hints: legacy rows store money differently (Sameer), GW-OTHER is the first option in the dropdown, some tickets appear twice, Priya says CSAT went up 0.4, Neha says refund + replacement cases are "one-offs" |
| `README.txt` | Column meanings: use agent_id not name, customer_id + sku is the fallback join when order_id is blank |

The email thread is basically a list of traps. We checked every claim in it against the data instead of trusting it.

---

## 2. Planning (`plan.md`)

- First plan: Python pipeline = rule-based cleaning, then an LLM to read free text, then reconciliation + Excel report + Streamlit app.
- Main idea we kept the whole way: **rules for facts, AI only for text.** Paise, duplicates and time zones have one correct answer, so code handles them. Messy Hinglish notes ("rfnd", "cx", "pkp") are where an LLM is actually needed.
- An outside review of the plan said it was too big for 5 hours. We agreed and changed:
  - **dropped the Streamlit app** — Arjun needs Excel for a board pack, and it adds setup risk
  - gold set 120 → **60** tickets, prompts v1/v2/v3 → **v1 and v2 only**
  - **double payout cost corrected** — the customer was owed one remedy, so only the cheaper of (refund) or (unit cost + 340) is lost money, not both. Our first figure of Rs 8.7L was overstated, the corrected one was Rs 2.95L
  - refund month = **resolved date** (when money goes out), not created date
  - talk about teams and processes in the memo, not individual agents

---

## 3. Notebook 01 — understanding the data (`01_data_understanding.ipynb`)

Only exploration, no changes to the data.

| Check | Result |
|---|---|
| Duplicates | 12,238 rows but 11,600 unique tickets. **638 tickets appear twice**, always one helpdesk + one legacy_fd copy |
| What differs between the copies | **Only `refund_amount_inr`** |
| Legacy vs helpdesk amount | On all 125 pairs with a refund in both copies, legacy = **exactly 100x** helpdesk (900 vs 90,000) → legacy Freshdesk stored **paise** |
| Raw total | **Rs 23.01 crore** — this is Arjun's crore |
| Quick fix (÷100 + dedupe) | **Rs 67.1 lakh**, ~Rs 12–16 lakh a quarter → matches the helpdesk's ~11 lakh |
| Legacy dates | All before 14 Sep 2025 (helpdesk go-live) — consistent with the policy |
| Reason codes | **GW-OTHER = 42%** of refunds (991). 879 of them above the Rs 500 cap |
| Refund + replacement flag | 166 tickets, mostly Chat Frontline and Logistics, only 13 Returns Desk |
| Returns Desk share | 26% of refunds, not the "large majority" the policy describes |
| CSAT | Flat at 3.46–3.54 every quarter — we couldn't find the +0.4 |
| Joins | All agent, SKU and customer IDs match. 34% of tickets have no order_id, only 212 recoverable from the message |
| Free text | GW-OTHER samples often have an obvious real reason in the note. Some notes are empty ("as discussed ~Amit") |

---

## 4. Notebook 02 — cleaning + reconciliation (`02_cleaning.ipynb`)

| Step | What we did | Why |
|---|---|---|
| 1. Duplicates | Kept the helpdesk copy, dropped 638 legacy copies | Helpdesk is the live system and already in rupees |
| 2. Paise | legacy refund ÷ 100 | Proven by the 125 pairs with ratio exactly 100 |
| 3. Timestamps | **No shift** (see below) | Tested it, legacy is already IST in this export |
| 4. order_id | Regex from message (212), then customer + SKU **only when exactly one order matches** (3,032). 655 still missing | Don't guess an order when there are several |
| 5. Joins | Agent roster (date-valid row), product unit cost | Need team and replacement cost |
| 6. Flags | GW-OTHER over Rs 500, refund + replacement, conservative and upper double payout cost | Policy checks |
| 7. Reconciliation | Waterfall with an `assert` that every rupee lands in exactly one bucket | "I want the total to reconcile" |

**The reconciliation waterfall:**

| Step | Rs |
|---|---|
| Raw export total (as Arjun sums it) | 23,01,24,081 |
| less: duplicate re-import rows | −3,61,01,100 |
| less: legacy paise → rupees | −18,73,13,049 |
| **True refund total (18 months)** | **67,09,932** |

**True refunds by quarter (resolved-month basis):** Q1'25 6.0L · Q2'25 7.2L · Q3'25 11.7L · **Q4'25 16.7L** · Q1'26 12.6L · Q2'26 12.6L · Jul'26 0.29L (partial — 10 tickets created in June, resolved after the data ends). Refunds really did roughly double during 2025.

**The timestamp decision (an example of not trusting a hint blindly):** the policy says the legacy event log stores UTC, so we first added 5:30 to legacy resolved times. Then we tested it properly: legacy and helpdesk tickets had the **same resolution-hour pattern** (peaks at 12:00–22:00) and the **same median handle time (0.45h)**. A UTC shift would have made every legacy ticket look 5.5 hours slower. Decision: no shift, and the evidence is in the notebook.

Output: `output/tickets_clean.csv`, `output/waterfall.csv`.

---

## 5. Notebook 03 — AI re-coding (`03_ai_labelling.ipynb`)

### 5.1 Why AI is needed here
42% of refund money sits under GW-OTHER, the default dropdown option. The only place the real reason exists is the free text: the customer message and the agent's closing note, written in shorthand, Hinglish and IVR transcripts. Rules can't read that reliably, so this is where we use an LLM.

### 5.2 Evaluating without AI first
- **Gold set** (`eval/gold_set.csv`, `eval/gold_set_labelling.xlsx`): 60 refunds, stratified — 25 GW-OTHER above cap, 10 GW-OTHER at/below cap, 15 with other codes, 10 refund + replacement. Each labelled with the true reason, whether it's genuine goodwill, and whether a replacement was also given. **Labelled before any model output existed.** The labels were written with Claude Code (coding assistant) reading each ticket against the policy, with reasoning in the `my_comment` column — this is disclosed and should be spot-checked by hand.
- **Baseline 1 — the agent's own code:** how often the dropdown code agrees with the true reason.
- **Baseline 2 — keyword rules:** an ordered list of regexes on the note (cancel → CANCEL, deducted/UTR → DUP-PAYMENT, QC/reverse pickup → RETURN-QC-OK …). On the non-GW refunds it agreed with the agent's code only 52% of the time, and gave no answer for 372 of the 991 GW-OTHER refunds. Typical failure: "cancellation… already shipped, advised return" → keyword says CANCEL.

### 5.3 Model choice
- First plan was Claude Haiku. Switched to **Gemini** because that's the key available. Free tier for `gemini-3.5-flash-lite`: 15 requests/min, 250k tokens/min, 500 requests/day.
- `gemini-3.5-flash-lite`: stable (not preview), biggest free quota of the family, and this is a simple classification task.
- temperature 0, JSON output.
- **20 tickets per call** with a 5 s pause — fewer calls, stays under 15/min.
- Every answer is cached in `cache/llm_labels.jsonl` by ticket_id + prompt version, so re-runs are free and the final tool can run without a key.
- Stops on the first API error instead of retrying (don't burn quota). Ignores any ticket_id the model returns that we didn't send.

### 5.4 Prompt v1 (`prompts/v1.txt`) — deliberately plain
Structure: one line of role ("reading tickets where a refund was given"), the list of 8 codes with **no definitions**, the tickets as a JSON list, output `{"ticket_id", "code"}`.

**Result on the gold set: 65%.** 10 of its 21 mistakes were the same thing: it called any faulty product **DOA-REPL**, even when a replacement was sent or the fault was already fixed. It also had no way to say "I don't know".

### 5.5 Prompt v2 (`prompts/v2.txt`)
Structure:
1. **Role:** auditing refunds for Vireo; each ticket already had a refund paid.
2. **Code definitions taken from the policy PDF** (DOA = within 7 days and refund chosen instead of replacement, etc.) plus **UNCLEAR**.
3. **Rules:**
   - the agent note says what was done, the customer message only what was asked
   - policy: never refund + replacement → flag `replacement_also_given`
   - a fault that was replaced or fixed is not DOA/buy-back → GW-OTHER
   - wrong item shipped has no code → GW-OTHER
   - "refund not credited" tickets → RETURN-QC-OK only if a return/pickup/QC is mentioned, else UNCLEAR
   - shorthand glossary (rfnd, rplc, cx, pkp, PG, FR, RMA)
   - don't guess
4. **Five made-up examples** (not taken from the gold set, to avoid fitting the test).
5. **Output:** `code`, `replacement_also_given`, `confidence`, `evidence` (≤12 words quoted from the ticket, so a human can verify in seconds).

### 5.6 Evaluation results

**Gold set (n = 60):**

| Method | Reason code accuracy |
|---|---|
| Agent's original code | 31.7% |
| Keyword rules | 38.3% |
| LLM v1 | 65.0% |
| **LLM v2** | **86.7%** |

On the GW-OTHER-above-cap stratum (the money question), v2 got 96%.

**Refund + replacement detection (gold set):** the agents' Y/N flag caught **10 of 17**. LLM v2 caught **17 of 17, 0 false alarms**.

**Fresh holdout (n = 20, new tickets, labelled before running)** — a check that v2 wasn't just fitted to the gold set, since v2 was written after seeing v1's gold-set mistakes:

| Method | Accuracy |
|---|---|
| Agent's code | 35% |
| Keyword rules | 65% |
| **LLM v2** | **90%** |

Replacement detection 3/3, 0 false alarms.

**What v2 still gets wrong:** "pickup missed" refunds (calls them LOST-TRANSIT), and refund + new unit on a return or transit case (calls it GW-OTHER where we said the underlying reason). The `confidence` field turned out to be useless — almost everything comes back "high", including the wrong ones.

### 5.7 Full run
- Sent: all 991 GW-OTHER refunds + 260 other refunds whose note mentions a replacement / new unit / RMA = **1,251 tickets**. Everything else keeps the agent's code.
- Final reason = AI code only where the agent chose GW-OTHER. The original code is always kept next to it — we never overwrite a financial record.

**Results:**
- Of the 991 GW-OTHER refunds, only **203 (Rs 7.1L) are genuine goodwill**. The rest have a real reason: returns 206, failed/duplicate payments 177, transit 136, cancellations 121, unclear 63, …
- Of the **879 GW-OTHER above the Rs 500 cap:** 628 mis-coded (Rs 19.9L — a dropdown problem, not lost money), **196 genuine goodwill above the cap (Rs 7.1L)**, 55 unclear. The amount above Rs 500 is roughly **Rs 1.1–2.0L a quarter** (peak Q4'25).
- **Double payouts:** 166 by the agent flag → **365 with the AI reading the notes** (199 the flag missed). Conservative leak ~**Rs 1.4L a quarter** in 2026 (Q1 1.39L, Q2 1.42L), up from ~0.5L in Q1'25. Top team: Logistics until Q3'25, Chat Frontline since.
- 1 GW-OTHER ticket didn't come back from the model; the next run picks it up.

Output: `output/refunds_labelled.csv` — one row per refund with the original code, AI code, evidence quote, double payout flag and leak. The total still comes to **Rs 67,09,932**.

### 5.8 Cost (actual)

| Run | Calls | Input tokens | Output tokens |
|---|---|---|---|
| v1 on gold set | 3 | 6,725 | 2,064 |
| v2 on gold set | 3 | 8,528 | 3,945 |
| v2 holdout | 1 | 2,828 | 1,291 |
| v2 full run | 60 | 167,794 | 80,866 |
| **Total** | **67** (+1 connection test) | **~186k** | **~88k** |

All on the Gemini free tier → **Rs 0**. Per ticket: ~140 input + ~65 output tokens. At Vireo's volume (~650 tickets/week, roughly 700 refund-related a month) that's ~35 calls a month, still inside the free tier. At paid Flash-Lite-class pricing it would be a few rupees a month.

---

## 6. Things we found that nobody asked about

- **The replacement flag is unreliable:** agents tick "replacement issued" in fewer than half the cases where the note says a new unit was sent.
- **No reason code exists for "wrong item shipped"**, so agents fall back to GW-OTHER.
- **Amounts that don't match the note:** e.g. note says Rs 332, field says Rs 3,324; note says "advised coupon terms, resolved" but Rs 6,648 was refunded; "order manually created" but a refund was still recorded.
- **Refunds paid before the item was picked up** (pickup missed → refund released anyway).
- **Notes like "both refund and replacement given as cx threatened social media"** — the double payouts are often a deliberate escalation tactic, not a mistake.
- **CSAT did not move** (3.54 → 3.46), which questions the "refunds up, CSAT up 0.4" trade-off.
- **Returns Desk handles only 26% of refunds**; frontline teams refund directly.

---

## 7. What we threw away (and why)

| Dropped | Why |
|---|---|
| Streamlit dashboard | Arjun needs Excel for the board pack; extra setup risk on a clean machine |
| UTC → IST shift on legacy timestamps | Tested and found the data is already IST; the shift would have been wrong |
| Rs 8.7L double payout figure (refund + full replacement cost) | Overstated — only the extra remedy is lost. Replaced with the conservative min() |
| Created-date month basis | Finance counts refunds when money goes out → resolved date |
| One ticket per API call | Wasteful; batching 20 per call cut calls 20x |
| Prompt v3 and a 120-ticket gold set | Not enough time for both done well; v1 → v2 already shows the improvement |
| Using the model's `confidence` to route to human review | Not calibrated — "high" was still wrong ~13% of the time |
| Claude Haiku as the model | No key available; Gemini free tier did the job |

---

## 8. Honest caveats so far

- Gold and holdout labels were written with an AI coding assistant (Claude Code), not purely by hand. Disclosed; the evidence is in `my_comment` and should be spot-checked.
- n = 60 and n = 20 are small; per-code accuracy is not reliable at that size.
- The 199 AI-only double payouts have not been individually verified yet.
- Double payouts and over-cap goodwill can overlap — they must not be simply added together.
- Tickets not sent to the AI (non-GW refunds without replacement words in the note) keep the agent's code and can't add to the double payout count, so 365 is a floor, not a ceiling.

---

## 9. Files produced so far

```
plan.md                          plan + reasoning
logs.md                          this file
01_data_understanding.ipynb      exploration
02_cleaning.ipynb                cleaning + reconciliation waterfall
03_ai_labelling.ipynb            gold set, baselines, LLM v1/v2, holdout, full run
prompts/v1.txt, prompts/v2.txt   prompt versions
eval/gold_set.csv / .xlsx        60 labelled tickets
eval/holdout.csv                 20 labelled holdout tickets
cache/llm_labels.jsonl           every model answer (lets the tool run without a key)
output/tickets_clean.csv         11,600 cleaned tickets
output/waterfall.csv             reconciliation
output/refunds_labelled.csv      2,340 refunds with AI reason + double payout flag
```

## 10. Spot-check of AI-only double payouts (`eval/spotcheck_double_payouts.csv`)

- 20 random of the 199 double payouts the agent flag missed, read by hand against the note.
- **18 clearly real** (note says refund AND new unit/replacement), **2 likely** (note shows only the replacement, the refund is in the amount field), **0 false alarms**.
- 1 evidence quote was taken from the customer message instead of the note — the flag was right, the quote was not.
- 72 of the 199 had a specific code (41 DOA-REPL, 31 WTY-BUYBACK), so agents pick a code but still don't tick "replacement issued".

## 11. Overlap and the final business goal number

- 150 of the 196 "real goodwill over cap" refunds are **also** double payouts (makes sense: a refund + replacement on a fault gets re-coded as GW-OTHER).
- Adding the two leaks would count the same money twice. Rule: if a ticket is a double payout, its goodwill excess is not counted again.
- **Policy leak, 2026 average per quarter: ~Rs 1.71 L** = double payouts Rs 1.40 L + goodwill above cap (not already counted) Rs 0.30 L. That is ~13.5% of the ~Rs 12.6 L refunded per quarter, ~Rs 6.8 L a year.
- Earlier rough figure of ~Rs 2.5 L/quarter thrown away (double counted).

## 12. The tool: `run.py` builds the board pack directly

Decision: no Excel built in a notebook first — that would mean building it twice. One script:
`clean (same steps as 02) → read cached AI labels → compute → write output/board_pack.xlsx`

- `python run.py` runs with **no API key** (cache only). `python run.py --label` asks Gemini only for refunds missing from the cache.
- Sheets: Summary, Quarterly, Waterfall, By reason (agent code / corrected), **By agent**, Exceptions (411 rows with note + AI evidence), AI accuracy (recomputed from the eval files), Method.
- **By agent** answers "who is giving away money" fairly: team next to every agent, tickets handled, refund rate = refunds ÷ tickets handled, double payouts and over-cap goodwill per agent, sorted by policy leak not raw refund Rs. Returns Desk has a 50% refund rate (its job) but low leak; leak sits in Logistics (Rs 2.28 L) and Chat Frontline (Rs 2.13 L). Excel only, not in the memo.
- Output matches the notebooks: true total Rs 67,09,932, policy leak Rs 1,70,648/quarter.

## 13. Tests (`tests/test_pipeline.py`)

Three checks, import from `run.py`: waterfall adds back to the raw total, no duplicate ticket_ids, monthly totals = Rs 67,09,932. **3 passed.**

**Clean-machine check:** copied only the repo files to an empty folder, new venv, `pip install -r requirements.txt`, `python run.py`, `pytest` → board pack written, 3 passed, no API key.

## 14. Business goal written into the tool + `--label` tested

- **Goal (computed in `run.py`, top of the Summary sheet):** *Cut refunds that also got a replacement from 17% of refunds to under 2%, worth about Rs 1.2 lakh a quarter (Rs 5.0 lakh a year).*
  - 2026 average: 17.4% of refunds (~80 a quarter) also got a replacement, costing Rs 1.40 L a quarter (~Rs 1,740 each, conservative). Up from 13.3% in Q1'25.
  - Target is under 2%, not zero: some team-lead-approved exceptions will happen. Saving = cases avoided × average cost per case.
  - Second goal (visibility, no rupee value): GW-OTHER is ~43% of refunds; make the reason mandatory / remove it as the default and get it under 10%.
- `python run.py --label` tested end to end: found the 2 refunds missing from the cache, labelled them in 1 call; the next run found 0 missing and made no calls. Tests still pass.

## 15. Incident: CSVs re-saved by Excel + robustness fix

- `tickets.csv`, `eval/gold_set.csv` and `eval/holdout.csv` got re-saved by Excel. Timestamps became US format (`1/1/2025 9:17`, 36,092 cells), the holdout `ticket_id` header became `/`, and blank rows and columns were added. `run.py` crashed.
- Checked before fixing: no labels were actually changed. Backed up the Excel-saved copies, restored `tickets.csv` from git, tidied the eval CSVs.
- Fix so it can't silently happen again: `run.py` now parses dates with an explicit `%Y-%m-%d %H:%M` format (an Excel-mangled file fails loudly instead of mixing up day and month), and skips a broken eval file with a warning. Same numbers after the fix, tests pass.
- Lesson: edit labels only in the `.xlsx`, never open the CSVs in Excel.

## 16. Extra checks run while looking for improvements

- **Refund larger than the order value:** 0 of 2,209 refunds with a known order. Good: nobody refunds more than the customer paid.
- **Amount in the note ≠ amount in the field:** only 2 of 1,503 notes that state an amount (e.g. note Rs 332 vs field Rs 3,324).
- **Evidence quote really in the ticket:** for ~93% of AI answers the start of the evidence quote is found in the note or message; ~6.5% aren't found verbatim (paraphrased or merged quotes). Crude check, not a hallucination rate.
- **Refund and replacement on different tickets for the same order:** 157 more refunds (Rs 4.3 L) beyond the within-ticket ones. Mostly *not* double payouts (e.g. a duplicate-payment refund, then a warranty replacement months later). But some look wrong: an order "cancelled before dispatch" and refunded, then a DOA replacement shipped later on the same order, so the product was delivered anyway. Needs proper rules and review → listed as a next step, NOT added to the numbers.

## 17. Next
- Review the 60 gold labels by hand and note how many I changed
- Memo to Arjun (1 page, non-technical)
- Submission form
- Screen recording (≤3 min): prompts v1 → v2, what changed, what was thrown away
