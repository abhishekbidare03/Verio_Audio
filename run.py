"""Vireo refund board pack.

clean the export -> attach cached AI labels -> write output/board_pack.xlsx

    python run.py            # uses cache/llm_labels.jsonl, no API key needed
    python run.py --label    # also asks Gemini for any refund not in the cache (needs GEMINI_API_KEY)
"""
import argparse
import json
import os
import re
import time

import numpy as np
import pandas as pd

GOODWILL_CAP = 500        # policy s5
REPL_SHIPPING = 340       # policy s5, reverse pickup + forward shipping
DP_TARGET_SHARE = 0.02    # goal: double payouts under 2% of refunds (not 0 - some TL-approved exceptions will happen)
PROMPT_VERSION = 'v3'
MODEL = 'gemini-3.5-flash-lite'
BATCH_SIZE = 20
VALID_CODES = {'GW-OTHER', 'DOA-REPL', 'LOST-TRANSIT', 'DUP-PAYMENT', 'CANCEL', 'PRICE-ADJ',
               'RETURN-QC-OK', 'WTY-BUYBACK', 'UNCLEAR'}
REPL_WORDS = r'rplc|replac|new unit|new set|new pair|fresh pair|\brma\b|re-?ship|sending a new|new one'


# ---------- cleaning (same steps as 02_cleaning.ipynb) ----------

def load_data(data_dir):
    read = lambda f: pd.read_csv(os.path.join(data_dir, f))
    return read('tickets.csv'), read('agents.csv'), read('orders.csv'), read('products.csv')


def clean(raw, agents, orders, products):
    # 1. duplicates: keep the helpdesk copy
    rank = (raw.source_system != 'helpdesk').astype(int)
    order = raw.assign(_rank=rank).sort_values(['ticket_id', '_rank'])
    keep_idx = order.drop_duplicates('ticket_id', keep='first').index
    dropped = raw.loc[~raw.index.isin(keep_idx)]
    df = raw.loc[keep_idx].reset_index(drop=True)

    # 2. legacy Freshdesk stored paise
    is_legacy = df.source_system == 'legacy_fd'
    df['refund_inr'] = np.where(is_legacy, df.refund_amount_inr / 100, df.refund_amount_inr)

    # 3. timestamps: already IST in this export (checked in 02), no shift
    # explicit format: if the csv was re-saved by Excel (1/2/2025 9:17) this fails loudly instead of mixing up day/month
    for c in ['created_at', 'first_response_at', 'resolved_at']:
        df[c] = pd.to_datetime(df[c], format='%Y-%m-%d %H:%M')
    df['refund_month'] = df.resolved_at.fillna(df.created_at).dt.to_period('M')

    # 4. order_id: message first, then customer + sku when exactly one order matches
    from_msg = df.customer_message.str.extract(r'(VR\d{6})', flags=re.I)[0].str.upper()
    fill = df.order_id.isna() & from_msg.isin(orders.order_id)
    df.loc[fill, 'order_id'] = from_msg[fill]
    one = orders.groupby(['customer_id', 'sku']).filter(lambda g: len(g) == 1).set_index(['customer_id', 'sku']).order_id
    joined = pd.Series(one.reindex(pd.MultiIndex.from_arrays([df.customer_id, df.product_sku])).values, index=df.index)
    fill = df.order_id.isna() & joined.notna()
    df.loc[fill, 'order_id'] = joined[fill]

    # 5. agent valid on the ticket date + product cost
    ag = agents.copy()
    ag['from_date'] = pd.to_datetime(ag.from_date)
    ag['to_date'] = pd.to_datetime(ag.to_date).fillna(pd.Timestamp('2099-12-31'))
    m = df[['ticket_id', 'agent_id', 'created_at']].merge(ag, on='agent_id', how='left')
    m = m[(m.created_at >= m.from_date) & (m.created_at <= m.to_date)]
    df = df.merge(m[['ticket_id', 'name', 'team']].rename(columns={'name': 'agent_name', 'team': 'agent_team'}),
                  on='ticket_id', how='left')
    df = df.merge(products[['sku', 'unit_cost_inr']], left_on='product_sku', right_on='sku', how='left').drop(columns='sku')
    return df, dropped


def waterfall(raw, df, dropped):
    raw_total = raw.refund_amount_inr.sum()
    dup = dropped.refund_amount_inr.sum()
    legacy_raw = df.loc[df.source_system == 'legacy_fd', 'refund_amount_inr'].sum()
    paise = legacy_raw - legacy_raw / 100
    clean_total = df.refund_inr.sum()
    return pd.DataFrame({
        'Step': ['Raw export total (as summed from the export)', 'less: duplicate tickets from migration re-import',
                 'less: legacy Freshdesk amounts stored in paise', 'True refund total'],
        'Rs': [raw_total, -dup, -paise, clean_total],
    })


# ---------- AI labels ----------

def load_cache(path):
    cache = {}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                rec = json.loads(line)
                # skip answers with an invented code, so --label asks again for that ticket
                if rec.get('prompt_version') == PROMPT_VERSION and rec.get('code') in VALID_CODES:
                    cache[rec['ticket_id']] = rec
    return cache


def label_missing(rows, cache, cache_path, prompt_path):
    """Ask Gemini only for tickets not already cached. 20 per call, stops on first error."""
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types
    load_dotenv(override=True)
    todo = [r for r in rows.itertuples() if r.ticket_id not in cache]
    print(f'{len(todo)} refunds not in cache')
    if not todo:
        return
    prompt = open(prompt_path, encoding='utf-8').read()
    client = genai.Client()
    sent = {r.ticket_id for r in todo}
    with open(cache_path, 'a', encoding='utf-8') as f:
        for i in range(0, len(todo), BATCH_SIZE):
            batch = [{'ticket_id': r.ticket_id, 'customer_message': r.customer_message, 'agent_note': r.agent_notes}
                     for r in todo[i:i + BATCH_SIZE]]
            try:
                resp = client.models.generate_content(
                    model=MODEL, contents=prompt.format(tickets=json.dumps(batch, ensure_ascii=False, indent=1)),
                    config=types.GenerateContentConfig(temperature=0, response_mime_type='application/json'))
                out = json.loads(resp.text)
            except Exception as e:
                print('stopped:', str(e)[:150])
                break
            for rec in out:
                if rec.get('ticket_id') in sent:
                    rec.update(prompt_version=PROMPT_VERSION, model=MODEL)
                    cache[rec['ticket_id']] = rec
                    f.write(json.dumps(rec) + '\n')
            time.sleep(5)


def attach_labels(refunds, cache):
    get = lambda field: refunds.ticket_id.map(lambda t: cache.get(t, {}).get(field))
    refunds['ai_code'] = get('code')
    # the model sometimes invents a code (seen once: 'WTY-BUYBUY') -> don't trust it, treat as UNCLEAR
    invalid = refunds.ai_code.notna() & ~refunds.ai_code.isin(VALID_CODES)
    if invalid.any():
        print(f'{invalid.sum()} AI answer(s) with an invalid code -> UNCLEAR:', refunds.loc[invalid, 'ai_code'].unique().tolist())
    refunds.loc[invalid, 'ai_code'] = 'UNCLEAR'
    refunds['ai_replacement'] = get('replacement_also_given') == True
    refunds['ai_evidence'] = get('evidence')

    is_gw = refunds.refund_reason_code == 'GW-OTHER'
    # AI only re-codes what the agent left as GW-OTHER; original code is always kept next to it
    refunds['corrected_code'] = np.where(is_gw & refunds.ai_code.notna(), refunds.ai_code, refunds.refund_reason_code)

    refunds['double_payout'] = (refunds.replacement_issued == 'Y') | refunds.ai_replacement
    repl_cost = refunds.unit_cost_inr + REPL_SHIPPING
    # customer was owed one remedy, so only the cheaper one is lost (conservative)
    refunds['double_payout_leak'] = np.where(refunds.double_payout, np.minimum(refunds.refund_inr, repl_cost), 0)

    refunds['goodwill_over_cap'] = is_gw & (refunds.corrected_code == 'GW-OTHER') & (refunds.refund_inr > GOODWILL_CAP)
    excess = np.where(refunds.goodwill_over_cap, refunds.refund_inr - GOODWILL_CAP, 0)
    # don't count the same ticket twice: if it's already a double payout, that leak covers it
    refunds['over_cap_excess'] = np.where(refunds.double_payout, 0, excess)
    refunds['policy_leak'] = refunds.double_payout_leak + refunds.over_cap_excess
    return refunds


# ---------- report tables ----------

def by_agent(df, refunds):
    handled = df.groupby('agent_id').size().rename('tickets_handled')
    g = refunds.groupby('agent_id')
    t = pd.DataFrame({
        'refunds': g.size(),
        'refund_rs': g.refund_inr.sum(),
        'double_payouts': g.double_payout.sum(),
        'double_payout_leak_rs': g.double_payout_leak.sum(),
        'goodwill_over_cap': g.goodwill_over_cap.sum(),
        'over_cap_excess_rs': g.over_cap_excess.sum(),
        'policy_leak_rs': g.policy_leak.sum(),
    })
    info = df.drop_duplicates('agent_id').set_index('agent_id')[['agent_name', 'agent_team']]
    t = info.join(handled).join(t).fillna(0)
    t['refund_rate'] = (t.refunds / t.tickets_handled).round(3)
    t = t.reset_index()[['agent_id', 'agent_name', 'agent_team', 'tickets_handled', 'refunds', 'refund_rate', 'refund_rs',
                         'double_payouts', 'double_payout_leak_rs', 'goodwill_over_cap', 'over_cap_excess_rs', 'policy_leak_rs']]
    return t.sort_values(['policy_leak_rs', 'double_payouts'], ascending=False)


def eval_scores(cache, eval_dir):
    """Accuracy of the AI vs hand-checked labels, recomputed from the eval files."""
    rows = []
    for name, f in [('Gold set', 'gold_set.csv'), ('Holdout', 'holdout.csv'), ('Holdout 2 (fresh, picked v3)', 'holdout2.csv')]:
        p = os.path.join(eval_dir, f)
        if not os.path.exists(p):
            continue
        e = pd.read_csv(p, keep_default_na=False)
        if not {'ticket_id', 'my_code', 'refund_reason_code'} <= set(e.columns):
            print(f'warning: {f} is missing columns (re-saved by Excel?), skipping it in AI accuracy')
            continue
        e = e[e.my_code != '']
        ai = e.ticket_id.map(lambda t: cache.get(t, {}).get('code'))
        rows.append({'Test set': name, 'Tickets': len(e),
                     "Agent's original code": round((e.refund_reason_code == e.my_code).mean(), 3),
                     f'AI (prompt {PROMPT_VERSION})': round((ai == e.my_code).mean(), 3)})
    return pd.DataFrame(rows)


def build_tables(raw, df, dropped, refunds, cache, eval_dir):
    wf = waterfall(raw, df, dropped)
    refunds = refunds.copy()
    refunds['quarter'] = refunds.refund_month.dt.asfreq('Q').astype(str)
    refunds['month'] = refunds.refund_month.astype(str)

    quarterly = refunds.groupby('quarter').agg(
        refunds=('refund_inr', 'size'), refund_rs=('refund_inr', 'sum'),
        double_payouts=('double_payout', 'sum'), double_payout_leak_rs=('double_payout_leak', 'sum'),
        over_cap_excess_rs=('over_cap_excess', 'sum'), policy_leak_rs=('policy_leak', 'sum')).reset_index()
    quarterly.loc[quarterly.quarter == '2026Q3', 'quarter'] = '2026Q3 (partial: resolved after 30 Jun)'

    orig = refunds.pivot_table(index='month', columns='refund_reason_code', values='refund_inr', aggfunc='sum', fill_value=0)
    corr = refunds.pivot_table(index='month', columns='corrected_code', values='refund_inr', aggfunc='sum', fill_value=0)
    for p in (orig, corr):
        p['TOTAL'] = p.sum(axis=1)

    exc_cols = ['ticket_id', 'month', 'agent_id', 'agent_name', 'agent_team', 'refund_inr', 'refund_reason_code',
                'corrected_code', 'replacement_issued', 'double_payout', 'goodwill_over_cap', 'policy_leak',
                'agent_notes', 'ai_evidence']
    exceptions = refunds[refunds.double_payout | refunds.goodwill_over_cap][exc_cols].sort_values('policy_leak', ascending=False)

    gw = refunds.refund_reason_code == 'GW-OTHER'
    recent = refunds[refunds.quarter.isin(['2026Q1', '2026Q2'])]

    # business goal: double payout share now -> target, saving = cases avoided x avg leak per case
    dp_share = recent.double_payout.mean()
    dp_leak_q = recent.double_payout_leak.sum() / 2
    target_leak_q = dp_leak_q * DP_TARGET_SHARE / dp_share
    goal = (f'Cut refunds that also got a replacement from {dp_share:.0%} of refunds to under {DP_TARGET_SHARE:.0%}, '
            f'worth about Rs {(dp_leak_q - target_leak_q) / 1e5:.1f} lakh a quarter '
            f'(Rs {(dp_leak_q - target_leak_q) * 4 / 1e5:.1f} lakh a year).')

    summary = pd.DataFrame([
        ('BUSINESS GOAL', goal),
        ('Double payouts as share of refunds, 2026', dp_share),
        ('Double payout cost per quarter, 2026 avg', dp_leak_q),
        ('Raw export total (what the export adds up to)', wf.Rs.iloc[0]),
        ('True refund total, Jan 2025 - Jun 2026', wf.Rs.iloc[-1]),
        ('Average refunds per quarter, 2026', recent.refund_inr.sum() / 2),
        ('Peak quarter (Q4 2025)', refunds[refunds.quarter == '2025Q4'].refund_inr.sum()),
        ('Refunds coded GW-OTHER (agent dropdown), share of Rs', refunds[gw].refund_inr.sum() / refunds.refund_inr.sum()),
        ('...of which still goodwill after AI reads the notes, share of Rs',
         refunds[gw & (refunds.corrected_code == 'GW-OTHER')].refund_inr.sum() / refunds.refund_inr.sum()),
        ('Double payouts (refund AND replacement) - agent flag', int((refunds.replacement_issued == 'Y').sum())),
        ('Double payouts - agent flag + AI reading the notes', int(refunds.double_payout.sum())),
        ('Policy leak per quarter, 2026 avg (double payouts + goodwill above Rs 500 cap, no overlap)',
         recent.policy_leak.sum() / 2),
        ('...of which double payouts', recent.double_payout_leak.sum() / 2),
    ], columns=['Metric', 'Value'])

    method = pd.DataFrame({'Decision / assumption': [
        'Duplicates: 638 tickets appear twice (helpdesk + legacy copy). Kept the helpdesk copy.',
        'Legacy Freshdesk refunds are stored in paise: divided by 100. Proven on 125 duplicate pairs (ratio exactly 100).',
        'Timestamps: policy says the legacy event log is UTC, but in this export legacy and helpdesk show the same '
        'resolution-hour pattern and handle time, so no shift was applied.',
        'Refund month = month resolved (when money goes out); created month if not resolved yet. '
        '2026Q3 holds 10 refunds created in June and resolved after the data cut-off.',
        f"AI (Gemini Flash-Lite, prompt {PROMPT_VERSION}) re-reads only refunds the agent coded GW-OTHER, plus refunds whose note mentions a "
        "replacement. The agent's original code is always kept next to the AI code.",
        'Double payout = refund AND replacement on the same ticket (policy: never). Cost counted conservatively as the '
        'cheaper of the refund or the replacement (unit cost + Rs 340), since one remedy was owed.',
        'Goodwill over cap = still goodwill after AI reading and above Rs 500. Only the excess above Rs 500 is counted, '
        'and not again if the ticket is already a double payout.',
        'Agent view shows refund rate (refunds / tickets handled) and team: Billing and Returns Desk refund by design.',
        'Double payout count is a floor: refunds that were neither GW-OTHER nor mention a replacement were not re-read.',
    ]})
    return {'Summary': summary, 'Quarterly': quarterly, 'Waterfall': wf, 'By reason - agent code': orig,
            'By reason - corrected': corr, 'By agent': by_agent(df, refunds), 'Exceptions': exceptions,
            'AI accuracy': eval_scores(cache, eval_dir), 'Method': method}


def write_excel(tables, path):
    from openpyxl.styles import Alignment, Font, PatternFill
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with pd.ExcelWriter(path, engine='openpyxl') as xw:
        for name, t in tables.items():
            t.to_excel(xw, sheet_name=name[:31], index=name.startswith('By reason'))
        for ws in xw.book.worksheets:
            ws.freeze_panes = 'B2' if ws.title.startswith('By reason') else 'A2'
            for cell in ws[1]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill('solid', fgColor='305496')
                cell.alignment = Alignment(wrap_text=True, vertical='top')
            for col in ws.columns:
                header = str(col[0].value or '')
                long_text = header in ('agent_notes', 'ai_evidence', 'Decision / assumption', 'Metric', 'Step')
                width = 70 if long_text else min(max(len(header), 10) + 2, 24)
                ws.column_dimensions[col[0].column_letter].width = width
                for cell in col[1:]:
                    if isinstance(cell.value, float):
                        is_share = 'rate' in header or (ws.title == 'Summary' and cell.value < 1)
                        cell.number_format = '0.0%' if is_share else '#,##0'
                    if long_text:
                        cell.alignment = Alignment(wrap_text=True, vertical='top')


def run(data_dir='.', out='output/board_pack.xlsx', do_label=False):
    raw, agents, orders, products = load_data(data_dir)
    df, dropped = clean(raw, agents, orders, products)
    refunds = df[df.refund_inr.notna()].copy()

    cache_path = os.path.join(data_dir, 'cache', 'llm_labels.jsonl')
    cache = load_cache(cache_path)
    if do_label:
        need = refunds[(refunds.refund_reason_code == 'GW-OTHER') |
                       refunds.agent_notes.str.contains(REPL_WORDS, case=False, na=False)]
        label_missing(need, cache, cache_path, os.path.join(data_dir, 'prompts', f'{PROMPT_VERSION}.txt'))

    refunds = attach_labels(refunds, cache)
    tables = build_tables(raw, df, dropped, refunds, cache, os.path.join(data_dir, 'eval'))
    write_excel(tables, out)
    return df, dropped, refunds, tables


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Build the Vireo refund board pack.')
    ap.add_argument('--data-dir', default='.')
    ap.add_argument('--out', default='output/board_pack.xlsx')
    ap.add_argument('--label', action='store_true', help='call Gemini for refunds missing from the cache')
    a = ap.parse_args()
    df, dropped, refunds, tables = run(a.data_dir, a.out, a.label)
    s = tables['Summary'].set_index('Metric').Value
    print(f'wrote {a.out}')
    print(f"  true refund total : Rs {s['True refund total, Jan 2025 - Jun 2026']:,.0f}"
          f"  (export sums to Rs {s['Raw export total (what the export adds up to)']:,.0f})")
    print(f'  goal              : {s["BUSINESS GOAL"]}')
