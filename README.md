# Vireo Audio: Refund Board Pack

**A small AI-assisted tool that turns Vireo's messy helpdesk export into a refund summary Finance can trust:** monthly, by reason code and by agent, reconciled to the rupee, with every policy breach flagged.

> **The short answer for Finance:** refunds are **Rs 12.6 lakh a quarter, not over a crore**. They doubled in 2025 mostly because ticket volume doubled. About **Rs 1.9 lakh a quarter is paid out against Vireo's own policy**, mainly customers who got a refund *and* a replacement.

---

## Quick start (no API key needed)

Needs **Python 3.10+**. Three commands:

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

You'll see:

```
wrote output/board_pack.xlsx
  true refund total : Rs 6,709,932  (export sums to Rs 230,124,081)
  goal              : Cut refunds that also got a replacement from 17% of refunds to under 2%, worth about Rs 1.2 lakh a quarter (Rs 4.9 lakh a year).
```

Then open **`output/board_pack.xlsx`**. This works offline: the AI's answers are already saved in `cache/llm_labels.jsonl`.

**Check it's correct:**

```bash
python -m pytest -q tests
```

---

## Where to find each deliverable

| What the brief asked for | Where it is |
|---|---|
| 1. A working AI-assisted tool | `run.py` (this README is the setup) |
| 2. A business goal, as a number | Top of the **Summary** sheet in `output/board_pack.xlsx`, and below |
| 3. A way of showing it works | `tests/`, the **AI accuracy** sheet, `eval/`, and [How we know it works](#how-we-know-it-works) below |
| 4. One-page memo to Arjun | `memo_to_arjun.md` |
| 5. Screen recording | Link in `submission-form.md` |
| 6. Submission form | `submission-form.md` |

---

## Results

### The number that was wrong

| Step | Rs |
|---|---|
| Raw export total (what Finance summed) | 23,01,24,081 |
| − duplicate tickets from the migration re-import (638 tickets) | −3,61,01,100 |
| − legacy Freshdesk amounts stored in paise, not rupees | −18,73,13,049 |
| **True refund total, Jan 2025 – Jun 2026** | **67,09,932** |

This matches the helpdesk's own report of about Rs 11 lakh a quarter.

### Refunds by quarter (Rs lakh)

| Q1 '25 | Q2 '25 | Q3 '25 | Q4 '25 | Q1 '26 | Q2 '26 |
|---|---|---|---|---|---|
| 6.0 | 7.2 | 11.7 | **16.7** | 12.6 | 12.6 |

About 1 in 5 tickets ends in a refund every quarter, and the average refund stays at Rs 2,700–3,000. **The rise comes from ticket volume doubling**, not from agents refunding more per ticket.

### The business goal

> **Cut refunds that also got a replacement from 17% of refunds to under 2%, from about Rs 1.4 lakh to Rs 0.2 lakh a quarter, saving about Rs 1.2 lakh a quarter (≈ Rs 5 lakh a year).**

Vireo's policy says a customer must never get both. The helpdesk's "replacement issued" tick-box catches fewer than half of these cases; **the rest only show up in the agents' notes, which is what the AI reads.** The tick-box shows 166; with the AI it's 363. The cost is counted conservatively: only the extra remedy, since the customer was owed one.

---

## How it works

```
 tickets.csv ──┐
 agents.csv  ──┤   1. CLEAN (plain Python, no AI)
 orders.csv  ──┼──▶  remove duplicates · paise → rupees · recover order IDs · join agents & products
 products.csv──┘                 │
                                 ▼
                    2. AI LABELS (Gemini, only where text needs reading)
                       re-reads refunds coded "Goodwill / Other" + notes that mention a replacement
                       → real reason · replacement also given? · evidence quote
                       (saved to cache/, so normal runs make no API calls)
                                 │
                                 ▼
                    3. BOARD PACK  →  output/board_pack.xlsx
```

**The principle: rules for facts, AI only for text.** Paise, duplicates and dates have one right answer, so plain code handles them. The agents' notes ("rfnd + rplc, cx escalation avoided", Hinglish, IVR transcripts) are where an LLM is actually needed.

### What's in the board pack

| Sheet | What it shows |
|---|---|
| **Summary** | The business goal and headline numbers |
| **Quarterly** | Refunds, double payouts and policy leak per quarter |
| **Waterfall** | Rs 23.01 crore → Rs 67.1 lakh, step by step |
| **By reason – agent code / corrected** | Month × reason, as agents coded it and after AI re-coding, side by side |
| **By agent** | Each agent with **team**, tickets handled, **refund rate**, double payouts and goodwill over the cap. Sorted by policy breaches, not rupees, so teams that refund by design (Returns Desk, Billing) aren't penalised |
| **Exceptions** | Every flagged refund with the agent's note and the AI's evidence quote, ready to check |
| **AI accuracy** | AI vs hand-checked labels on all three test sets, recomputed on every run |
| **Method** | Every assumption and decision, in plain words |

### Key decisions

| Decision | Why |
|---|---|
| Legacy Freshdesk amounts ÷ 100 | On all 125 duplicated pairs, the legacy amount is exactly 100× the helpdesk amount |
| Keep the helpdesk copy of duplicated tickets | It's the live system and already in rupees |
| **No** UTC → IST shift on legacy timestamps | The policy says the legacy log is UTC, but tests show the export is already IST (same hour pattern, same handle time) |
| Refunds counted in the month they were **resolved** | That's when the money goes out |
| Double payout cost = the cheaper of refund or replacement (unit cost + Rs 340) | One remedy was owed, so only the extra one is lost |
| The AI only *suggests*; the agent's original code is always kept | Never overwrite a financial record |

---

## How we know it works

**The money:** `tests/test_pipeline.py` checks that the waterfall adds back to the raw export total, that no duplicate tickets remain, and that monthly totals equal Rs 67,09,932. The cleaned total also matches the helpdesk's own figure.

**The AI:** tested on 100 tickets, labelled against a written rulebook (`eval/labelling_rules.md`) before the model saw them.

| Test set | Tickets | Agents' own code | Keyword rules | **AI (prompt v3)** |
|---|---|---|---|---|
| Gold set | 60 | 37% | 38% | **85%** |
| Holdout 1 | 20 | 40% | 65% | **100%** |
| Holdout 2 (fresh, decided v2 vs v3) | 20 | 40% | 35% | **90%** |

- **Refund + replacement detection:** 28/28 across all test sets, 0 false alarms. A hand spot-check of 20 cases only the AI found: 18 confirmed, 2 likely, 0 wrong.
- **Where it's wrong** (about 1 in 10): "refund not credited" follow-ups that should be UNCLEAR, refund + replacement on a return or transit case, and notes that say nothing ("done", "closed").
- **Test labels:** first drafted with Claude Code, then reviewed and corrected by hand. The drafts are kept as `eval/*_1.*`.

### Prompt versions

| Version | What changed, and why | Result |
|---|---|---|
| `prompts/v1.txt` | Deliberately plain: "here are the codes, pick one" | 60% (gold) |
| `prompts/v2.txt` | v1 called every faulty product "dead on arrival". Added policy definitions, the "never refund *and* replace" rule with a yes/no field, a shorthand glossary, an UNCLEAR option and an evidence quote | 82% (gold) |
| `prompts/v3.txt` **(used)** | v2 treated refunds after a *missed* pickup as returns. One change: a return only counts once the item is back | 85% gold · 90% on a fresh set where v2 got 70% |

v3 was adopted under a rule written *before* running it: it had to be at least as good on 20 fresh tickets that played no part in writing it. Approaches that were tried and dropped are in `dropped_approaches.md`.

---

## Re-labelling with the AI (optional)

Only needed for new tickets that aren't in the cache. Create a `.env` file (it's git-ignored):

```
GEMINI_API_KEY=your-key
```

Then run:

```bash
python run.py --label
```

It sends **only refunds missing from the cache**, 20 per call, stops on the first API error, and rejects any answer with an invented code. The model is `gemini-3.5-flash-lite`; the whole project ran on the free tier.

| | Calls | Approx. cost if paid |
|---|---|---|
| One full labelling run (1,251 refunds) | ~63 | ≈ Rs 4–5 |
| A month at Vireo's volume (~650 tickets/week) | ~15 | ≈ Rs 1 |
| Normal `python run.py` | 0 | Rs 0 |

---

## Project structure

```
run.py                        the tool: clean → cached AI labels → board pack (+ --label)
requirements.txt
tests/test_pipeline.py        3 reconciliation checks
prompts/v1.txt v2.txt v3.txt  prompt history (v3 is used)
cache/llm_labels.jsonl        every AI answer (lets the tool run offline)
eval/                         test sets, labelling rulebook, spot-check, draft labels (*_1)
output/board_pack.xlsx        ← the deliverable for Finance
memo_to_arjun.md              one-page memo for the board pack
submission-form.md            answers to the submission questions
dropped_approaches.md         what was tried, dropped or replaced
01_data_understanding.ipynb   exploration
02_cleaning.ipynb             cleaning decisions and the reconciliation
03_ai_labelling.ipynb         gold set, baselines, prompts v1 → v3, holdouts, full runs
*.csv, support-policy.pdf, EMAIL_THREAD.txt, README.txt   the data pack as provided
```

---

## Known limitations

- The test sets are small (60 + 20 + 20); one ticket moves a 20-ticket score by 5 points.
- **The double payout count is a minimum.** The AI only re-reads refunds coded "Goodwill / Other" or whose note mentions a replacement, and refunds and replacements on *different* tickets for the same order aren't counted yet.
- "Goodwill above the cap" is approximate, because wrong-item refunds also land in "Goodwill / Other" (no code exists for them).
- The model isn't perfectly repeatable even at temperature 0, which is why answers are cached rather than re-asked.
- **Don't open and re-save the CSVs in Excel.** It rewrites the timestamps (e.g. `1/1/2025 9:17`). `run.py` will stop with a date-format error rather than produce wrong months. Restore with `git checkout -- tickets.csv`.
