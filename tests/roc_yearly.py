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
from pandas import rolling_mean
import collections
from datetime import timedelta
import pprint

from dttrader import DTPortfolio, DTEODChangeTrader

class DTPortfolio:
    def __init__(self, cash):
        self.start_cash = cash
        self.port = {'cash': cash}
        self.buy_dates = []
        self.sell_dates = []
        self.pct = 0

    def pre_cache(self, context, data):
        for stock in context.stocks:
            if stock.symbol not in self.port:
                self.port[stock.symbol] = {'pos': 0, 'trades': [], 'first_price': data[stock].price}
            self.port[stock.symbol]['last_price'] = data[stock].price

    def order_add_percent(self, context, data, stock, pct, quiet=True):
        now = get_datetime().date()
        if not quiet:
            print("buy", now, stock.symbol)
        new_pct = min(self.pct + pct, 1)
        self.buy_dates.append(now)
        self.order_target_percent(context, data, stock, new_pct)

    def order_sub_percent(self, context, data, stock, pct, quiet=True):
        now = get_datetime().date()
        if not quiet:
            print("sell", now, stock.symbol)
        new_pct = max(self.pct - pct, 0)
        self.sell_dates.append(now)
        self.order_target_percent(context, data, stock, new_pct)

    def order_target_percent(self, context, data, stock, pct):
        # quantopian...
        # order_target_percent(stock, pct)

        # our naive simulation...
        now = get_datetime().date()
        # pct = min(max(pct, 0), 1)
        self.pct = pct

        if stock.symbol not in self.port:
            self.port[stock.symbol] = {'pos': 0, 'trades': []}

        dict = self.port[stock.symbol]
        price = int(data[stock].price * 100) / 100.0
        value = self.port['cash'] + price * dict['pos']
        to_invest = value * pct
        new_pos = int(to_invest / price)
        prev_pos = dict['pos']
        diff_pos = new_pos - prev_pos
        to_invest = int(price * diff_pos * 100) / 100.0
        dict['pos'] = new_pos
        self.port['cash'] -= to_invest
        dict['trades'].append({'date': now, 'cost': to_invest, 'price': price, 'pos': diff_pos, 'value': value})
        self.port[stock.symbol] = dict

    def dump(self):
        pprint.pprint(self.port, width=200)

    def performance_csv(self, prefix=""):
        sp = self.port[my_stock]
        st = int((self.port['cash'] + sp['pos'] * sp['last_price']) * 100.0) / 100.0
        print(prefix+",%.2f" % (st))

    def csv(self):
        #print("--- portfolio csv ---")

        print("cash,10000")
        sp = self.port[my_stock]
        bhpos = 5000 / sp['first_price']
        bh = int((bhpos * sp['last_price'] + 5000) * 100.0) / 100.0
        st = int((self.port['cash'] + sp['pos'] * sp['last_price']) * 100.0) / 100.0

        print("first price,%0.2f" % (sp['first_price']))
        print("last price,%0.2f" % (sp['last_price']))
        print("Buy&Hold,%0.2f" % (bh))
        print("Strategy,%0.2f\n" % (st))

        print("cost,date,position,price,st value,bh value")
        for trade in sp['trades']:
            d = trade['date']
            bh = int((bhpos * trade['price'] + 5000) * 100.0) / 100.0
            print("%0.2f,%d-%d-%d,%d,%0.2f,%0.2f,%0.2f" %
                  (trade['cost'], d.year, d.month, d.day, trade['pos'], trade['price'], trade['value'], bh))

        print("Buy&Hold,%0.2f" % (bh))
        print("Strategy,%0.2f" % (st))
        #print("\n--- portfolio csv ---")

    def plot_signals(self, ax1):
        ymin, ymax = ax1.get_ylim()
        ax1.vlines(x=self.sell_dates, ymin=ymin, ymax=ymax, color='r')
        ax1.vlines(x=self.buy_dates, ymin=ymin, ymax=ymax, color='b')

        # all_dates = pv.axes[0].date
        # yx = (ymax - ymin) / 3
        # ax1.vlines(x=all_dates, ymin=ymin+yx, ymax=ymax-yx, color='g')


class DTEODChangeTrader:
    def __init__(self, buy_roc, sell_roc, buy_target, sell_target, roc_window=180):
        self.buy_roc = buy_roc
        self.sell_roc = sell_roc
        self.buy_target = buy_target
        self.sell_target = sell_target
        self.roc_window = roc_window
        self.name = "EODCT"
        self.prices = 0
        self.portfolio = DTPortfolio(10000)

    @property
    def portfolio(self):
        return self.__portfolio

    @portfolio.setter
    def portfolio(self, portfolio):
        self.__portfolio = portfolio

    def pre_cache(self):
        # closing prices for all stocks
        self.prices = history(self.roc_window, '1d', 'price')

    def handle(self, context, data, stock, quiet=True):
        # find the historical daily % changes
        # choose the top x% and bellow y% value
        # use them as thresholds for sell/buy signals

        velocity = self.prices.diff()
        rate_of_change = velocity / self.prices
        roc_sorted = rate_of_change.sort(stock)
        roc_size = len(roc_sorted)
        # index of nth element (top/bottom n% roc)
        buy_index = roc_size * self.buy_roc
        sell_index = -roc_size * self.sell_roc
        buy_threashold = roc_sorted.values[buy_index][0]
        sell_threashold = roc_sorted.values[sell_index][0]
        record(self.name + '_buy', buy_threashold)
        record(self.name + '_sell', sell_threashold)

        # calculate today's (now's) % change (roc)
        p_yesterday = self.prices[stock][-2]
        p_today = data[stock].price
        p_change = 1 - p_yesterday / p_today

        if p_change > sell_threashold:
            self.portfolio.order_sub_percent(context, data, stock, self.sell_target, quiet=quiet)
        elif p_change < buy_threashold:
            self.portfolio.order_add_percent(context, data, stock, self.buy_target, quiet=quiet)

year = 2015
my_stock = 'RUSL'  # CHAU
trade_start = 0

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

    if now < trade_start:
        return

    for stock in context.stocks:
        # to build stats later
        trader.handle(context, data, stock)

        # print(context.portfolio.positions)
        # print(context.portfolio.cash, context.portfolio.portfolio_value)


def plot_histogram(roc, ax3):
    h2 = {}
    # h3 = {}
    # hns = {}
    # hps = {}
    # ps = 0
    # ns = 0
    # for h in roc:
    #     if h >= 0:
    #         ps += 1
    #         if ns > 0:
    #             hns[ns] = hns.get(ns, 0)+1
    #         ns = 0
    #     elif h < 0:
    #         ns += 1
    #         if ps > 0:
    #             hps[ps] = hps.get(ps, 0)+1
    #         ps = 0
    #
    #     h3[h > 0] = h3.get(h > 0, 0)+1
    #     h = int(h*100)
    #     h2[h] = h2.get(h, 0)+1
    #
    # if h >= 0:
    #     hps[ps] = hps.get(ps, 0)+1
    # else:
    #     hns[ns] = hns.get(ns, 0)+1
    #
    # # h2 = hns
    # print("hps", hps)
    # print("hns", hns)
    # oh2 = collections.OrderedDict(sorted(h2.items()))

    # X2 = arange(len(h2))
    # ax3.bar(X2, oh2.values(), align='center', width=0.5)
    # plt.xticks(X2, oh2.keys())

    # print("h2", h2)
    # oh2 = collections.OrderedDict(sorted(h2.items()))
    #
    # X2 = arange(len(h2))
    # ax3.bar(X2, oh2.values(), align='center', width=0.5)
    # plt.xticks(X2, oh2.keys())

    # tmp = {}
    # tmp[-1] = h3[False]
    # tmp[1] = h3[True]
    # h3 = tmp
    # print("h3", h3)
    #
    # oh3 = collections.OrderedDict(sorted(h3.items()))
    # X3 = arange(len(h3))
    # ax3.bar(X3+0.5, oh3.values(), align='center', color='r', width=0.5)


def plot_roc(r, ax2):
    v = diff(r)
    v = insert(v, 0, v[0])
    roc = v / r
    obj = r.axes[0].date
    ax2.plot(obj, roc, 'x-', label='v')
    return roc


# Note: this function can be removed if running
# this algorithm on quantopian.com
def analyze(context=None, results=None):
    import matplotlib.pyplot as plt
    f, (ax1, ax2) = plt.subplots(nrows=2)
    # ax1.set_ylabel('Portfolio value (USD)')
    pv = results.portfolio_value
    pv = (pv / pv[0])
    # pv.plot(ax=ax1)

    global year
    ds = datetime(year, 1, 1)
    de = datetime(year, 3, 1)
    for symbol in [my_stock]:
        r = results.get(symbol)
        roc = plot_roc(r, ax2)
        r = (r / r[0])
        r.plot(ax=ax1)
        results.get('EODCT_buy').plot(ax=ax2, color='g')
        results.get('EODCT_sell').plot(ax=ax2, color='r')

        # plot_histogram(roc, ax3)
        ax2.set_xlim(ds, de)
        ax1.set_xlim(ds, de)

    # ax2.set_ylabel('price (USD)')

    plt.gcf().set_size_inches(18, 8)

    port.plot_signals(ax2)
    port.csv()

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

    # RUSL 2014 10000 0.15 0.3 0.4 0.2
    my_stock = sys.argv[1]
    year = int(sys.argv[2])
    port = DTPortfolio(int(sys.argv[3]))
    trader = DTEODChangeTrader(buy_threshold=float(sys.argv[4]),
                               sell_threshold=float(sys.argv[5]),
                               buy_pct=float(sys.argv[6]),
                               sell_pct=float(sys.argv[7]))
    trader.portfolio = port

    # Set the simulation start and end dates
    # create more data to prime metrics
    start = datetime(year - 1, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(year + 1, 1, 1, 0, 0, 0, 0, pytz.utc)
    trade_start = datetime(year, 1, 1, 0, 0, 0, 0, pytz.utc)

    # Load price data from yahoo.
    # print("load data")
    data = load_from_yahoo(stocks=[my_stock], indexes={}, start=start,
                           end=end)

    # Create and run the algorithm.
    algo = TradingAlgorithm(initialize=initialize, handle_data=handle_data,
                            identifiers=[my_stock], capital_base=10000)
    # print("run")
    results = algo.run(data)
    # print("analyze")
    # analyze(results=results)
    port.performance_csv(prefix="%s,%s,%s,%s,%s,%s,%s" % (sys.argv[1],sys.argv[2],sys.argv[3],
                                                          sys.argv[4],sys.argv[5],sys.argv[6],
                                                          sys.argv[7]))
