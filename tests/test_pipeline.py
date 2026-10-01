import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import run  # noqa: E402

TRUE_TOTAL = 6_709_932


@pytest.fixture(scope='module')
def cleaned():
    raw, agents, orders, products = run.load_data(ROOT)
    df, dropped = run.clean(raw, agents, orders, products)
    return raw, df, dropped


def test_waterfall_adds_back_to_raw_total(cleaned):
    raw, df, dropped = cleaned
    wf = run.waterfall(raw, df, dropped)
    # every rupee of the raw export lands in exactly one step
    assert abs(wf.Rs.iloc[:3].sum() - wf.Rs.iloc[3]) < 0.01
    assert abs(wf.Rs.iloc[0] - raw.refund_amount_inr.sum()) < 0.01


def test_no_duplicate_tickets(cleaned):
    _, df, _ = cleaned
    assert df.ticket_id.is_unique


def test_monthly_totals_equal_true_total(cleaned):
    _, df, _ = cleaned
    monthly = df[df.refund_inr.notna()].groupby('refund_month').refund_inr.sum()
    assert round(monthly.sum()) == TRUE_TOTAL
