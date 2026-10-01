# Vireo Audio — Refund Reconciliation Tool: Detailed Plan

> Internship task: Task 1 V5, Set C · Time cap: ~5 hours · Client: Arjun Mehta (Finance Controller)

---

## 1. The problem in simple words

**What Arjun asked for:** "A monthly summary of refunds by reason code and by agent, which I can put in the board pack, and **the total must reconcile**."

**What is really going on:** Arjun says refunds are over **Rs 1 crore a quarter**. The helpdesk says **Rs 11 lakh a quarter**. Both come from the same export, so one of them is reading it wrong. Until we know which refund number is true, any "summary" is meaningless.

**So the real job is three steps, in this order:**
1. **Fix the number**: clean the export and give one refund total that reconciles, with every step explained.
2. **Explain the number**: split refunds by month × reason × agent, with the reason codes actually made trustworthy (using AI to read the free text).
3. **Act on the number**: find where money is leaking *against policy* and turn it into a business goal worth Rs X per quarter.

The evaluator is checking whether we (a) notice the data traps hidden in the email thread, (b) use AI only where it adds value, (c) prove our output is correct, and (d) make clear, written scope decisions.

---

## 2. What the data actually says (already checked, real numbers)

| # | Finding | Evidence | Impact |
|---|---|---|---|
| 1 | **Legacy Freshdesk amounts are stored in paise (×100)** | TK-240009: `2124` (helpdesk) vs `212400` (legacy_fd). Legacy median refund = 2,24,900 vs helpdesk 2,499. Policy §9: "legacy tool stored money in its own native unit" | Raw export total = **Rs 23.0 crore** over 18 months (~Rs 3.8 cr/quarter). This is Arjun's "crore". |
| 2 | **638 tickets appear twice** (once per source system) | 12,238 rows vs 11,600 unique ticket_ids. Sameer: "Some tickets appear twice from the migration re-import" | Double counting |
| 3 | **Correct total after cleaning = Rs 67.1 lakh** (2,340 refunds) | Per quarter: Q1'25 6.1L · Q2'25 7.3L · Q3'25 12.1L · **Q4'25 16.3L** · Q1'26 12.6L · Q2'26 12.8L | Matches the helpdesk's "~Rs 11 lakh a quarter". Refunds really did **double** from Q1'25 to Q4'25. |
| 4 | **GW-OTHER is a junk default**: 42% of refunds | First option in the dropdown ("agents are agents" — Sameer). Share grows 37% → 46%. Some agents use it for 89% of refunds | "By reason code" cannot be trusted for almost half the money |
| 5 | **879 GW-OTHER refunds are above the Rs 500 goodwill cap** | Policy §5: goodwill capped at Rs 500 with TL approval | Either the code is wrong or the policy is being broken. AI re-coding tells us which |
| 6 | **Refund + replacement on the same ticket: 166 cases** | Policy §5: "In no case" should both happen. Neha: "probably one-offs, Returns Desk is careful" | **Rs 8.7 lakh leaked** (refund + unit cost + Rs 340 shipping). **Rs 3.7 lakh in H1 2026 alone ≈ Rs 1.8 lakh/quarter**, and rising (15/quarter → 43/quarter) |
| 7 | **Those double payouts are NOT Returns Desk** | Chat Frontline 51, Logistics 49, Email 24, Returns Desk only 14. One agent (A3030, Logistics) has 27 | Neha's assumption is wrong. This answers "who is giving away money" |
| 8 | **Returns Desk handles only 26% of refunds**, not the "large majority" | Billing 25%, Chat 17%, Logistics 15% | Policy §6 says Returns Desk should own refunds. Frontline is refunding directly |
| 9 | **CSAT did NOT go up 0.4** | Avg CSAT by quarter (blanks excluded): 3.54 → 3.51 (Q4'25) → 3.46 | Priya's justification is not supported by the data. Say this carefully and neutrally |
| 10 | **1,192 tickets mention a refund in agent notes but have no amount** | e.g. TK-240001: "rfnd processed without pickup as goodwill", amount blank | Possible unrecorded refunds, or "refund declined". **Only an AI/NLP pass can tell** |
| 11 | 33.6% of tickets have no order_id | Customer message often contains it ("VR896352") | Regex recovery lets us join to orders/products |
| 12 | Legacy resolved_at is in UTC, the rest in IST | Policy §9 | Month bucketing shifts by 5.5h near month-end. Minor, fix it anyway |

> **All numbers above will be recomputed by the tool.** They come from a quick first pass and are the "expected results" we check the tool against.

---

## 3. Decisions we make (and write down — the brief asks for this)

| Decision | Why |
|---|---|
| Legacy amounts ÷ 100 | Policy §9 + side-by-side duplicate pairs prove it (2124 vs 212400) |
| When a ticket is duplicated, keep the **helpdesk** row | It is the live system and already in rupees |
| Assign refunds to **agent_id** (resolving agent), never by name | README says "use the id, not the name". Names repeat (two "Rohit"s) |
| Month = **ticket created_at** month (IST) | resolved_at is blank for open tickets and in UTC for legacy rows. Created date is always there. Documented alternative: resolved month |
| Keep the **original** reason code AND show an **AI-suggested** code side by side | Finance must see what the agent chose; we never silently overwrite a financial record |
| Don't rank agents by raw refund amount | Unfair (Billing/Returns Desk handle refunds by design). Rank by **policy exceptions** and **refund rate per ticket handled** instead |
| Double-payout cost = refund + unit_cost + Rs 340 | Policy §5 replacement-cost formula, "no refurbishment recovery" |
| Notes-only refunds are **flagged, not added** to the total | We can't prove the money moved. Finance can verify it against the payment gateway |

---

## 4. The solution: architecture

```
tickets.csv ─┐
agents.csv  ─┤   STAGE 1: CLEAN (pure Python, no AI)
orders.csv  ─┼─► dedupe · paise fix · UTC→IST · agent join · order_id regex
products.csv─┘         │
                       ▼
               STAGE 2: AI READ (LLM, only on refund-related rows)
               customer_message + agent_notes → strict JSON
               {suggested_reason, refund_in_note, amount_in_note,
                replacement_in_note, confidence, evidence_quote}
               cached to cache/llm_labels.jsonl (committed)
                       │
                       ▼
               STAGE 3: RECONCILE + REPORT
               • Waterfall: Rs 23 cr raw → Rs 67 L true
               • Monthly pivot: reason (original vs AI) × agent
               • Exceptions: refund+replacement, goodwill > Rs 500,
                 notes-only refunds, low-confidence rows
                       │
          ┌────────────┼──────────────┐
          ▼            ▼              ▼
  board_pack.xlsx   Streamlit app   eval report
```

### Stage 1: Deterministic cleaning (`src/clean.py`)
- Parse CSV safely (multi-line quoted fields: pandas handles this)
- `amount_inr = refund_amount_inr / 100 if source_system == legacy_fd`
- Drop duplicate ticket_ids, keeping the helpdesk row. Log how many were dropped and their value
- Convert legacy `resolved_at` from UTC to IST (+5:30)
- Recover `order_id` from message text with regex `VR\d{6}` (case-insensitive)
- Join agents (id → name, team, site, tier), taking from/to dates into account
- Join products (unit_cost_inr) for the replacement cost

**Why no AI here:** these have one exact right answer. An LLM would add cost, randomness and errors.

### Stage 2: AI extraction (`src/llm_label.py`)
- **Input rows:** every refund row (~2,340) plus notes that mention refund words without an amount (~1,192), so **~3,500 rows**, not all 11,600
- **Model:** Claude Haiku 4.5 (cheap, fast, good at short-text classification). Model name lives in config and can be swapped
- **Output:** JSON checked against a schema (pydantic). Invalid output is retried once, then marked `needs_review`
- **Prompt includes:** the 8 reason code definitions from policy §5, 6–8 few-shot examples (including Hinglish, IVR transcripts, shorthand like "rfnd", "cx", "rslvd"), and a rule: *"If unclear, say UNCLEAR. Do not guess."*
- **Evidence quote:** the model must quote the words it used, so a human can check in 5 seconds
- **Caching:** results are keyed by ticket_id + prompt version and saved in `cache/llm_labels.jsonl`, which is committed to the repo. So:
  - the tool **runs on a clean machine with no API key** (a key is only needed to re-label)
  - re-runs are free and give the same output every time
- **Batching:** 10–20 tickets per call to cut cost and time

### Stage 3: Reconcile + report (`src/reconcile.py`, `src/report.py`)
- **Reconciliation waterfall** (the most important output for Arjun):
  ```
  Raw export sum                         Rs 23.01 cr
  − duplicate re-import rows             − Rs  X
  − legacy paise correction              − Rs  Y
  = True refunds (18 months)             Rs 67.1 L
    of which last quarter                Rs 12.8 L   ← vs helpdesk "~11 L"
  ```
  A check confirms the buckets add back up to the raw total **to the rupee**.
- **Monthly summary**: month × reason code (original + AI-suggested) and month × agent (count, Rs, refund rate)
- **Exceptions register**: refund+replacement (ticket, agent, Rs leak), goodwill over cap, notes-only refunds
- **Outputs**: `output/board_pack.xlsx` (tabs: Summary, Waterfall, By Reason, By Agent, Exceptions, Needs Review, Method & Assumptions), plus a Streamlit app for the demo

---

## 5. Business goal (stated as a number)

**Main:**
> **"Stop refund-plus-replacement double payouts: currently ~40 tickets a quarter costing about Rs 1.8 lakh a quarter (Rs 8.7 lakh leaked in 18 months), down to zero, with a same-day exception check. Worth about Rs 7 lakh a year."**

Why this one:
- It is **money lost against written policy** (§5 "in no case"), so nobody can argue it is a trade-off
- It is **growing** (15 → 43 per quarter)
- It directly answers "**who** is giving away money" (Chat Frontline + Logistics, one agent with 27 cases)
- It does **not** attack Priya's "stop arguing with customers" decision. That is allowed goodwill. This isn't
- The fix is cheap: a blocking rule in the helpdesk, or our daily exception report

**Secondary (visibility):**
> **"Cut GW-OTHER from 42% of refunds (Rs ~28 lakh) to under 10%"** by removing it as the dropdown default and adding a mandatory reason. Until then, our AI re-coding bridges the gap.

---

## 6. How we prove it works (evaluation)

1. **Reconciliation tests** (`tests/test_reconcile.py`, pytest):
   - rupees are conserved: the raw total equals the sum of all waterfall buckets
   - no duplicate ticket_id after cleaning
   - every legacy duplicate pair matches after ÷100 (2124 == 212400/100)
   - the monthly pivot total equals the true total
2. **AI accuracy on a hand-labelled gold set** (`eval/gold_set.csv`, `eval/evaluate.py`):
   - **~120 tickets**, stratified: 40 GW-OTHER, 25 other codes, 25 notes-only, 20 refund+replacement, 10 Hinglish/IVR
   - I label them myself **before** looking at the model output (to avoid bias)
   - Report: accuracy per field, a confusion matrix of reasons, precision/recall for "refund in note"
   - List the **types of case it gets wrong** (e.g. "goodwill vs price-adjustment", "refund offered but declined")
3. **Prompt versions compared** on the same gold set: v1 → v2 → v3 with scores (this also covers the screen recording)
4. **Confidence routing**: anything below the threshold goes to "Needs Review", and we report what % that is
5. **External sanity check**: the cleaned quarterly total (~Rs 11–16 L) matches the helpdesk's own "~Rs 11 L". Two independent sources agree

---

## 7. Why this approach is the best fit

- **Rules for facts, AI for text.** Money conversion, duplicates and time zones are exact, so plain code handles them. Messy Hinglish notes are where AI is genuinely needed. This is the right tool at each step
- **Reconciliation first** answers Arjun's actual words: *"I want the total to reconcile."*
- **Never overwrites financial data.** The AI *suggests*, Finance *decides*. That matters for audit and trust
- **Evidence quotes + confidence** make every AI decision checkable by a non-technical person
- **Cached and small** means it runs from the README on a clean machine ("a small thing that runs beats a large thing that does not")
- **Cheap**: see §9. Pennies per run
- **Future-proof**:
  - new monthly export? Run `python run.py --input new_tickets.csv`. Only new tickets hit the LLM (cache)
  - model is set in config (Haiku → any provider)
  - rules live in one `config.yaml` (goodwill cap, replacement shipping cost, legacy unit), so a policy change is a one-line edit
  - the exceptions report can run daily as a control, not just once for the board pack

## 8. Why other options are worse

| Option | Why it's not the best fit |
|---|---|
| **Plain Excel pivot** | Faithfully reports the wrong Rs 23 crore, with 42% "Other". It's the mess Arjun already has |
| **Put the whole CSV into ChatGPT/Claude** | Not reproducible, can't reconcile to the rupee, LLMs do arithmetic badly, can't be tested, and it sends 12k customer records to a chat UI |
| **LLM on every row, including cleaning** | 3–4× the cost, non-deterministic results for things that have one right answer |
| **Train a custom ML classifier** | There are no labels, 5 hours isn't enough, and it's worse on Hinglish than an LLM. Overkill |
| **Keyword/regex only for notes** | Fails on "refund declined", "rfnd", "paisa wapas", negations. We'll show this as a *baseline* in the eval so the AI has to prove it's better |
| **Power BI / Tableau dashboard** | Pretty but fails "runs from README on a clean machine", and fixes nothing underneath |
| **Agent leaderboard by refund Rs** | Punishes Billing/Returns Desk for doing their job. Misleading in a board pack |

---

## 9. Cost (for the submission form)

Rough estimate (confirm with real token counts after the run):
- ~3,500 rows × ~350 input tokens ≈ 1.2M input tokens, plus ~60 output tokens/row ≈ 0.2M output
- At Haiku 4.5 pricing ($1/M input, $5/M output): ≈ **$1.2 + $1.0 ≈ $2.2 for the full 18-month backfill**
- **Monthly at Vireo's volume:** 650 tickets/week ≈ 2,800/month, ~30% refund-related ≈ 850 rows, so **≈ $0.50/month** (~Rs 45)
- Compare: one avoided double payout ≈ Rs 5,000

---

## 10. Deliberately left out (and why)

| Left out | Why |
|---|---|
| SLA-breach store credits (Rs 350/breach) | Real money, but it's a separate P&L line (SLA credit), not "refunds". Listed as a finding for later |
| Repeat contacts / FCR cost | Not Arjun's question |
| Transfers cost (Rs 305) | Not refunds. Only exists in the new helpdesk |
| Lot-code defect analysis (orders.lot_code) | Could explain DOA refunds. Mentioned as the next step |
| Full CSAT analysis | Only checked Priya's +0.4 claim, because it bears directly on the refund story |
| Auth, database, deployment | Not needed for a monthly board-pack tool |

These go into the "found but not built" section. They show we saw them and chose not to build them.

---

## 11. Repo structure

```
Task1/
├── README.md               # setup + run in 3 commands
├── requirements.txt        # pandas, openpyxl, anthropic, pydantic, streamlit, pytest
├── config.yaml             # policy constants, model name, prompt version
├── run.py                  # CLI: clean → label (cache) → reconcile → excel
├── app.py                  # Streamlit demo
├── src/
│   ├── clean.py
│   ├── llm_label.py
│   ├── reconcile.py
│   └── report.py
├── prompts/  v1.txt  v2.txt  v3.txt
├── cache/llm_labels.jsonl  # committed → runs without API key
├── eval/  gold_set.csv  evaluate.py  results.md
├── tests/test_reconcile.py
├── output/board_pack.xlsx
├── memo_to_arjun.md        # 1 page, non-technical
├── submission-form.md
└── data/ (the provided CSVs)
```

---

## 12. Memo to Arjun (one page, outline)

1. **Headline:** "Your refunds are about Rs 12–13 lakh a quarter, not over a crore. The crore comes from old Freshdesk rows stored in paise, plus duplicated tickets."
2. **The reconciliation** in 3 lines (raw → fixes → true), which ties to the helpdesk's ~11 L
3. **Refunds did double**: Rs 6 L (Q1'25) → Rs 16 L (Q4'25), then settled at ~Rs 12.7 L
4. **Where it's leaking**: 166 customers got both a refund *and* a new unit (Rs 8.7 L), mostly through Chat and Logistics, not Returns Desk. This is growing
5. **Why "by reason" is blurry**: 42% coded "Goodwill/Other" because it's the default. Here's our AI-corrected view
6. **Asks**: (a) block refund+replacement in the helpdesk, (b) remove GW-OTHER as the default, (c) route refunds through Returns Desk as the policy says
7. **Caveats**: AI re-coding is X% accurate on a 120-ticket check. CSAT hasn't moved (3.5 → 3.46), so worth a conversation with Priya

---

## 13. Screen recording (≤3 min) script

1. (0:00–0:30) The problem: crore vs 11 lakh, then show the waterfall
2. (0:30–1:30) Prompts: v1 (plain classification) → v2 (added policy definitions + evidence quote) → v3 (few-shot Hinglish + UNCLEAR option), with gold-set scores for each
3. (1:30–2:15) What I threw away: e.g. LLM doing the cleaning, a keyword-only approach, an agent leaderboard by Rs, a dashboard idea
4. (2:15–3:00) Run `python run.py`, open the Excel exceptions tab and the Streamlit app

Keep notes during the build: **save every prompt version and every discarded idea** as you go (needed for the video and form Q8).

---

## 14. Time plan (5 hours, hard cap)

| Block | Time | Output |
|---|---|---|
| 1. Cleaning + waterfall + tests | 1h 15m | `clean.py`, `reconcile.py`, pytest passing |
| 2. Gold set labelling (before the AI) | 45m | `gold_set.csv` (120 rows) |
| 3. LLM labelling, prompt v1→v3, cache | 1h 15m | `llm_label.py`, `cache/`, `prompts/` |
| 4. Eval script + results | 30m | `eval/results.md` |
| 5. Excel report + minimal Streamlit | 30m | `board_pack.xlsx`, `app.py` |
| 6. Memo + form + README + recording | 45m | final deliverables |

**If running out of time, cut in this order:** Streamlit app → notes-only refund detection → prompt v3. **Never cut:** the waterfall, the tests, the gold-set eval, the memo, the form.

---

## 15. Known risks / honesty items (for form Q5)

- Gold set labelled by one person (me), so there may be label bias
- "Notes-only refunds" may be refunds that were offered but not processed. We flag them and don't add them
- Month assigned by created_at; resolved_at would move some edge refunds
- Roster from/to dates: this data set has one row per agent, but the code supports multiple rows
- The CSAT finding uses all responses. It may differ if Priya meant a specific channel or cohort

---

## 16. Verification checklist before submitting

- [ ] Fresh venv: `pip install -r requirements.txt && python run.py` works with **no API key**
- [ ] `pytest` passes (rupee conservation, no duplicates)
- [ ] `python eval/evaluate.py` prints accuracy + confusion matrix
- [ ] Waterfall total = raw export total to the rupee
- [ ] Memo ≤ 1 page, no jargon
- [ ] Recording ≤ 3 minutes
- [ ] Every field in `submission-form.md` filled, including honest hours and AI cost

---

## 17. Updated plan (after notebooks 01–03) — replaces §4 architecture, §11 repo layout and §14 timing

Notebooks 01–03 are done (see `logs.md`). Changes since the original plan: Gemini instead of Claude, no Streamlit, gold set 60 + holdout 20, prompts v1/v2 only, legacy timestamps NOT shifted, refund month = resolved date.

### Remaining steps, in order

1. **Spot-check the AI-only double payouts** (~20 of the 199 the agent flag missed). Read note + AI evidence, record how many are real. No API calls.
2. **Remove the overlap** between double payouts and over-cap goodwill, and fix the final business-goal number.
3. **`run.py` builds the board pack directly — one script, no notebook version of the Excel:**
   `clean (same logic as 02) → read cached labels (cache/llm_labels.jsonl) → compute → write output/board_pack.xlsx`
   - runs with **no API key** (cache only); optional `--label` flag calls Gemini only for tickets not in the cache
   - running the tool *is* producing the board pack
4. **Excel sheets:**
   | Sheet | Content |
   |---|---|
   | Summary | true total, quarterly trend, the two policy leaks, headline numbers |
   | Waterfall | Rs 23.01 cr raw → Rs 67.1 L true, step by step |
   | By reason (monthly) | month × reason: agent's original code and AI-corrected code side by side |
   | **By agent** | see below |
   | Exceptions | every double payout and every over-cap goodwill refund, with the note and the AI evidence quote |
   | Method | assumptions and decisions (paise, dedupe, no UTC shift, resolved month, conservative leak, AI accuracy) |
5. **By agent sheet** — answers "who is giving away money", kept fair:
   - agent, **team** (shown next to every agent), tickets handled, refunds count + Rs, **refund rate = refunds ÷ tickets handled**
   - double payouts and over-cap goodwill per agent (count + Rs)
   - sorted by policy exceptions, not by raw refund Rs, so Billing / Returns Desk don't look bad for doing their job
   - **Excel only, not in the memo** (memo talks about teams and processes)
6. **`tests/test_pipeline.py`** — 3 checks that import from `run.py`:
   - the waterfall adds back to the raw export total
   - no duplicate ticket_ids remain after cleaning
   - monthly refund totals sum to Rs 67,09,932
7. **README** (setup + run in 3 commands), **memo**, **submission form**, **screen recording**.

### Repo layout (final)
```
run.py                     clean → cached labels → board_pack.xlsx  (+ --label to call Gemini)
requirements.txt
README.md
tests/test_pipeline.py
prompts/v1.txt, v2.txt
cache/llm_labels.jsonl
eval/gold_set*.{csv,xlsx}, eval/holdout.csv
01_/02_/03_*.ipynb         the working, kept as evidence of how we got here
output/board_pack.xlsx
logs.md, plan.md, memo_to_arjun.md, submission-form.md
```

### Gold set honesty
First-pass labels were drafted with Claude Code. Before submitting, I review all 60 in `eval/gold_set_labelling.xlsx`, change any I disagree with, re-run notebook 03 (cache only, no API), and report it as "drafted with AI, reviewed and corrected by me (N changed)".
