import pandas as pd
import numpy as np
from copy import deepcopy
from math import exp, isnan

def nanmax(*args, default=None): # returns the maximum of the given values without nan
    """
    Find the maximum value, ignoring nan values.

    Parameters:
    - *args: Variable number of arguments or a single iterable (numeric values).
    - default: The value to return if no non-nan values are provided.

    Returns:
    - The maximum numeric value, or the specified default if no non-nan values are provided.
    """
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        iterable = args[0]
    else:
        iterable = args

    filtered_values = [x for x in iterable if not isnan(x)]

    if not filtered_values:
        return default

    return max(filtered_values)

def nanmin(*args, default=None):
    """
    Find the minimum value, ignoring nan values.

    Parameters:
    - *args: Variable number of arguments or a single iterable (numeric values).
    - default: The value to return if no non-nan values are provided.

    Returns:
    - The minimum numeric value, or the specified default if no non-nan values are provided.
    """
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        iterable = args[0]
    else:
        iterable = args

    filtered_values = [x for x in iterable if not isnan(x)]

    if not filtered_values:
        return default

    return min(filtered_values)

class Operation():
    def __init__(self, amnt:float, typ="Buy"):#, info={"ticker":"", "entryTime":"", "entryPrice":0, "fee":0}):
        self.amount = amnt
        self.type = typ # could also be sell meaning bearish means profit
        # self.stockInfo = info
        self.diagnostics = {} # diagnostic values at the end like exit percentage etc
        self.variables = {} # variables that can be defined for each operation
        self.reviewVis = [] # objects that should be shown when the review is run

class Visual():
    def __init__(self, name, shape, color, data=[]):
        self.name = name # name of the object class i.e. dot, line...
        self.color = color # color of the object
        self.shape = shape 
        self.toolTip = ""
        self.data = data # data e.g. line data | if data is a string; take variable with name from parent indicator
        self.position = (None, None) # if none then copy values from viewer

class Indicator(): # parent class to make initializing easier
    def __init__(self, stock: list):
        self.stock = stock # stock data given to it
        self.data = {} # data for indicator
        self.argTypes = {}
        # list of displaymodes: "graph", "bottom graph", "volume"
        self.dMode = "" # displaymode for viewing indicator
        self.dData = {} # displaydata for viewing indicator

    def setArgs(self, args): 
        for a in range(len(self.argTypes.keys())):
            key = list(self.argTypes.keys())[a]
            setattr(self, key, args[a])

class Volume(Indicator): # simple moving average
    def __init__(self, stock: list = []):
        super().__init__(stock)
        self.dMode = "bottom graph"
        if stock != []: self.calculate()
    
    def calculate(self):
        self.data["value"] = [x[4] for x in self.stock]
        col = [x[3]> x[0] for x in self.stock]
        for i in range(len(self.stock)):
            if col[i]: col[i] = "#00ff00"
            else: col[i] = "#ff0000"
        mi, ma = float("inf"), float("-inf")
        for c in self.stock:
            if c[4] > ma: ma = c[4]
            if c[4] < mi: mi = c[4]
        rangey = (mi, ma)
        self.dData = {"volume": Visual("rect", "r2", col, (0, "value")), "rangey":rangey}

class SMA(Indicator): # simple moving average
    def __init__(self, stock: list = [], window: int = 200):
        super().__init__(stock)
        self.window = window # sma window
        self.argTypes = {"window":{"argName":"Window", "value":200, "default":200, "type":int, "lower":1, "upper":float("nan")}}
        self.dMode = "graph"
        if stock != []: self.calculate()
    
    def calculate(self):
        if len(self.stock) <= self.window: # if too little data is given; make a list of nan values
            self.data["value"] = self.window*[float("nan")]
        temp = pd.DataFrame(self.stock)
        self.data["value"] = temp.rolling(window=self.window).mean()[3].reset_index(drop=True).to_list()
        self.dData = {"line": Visual("line", "", "#ff0000", "value")}

class EMA(Indicator): # exponential moving average
    def __init__(self, stock: list = [], window: int = 200):
        super().__init__(stock)
        self.window = window # ema window
        self.argTypes = {"window":{"argName":"Window", "value":200, "default":200, "type":int, "lower":1, "upper":float("nan")}}
        self.dMode = "graph"
        if stock != []: self.calculate()
    
    def calculate(self):
        if len(self.stock) <= self.window: # if too little data is given; make a list of nan values
            self.data["value"] = self.window*[float("nan")]
        temp = pd.DataFrame(self.stock)
        self.data["value"] = temp.ewm(span=self.window, adjust=False).mean()[3].reset_index(drop=True).to_list()
        self.dData = {"line": Visual("line", "", "#ff0000", "value")}

class RV(Indicator): # relative volume
    def __init__(self, stock: list = [], window: int = 20):
        super().__init__(stock)
        self.window = window # rv window
        self.argTypes = {"window":{"argName":"Window", "value":20, "default":20, "type":int, "lower":1, "upper":float("nan")}}
        self.dMode = "graph"
        if stock != []: self.calculate()
    
    def calculate(self):
        if len(self.stock) <= self.window: 
            self.data["value"] = self.window*[float("nan")]
        temp = pd.DataFrame(self.stock)
        temp = temp.rolling(window=self.window).mean()[4].reset_index(drop=True).to_list() # rolling volume average
        out = []
        for v in range(len(temp)):
            out.append(self.stock[v][4]/temp[v])
        self.data["value"] = out

class Sigma(Indicator): # sigma; standard deviation
    def __init__(self, stock: list = [], window: int = 20):
        super().__init__(stock)
        self.window = window # sigma window
        self.argTypes = {"window":{"argName":"Window", "value":20, "default":20, "type":int, "lower":1, "upper":float("nan")}}
        if stock != []: self.calculate()
    
    def calculate(self):
        temp = pd.DataFrame(self.stock)
        avg = temp.rolling(window=self.window).mean()[3].reset_index(drop=True).to_list() # get list of moving average
        dist = [] # distances
        sigmas = []
        for t in range(len(self.stock)):
            if t < self.window: dist.append(float("nan")) # if movavg has no value yet
            else: dist.append(pow(self.stock[t][3] - avg[t], 2))
        for t in range(len(self.stock)):
            if t < self.window*2: sigmas.append(float("nan")) # if movavg hasn't existed for self.window values yet
            else: 
                var = 0
                for i in range(self.window):
                    var += dist[t-self.window+i] # make average of last self.window values
                var /= self.window
                sigma = var**(1/2)
                sigmas.append(sigma)
        self.data["value"] = sigmas

class VWAP(Indicator): # volume weighted average price
    def __init__(self, stock: list = [], window: int = 60):
        super().__init__(stock)
        self.window = window # vwap window
        self.argTypes = {"window":{"argName":"Window", "value":60, "default":60, "type":int, "lower":1, "upper":float("nan")}}
        self.dMode = "graph"
        if stock != []: self.calculate()
    
    def calculate(self):
        if len(self.stock) <= self.window: 
            self.data["value"] = self.window*[float("nan")]
        temp = []
        prods = [] # price * volume of all
        for i in range(len(self.stock)): # equal to len(stock)
            prods.append(self.stock[i][3] * self.stock[i][4])
        for i in range(self.window): temp.append(float("nan")) # no value for first few values
        for i in range(self.window, len(self.stock)):
            cumsum = 0
            vols = 0 # all volumes
            for m in range(self.window): # for every window
                cumsum += prods[i-m]
                vols += self.stock[i-m][4]
            temp.append(cumsum/vols)
        self.data["value"] = temp
        self.dData = {"line": Visual("line", "", "#ff0000", "value")}

class RSI(Indicator): # relative strength index
    def __init__(self, stock: list = [], window: int = 14):
        super().__init__(stock)
        self.window = window # rv window
        self.argTypes = {"window":{"argName":"Window", "value":14, "default":14, "type":int, "lower":1, "upper":float("nan")}}
        self.dMode = "bottom graph"
        self.dData = {"rangey": (0, 100), "gridconv":[None, None, None, 25]}
        if stock != []: self.calculate()
    
    def calculate(self):
        # args [0] is window
        rss = [] # multiple rsi
        for spot in range(len(self.stock)):
            closes = []
            x = spot - self.window
            if x < 0: x = 0
            for st in self.stock[x:spot+1]:
                closes.append(st[3]) # get all closes in range
            prices = np.asarray(closes)
            deltas = np.diff(prices)
            gains = np.where(deltas >= 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            if len(gains) == 0: avg_gain = 0
            else: avg_gain = np.mean(gains[:self.window])
            if len(losses) == 0: avg_loss = 0
            else: avg_loss = np.mean(losses[:self.window])
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs)) # on a scale of 0-100
            else: rsi = 50 # if divide by 0 default to 50
            rss.append(rsi)
        self.data["value"] = rss
        self.dData["line"] = Visual("line", "", "#ff0000", "value")
        self.dData["middle"] = Visual("line", "", "#888888", 50)

class MACD(Indicator): # moving average convergence divergence
    def __init__(self, stock: list = []):
        super().__init__(stock)
        self.dMode = "bottom graph"
        self.dData = {"rangey": (-3, 3), "gridconv":[None, None, None, 1.5]}
        if stock != []: self.calculate()
    
    def calculate(self):
        temp = pd.DataFrame(self.stock)
        ema12 = temp.ewm(span=12, adjust=False).mean()[3].reset_index(drop=True).to_list()
        ema26 = temp.ewm(span=26, adjust=False).mean()[3].reset_index(drop=True).to_list()
        macd = []
        for e in range(len(ema12)):
            macd.append(ema12[e]-ema26[e])
        temp = pd.DataFrame(macd)
        signal = temp.ewm(span=9, adjust=False).mean()[0].reset_index(drop=True).to_list()
        self.data["macd"] = macd
        self.data["signal"] = signal
        self.dData = {"macd": Visual("line", "", "#ffff00", "macd"), "signal": Visual("line", "", "#ff0000", "signal"),
                      "zero": Visual("line", "", "#888888", 0), "rangey": (min(macd), max(macd)), "gridconv":[None, None, None, 1.5]}

class BollingerBands(Indicator): # bollinger bands
    def __init__(self, stock: list = [], window: int = 20, k: float = 2):
        super().__init__(stock)
        self.window = window # sma window
        self.k = k # factor for width of bands
        self.argTypes = {"window":{"argName":"Window", "value":20, "default":20, "type":int, "lower":1, "upper":float("nan")},
                         "k":{"argName":"Window", "value":2, "default":2, "type":float, "lower":0, "upper":99}}
        self.dMode = "graph"
        self.dData = {"upper": Visual("line", "", "#0000ff", "upper"), "middle": Visual("line", "", "#0000ff", "middle"),
                      "lower": Visual("line", "", "#0000ff", "lower"), "channel": Visual("rect", "f2", "#330000ff", "lower,upper")}
        if stock != []: self.calculate()
    
    def calculate(self):
        temp = pd.DataFrame(self.stock)
        avg = temp.rolling(window=self.window).mean()[3].reset_index(drop=True).to_list() # get list of moving average
        dist = [] # distances
        bands = [[], []]
        for t in range(len(self.stock)):
            if t < self.window: dist.append(float("nan")) # if movavg has no value yet
            else: dist.append(pow(self.stock[t][3] - avg[t], 2))
        for t in range(len(self.stock)):
            if t < self.window*2: 
                for i in range(2): bands[i].append(float("nan")) # if movavg hasn't existed for self.window values yet
            else: 
                var = 0
                for i in range(self.window):
                    var += dist[t-self.window+i] # make average of last self.window values
                var /= self.window
                sigma = (var**(1/2))*self.k
                bands[0].append(avg[t] - sigma) # lower band
                bands[1].append(avg[t] + sigma) # upper band
        self.data["lower"] = bands[0]
        self.data["middle"] = avg
        self.data["upper"] = bands[1]

class GaussianChannel(Indicator): # gaussian channel
    def __init__(self, stock: list = [], window: int = 50, k: float = 2):
        super().__init__(stock)
        self.window = window # sma window
        self.k = k # factor for width of channel
        self.argTypes = {"window":{"argName":"Window", "value":50, "default":50, "type":int, "lower":1, "upper":float("nan")},
                         "k":{"argName":"Window", "value":2, "default":2, "type":float, "lower":0, "upper":99}}
        self.dMode = "graph"
        if stock != []: self.calculate()
    
    def calculate(self):
        temp = pd.DataFrame(self.stock)
        avg = temp.rolling(window=self.window).mean()[3].reset_index(drop=True).to_list() # get list of moving average
        dist = [] # distances
        channels = [[], []]
        for t in range(len(self.stock)):
            if t < self.window: dist.append(float("nan")) # if movavg has no value yet
            else: dist.append(pow(self.stock[t][3] - avg[t], 2))
        for t in range(len(self.stock)):
            if t < self.window*2: 
                for i in range(2): channels[i].append(float("nan")) # if movavg hasn't existed for self.window values yet
            elif t == self.window*2: # initial sigma
                var = 0
                for i in range(self.window):
                    var += dist[t-self.window+i] # make average of last self.window values
                var /= self.window
                sigma = var**(1/2)
                channels[0].append(avg[t] - sigma*self.k) # lower channel
                channels[1].append(avg[t] + sigma*self.k) # upper channel
            else: 
                sigma = (((self.window - 1) * sigma**2 + (self.stock[t][3] - avg[t])**2) / self.window)**(1/2)
                channels[0].append(avg[t] - sigma*self.k) # lower channel
                channels[1].append(avg[t] + sigma*self.k) # upper channel
        self.data["lower"] = channels[0]
        self.data["middle"] = avg
        self.data["upper"] = channels[1]
        self.dData = {"upper": Visual("line", "", "#0000ff", "upper"), "middle": Visual("line", "", "#0000ff", "middle"),
                      "lower": Visual("line", "", "#0000ff", "lower"), "channel": Visual("rect", "f2", "#330000ff", "lower,upper")}

class HeikinAshi(Indicator): # heikin ashi
    def __init__(self, stock: list = []):
        super().__init__(stock)
        if stock != []: self.calculate()
    
    def calculate(self):
        ha = [] # heikin ashi return list
        if len(self.stock) == 0: self.data["ohlc"] = []
        last = deepcopy(self.stock[0])
        ha.append(last)
        for c in self.stock[1:]: # all except first one
            ohlc = deepcopy(last)
            new = deepcopy(c)
            ohlc[0] = (ohlc[0] + ohlc[3])/2 # previous open + close /2
            ohlc[1] = max([new[0], new[1], new[3]]) # max of high open or close
            ohlc[2] = min([new[0], new[2], new[3]]) # min of low open or close
            ohlc[3] = (new[0] + new[1] + new[2] + new[3])/4
            if ohlc[0] > ohlc[1]: ohlc[1] = ohlc[0] # to prevent errors
            elif ohlc[0] < ohlc[2]: ohlc[2] = ohlc[0]
            last = ohlc
            ha.append(last)
        
        self.data["ohlc"] = ha

class ATR(Indicator): # average true range
    def __init__(self, stock: list = [], window: int = 14):
        super().__init__(stock)
        self.window = window # atr window
        self.argTypes = {"window":{"argName":"Window", "value":14, "default":14, "type":int, "lower":1, "upper":float("nan")}}
        self.dMode = "bottom graph"
        self.dData = {"rangey": (0, None), "gridconv":[None, None, None, "0.25"]}
        if stock != []: self.calculate()
    
    def calculate(self):
        # self.window is window 
        trs = [] # true range values

        for i in range(len(self.stock)):
            if i == 0:
                trs.append(self.stock[i][1] - self.stock[i][2])
            else:
                tr1 = self.stock[i][1] - self.stock[i][2]
                tr2 = abs(self.stock[i][1] - self.stock[i-1][3])
                tr3 = abs(self.stock[i][2] - self.stock[i-1][3])
                truerange = max(tr1, tr2, tr3)
                trs.append(truerange)

        atr = [sum(trs[:self.window]) / self.window]  # Initial ATR value
        for i in range(self.window, len(trs)):
            atrval = (atr[-1]*(self.window-1) + trs[i]) / self.window
            atr.append(atrval)
        
        atr = [float("nan")]*(self.window-1) + atr # append nan to beginning to correctly fit the graph

        self.data["value"] = atr
        self.dData["line"] = Visual("line", "", "#8855ff", "value")
        self.dData["rangey"] = (nanmin(atr), nanmax(atr))

class CI(Indicator): # change index (future indicator)
    def __init__(self, stock: list = [], window: int = 16):
        super().__init__(stock)
        self.window = window
        self.argTypes = {"window":{"argName":"Window", "value":16, "default":16, "type":int, "lower":1, "upper":float("nan")}}
        if stock != []: self.calculate()
    
    def calculate(self):
        exps = []
        for i in range(self.window):
            val = exp(-(4/pow(self.window, 2))*pow(i+1-(self.window/4), 2))
            exps.append(val)
        mus = []
        for i in range(len(self.stock)):
            mu = 0
            posind = 0 # positivity index (how many values in the next 15 are above the current) (-1 to 1)
            posneg = [0, 0] # weighted sum of positives and negatives
            if len(self.stock)-1 >= i + self.window: # make sure there are at least 16 more samples
                for s in range(1, self.window):
                    if self.stock[i+s][3] > self.stock[i][3]: posind += 1
                    else: posind -= 1
                    p = self.stock[i+s][3] - self.stock[i+s-1][3]
                    p *= exps[s]
                    if p > 0: posneg[0] += p
                    else: posneg[1] -= p
                if posneg[0] == 0 or posneg[1] == 0: 
                    mus.append(float("inf"))
                    continue
                if posneg[0] > posneg[1]: mu = posneg[0]/posneg[1]-1
                else: mu = -(posneg[1]/posneg[0]-1)
                posind /= self.window-1
                if mu < 0 or posind < 0: negator = -1
                else: negator = 1
                mu = abs(mu*posind)*negator
                mus.append(mu)
            else: mus.append(0)
        self.data["value"] = mus

class Strategy(): # default example strategy
    def __init__(self):
        self.stratVals = {"Balance":10000, "Fees":0} # strategy values given by sim before running
        self.tradePrice = 1000
        self.reinit()
        self.preferredRes = {"Period":"2y", "Interval":"1d"}
        self.args = {} # arguments that the user can input from the gui | form: {"name":["argName", value=default, default, type, lower-, upper limit]}}
    
    def reinit(self): # reset stock/test specific values
        self.entryVals = {"currentTrue":False} # values for calculating entry
        self.reoccData = {} # same as precalc

    def entry(self, stock, dates, spot):
        if len(self.reoccData) <= 1: # 1 because change index can be there
            sma200 = SMA(stock, 200)
            sma90 = SMA(stock, 90)
            self.reoccData["sma90"] = sma90
            self.reoccData["sma200"] = sma200
        else:
            sma200 = self.reoccData["sma200"]
            sma90 = self.reoccData["sma90"]
        expression = sma90.data["value"][spot] > sma200.data["value"][spot]
        if expression and not self.entryVals["currentTrue"]: # first true filter
            self.entryVals["currentTrue"] = True
            return True
        elif not expression and self.entryVals["currentTrue"]:
            self.entryVals["currentTrue"] = False
        return False

    def entryReviews(self, stock, spot):
        lower = spot - 200
        if lower < 0: lower = 0
        upper = spot + 201
        if upper > len(stock): upper = len(stock) - 1
        sma90 = self.reoccData["sma90"].data["value"][lower:upper]
        sma200 = self.reoccData["sma200"].data["value"][lower:upper]
        visuals = []
        vis = Visual("line", "", "#ff0000")
        vis.data = sma90
        vis.position = (lower, None)
        visuals.append(vis)
        vis = Visual("line", "", "#0069ff")
        vis.data = sma200
        vis.position = (lower, None)
        visuals.append(vis)
        return visuals

    def exit(self, stock, dates, spot, operation):
        if len(operation.variables) == 0: # if operation is new
            operation.variables["Trail"] = stock[spot-1][3]*0.99
        if stock[spot][3] < operation.variables["Trail"]: return True # if trailing line was crossed
        if stock[spot][3]*0.99 > operation.variables["Trail"]: operation.variables["Trail"] = stock[spot][3]*0.99
        return False

    def exitReviews(self, stock, entry, exit):
        trails = [stock[entry][3]*0.99]
        i = entry + 1
        while i < exit:
            if stock[i][3]*0.99 > trails[-1]: trails.append(stock[i][3]*0.99)
            else: trails.append(trails[-1])
            i += 1
        vis = Visual("line", "dashed", "#ffff00")
        vis.data = trails
        vis.position = (entry, None)
        return [vis]

    def data(self, stock, dates): # main data function | doesn't have to be overridden
        self.reinit() # reset values for stock
        self.reoccData["changeIndex"] = CI(stock)
        if dates == []:
            dates = len(stock)*[float("nan")] # if no dates were gotten
        operations = []
        finished = []
        calcVals = deepcopy(self.stratVals)

        for t in range(len(stock)): # for each timespot
            i = 0 # sell signal
            while i < len(operations):
                op = operations[i]
                signal = self.exit(stock, dates, t, op)
                if signal:
                    calcVals["Balance"] += op.amount * stock[t][3]
                    op.diagnostics["Exit Percentage"] = 100*((stock[t][3]/op.diagnostics["Entry Price"])-1)
                    op.diagnostics["Exit Spot"] = t
                    op.diagnostics["Exit Time"] = dates[t]
                    op.diagnostics["Exit Price"] = stock[t][3]
                    op.diagnostics["Exit CI"] = self.reoccData["changeIndex"].data["value"][t]
                    op.reviewVis += self.exitReviews(stock, op.diagnostics["Entry Spot"], t)
                    finished.append(op)
                    del operations[i]
                i += 1
            
            signal = self.entry(stock, dates, t) # buy signal
            if signal and calcVals["Balance"] > self.tradePrice:
                op = Operation(self.tradePrice/stock[t][3])
                op.diagnostics["Ticker"] = self.stratVals["Ticker"]
                op.diagnostics["Period"] = self.stratVals["Period"]
                op.diagnostics["Interval"] = self.stratVals["Interval"]
                op.diagnostics["Entry Spot"] = t
                op.diagnostics["Amount"] = self.tradePrice/stock[t][3]
                op.diagnostics["Entry Price"] = stock[t][3]
                op.diagnostics["Entry Time"] = dates[t]
                op.diagnostics["Entry CI"] = self.reoccData["changeIndex"].data["value"][t]
                op.reviewVis += self.entryReviews(stock, t)
                operations.append(op)
                calcVals["Balance"] -= self.tradePrice

            if t == len(stock)-1: # if last time spot
                for op in operations: # sell all operations
                    op.diagnostics["Exit Percentage"] = 100*((stock[t][3]/op.diagnostics["Entry Price"])-1)
                    op.diagnostics["Exit Spot"] = t
                    op.diagnostics["Exit Time"] = dates[t]
                    op.diagnostics["Exit Price"] = stock[t][3]
                    finished.append(op)
                    calcVals["Balance"] += op.amount * stock[t][3]
        
        return finished

