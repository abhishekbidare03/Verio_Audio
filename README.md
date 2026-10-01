# Vireo Audio — refund board pack

Turns the helpdesk export into a monthly refund summary that reconciles, by reason and by agent, with policy exceptions flagged.

## Run it (no API key needed)

Needs Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python run.py
```

Output: `output/board_pack.xlsx`. The AI labels are already saved in `cache/llm_labels.jsonl`, so this runs offline.

Check it:

```bash
python -m pytest -q tests
```

Three checks: the waterfall adds back to the raw export total, no duplicate tickets remain, and monthly totals equal the true total (Rs 67,09,932).

## What it does

1. **Clean** (plain code): removes 638 duplicate tickets from the migration re-import, converts legacy Freshdesk amounts from paise to rupees, recovers missing order IDs, joins agents and products.
2. **AI labels** (Gemini Flash-Lite, prompt `prompts/v3.txt`): re-reads refunds the agent coded GW-OTHER ("Goodwill / Other", the default dropdown) and refunds whose note mentions a replacement. It finds the real reason and whether a replacement was also given. The agent's original code is always kept next to it.
3. **Board pack** (`output/board_pack.xlsx`):

| Sheet | What it shows |
|---|---|
| Summary | headline numbers |
| Quarterly | refunds and policy leak by quarter |
| Waterfall | Rs 23.01 cr (export) → Rs 67.1 L (true) step by step |
| By reason – agent code / corrected | month × reason, before and after AI re-coding |
| By agent | tickets handled, refund rate, double payouts, goodwill over cap, with team |
| Exceptions | every double payout and over-cap goodwill refund, with the note and the AI's evidence quote |
| AI accuracy | AI vs hand-checked labels on the gold set (60), holdout (20) and holdout 2 (20) |
| Method | every assumption and decision |

## Re-labelling with the AI (optional)

Only needed for new tickets that aren't in the cache. Put a key in `.env`:

```
GEMINI_API_KEY=your-key
```

then run `python run.py --label`. It only sends refunds missing from the cache, 20 per call. The free tier is enough.

> **Don't open and save the CSVs in Excel.** Excel rewrites the timestamps (e.g. `1/1/2025 9:17`). `run.py` will stop with a date-format error rather than produce wrong months. To restore the original data: `git checkout -- tickets.csv`.

## Other files

- `01_data_understanding.ipynb`, `02_cleaning.ipynb`, `03_ai_labelling.ipynb`: how we got here (exploration, cleaning decisions, prompt v1 / v2 / v3 evaluation)
- `eval/`: test sets (gold set, holdout, holdout 2), labelling rules, spot-check, and the first-draft label files (`*_1`) kept to show the review
- `dropped_approaches.md`: what I tried, dropped or replaced, and the prompt versions
