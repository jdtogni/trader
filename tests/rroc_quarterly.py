#!/usr/bin/env python
#
# Copyright 2014 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zipline.api import order, order_target_percent, record, symbol, symbols, set_symbol_lookup_date, history, \
    get_datetime, schedule_function, date_rules, time_rules, get_open_orders
from numpy import diff, isnan, arange, insert, sort, array
from pandas import rolling_mean, Timestamp, to_datetime
import collections
from datetime import timedelta, date
import pprint
from dttrader import DTPortfolio, DTEODChangeTrader, DTEODChangeTrader2


year = 0
month = 1
my_stock = ''
trade_start = 0
start = 0
end = 0

def initialize(context):
    set_symbol_lookup_date('2015-02-08')
    context.stocks = symbols(my_stock)
    context.prev_cash = 0

    schedule_function(handle_end_of_day,
                      date_rules.every_day(),
                      time_rules.market_close(minutes=30))


def handle_data(context, data):
    today = get_datetime().date()
    return


def handle_end_of_day(context, data):
    # yesterday + today close price
    now = get_datetime()
    # price_history = history(2, '1d', 'price')

    global trade_start, port, trader
    trader.pre_cache()
    port.pre_cache(context, data)

    for stock in context.stocks:
        record(stock.symbol, data[stock].price)

    if now.date() < trade_start:
        return

    port.handle(context, data)

    for stock in context.stocks:
        # to build stats later
        trader.handle(context, data, stock, quiet=False)

# Note: this function can be removed if running
# this algorithm on quantopian.com
def analyze(context=None, results=None):
    import matplotlib.pyplot as plt
    f, (ax1, ax2) = plt.subplots(nrows=2)
    # ax1.set_ylabel('Portfolio value (USD)')
    pv = results.portfolio_value
    pv = (pv / pv[0])
    # pv.plot(ax=ax1, color='b')

    p = results.get('pct')
    p = p.dropna()
    p.plot(ax=ax1, color='gray')

    bh = results.get(my_stock)
    bh = (bh/bh.loc[str(trade_start):str(trade_start+timedelta(days=1)):][0])
    bh.plot(ax=ax1, color='g')

    v = results.get('value')
    v = v.dropna()
    v = (v/v[0])
    v.plot(ax=ax1, color='r')

    trader.plot(results, my_stock, ax2)
    port.plot_signals(ax2)

    ax2.set_xlim(trade_start, end)
    ax1.set_xlim(trade_start, end)

    plt.gcf().set_size_inches(18, 8)

    print("show")
    plt.show()
    print("after show")
    # print(results)

# Note: this if-block should be removed if running
# this algorithm on quantopian.com
if __name__ == '__main__':
    from datetime import datetime
    import pytz
    from zipline.algorithm import TradingAlgorithm
    from zipline.utils.factory import load_from_yahoo
    import sys

    # sys.argv = sys.argv + ("SOXL 2015-3 10000 0.15 0.35 1 0.2".split(" "))
    # sys.argv = sys.argv + ("SOXL 2014-1 10000 1".split(" "))
    sys.argv = sys.argv + ("BRZU 2015-3 10000 0.5".split(" "))
    my_stock = sys.argv[1]
    year = int(sys.argv[2][:4])
    quarter = int(sys.argv[2][5:])
    month = (quarter - 1) * 3 + 1

    port = DTPortfolio(cash=int(sys.argv[3]))
    window = 180

    trader = DTEODChangeTrader2(rate=float(sys.argv[4]), roc_window=window)
    trader.portfolio = port

    # Set the simulation start and end dates
    # create more data to prime metrics
    trade_start = date(year, month, 1)
    start = trade_start + timedelta(days=-300)
    end = trade_start + timedelta(days=92)

    # Load price data from yahoo.
    data = load_from_yahoo(stocks=[my_stock], indexes={}, start=start, end=end)

    # Create and run the algorithm.
    algo = TradingAlgorithm(initialize=initialize, handle_data=handle_data,
                            identifiers=[my_stock], capital_base=10000)
    results = algo.run(data)
    # port.performance_csv(prefix="%s,%s,%s,%s,%s,%s,%s" % (sys.argv[1], sys.argv[2], sys.argv[3],
    #                                                       sys.argv[4], sys.argv[5], sys.argv[6],
    #                                                       sys.argv[7]))
    port.performance_csv(prefix="%s,%s,%s,%s" % (sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
    analyze(results=results)
