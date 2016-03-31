import numpy as np
from zipline.api import order, record, symbol, symbols, set_symbol_lookup_date

# Put any initialization logic here.  The context object will be passed to
# the other methods in your algorithm.
def initialize(context):
    set_symbol_lookup_date('2015-02-08')
    context.stocks = symbols(
        # we need stocks that are great when they are good
        
        # tech
        'AAPL', 'MSFT', 'INTC', 'FB', 
        'IBM', 'CSCO', 'ORCL',
        'AMZN', 'EA', 
        'EBAY', 'NVDA', 'YHOO', 

        # bio, from VNQ - they have bad sentiment for a while, so add more
        'SPG', 'PSA', 'EQR', 'HCN',
        'VTR', 'PLD', 'AVB', 'BXP',
        'HCP', 'VNO',
        
        # comodities
        # 'COKE',
        
        # no google data :( 'GOOG',
        # indexes and ETFs tend to not be as great when good.
        # 'SPY', 'VNQ', 'IHE', # mirror sp500, fresx, fbiox
        # 'IGE', 'IGM', 'IGN', 'IGV',  # ishares etfs
        # 'ONNN', 'SNPS', 'CDNS' # microelectronics, for kicks
       )
    context.sentiment_size = 100
    context.short_sentiment_size = 12
    context.sentiment = {}
    context.state = {}
    
    context.portfolio_percentages = [30, 20, 10, 8, 5, 2] # used for rebalance
    # reminder will be used on intraday
    
    context.portfolio_size = len(context.portfolio_percentages)
    context.frequency = 7
    context.date = None
    context.rebalance_date = None
    # set_nodata_policy(NoDataPolicy.LOG_ONLY)
    context.benchmark = symbol('SPY')

    context.cci = {}
    context.cci_level = {}
    context.HIGH_CCI = 180
    context.LOW_CCI = -180
    
    context.realize_gains_at = 5
    context.discounted_when = -2
    context.prev_cash = 0

    if context.done_for_the_day:
        context.done_for_the_day = False
    
# Will be called on every trade event for the securities you specify. 
def handle_data(context, data):
    today = get_datetime().date()

    if context.date is None:
        # lets start following SPY and make decisions later
        # order_target_percent(context.benchmark, 1) 
        context.date = today
        return
        
    for stock in symbols(        
        'SPG', 
        #'PSA', 'EQR', 'HCN',
        # 'VTR', 'PLD', 'AVB', 'BXP',
       ):
        record(stock.symbol, data[stock].price)

    # Do nothing unless the date has changed and its a new day.
    date_diff = today - context.date
    context.date = today
    
    if context.prev_cash != context.portfolio.cash:
        log.info("cash $%.2f" % (context.portfolio.cash))
        log.info("port "+str(context.portfolio.positions))
    context.prev_cash = context.portfolio.cash

    if date_diff.days == 0 and not(context.done_for_the_day):
        return handle_intraday(context, data)
    else:
        context.done_for_the_day = False
        return handle_overnight(context, data)
    
def handle_intraday(context, data):
    for stock in context.portfolio.positions:
        returns = calculate_returns(context, data, stock)
        # log.info("realize gains %s %.4f %.2f" % (stock.symbol, returns, context.realize_gains_at/100.0))
        if returns >= context.realize_gains_at/100.0:
            # realize gains
            _order_target_percent(context, data, stock, 0, "intraday")

    buy_list = []
    price_history = None
    for stock in context.stocks:
        v1 = data[stock].mavg(30)

        # calculate long sentiment if not there
        if not(stock in context.sentiment) or not(context.sentiment_size in context.sentiment[stock]):
            if price_history is None:
                price_history = history(context.sentiment_size * 2, '1d', 'price')
            calculate_sentiment(context, stock, price_history, context.sentiment_size)
            
        # score is better if short is bellow long
        long_sentiment = context.sentiment[stock][context.sentiment_size]
        score = (data[stock].price - v1)/v1
        
        # score is the most discounted, lets buy this one
        # price is 2% less than mavg
        if long_sentiment['days'] >= 30:
            if score < context.discounted_when/100.0:
                buy_list.append(stock)
    
    if len(buy_list)>5: # not sorting for now
        buy_list = buy_list[0:5]
        
    if len(buy_list)>0:
        context.done_for_the_day = True
        remaining_cash = context.portfolio.cash/len(buy_list)
        for stock in buy_list:
            if remaining_cash > data[stock].price*1.1 and not(stock is None):
                _order_target_value(context, data, stock, remaining_cash, "intraday")

def handle_overnight(context, data):
    today = context.date
    # calculates sentiments every day to keep track of happy days
    sentiment = {}
    cci = {}

    price_history = history(context.sentiment_size * 2, '1d', 'price')
    bars = context.short_sentiment_size
    high = history(bar_count = bars, frequency = '1d', field = 'high')
    low = history(bar_count = bars, frequency = '1d', field = 'low')
    close = history(bar_count = bars, frequency = '1d', field = 'close_price')
    
    # lets precalculate some metrics
    for stock in context.stocks:
        sentiment[stock] = calculate_sentiment(context, stock, price_history, context.sentiment_size)
        cci[stock] = calculate_cci(context, bars, high, low, close, stock)

    # also calculate measurements for benchmark
    benchmark = context.benchmark
    if not(benchmark in context.stocks):
        stock = benchmark
        sentiment[stock] = calculate_sentiment(context, stock, price_history, context.sentiment_size)
        cci[stock] = calculate_cci(context, bars, high, low, close, stock)
        
    # check if its time to rebalance
    if not(context.rebalance_date is None):
        date_diff = today - context.rebalance_date
        if date_diff.days < context.frequency:
            return
        
    context.rebalance_date = today

    # calculate scores, must buy and must sell
    # log.info("Calculating scored and must sell/buy")
    scores = []
    buy_list = []
    sell_list = []
    for stock in context.stocks:
        long_sentiment = sentiment[stock]

        # score will rank/sort, thus change portfolio holdings
        # not sure what is a good metric for score
        short_sentiment = calculate_sentiment(context, stock, price_history, context.short_sentiment_size)
        
        price_pct = calculate_returns(context, data, stock)
        score = - short_sentiment['sentiment'] # oposite from short trand!?
        # score = cci[stock] 

        if long_sentiment['days'] < 30: # or 1.1 * long_sentiment['sentiment'] < sentiment[benchmark]['sentiment']
            # if long sentiment less than 5% worse its a bad horse
            # if long sentiment not positive for at least 30 days its a bad horse
            # never riding bad horses
            sell_list.append([stock, score])
        else:
            ema_diff = sentiment[stock]['ema_diff']
            if ema_diff < context.discounted_when/100.0: 
            # if cci[stock] < 0:
                # stock is down, but we believe on it
                # so we consider it as "discounted", thus we buy it
                buy_list.append([stock, score])
            else:
                # not really sure how what to do
                scores.append([stock, score])

    # sort stocks by score - ignoring sell/buy stocks
    scores.sort(key=lambda score: score[1],reverse=True)
    buy_list.sort(key=lambda score: score[1],reverse=True)
    
    # prune stocks to portfolio size
    keep_size = context.portfolio_size - len(buy_list)
    if keep_size > 0:
        sell_list.extend(scores[keep_size:-1]) # more to sell
        buy_list.extend(scores[0:keep_size]) # more to keep/buy
    else:
        sell_list.extend(scores)
        sell_list.extend(buy_list[context.portfolio_size:-1])
        buy_list = buy_list[0:context.portfolio_size]
        
    # log info
    if len(buy_list) > 0:
        print_scores("buy", buy_list)
        
    # rebalance stocks
    portfolio_percentages = context.portfolio_percentages
    for index, score in enumerate(sell_list):
        _order_target_percent(context, data, score[0], 0, "rebalance")

    for index, score in enumerate(buy_list):
        _order_target_percent(context, data, score[0], portfolio_percentages[index]/100.0, "rebalance")
        
    # fill up with benchmark stock
    if len(buy_list) < context.portfolio_size:
        remaining = 0
        for index in range(len(buy_list), context.portfolio_size):
            remaining = remaining + portfolio_percentages[index]
        _order_target_percent(context, data, benchmark, remaining/100.0, "top off")
    
def _order_target_value(context, data, stock, value, reason="-"):
    order_target_value(stock, value)
    _order(context, data, stock, None, value, reason)

def _order_target_percent(context, data, stock, percent, reason="-"):
    order_target_percent(stock, percent)
    _order(context, data, stock, percent)
    
def _order(context, data, stock, percent=None, value=None, reason="-"):
    if not(stock in context.state):
        context.state[stock] = {'%': 0, 
                                'value': 0,
                                'sales': [], 
                                'purchases': [],
                                'last_purchase_price': 0
                               }
        
    prev = context.state[stock]['%']

    if value > 0 or percent is None: # otherwise we process the values incorrectly
        percent = value/context.portfolio.portfolio_value
    if value is None:
        value = 0
        
    context.state[stock]['%'] = percent
    context.state[stock]['value'] = value
    price = data[stock].price
    if value > 0 or percent > prev:
        # buying
        context.state[stock]['last_purchase_price'] = price
        context.state[stock]['purchases'].append({'price': price})
        log.info("%s buying %s %.2f%% ($%.2f) at $%.2f" % (reason, stock.symbol, percent*100.0, value, price))
    elif prev > percent: 
        # selling
        gain = calculate_returns(context, data, stock)
        log.info("%s selling %d %s return %.2f" % (reason, (prev-percent)*100.0, stock.symbol, gain*100))
        context.state[stock]['sales'].append({'price': price})
        
def calculate_returns(context, data, stock):
    # for positions we dont hold return 0
    returns = 0 
    if stock in context.portfolio.positions and context.portfolio.positions[stock].amount > 0:
        # calculate % gain
        if stock in context.state:
            purchased_at = context.state[stock]['last_purchase_price']
            returns = (data[stock].price - purchased_at)/purchased_at
    return returns            

def print_scores(msg, scores):
    s = []
    for score in scores:
        s.append([score[0].symbol, score[1]])
        
    log.info(msg+" "+str(s))

def calculate_cci(context, bars, high, low, close, stock):
    cci_result = talib.CCI(high[stock], low[stock], close[stock])
       
    if cci_result[-1] > context.HIGH_CCI:
        cci_level = 1
    elif cci_result[-1] < context.LOW_CCI:
        cci_level = -1
    else:
        cci_level = 0
        
    context.cci[stock] = cci_result[-1]
    context.cci_level[stock] = cci_level
    return cci_result[-1]

    
def calculate_sentiment(context, stock, price_history, size=100):
    # log.info('Calculating sentiment for '+stock.symbol)
    prices = price_history[stock]
        
    if not(stock in context.sentiment):
        context.sentiment[stock] = {}
        
    data = {}
    if size in context.sentiment[stock]:
        data = context.sentiment[stock][size]

    if np.isnan(prices).any():
        data['sentiment'] = -999
        data['days'] = 0
        context.sentiment[stock][size] = data
        return data
        
    ema = talib.EMA(prices, timeperiod=size)
    x = np.array(np.arange(size))
    y = np.array(ema[-(1+size):-1])
    coefs = np.polyfit(x, y, 1)
    sentiment = coefs[0] # a in (a*x + c)

    if sentiment < 0:
        days = 0
    else:
        if 'days' in data:
            days = data['days'] + 1
        else:
            # start with 30 to prevent not transacting in the beginning
            days = 30

    data['sentiment'] = sentiment
    data['days'] = days

    ema_fast = talib.EMA(prices, timeperiod=5)
    # ema_long = talib.EMA(prices, timeperiod=50)
    ema_diff = (ema_fast[-1] - ema[-1])/ema[-1]
    data['ema_diff'] = ema_diff

    # log.info(data)
    context.sentiment[stock][size] = data

    return data
    
# Define the MACD function   
def MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9):
    '''
    Function to return the difference between the most recent 
    MACD value and MACD signal. Positive values are long
    position entry signals 

    optional args:
        fastperiod = 12
        slowperiod = 26
        signalperiod = 9

    Returns: macd - signal
    '''
    macd, signal, hist = talib.MACD(prices, 
                                    fastperiod=fastperiod, 
                                    slowperiod=slowperiod, 
                                    signalperiod=signalperiod)
    return macd[-1] - signal[-1]

