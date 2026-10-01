# Submission form — Vireo Audio, Task 1 (Set C)

### What did you build, and what business outcome does it move? (State the number and the money.)

I built a small Python tool (`run.py`) that takes the raw helpdesk export and produces the board pack Arjun asked for: `output/board_pack.xlsx`. It has monthly refunds by reason code and by agent, a reconciliation from his number to the real one, and a list of every refund that broke policy. One command builds it, and it runs without an API key because the AI's answers are saved in the repo.

The first thing it does is fix the number itself. Arjun's export adds up to Rs 23 crore over 18 months. The real figure is **Rs 67.1 lakh, about Rs 12.6 lakh a quarter**. The difference is old Freshdesk rows stored in paise, plus 638 tickets that were imported twice.

The business outcome:

> **Cut refunds that also got a replacement from 17% of refunds to under 2%, worth about Rs 1.2 lakh a quarter (around Rs 5 lakh a year).**

Policy says a customer should never get both, but in 2026 about 80 refunds a quarter came with a replacement. Fewer than half of them are visible in the helpdesk's tick-box; the rest only show up when you read the agents' notes, which is what the AI does. I put the target at under 2% rather than zero because some Team-Lead-approved exceptions will always happen. The cost is counted conservatively: only the extra remedy, since the customer was owed one of the two.

---

### What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)? Show the arithmetic.

**Everything I ran was on the Gemini free tier, so I actually paid Rs 0.** Model: `gemini-3.5-flash-lite`. The free tier allows 500 requests a day and 15 a minute, and I used about 135 requests across all experiments.

- **Running `python run.py` costs nothing.** It reads the saved answers in `cache/llm_labels.jsonl` and makes no API calls.
- **One full AI labelling run** (what `python run.py --label` does from an empty cache): 1,251 refunds, 20 per call = **~63 calls**.
  - I measured about **145 input + 68 output tokens per ticket**, including the prompt.
  - 1,251 × 145 ≈ 181k input tokens, and 1,251 × 68 ≈ 85k output tokens.
  - At Flash-Lite-class paid prices (~$0.10 per million input, ~$0.40 per million output; worth re-checking current pricing): $0.018 + $0.034 ≈ **$0.05, about Rs 4–5 a run**.
- **A month at Vireo's volume:**
  - 650 tickets a week ≈ 2,800 a month.
  - About 20% are refunds (2,340 of 11,600 in this data), so ≈ 560 refunds.
  - About 53% of refunds get sent to the AI (Goodwill/Other, or the note mentions a replacement), so ≈ 300 tickets a month ≈ **15 calls**.
  - 300 × 145 ≈ 44k input and 300 × 68 ≈ 20k output tokens ≈ **$0.01, about Rs 1 a month**, and well inside the free tier anyway.
- **All my experiments together:** about 2,600 ticket-labels across prompt v1, v2 and v3 ≈ 380k input + 180k output tokens. That's about $0.11 (≈ Rs 10) if it had been paid.

---

### How do you know it works? (Sample size, how you checked, error rate, and the kind of case it gets wrong.)

There are two separate things to prove: that the money is right, and that the AI reads the notes correctly.

**The money:**
- `tests/test_pipeline.py` checks that the reconciliation adds back to the raw total to the rupee, that no duplicate tickets remain, and that the monthly totals equal Rs 67,09,932. All 3 pass.
- An independent check: my cleaned total (~Rs 12.6 lakh a quarter) matches the helpdesk's own report (~Rs 11 lakh) that Sameer mentioned.
- Clean-machine check: I copied only the repo into an empty folder, made a fresh virtual env, installed the requirements and ran it. It worked with no API key.

**The AI.** I tested it on 100 tickets in three sets, labelled before the model ever saw them:

| Test set | Tickets | Agents' own code | Keyword rules | AI (final prompt v3) |
|---|---|---|---|---|
| Gold set | 60 | 37% | 38% | **85%** |
| Holdout 1 | 20 | 40% | 65% | **100%** |
| Holdout 2 (fresh, used to decide v2 vs v3) | 20 | 40% | 35% | **90%** |

- **Refund + replacement detection:** found 28 of 28 across all three sets, with 0 false alarms. The agents' tick-box found 10 of 17 on the gold set. I also hand-checked 20 of the ~200 cases only the AI found: 18 confirmed, 2 likely, 0 wrong.
- **How the labels were made:** the first pass was drafted with Claude Code against a written rulebook (`eval/labelling_rules.md`). I reviewed them and changed 3 reason codes and 7 goodwill labels on the gold set, and 1 code and 1 goodwill label on holdout 1. A later consistency pass against the rulebook made 2 more goodwill labels consistent. I also went through holdout 2 and kept its labels, with one borderline ticket. Both versions of the gold file are in the repo.
- **Error rate:** roughly 1 in 10 on unseen tickets.
- **The kind of case it gets wrong:**
  - "Refund not credited" follow-ups with no return mentioned. The right answer is UNCLEAR, but v3 sometimes guesses "return". This is a side effect of the v3 rule.
  - Refund + replacement on a return or transit case, where it calls the reason goodwill instead of the underlying reason.
  - Very thin notes like "done" or "closed".
  - Once it invented a code ("WTY-BUYBUY"). The tool now rejects any code that isn't one of the 9 valid ones.
- **The model's "confidence" field turned out to be useless.** Nearly everything came back "high", including the wrong answers, so I don't use it.

---

### Did you change, narrow, or push back on the client's ask? (What, when, and why.)

Yes, mostly on day one, after reading the email thread against the data.

- **I changed the order of the work.** Arjun asked for a summary by reason and agent. But a summary of the export would have faithfully reported Rs 23 crore and 42% "Goodwill/Other". So I fixed and reconciled the total first, and only then summarised.
- **"Who is giving away money": I didn't rank agents by rupees refunded.** The Returns Desk and Billing refund by design, so they'd top that list for doing their job. The agent sheet shows each agent's team, tickets handled, refund rate, and policy breaches (double payouts and goodwill above the cap), and it's sorted by breaches. That sheet goes in the Excel only. The memo talks about teams and processes, not names.
- **"By reason code" can't be taken at face value.** 43% of the money sits under the default dropdown option, so I report the agents' codes and an AI-corrected view side by side, and never overwrite the agent's code.
- **I checked the claims in the thread instead of accepting them.**
  - Neha's "probably one-offs" on refund + replacement turned out to be 17% of refunds.
  - I couldn't find Priya's "CSAT up 0.4" in the export; it's flat at about 3.5.
  - The policy says legacy timestamps are UTC, but I tested it and they're already IST in this export, so I didn't shift them.

---

### What is wrong with what you are handing us? (Be specific: bugs, shortcuts, things you know are off.)

- **The test sets are small:** 60 + 20 + 20. One ticket moves a 20-ticket score by 5 points.
- **The first-pass test labels were drafted with an AI (Claude Code), not by hand.** I reviewed them, but a second independent human labeller would make the test stronger. One holdout-2 ticket (TK-242666) is borderline and could reasonably be labelled either way.
- **v3 made a few things worse:** 3–4 "refund not credited" tickets that v2 got right (UNCLEAR) are now called "return". It's better overall, but it isn't a clean win.
- **The model isn't fully repeatable**, even at temperature 0. Asking again for the same ticket gave a different answer (TK-244355: first an invented code, then GW-OTHER, where the rulebook says WTY-BUYBACK). That's why the tool saves answers instead of re-asking.
- **The double payout count (363) is a floor.** The AI only re-read refunds coded Goodwill/Other or whose note mentions a replacement. I also didn't count cases where the refund and the replacement are on *different* tickets for the same order.
- **"Goodwill above the cap" is approximate.** Wrong-item-shipped refunds also land in Goodwill/Other, because no code exists for them, so some aren't really goodwill. It's only about Rs 0.5 lakh of the Rs 1.9 lakh a quarter leak, but it isn't precise.
- **The cleaning logic exists twice**, in `02_cleaning.ipynb` and in `run.py`. They match today, but they could drift. `run.py` is the one that counts.
- **The evidence quotes:** about 6% aren't word-for-word from the ticket (paraphrased or stitched together).
- **Smaller things:**
  - 655 tickets still have no order ID.
  - July 2026 holds 10 refunds resolved after the data cut-off; it's labelled "partial".
  - The roster logic handles agents changing team, but this data never exercises it.
  - The Gemini library prints a harmless warning on every call.

---

### What did you deliberately leave out, and why that rather than something else?

Arjun asked about refunds, so anything that wasn't refunds lost out, even when it was real money:

- **SLA breach credits** (Rs 350 per late first response), **repeat-contact costs** and **transfer costs** are all in the policy and all measurable, but they're separate cost lines, not refunds.
- **Product and lot-code defect analysis** could explain the dead-on-arrival refunds, but it's a different question.
- **Refunds and replacements on different tickets for the same order:** 157 refunds (Rs 4.3 lakh) look like this. Some are genuinely wrong, but many are legitimate, and separating them properly needs rules and review. I listed it as a next step instead of putting a shaky number in front of Finance.
- **The 1,192 notes that mention a refund but have no amount:** I looked at them, but proving whether money moved needs payment-gateway data.
- **A dashboard (Streamlit):** Arjun needs something for a board pack, and that's Excel. It also added setup risk on a clean machine.
- **A fourth prompt version:** I know what v3 gets wrong, but every new version needs a fresh test set to be fair, and I was out of time.

---

### Anything you built or found that nobody asked for?

- **Hidden double payouts.** The helpdesk's "replacement issued" tick-box misses more than half of the refund + replacement cases. Agents pick a specific reason code but don't tick the box. The AI found about 200 that the flag missed.
- **Refunds released before the item came back.** 65 refunds went out while the pickup was missed or still pending, mostly on the Returns Desk.
- **There's no reason code for "wrong item shipped"**, so those refunds fall into Goodwill/Other.
- **The Returns Desk handles only 26% of refunds**, though the policy says it should handle the "large majority". Frontline teams refund directly.
- **Refunds doubled because ticket volume doubled.** About 1 in 5 tickets ends in a refund every quarter and the average refund is flat (Rs 2,700–3,000), so per ticket agents did not get more generous. Within that, genuine goodwill grew fastest (Rs 0.5 lakh → 1.8 lakh a quarter).
- **CSAT didn't move**, which weakens the "refunds up, CSAT up" trade-off in the thread.
- **The legacy timestamps are not UTC**, despite what the policy says. I tested it before trusting it.
- **Some cancelled-before-dispatch orders later got a dead-on-arrival replacement on the same order**, so the product was delivered after the customer had been refunded.
- **Extra tooling nobody asked for:**
  - a written labelling rulebook (`eval/labelling_rules.md`)
  - a reconciliation that fails loudly if someone re-saves the CSV in Excel (that actually happened to me mid-project)
  - a check that rejects any AI answer with an invalid code

---

### What did you use AI for? (Tools and models, where they helped, where they wasted your time, what you threw away. Link your three-minute screen recording here.)

**Tools:**
- **Claude Code (Claude Opus)** as my coding and thinking partner. It helped with planning, writing the notebooks, `run.py` and the tests, drafting the first-pass test labels (which I then reviewed and corrected), and drafting the memo and this form, which I edited.
- **Gemini 3.5 Flash-Lite** inside the tool, to read the agents' notes and re-code refunds. Free tier.

**Where it helped:**
- Reading 1,251 messy, Hinglish, shorthand notes. No regex could do that: keyword rules scored 35–65%, the AI about 90%.
- Moving fast on the code.
- Pushing me to test claims instead of trusting them.

**Where it wasted time or was wrong:**
- Claude's first double-payout cost counted both the refund and the replacement (Rs 8.7 lakh). That was overstated; the right figure counts only the extra remedy.
- It first applied a UTC→IST timestamp shift because the policy said so. A test showed that was wrong.
- An early "total leak" figure added two leaks that overlapped on 150 tickets.
- Fiddly setup: the API key format and an old system environment variable overriding it.
- Excel silently re-saving the CSVs and breaking dates.

**What I dropped or replaced:**
- the Streamlit dashboard
- the timestamp shift
- the overstated cost figure
- the double-counted leak
- one-ticket-per-call (switched to 20 per call)
- using the model's confidence score to route tickets to human review
- the plan to use Claude Haiku (I used the Gemini key I had)

**Prompt history:**
- **v1** was deliberately plain: 60%.
- **v2** added the policy definitions, the "never refund and replace" rule, a shorthand glossary, an UNCLEAR option and an evidence quote: 82%.
- **v3** changed one thing: a return only counts once the item is back. 85% on the gold set, and 90% on a fresh set where v2 got 70%.

**Screen recording:** [paste Google Drive link]

---

### Your Public Google Drive Link
[paste link]

---

### Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. **`python run.py` builds the whole board pack** from the raw CSVs and the saved AI answers, with no key needed. Use `python run.py --label` only for new tickets; it only sends what isn't already saved. **Never open and re-save the CSVs in Excel.** It rewrites the dates; the script will stop with an error, and `git checkout -- tickets.csv` restores the file.
2. **The numbers rest on four cleaning decisions**, all written in the "Method" sheet of the board pack: legacy amounts ÷ 100, keep the helpdesk copy of duplicated tickets, no timestamp shift, and refunds counted in the month they were resolved. If any of these turns out wrong, everything moves.
3. **The AI only re-reads refunds coded Goodwill/Other or whose note mentions a replacement**, so the double payout count is a minimum. Prompts are versioned in `prompts/`, test labels and the rulebook are in `eval/`, and the obvious next step is the cross-ticket check (refund and replacement on different tickets for the same order).

---

### Honest hours spent
[one number]

---

### Github Repo Link
[paste public repo URL]
