from zipline.api import order, order_target_percent, record, symbol, symbols, set_symbol_lookup_date, history, \
    get_datetime, schedule_function, get_open_orders
import pprint
from numpy import diff, isnan, arange, insert, sort, array


class DTPortfolio:
    def __init__(self, cash):
        self.start_cash = cash
        self.port = {}
        self.cash = cash
        self.buy_dates = []
        self.sell_dates = []
        self.pct = 0

    def pre_cache(self, context, data):
        for stock in context.stocks:
            if stock.symbol not in self.port:
                self.port[stock.symbol] = {'pos': 0, 'trades': []}
            self.port[stock.symbol]['last_price'] = data[stock].price

    def handle(self, context, data):
        for stock in context.stocks:
            record("value", self.value(data, stock))
            record("pct", self.pct)
            if 'first_price' not in self.port[stock.symbol]:
                self.port[stock.symbol]['first_price'] = data[stock].price

    def order_add_percent(self, context, data, stock, pct, quiet=True):
        now = get_datetime().date()
        new_pct = min(self.pct + pct, 1)
        if not quiet:
            print("buy", str(now), stock.symbol, new_pct)
        self.buy_dates.append(now)
        self.order_target_percent(context, data, stock, new_pct)

    def order_sub_percent(self, context, data, stock, pct, quiet=True):
        now = get_datetime().date()
        new_pct = max(self.pct - pct, 0)
        if not quiet:
            print("sell", str(now), stock.symbol, new_pct)
        self.sell_dates.append(now)
        self.order_target_percent(context, data, stock, new_pct)

    def value(self, data, stock):
        price = data[stock].price
        value = int((self.cash + price * self.port[stock.symbol]['pos']) * 100.0)/100.0
        return value

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
        value = self.cash + price * dict['pos']
        to_invest = value * pct
        new_pos = int(to_invest / price)
        prev_pos = dict['pos']
        diff_pos = new_pos - prev_pos
        to_invest = int(price * diff_pos * 100) / 100.0
        dict['pos'] = new_pos
        self.cash -= to_invest
        dict['trades'].append({'date': now, 'cost': to_invest, 'price': price, 'pos': diff_pos, 'value': value})
        self.port[stock.symbol] = dict

    def dump(self):
        pprint.pprint(self.port, width=200)

    def performance_csv(self, prefix=""):
        for my_stock in self.port:
            sp = self.port[my_stock]
            st = int((self.cash + sp['pos'] * sp['last_price']) * 100.0) / 100.0
            bhpos = self.start_cash / sp['first_price']
            bh = int((bhpos * sp['last_price']) * 100.0) / 100.0
            print(prefix+",%.2f,%.2f" % (st, bh))

    def csv(self):
        #print("--- portfolio csv ---")

        print("cash,10000")
        for my_stock in self.port:
            sp = self.port[my_stock]
            bhpos = self.start_cash / sp['first_price']
            bh = int((bhpos * sp['last_price']) * 100.0) / 100.0
            st = int((self.cash + sp['pos'] * sp['last_price']) * 100.0) / 100.0

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

            print("Strategy,%0.2f" % (st))
            print("Buy&Hold,%0.2f" % (bh))

        #print("\n--- portfolio csv ---")

    def plot_signals(self, ax1):
        ymin, ymax = ax1.get_ylim()
        ax1.vlines(x=self.sell_dates, ymin=ymin, ymax=ymax, color='r')
        ax1.vlines(x=self.buy_dates, ymin=ymin, ymax=ymax, color='b')

        # all_dates = pv.axes[0].date
        # yx = (ymax - ymin) / 3
        # ax1.vlines(x=all_dates, ymin=ymin+yx, ymax=ymax-yx, color='g')

class DTEODChangeTrader:
    def __init__(self, buy_threshold, sell_threshold, buy_pct, sell_pct, roc_window=180):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.buy_pct = buy_pct
        self.sell_pct = sell_pct
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
        buy_index = roc_size * self.buy_threshold
        sell_index = -roc_size * self.sell_threshold
        buy_threashold = roc_sorted.values[buy_index][0]
        sell_threashold = roc_sorted.values[sell_index][0]
        record(self.name + '_buy', buy_threashold)
        record(self.name + '_sell', sell_threashold)

        # calculate today's (now's) % change (roc)
        p_yesterday = self.prices[stock][-2]
        p_today = data[stock].price
        p_change = 1 - p_yesterday / p_today

        if p_change > sell_threashold:
            self.portfolio.order_sub_percent(context, data, stock, self.sell_pct, quiet=quiet)
        elif p_change < buy_threashold:
            self.portfolio.order_add_percent(context, data, stock, self.buy_pct, quiet=quiet)

    def plot(self, results, symbol, ax2):
        r = results.get(symbol)
        self.plot_roc(r, ax2)
        # plot threasholds
        results.get(self.name + '_buy').plot(ax=ax2, color='g')
        results.get(self.name + '_sell').plot(ax=ax2, color='r')

    def plot_roc(self, r, ax2):
        v = diff(r)
        v = insert(v, 0, v[0])
        roc = v / r
        obj = r.axes[0].date
        ax2.plot(obj, roc, 'x-', label='v')
        return roc


class DTEODChangeTrader2:
    def __init__(self, rate=0.5, roc_window=180):
        self.rate = rate
        self.roc_window = roc_window
        self.name = "EODCT"
        self.prices = 0
        self.portfolio = DTPortfolio(10000)
        self.last_txn = 0
        self.setup()

    def setup(self):
        # Offset makes strategy to like to trade
        pref_sell = 1 + (max(0, self.portfolio.pct - 0.75) * 3)
        pref_buy = 1 + (max(0, 0.25 - self.portfolio.pct) * 3)

        # threashold 0.05 to 0.4, 0.05 step => 1 to 0.1
        # pct = if threashold is 0.4, pct is 20%, if 0.05, pct is 100%
        self.buy_threasholds  = arange(0.4, 0.0499, -0.05) * self.rate * pref_buy * (2 - pref_sell)
        self.sell_threasholds = arange(0.4, 0.0499, -0.05) * self.rate * pref_sell* (2 - pref_buy)

        ranges = len(self.buy_threasholds) - 1

        self.buy_pcts = arange(0.2, 1.01, 0.8/ranges)
        self.sell_pcts = arange(0.2, 1.01, 0.8/ranges)


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
        self.setup()
        # find the historical daily % changes
        # choose the top x% and bellow y% value
        # use them as thresholds for sell/buy signals

        velocity = self.prices.diff().dropna()
        rate_of_change = (velocity / self.prices).dropna()
        roc_sorted = rate_of_change.sort(stock)
        roc_size = len(roc_sorted)

        # calculate today's (now's) % change (roc)
        p_yesterday = self.prices[stock][-2]
        p_today = data[stock].price
        p_change = 1 - p_yesterday / p_today
        if not quiet:
            print("y %.2f, t %.2f, c %.4f" % (p_yesterday, p_today, p_change))

        # index of nth element (top/bottom n% roc)
        ranges = len(self.buy_threasholds)
        done = False
        for i in range(ranges-1, -1, -1):
            bi = (roc_size - 1) * min(1.0, self.buy_threasholds[i])
            bt = roc_sorted.values[bi][0]

            si = - (roc_size - 1) * min(1.0, self.sell_threasholds[i])
            st = roc_sorted.values[si][0]
            if not quiet:
                print("* bi %.2f, bi %d, bt %.4f, bp %.4f, si %.2f, si %d, st %.4f, sp %.4f" %
                    (self.buy_threasholds[i], bi, bt, self.buy_pcts[i],
                    self.sell_threasholds[i], si, st, self.sell_pcts[i]))

            if not done:
                if p_change > st:
                    self.portfolio.order_sub_percent(context, data, stock, self.sell_pcts[i], quiet)
                    self.last_txn = get_datetime().date()
                    done = True

                elif p_change < bt:
                    self.portfolio.order_add_percent(context, data, stock, self.buy_pcts[i], quiet)
                    self.last_txn = get_datetime().date()
                    done = True

            record(self.name + '_buy' + str(i), bt if bt < 0 else 0)
            record(self.name + '_sell' + str(i), st if st > 0 else 0)

    def plot(self, results, symbol, ax2):
        r = results.get(symbol)
        self.plot_roc(r, ax2)
        # plot threasholds
        ranges = len(self.buy_threasholds)
        for i in [0, ranges-1]:
            results.get(self.name + '_buy' + str(i)).plot(ax=ax2)
            results.get(self.name + '_sell' + str(i)).plot(ax=ax2)
            # print("b", i, results.get(self.name + '_buy' + str(i)).dropna(),
            #       "s", i, results.get(self.name + '_sell' + str(i)).dropna())

    def plot_roc(self, r, ax2):
        v = diff(r)
        v = insert(v, 0, v[0])
        roc = v / r
        obj = r.axes[0].date
        ax2.plot(obj, roc, 'x-', label='v')
        return roc

