"""Money-weighted return (XIRR) for the Saxo portfolio.

Time-weighted return doesn't need a local implementation: Saxo's
hist/v4/performance/timeseries endpoint already computes it server-side
(TimeWeighted.Accumulated) - see src/saxo/performance.py.

XIRR does need local computation: Saxo's Balance.CashTransfer series is a
running cumulative total of net deposits/withdrawals, not individual
cashflow events, and there's no money-weighted return field in KeyFigures.
"""

from typing import List

from pyxirr import xirr


def compute_xirr(cash_transfer_series: List[dict], final_value: float, final_date: str) -> float:
    """cash_transfer_series: Saxo's Balance.CashTransfer points, cumulative
    over time ([{"Date": ..., "Value": ...}, ...]).

    A rise in the cumulative total is a deposit (money the investor sent
    into the account - an outflow from their point of view, so negative for
    XIRR); a drop is a withdrawal (positive). The final portfolio value is
    added as a terminal positive cashflow, as if liquidated on that date.
    """
    dates = []
    amounts = []
    previous = 0.0

    for point in sorted(cash_transfer_series, key=lambda p: p["Date"]):
        delta = point["Value"] - previous
        if delta != 0:
            dates.append(point["Date"])
            amounts.append(-delta)
        previous = point["Value"]

    dates.append(final_date)
    amounts.append(final_value)

    return xirr(dates, amounts)
