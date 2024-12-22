import pathlib
from math import isnan, ceil, exp, sqrt, sin, asin, cos, acos, tan, atan, pi, floor, log10
import typing
import pandas as pd
from random import SystemRandom
import yfinance as yf
import datetime as dt
from copy import deepcopy
from numpy import corrcoef, polyfit
import numpy as np
import sys
from PyQt6 import QtWidgets, QtGui, QtCore
import winsound
import threading
import multiprocessing
import os
from time import sleep
from time import time as now
import pickle

def playsound(which="Error"): # For the error sound
    if which == "Error": winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
    elif which == "Asterisk": winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
    elif which == "Exclamation": winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)

# based on sim version = "1.2.1" 
version = "0.9.5"

theme = "dark"
look = "Windows"

if theme == "light": # for light theme
    dockstring = "QDockWidget::title { background-color: #A0A0A0; border: 2px solid #BEBEBE;}"
    widgetstring = "background-color: #ffffff; border: 2px inset #A0A0A0;"
else: # for dark theme
    dockstring = "QDockWidget::title { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0A246A, stop:1 #A6CAF0); border: 2px solid #BEBEBE;}"
    widgetstring = "background-color: #191919; border: 2px inset #A0A0A0;"

sp500 = [] # s&p 500 ticker list for live data

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

try:
    file_path = os.path.join(root_dir, "read", "Usable.xlsx")
    stocklist = pd.read_excel(file_path)["Symbols"] # read only the ticker symbols
    del file_path

    stocks = stocklist.sort_values().reset_index(drop=True) # sort the stocks alphabetically so ai doesn't only train on good ones
    stocks = stocks.to_list()
    del stocklist
except:
    stocks = []

try: # get presets for condition creator viewer
    presetFile = open(os.path.join(os.path.dirname(__file__), "Presets.txt"))
    presetlines = presetFile.readlines()
    presets = [[]]
    for l in presetlines:
        if l == "\n": presets.append([])
        else: presets[-1].append(l)
    presetFile.close()
    del presetFile, presetlines
    for pre in presets:
        for l in range(len(pre)):
            old = pre[l]
            pre[l] = []
            prp = ""
            for c in old:
                if c == "," or c == "\n":
                    if prp != "":
                        pre[l].append(float(prp))
                        prp = ""
                else: prp += c
    del prp, pre, old, c

except:
    presets = [[], [], [], [], [], []]

raw = [] # raw y2h stock data
operations = [] # stores the active operations

# available indicators
avinds = ["ohlcv", "extra", "heikin-ashi", "time", "sigma", "rv", "sma", "ema", "vwap", "rsi", "macd", "bollinger", "gaussian", "atr",
           "v", "ʌ", "m", "w", "shs", "trend", "support", "resistance", "line"]

visinds = ["volume", "sma", "ema", "vwap", "rsi", "macd", "bollinger", "gaussian", "atr"] # indicators that can be added to the main view

# what is required for each indicator {"key":{"name":name displayed, "args":[value name, default, type, min, max]}}
indargs = {"ohlcv":{"name":"Stock data", "args":[]}, "extra":{"name":"Adv. stock data", "args":[]}, "heikin-ashi":{"name":"Heikin-Ashi data", "args":[]},
"time":{"name":"Time data", "args":[]}, "sigma":{"name":"Standard Deviation", "args":[["Window", 20, int, 1, "nan"]]},
"rv":{"name":"RV", "args":[["Window", 20, int, 1, "nan"]]},
"sma":{"name":"SMA", "args":[["Window", 200, int, 1, "nan"]]}, "ema":{"name":"EMA", "args":[["Window", 200, int, 1, "nan"]]},
"vwap":{"name":"VWAP", "args":[["Window", 60, int, 1, "nan"]]}, "rsi":{"name":"RSI", "args":[["Window", 14, int, 1, "nan"]]},
"macd":{"name":"MACD", "args":[]}, "bollinger":{"name":"Bollinger Bands", "args":[["Moving Average", 20, int, 1, "nan"], ["σ-Multiplier", 2, float, 0, 99]]},
"gaussian":{"name":"Gaussian Channels", "args":[["Moving Average", 50, int, 1, "nan"], ["σ-Multiplier", 1, float, 0, 99]]}, "atr":{"name":"ATR", "args":[["Window", 14, int, 1, "nan"]]},
"v":{"name":"V-Shape", "args":[["Min size", 5, int, 5, "nan"], ["Max size", 100, int, 5, "nan"], ["Spot", -1, int, "nan", "nan"]]},
"ʌ":{"name":"Ʌ-Shape", "args":[["Min size", 5, int, 5, "nan"], ["Max size", 100, int, 5, "nan"], ["Spot", -1, int, "nan", "nan"]]},
"m":{"name":"M-Shape", "args":[["Min size", 5, int, 5, "nan"], ["Max size", 100, int, 5, "nan"], ["Spot", -1, int, "nan", "nan"]]},
"w":{"name":"W-Shape", "args":[["Min size", 5, int, 5, "nan"], ["Max size", 100, int, 5, "nan"], ["Spot", -1, int, "nan", "nan"]]},
"shs":{"name":"SHS-Shape", "args":[["Min size", 5, int, 5, "nan"], ["Max size", 100, int, 5, "nan"], ["Spot", -1, int, "nan", "nan"]]},
"trend":{"name":"Trendline", "args":[["Window", 20 ,int, 2, "nan"]]}, "support":{"name":"Support Line", "args":[]}, "resistance":{"name":"Resistance Line", "args":[]},
"line":{"name":"Line", "args":[["Spot", -1, int, "nan", "nan"], ["Slope", 0.5, float, "-inf", "inf"]]}, "volume":{"name":"Volume data", "args":[]}, 
"entvars":{"name":"Entry data", "args":[["var1", "", str, "nan", "nan"], ["var2", "", str, "nan", "nan"], ["var3", "", str, "nan", "nan"]]}}

# what is given by each indicator; {"key":{"vars":[whatever the given variables are], "vtype":[what types the given variables are],
# "once":whether to generate once or each time, "existcheck":if general check must first be made}}
indinfo = {"ohlcv":{"vars":["open", "high", "low", "close", "volume"], "vtypes":[list, list, list, list, list], "once":True, "existcheck":False},
"extra":{"vars":["top", "bottom", "avgbody"], "vtypes":[list, list, float], "once":True, "existcheck":False}, 
"heikin-ashi":{"vars":["open", "high", "low", "close"], "vtypes":[list, list, list, list], "once":True, "existcheck":False},
"time":{"vars":["spot"], "vtypes":[int], "once":False, "existcheck":False}, "sigma":{"vars":["sigma"], "vtypes":[list], "once":True, "existcheck":False}, 
"rv":{"vars":["value"], "vtypes":[list], "once":True, "existcheck":False}, 
"sma":{"vars":["value"], "vtypes":[list], "once":True, "existcheck":False}, "ema":{"vars":["value"], "vtypes":[list], "once":True, "existcheck":False},
"vwap":{"vars":["value"], "vtypes":[list], "once":True, "existcheck":False}, "rsi":{"vars":["value"], "vtypes":[list], "once":True, "existcheck":False},
"macd":{"vars":["macd", "signal"], "vtypes":[list, list], "once":True, "existcheck":False}, 
"bollinger":{"vars":["lower", "value", "upper"], "vtypes":[list, list, list], "once":True, "existcheck":False},
"gaussian":{"vars":["lower", "value", "upper"], "vtypes":[list, list, list], "once":True, "existcheck":False},
"atr":{"vars":["value"], "vtypes":[list], "once":True, "existcheck":False}, 
"v":{"vars":["peak1", "valley", "peak2", "size"], "vtypes":[int, int, int, int], "once":False, "existcheck":True}, 
"ʌ":{"vars":["valley1", "peak", "valley2", "size"], "vtypes":[int, int, int, int], "once":False, "existcheck":True},
"m":{"vars":["valley1", "peak1", "valley2", "peak2", "valley3", "size"], "vtypes":[int, int, int, int, int, int], "once":False, "existcheck":True},
"w":{"vars":["peak1", "valley1", "peak2", "valley2", "peak3", "size"], "vtypes":[int, int, int, int, int, int], "once":False, "existcheck":True},
"shs":{"vars":["valley1", "peak1", "valley2", "peak2", "valley3", "peak3", "valley4", "neckline", "size"], 
       "vtypes":[int, int, int, int, int, int, int, float, int], "once":False, "existcheck":True},
"trend":{"vars":["slope"], "vtypes":[list], "once":True, "existcheck":False}, 
"support":{"vars":["price", "slope", "length"], "vtypes":[float, float, int], "once":False, "existcheck":True},
"resistance":{"vars":["price", "slope", "length"], "vtypes":[float, float, int], "once":False, "existcheck":True}, 
"line":{"vars":["price"], "vtypes":[list], "once":False, "existcheck":False},
"volume":{"vars":["volume"], "vtypes":[list], "once":True, "existcheck":False},
"entvars":{"vars":["price", "spot", "var1", "var2", "var3"], "vtypes":[float, int, str, str, str], "once":False, "existcheck":False}}

def isint(string: str): # checks if a string is an instance of int
    try:
        i = int(string)
        return True
    except:
        return False

def isfloat(string: str): # checks if a string is an instance of float
    try:
        i = float(string)
        return True
    except:
        return False

def randint(low, high): # different random function to improve randomness
    high = int(high + 1)
    low = int(low)
    n = SystemRandom().random() # random seed
    for i in range(1, high-low):
        if (n <= i/(high-low)): return i - 1 + low # if max = 4 and min = 1: if 0.2143124 < 1/4: return 0
    return high - 1

def split(lis, indx): # split list into two at given index
    if len(lis) == 0: return ([], [])
    elif len(lis) == 1 and indx == 0: return([], []) 
    elif indx == len(lis)-1: return (lis[:-1], [])
    elif indx == 0: return ([], lis[1:])

    a = lis[indx + 1:]
    b = lis[:indx]
    return (a, b)

def stock_data(ticker, start=None, end=None, interval=None, period=None): # get stock data and convert it to a list
    try:
        tik = yf.Ticker(ticker)
        tim = tik._get_ticker_tz(None, 10) # error check
        if tim == None:
            raise Exception("Delisted")
        if start is not None: # fixed
            dat = tik.history(start=start, end=end, interval=interval)
        else: # dynamic
            dat = tik.history(period=period, interval=interval)
    except Exception as e:
        return [e.args[0]], []
    if dat.empty: return [], []
    date = dat.index.to_list() # date of points
    data = [] # datapoints
    op = dat["Open"].to_list() # 0
    hi = dat["High"].to_list() # 1
    lo = dat["Low"].to_list() # 2
    cl = dat["Close"].to_list() # 3
    vo = dat["Volume"].to_list() # 4
    for t in range(len(op)):
            a = op[t]
            b = hi[t]
            c = lo[t]
            d = cl[t]
            e = vo[t]
            if not isnan(a): data.append([a, b, c, d, e]) 
    return data, date

def read(x, isPath=False): # get 2 year hourly data from 1/20/2023
    if not isPath: # when ticker is passed in
        pat = os.path.join(root_dir, "read", f"{x}.txt")
        path = pathlib.Path(pat)
        if not path.exists(): 
            return [] # check if file exists in dataset else return empty list
        file = open(pat)
    else: file = open(x) # when path is passed in
    op = []
    lines = file.read() # read the lines
    lins = lines.splitlines() # split lines when \n is present
    try:
        for line in lins:
            l = line.split(",") # get values in line by splitting at ","
            a = float(l[0])
            b = float(l[1])
            c = float(l[2])
            d = float(l[3])
            e = float(l[4])
            if not isnan(a): op.append([a, b, c, d, e]) # for shape (75, 3000, 5), also exclude nans
        file.close()
    except:
        return []
    return op

class Operation():
    def __init__(self, stock, stty, number, time, stlo=0, tapr=0, perc=1, fee=0): # acts as buy function as well
        # if fractional shares are allowed: number = float, else number = int
        super().__init__()
        self.running = True
        self.ind = stock
        self.type = stty
        self.amnt = number
        self.stop = stlo
        self.take = tapr
        self.trai = perc
        self.time = time # save for evaluation purposes
        self.fees = fee
        self.stopprice = raw[stock][time][3]*(1-perc)
        self.buyprice = raw[stock][time][3] # price when the stock was bought
    def sell(self, time): # sells for current market price
        self.running = False
        if self.type == "Stop Limit":
            return raw[self.ind][time][3]*self.amnt 
        else:
            return self.stopprice*self.amnt # trailing stop

def near(a, b, n): # rounds a and b to n digits and checks if they're the same
    return round(a, n) == round(b, n) # if a rounded = b rounded then they're really close

def exp_values(n): # get exponent weights in list
    exps = []
    for i in range(n):
        val = exp(-(4/pow(n, 2))*pow(i+1-(n/4), 2))
        exps.append(val)
    return exps

def numtostr(number, roundto=3): # for better readability in the plr files
    if type(number) == int: # if int return normal string
        return str(number)
    number = round(number, roundto) # round so it doesn't get too cluttered
    if number > -1 and number < 1 and number != 0: # if the number is between -1 and 1 and not 0 then we can shorten it to ex. -.5
        if number < 0: return "-" + str(number)[2:] # remove the 0 from the string and add - to beginning
        else: return str(number)[1:]
    return str(number)

def bollinger(stock, ma, k): # calculate bollinger bands
    temp = pd.DataFrame(stock)
    avg = temp.rolling(window=ma).mean()[3].reset_index(drop=True).to_list() # get list of moving average
    dist = [] # distances
    bands = [[], []]
    for t in range(len(stock)):
        if t < ma: dist.append(float("nan")) # if movavg has no value yet
        else: dist.append(pow(stock[t][3] - avg[t], 2))
    for t in range(len(stock)):
        if t < ma*2: 
            for i in range(2): bands[i].append(float("nan")) # if movavg hasn't existed for ma values yet
        else: 
            var = 0
            for i in range(ma):
                var += dist[t-ma+i] # make average of last ma values
            var /= ma
            sigma = sqrt(var)*k
            bands[0].append(avg[t] - sigma) # lower band
            bands[1].append(avg[t] + sigma) # upper band
    return bands[0], avg, bands[1] # return lower, middle, upper band

def gaussian(stock, ma, k): # calculate gaussian channel
    temp = pd.DataFrame(stock)
    avg = temp.rolling(window=ma).mean()[3].reset_index(drop=True).to_list() # get list of moving average
    dist = [] # distances
    channels = [[], []]
    for t in range(len(stock)):
        if t < ma: dist.append(float("nan")) # if movavg has no value yet
        else: dist.append(pow(stock[t][3] - avg[t], 2))
    for t in range(len(stock)):
        if t < ma*2: 
            for i in range(2): channels[i].append(float("nan")) # if movavg hasn't existed for ma values yet
        elif t == ma*2: # initial sigma
            var = 0
            for i in range(ma):
                var += dist[t-ma+i] # make average of last ma values
            var /= ma
            sigma = sqrt(var)
            channels[0].append(avg[t] - sigma*k) # lower channel
            channels[1].append(avg[t] + sigma*k) # upper channel
        else: 
            sigma = sqrt(((ma - 1) * sigma**2 + (stock[t][3] - avg[t])**2) / ma)
            channels[0].append(avg[t] - sigma*k) # lower channel
            channels[1].append(avg[t] + sigma*k) # upper channel
    return channels[0], avg, channels[1] # return lower, middle, upper band

def getHeikinAshi(stock): # returns heikin ashi ohlc
    ha = [] # heikin ashi return list
    if len(stock) == 0: return []
    last = deepcopy(stock[0])
    ha.append(last)
    for c in stock[1:]: # all except first one
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
    
    return ha

def getAvgBody(stock, spot): # returns average body size to eliminate price bias
    x = spot - 20
    if x < 0: x = 0 # get range up to last 100
    avg = 0
    for i in range(x, spot+1): # get the average size of all bodies in range
        avg += abs(stock[i][3]-stock[i][0])
    if spot != 0: avg /= spot-x

    if avg <= 0.000025: # if no avg body size; just make it really small
        avg = 0.00005

    # find nearest square size
    tenpows = [0.000025]
    while tenpows[-1] < avg: # fill up the list
        if str(1000/tenpows[-1])[0] == "4": # multiple of 2.5
            tenpows.append(tenpows[-1]*2)
        else: tenpows.append(tenpows[-1]*5)
    contenders = [abs(avg/tenpows[-2]-1), abs(avg/tenpows[-1]-1)]
    if contenders[0] < contenders[1]: tenpow = tenpows[-2]
    else: tenpow = tenpows[-1]
    #tenpow *= 2 # because it looked for square size 

    return tenpow

def indicator(index, name, args, time):
    # 0 open | 1 high | 2 low | 3 close | 4 volume
    stock = raw[index]
    if name == "ohlcv":
        o, h, l, c, v = [], [], [], [], []
        for i in range(len(stock)):
            if i > time+1: return o, h, l, c, v
            o.append(stock[i][0])
            h.append(stock[i][1])
            l.append(stock[i][2])
            c.append(stock[i][3])
            v.append(stock[i][4])
        return o, h, l, c, v
    elif name == "extra":
        top, bottom = [], []
        for i in range(len(stock)):
            if i > time+1: break
            if stock[i][3] > stock[i][0]: # if close > open
                top.append(stock[i][3])
                bottom.append(stock[i][0])
            else:
                top.append(stock[i][0])
                bottom.append(stock[i][3])
        body = getAvgBody(stock, time)
        return top, bottom, body
    elif name == "volume":
        v = []
        for i in range(len(stock)):
            if i > time+1: return v
            v.append(stock[i][4])
        return v
    elif name == "rv": # relative volume
        # args[0] is window
        if time <= args[0]: 
            temp = []
            for i in range(args[0]): temp.append(float("nan")) # no value for first few values
            return temp
        temp = pd.DataFrame(stock[:time+1])
        temp = temp.rolling(window=args[0]).mean()[4].reset_index(drop=True).to_list()
        out = []
        for v in range(len(temp)):
            out.append(stock[v][4]/temp[v])
        return out
    elif name == "time":
        return time#, None
    elif name == "heikin-ashi":
        ha = getHeikinAshi(stock)[:time+1]
        o, h, l, c = [], [], [], []
        for ho in ha:
            o.append(ho[0])
            h.append(ho[1])
            l.append(ho[2])
            c.append(ho[3])
        return o, h, l, c
    elif name == "sigma":
        # args[0] is window
        temp = pd.DataFrame(stock[:time+1])
        avg = temp.rolling(window=args[0]).mean()[3].reset_index(drop=True).to_list() # get list of moving average
        dist = [] # distances
        sigmas = []
        for t in range(time+1):
            if t < args[0]: dist.append(float("nan")) # if movavg has no value yet
            else: dist.append(pow(stock[t][3] - avg[t], 2))
        for t in range(time+1):
            if t < args[0]*2: sigmas.append(float("nan")) # if movavg hasn't existed for ma values yet
            else: 
                var = 0
                for i in range(args[0]):
                    var += dist[t-args[0]+i] # make average of last ma values
                var /= args[0]
                sigma = sqrt(var)
                sigmas.append(sigma)
        return sigmas
    elif name == "sma":
        # args [0] is window
        if time <= args[0]: 
            temp = []
            for i in range(args[0]): temp.append(float("nan")) # no value for first few values
            return temp
        temp = pd.DataFrame(stock[:time+1])
        return temp.rolling(window=args[0]).mean()[3].reset_index(drop=True).to_list()
    elif name == "ema":
        # args [0] is window
        if time <= args[0]: 
            temp = []
            for i in range(args[0]): temp.append(float("nan")) # no value for first few values
            return temp
        temp = pd.DataFrame(stock[:time+1])
        return temp.ewm(span=args[0], adjust=False).mean()[3].reset_index(drop=True).to_list()
    elif name == "vwap":
        # args [0] is window
        temp = []
        prods = [] # price * volume of all
        for i in range(time+1): # equal to len(stock)
            prods.append(stock[i][3] * stock[i][4])
        for i in range(args[0]): temp.append(float("nan")) # no value for first few values
        for i in range(args[0], time+1):
            cumsum = 0
            vols = 0 # all volumes
            for m in range(args[0]): # for every window
                cumsum += prods[i-m]
                vols += stock[i-m][4]
            temp.append(cumsum/vols)
        return temp
    elif name == "rsi":
        # args [0] is window
        rss = [] # multiple rsi
        for spot in range(time+1):
            closes = []
            x = spot - args[0]
            if x < 0: x = 0
            for st in stock[x:spot+1]:
                closes.append(st[3]) # get all closes in range
            prices = np.asarray(closes)
            deltas = np.diff(prices)
            gains = np.where(deltas >= 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            if len(gains) == 0: avg_gain = 0
            else: avg_gain = np.mean(gains[:args[0]])
            if len(losses) == 0: avg_loss = 0
            else: avg_loss = np.mean(losses[:args[0]])
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs)) # on a scale of 0-100
            else: rsi = 50 # if divide by 0 default to 50
            rss.append(rsi)
        return rss
    elif name == "macd":
        temp = pd.DataFrame(stock)
        ema12 = temp.ewm(span=12, adjust=False).mean()[3].reset_index(drop=True).to_list()
        ema26 = temp.ewm(span=26, adjust=False).mean()[3].reset_index(drop=True).to_list()
        macd = []
        for e in range(len(ema12)):
            macd.append(ema12[e]-ema26[e])
        temp = pd.DataFrame(macd)
        signal = temp.ewm(span=9, adjust=False).mean()[0].reset_index(drop=True).to_list()
        return macd, signal
    elif name == "bollinger":
        # args[0] is mov avg, args[1] is k
        temp = bollinger(stock[:time+1], args[0], args[1])
        return temp[0], temp[1], temp[2] # lower, middle, upper
    elif name == "gaussian":
        # args[0] is mov avg, args[1] is k
        temp = gaussian(stock[:time+1], args[0], args[1])
        return temp[0], temp[1], temp[2] # lower, middle, upper
    elif name == "atr": # average true range
        # args[0] is window 
        atrVals = []

        for i in range(time+1):
            if i == 0:
                atrVals.append(stock[i][1] - stock[i][2])
            else:
                tr1 = stock[i][1] - stock[i][2]
                tr2 = abs(stock[i][1] - stock[i-1][3])
                tr3 = abs(stock[i][2] - stock[i-1][3])
                truerange = max(tr1, tr2, tr3)
                atrVals.append(truerange)

        atr = [sum(atrVals[:args[0]]) / args[0]]  # Initial ATR value
        for i in range(args[0], len(atrVals)):
            atrval = (atrVals[i] - atrVals[i - 1]) / args[0] + atr[-1]
            atr.append(atrval)
        
        atr = [float("nan")]*args[0] + atr # append nan to beginning to correctly fit the graph

        return atr
        # vals = []
        # trs = [] # true ranges as to not recalculate everytime
        # for i in range(time+1):
        #     maxxs = []
        #     maxxs.append(stock[i][1]-stock[i][2])
        #     if i != 0:
        #         maxxs.append(abs(stock[i][1]-stock[i-1][3]))
        #         maxxs.append(abs(stock[i][2]-stock[i-1][3]))
        #     trs.append(max(maxxs))
        # for i in range(time+1):
        #     if i < args[0]-1: vals.append(float("nan"))
        #     else: 
        #         if vals[-1] != vals[-1]: # if previous is nan
        #             new = sum(trs[:i+1]) # for first take moving average from all before
        #             prv = 0 
        #         else: 
        #             new = trs[i]
        #             prv = vals[-1]*i
        #         vals.append((new+prv)/(i+1)) # whole formula: (prvatr*(n-1)+tr)/n
        # return vals
    elif name == "v":
        # args[0] is minimum, args[1] is maximum width, args[2] is spot

        if args[2] > time or args[2] < -time-1: return False, -1, -1, -1, -1
        elif args[2] < 0: # convert from total scale to truncated scale bc of time
            args[2] = time + args[2] + 1
        
        time = args[2] # treat it as spot

        avg = getAvgBody(stock, time)

        while time-args[0] >= 0 and args[0] <= args[1]: # k is maximum width

            for x in [0]: # to allow breaking
                # neckline
                if stock[time][3]-stock[time-args[0]][3] > avg: break # have to be at the same height

                # get tallest in middle of v
                mid = stock[time-args[0]+1:time]
                peak = 0
                for m in range(len(mid)):
                    if mid[m][3] > mid[peak][3]: peak = m

                if mid[peak][3]-stock[time][3] > avg/2: break # if something in the v is above neckline

                # check for valley in middle
                pit = stock[time-args[0]:time+1]
                val = 0
                for p in range(len(pit)):
                    if pit[p][3] < pit[val][3]:
                        val = p
                
                if val == len(pit)-1 or abs(val/(len(pit)-val-1)-1) > 0.2: break # if valley too far off middle

                # check whether they follow the shape of a v
                c = stock[time][3] + (stock[time][3] - pit[val][3])/3 # time + (time-v)/3 | start of v
                m = (stock[time][3] - pit[val][3])/(val+1) # rise over run

                # check angle if v is steep enough
                if 180*atan(m)/pi < 20: break # if angle under 20°; too flat

                m *= -1 # to get negative rise

                half = pit[:val]
                cancel = False
                for h in range(len(half)):
                    if half[h][3] > c+m*h: cancel = True # if price above follow line; cancel
                
                # do same for other half
                half = pit[val:]
                half.reverse() # reverse so valley is in middle
                for h in range(len(half)):
                    if half[h][3] > c+m*h: cancel = True # if price above follow line; cancel
                if cancel: break

                return True, time-args[0], time-args[0]+val, time, args[0]
            
            args[0] += 1
        # default return false
        return False, -1, -1, -1, -1
    elif name == "ʌ":
        # args[0] is minimum, args[1] is maximum width, args[2] is spot

        if args[2] > time or args[2] < -time-1: return False, -1, -1, -1, -1
        elif args[2] < 0: # convert from total scale to truncated scale bc of time
            args[2] = time + args[2] + 1
        
        time = args[2] # treat it as spot

        avg = getAvgBody(stock, time)

        while time-args[0] >= 0 and args[0] <= args[1]: # k is maximum width

            for x in [0]: # to allow breaking
                # neckline
                if stock[time][3]-stock[time-args[0]][3] > avg: break # have to be at the same height

                # get lowest in middle of ʌ
                mid = stock[time-args[0]+1:time]
                val = 0
                for m in range(len(mid)):
                    if mid[m][3] < mid[val][3]: val = m

                if stock[time][3]-mid[val][3] > avg/2: break # if something in the ʌ is below neckline

                # check for peak in middle
                pit = stock[time-args[0]:time+1]
                peak = 0
                for p in range(len(pit)):
                    if pit[p][3] > pit[peak][3]:
                        peak = p
                
                if peak == len(pit)-1 or abs(peak/(len(pit)-peak-1)-1) > 0.2: break # if peak too far off middle

                # check whether they follow the shape of a ʌ
                c = stock[time][3] - (pit[peak][3] - stock[time][3])/3 # time - (ʌ-time)/3 | start of ʌ
                m = (pit[peak][3] - stock[time][3])/(peak+1) # rise over run

                # check angle if ʌ is steep enough
                if 180*atan(m)/pi < 20: break # if angle under 20°; too flat

                half = pit[:peak]
                cancel = False
                for h in range(len(half)):
                    if half[h][3] < c+m*h: cancel = True # if price below follow line; cancel
                
                # do same for other half
                half = pit[peak:]
                half.reverse() # reverse so peak is in middle
                for h in range(len(half)):
                    if half[h][3] < c+m*h: cancel = True # if price below follow line; cancel
                if cancel: break

                return True, time-args[0], time-args[0]+peak, time, args[0]
            
            args[0] += 1
        # default return false
        return False, -1, -1, -1, -1
    elif name == "m":
        # args[0] is minimum, args[1] is maximum width, args[2] is spot

        if args[2] > time or args[2] < -time-1: return False, -1, -1, -1, -1, -1, -1
        elif args[2] < 0: # convert from total scale to truncated scale bc of time
            args[2] = time + args[2] + 1
        
        time = args[2] # treat it as spot

        while time-args[0] >= 0 and args[0] <= args[1]: # to get any size of m

            for x in [0]: # simple loop to allow breaking
                # get middle valley
                mid = stock[time-int(args[0]*3/4):time-int(args[0]/4)+1] # middle area from w*3/4 to w/4
                val1 = 0
                for m in range(len(mid)):
                    if mid[m][3] < mid[val1][3]:
                        val1 = m
                
                if val1 == len(mid)-1 or abs(val1/(len(mid)-val1-1)-1) > 0.33: break # if valley too far off middle

                # outer valleys
                side = stock[time-args[0]:time-int(args[0]*3/4)+1] # outer left valley
                val = 0
                for s in range(len(side)):
                    if side[s][3] < side[val][3]:
                        val = s
                if val != 0: break # if valley is not at very left; cant be an m

                # do same for other side
                side = stock[time-int(args[0]/4):time+1] # outer right valley
                side.reverse() # reverse so valley is at 0
                val = 0
                for s in range(len(side)):
                    if side[s][3] < side[val][3]:
                        val = s
                if val != 0: break # if valley is not at very right; cant be an m

                # check for peaks in between
                bigs = stock[time-args[0]//2: time+1]
                peak = 0
                for b in range(len(bigs)):
                    if bigs[b][3] > bigs[peak][3]: peak = b
                
                if peak == len(bigs)-1 or abs(peak/(len(bigs)-peak-1)-1) > 0.33: break # if peak too far off middle
                
                bigs = stock[time-args[0]:time-args[0]//2+1]
                peak2 = 0
                for b in range(len(bigs)):
                    if bigs[b][3] > bigs[peak2][3]: peak2 = b
                
                if peak2 == len(bigs)-1 or abs(peak2/(len(bigs)-peak2-1)-1) > 0.33: break # if peak too far off middle

                return True, time-args[0], time-args[0]+peak2, time-int(args[0]*3/4)+val1, time-args[0]//2+peak, time, args[0]
            args[0] += 1

        return False, -1, -1, -1, -1, -1, -1
    elif name == "w":
        # args[0] is minimum, args[1] is maximum width, args[2] is spot

        if args[2] > time or args[2] < -time-1: return False, -1, -1, -1, -1, -1, -1
        elif args[2] < 0: # convert from total scale to truncated scale bc of time
            args[2] = time + args[2] + 1
        
        time = args[2] # treat it as spot

        while time-args[0] >= 0 and args[0] <= args[1]: # to get any size of w
            
            for x in [0]: # simple loop to allow breaking
                # get middle peak
                mid = stock[time-int(args[0]*3/4):time-int(args[0]/4)+1] # middle area from w*3/4 to w/4
                peak1 = 0
                for m in range(len(mid)):
                    if mid[m][3] > mid[peak1][3]:
                        peak1 = m
                
                if peak1 == len(mid)-1 or abs(peak1/(len(mid)-peak1-1)-1) > 0.33: break # if peak too far off middle

                # outer peaks
                side = stock[time-args[0]:time-int(args[0]*3/4)+1] # outer left peak
                peak = 0
                for s in range(len(side)):
                    if side[s][3] > side[peak][3]:
                        peak = s
                if peak != 0: break # if peak is not at very left; cant be a w

                # do same for other side
                side = stock[time-int(args[0]/4):time+1] # outer right peak
                side.reverse() # reverse so peak is at 0
                peak = 0
                for s in range(len(side)):
                    if side[s][3] > side[peak][3]:
                        peak = s
                if peak != 0: break # if peak is not at very right; cant be a w
                
                # check for valleys in between
                bigs = stock[time-args[0]//2: time+1]
                val1 = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val1][3]: val1 = b
                
                if val1 == len(bigs)-1 or abs(val1/(len(bigs)-val1-1)-1) > 0.33: break # if valley too far off middle
                
                bigs = stock[time-args[0]:time-args[0]//2+1]
                val = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val][3]: val = b
                
                if val == len(bigs)-1 or abs(val/(len(bigs)-val-1)-1) > 0.33: break # if valley too far off middle

                return True, time-args[0], time-args[0]+val, time-int(args[0]*3/4)+peak1, time-args[0]//2+val1, time, args[0]
            args[0] += 1
        
        # if args[0] > time; no w has been found
        return False, -1, -1, -1, -1, -1, -1
    elif name == "shs":
        # args[0] is minimum, args[1] is maximum width, args[2] is spot

        if args[2] > time or args[2] < -time-1: return False, -1, -1, -1, -1, -1, -1, -1, -1, -1
        elif args[2] < 0: # convert from total scale to truncated scale bc of time
            args[2] = time + args[2] + 1
        
        time = args[2] # treat it as spot

        avg = getAvgBody(stock, time)
        while time-args[0] >= 0 and args[0] <= args[1]: # to get any size of shs
            
            for x in [0]: # simple loop to allow breaking
                # get middle peak
                mid = stock[time-int(args[0]*2/3):time-int(args[0]/3)+1] # middle area from w*2/3 to w/3
                mpeak = 0
                for m in range(len(mid)):
                    if mid[m][3] > mid[mpeak][3]:
                        mpeak = m
                
                if mpeak == len(mid)-1 or abs(mpeak/(len(mid)-mpeak-1)-1) > 0.33: break # if peak too far off middle

                # lesser peaks
                side = stock[time-args[0]:time-int(args[0]*2/3)+1] # left peak
                peak = 0
                for s in range(len(side)):
                    if side[s][3] > side[peak][3]:
                        peak = s

                if peak == len(side)-1 or abs(peak/(len(side)-peak-1)-1) > 0.33: break # if peak too far off middle

                # do same for other side
                side2 = stock[time-int(args[0]/3):time+1] # right peak
                peak2 = 0
                for s in range(len(side2)):
                    if side2[s][3] > side2[peak2][3]:
                        peak2 = s
                if peak2 == len(side2)-1 or abs(peak2/(len(side2)-peak2-1)-1) > 0.33: break # if peak too far off middle
                
                if side[peak][3] > mid[mpeak][3] or side2[peak2][3] > mid[mpeak][3]: break # outer peaks have to be lower than middle peak

                # check for valleys in between
                valvals = [stock[time][3]] # valley values
                bigs = stock[time-args[0]//2: time-args[0]//6+1]
                val1 = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val1][3]: val1 = b
                
                valvals.append(bigs[val1][3])
                
                bigs = stock[time-5*args[0]//6:time-args[0]//2+1]
                val = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val][3]: val = b
                
                valvals.append(bigs[val][3])
                valvals.append(stock[time-args[0]][3])

                # valvals now holds all of the points on the neckline
                m = (valvals[0]-valvals[1])/(args[0]/3) # rise over run
                cancel = False
                for v in range(len(valvals)):
                    if abs(valvals[v]-(stock[time][3] + m*v)) > avg*2: # if actual neckline is too far away from theoretical neckline
                        cancel = True
                if cancel: break
                return True, time-args[0], time-args[0]+peak, time-5*args[0]//6+val, time-int(args[0]*2/3)+mpeak, time-args[0]//2+val1, time-int(args[0]/3)+peak2, time, m, args[0]
            args[0] += 1
        
        # if args[0] > time; no w has been found
        return False, -1, -1, -1, -1, -1, -1, -1, -1, -1
    elif name == "trend":
        # args[0] is window
        l = [0] # start with 0, because first is skipped
        for i in range(1, time+1):
            start = i - args[0] # so it wont wrap around
            if start <= 0: 
                start = 0
                x = list(range(i+1))
                y = stock[start:i+1]
            else: 
                x = list(range(args[0]))
                y = stock[start+1:i+1] # get last 100 price points
            y.reverse() # so that the tangent will fixate on last price point
            coeffs = polyfit(x, y, 1)
            l.append(coeffs[0][3]*-1) # -1 because it has been reversed
        return l
    elif name == "support":
        spot = time
        avg = getAvgBody(stock, spot)

        if spot < 20: return False, -1, -1, -1 # some spots need to be present
        closes = []
        for i in stock[spot-4:spot+1]: # get closes
            closes.append(i[3])
        i = closes.index(min(closes)) # get index of valley
        i = spot-4+i # global index
        touches = [i] # when the line has been touched
        cooldown = 0 # set to 3 if a touch has been detected to avoid detecting 3 of the same touch
        s = spot-1
        while s >= 0 and spot-s < 200: # look for intersections
            if cooldown == 0 and abs(stock[s][3]-stock[i][3]) <= avg/2: # if the line has been touched
                cooldown = 3
                touches.append(s)
            elif cooldown > 0: cooldown -= 1
            if len(touches) == 3: break
            s -= 1
        
        if len(touches) != 3: return False, -1, -1, -1 # if no three touches; cant be a resistance line
        x = spot-touches[-1] # range of resistance
        for j in range(2):
            if touches[j]-touches[j+1] < x/3: return False, -1, -1, -1 # minimum distance
        
        add = 0
        for j in range(x):
            if stock[spot-j][3] > stock[i][3]: add += 1 # if above line
        
        if add/x < 0.90: return False, -1, -1, -1
        
        return True, stock[i][3], 0, x
    elif name == "resistance":
        spot = time
        avg = getAvgBody(stock, spot)

        if spot < 20: return False, -1, -1, -1 # some spots need to be present
        closes = []
        for i in stock[spot-4:spot+1]: # get closes
            closes.append(i[3])
        i = closes.index(max(closes)) # get index of peak
        i = spot-4+i # global index
        touches = [i] # when the line has been touched
        cooldown = 0 # set to 3 if a touch has been detected to avoid detecting 3 of the same touch
        s = spot-1
        while s >= 0 and spot-s < 200: # look for intersections
            if cooldown == 0 and abs(stock[s][3]-stock[i][3]) <= avg/2: # if the line has been touched
                cooldown = 3
                touches.append(s)
            elif cooldown > 0: cooldown -= 1
            if len(touches) == 3: break
            s -= 1
        
        if len(touches) != 3: return False, -1, -1, -1 # if no three touches; cant be a resistance line
        x = spot-touches[-1] # range of resistance
        for j in range(2):
            if touches[j]-touches[j+1] < x/3: return False, -1, -1, -1 # minimum distance
        
        add = 0
        for j in range(x):
            if stock[spot-j][3] < stock[i][3]: add += 1 # if below line
        
        if add/x < 0.90: return False, -1, -1, -1
        
        return True, stock[i][3], 0, x
    elif name == "line":
        # args[0] is spot, args[1] is slope
        spot = args[0]
        if spot > time or spot < -time-1: return [0] * (time+1) # returns as many zeroes as timeframes
        elif spot < 0: # convert from total scale to truncated scale bc of time
            spot = time + spot + 1
        c = stock[spot][3]
        m = args[1]
        vals = []
        for i in range(time+1):
            vals.append(m*(i-spot)+c)
        return vals

def equation(typ, args): # solves equations
    if typ == "Basic":
        # args [1] is operator; the others are numbers
        # "+", "-", "*", "/", "%", "//", "**"
        if args[1] in ["/", "//", "%"]:
            if args[2] == 0: return float("nan") # divide by zero
        return eval("args[0]" + args[1] + "args[2]")
    elif typ == "Constants":
        # args[0] is symbol
        # "π", "e", "ϕ"
        if args[0] == "π": return pi
        elif args[0] == "e": return exp(1)
        elif args[0] == "ϕ": return (1+5**(1/2))/2
    elif typ == "Trigonometric":
        # args[0] is function, args[1] is value
        # "Sin", "Asin", "Cos", "Acos", "Tan", "Atan"
        return eval(args[0].lower() + "(args[1])")
    elif typ == "Aggregates":
        # args [0] is key and 1 is number list
        # "Max", "Min", "Average", "Sum"
        if len(args[1]) == 0: return float("nan")
        if args[0] != "Average":
            return eval(args[0].lower() + "(args[1])")
        else:
            val = 0
            for v in args[1]: val += v
            val /= len(args[1])
            return val
    elif typ == "Round":
        return round(args[0], int(args[1]))
    elif typ == "Spot of":
        # args[0] is value and args[1] is in what it's looking
        for i in range(len(args[1])):
            if args[1][i] == args[0]: return i
        return float("nan") # if nothing has been found
    elif typ == "Functions":
        # args[0] is key, args[1] is number
        # "Floor", "Ceil", "Abs"
        return eval(args[0].lower() + "(args[1])")
    elif typ == "Time":
        # args[0] is what should be isolated
        # args[1] is a datetime object
        return eval("args[1]." + args[0].lower())

def expression(typ, args): # solves expressions
    if typ == "Compare":
        # args[1] is operator
        # "==", "<", "<=", ">", ">="
        return eval("args[0] " + args[1] + " args[2]")
    elif typ == "Combine":
        # args[1] is operator
        # "and", "or", "xor"
        if args[1] == "xor": args[1] = "^"
        return eval("args[0] " + args[1] + " args[2]")
    elif typ == "Not":
        return not args[0]
    elif typ == "Dynamic Near":
        # args[0] and [1] are numbers, [2] is the body size
        return abs(args[0] - args[1]) < args[2]

def coordinate(what: str, value, gridc, rx, ry, height):
    if what == "x":
        coord = (gridc[0]*(value-rx[0]))/gridc[1]
        return coord
    elif what == "y":
        coord = height-(gridc[2]*(value-ry[0]))/gridc[3]
        return coord

class Grid(QtWidgets.QGraphicsItem):
    def __init__(self, rect, grid_information=None):
        super().__init__()
        self.rect = rect
        self.conversion = grid_information # (dx, corr dt, dy, corr dp)
        self.density = (20, 20)
        
    def boundingRect(self):
        return self.rect
    
    def paint(self, painter, option, widget):
        # draw grid

        if theme == "light": painter.setPen(QtCore.Qt.GlobalColor.gray)
        else: painter.setPen(QtGui.QColor(56, 56, 56))
        for x in range(int(self.rect.left()), int(self.rect.right()), self.density[0]):
            painter.drawLine(x, int(self.rect.top()), x, int(self.rect.bottom()))
        for y in range(int(self.rect.top()), int(self.rect.bottom()), self.density[1]):
            painter.drawLine(int(self.rect.left()), y, int(self.rect.right()), y)

class Candle(QtWidgets.QGraphicsItem):
    def __init__(self, time, ohlc, date=None):
        super().__init__()
        self.text = "Default"
        self.time = time
        self.ohlc = ohlc
        self.date = date
        self.setAcceptHoverEvents(True)
        
    def convCoords(self, gridc, rx, ry, height):
        self.x = coordinate("x", self.time, gridc, rx, ry, height)
        self.up = self.ohlc[0] < self.ohlc[3] # open < close
        self.wid = gridc[0]/gridc[1] # px per nt/ t per npx
        if self.up: # if price went up use close as top
            self.y = coordinate("y", self.ohlc[3], gridc, rx, ry, height)
        else: # else use open
            self.y = coordinate("y", self.ohlc[0], gridc, rx, ry, height)
        self.hei = abs(self.ohlc[0]-self.ohlc[3])*(gridc[2]/gridc[3]) # dp*px per np/ p per npx
        self.top = coordinate("y", self.ohlc[1], gridc, rx, ry, height) # high
        self.tip = coordinate("y", self.ohlc[2], gridc, rx, ry, height) # low

    def boundingRect(self): # important for boundaries
        return QtCore.QRectF(self.x, self.top, self.wid, self.tip-self.top) # rect from high to low in 1 timeframe
        
    def paint(self, painter, option, widget):
        #painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if self.up: 
            c = QtGui.QColor(96, 228, 48) # lime
            painter.setPen(c)
            painter.setBrush(c)
        else: 
            c = QtGui.QColor(225, 0, 0) # red
            painter.setPen(c)
            painter.setBrush(c)
        #painter.drawEllipse(QtCore.QPointF(self.x, self.y), 10, 10)
        add = 0
        if self.wid % 2 == 0: # if width of candle is even, try to change the line position with subpixels
            add = 0.5
        painter.drawLine(QtCore.QLineF(self.x+self.wid/2+add, self.top, self.x+self.wid/2+add, self.tip)) # wick
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        #painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        rec = QtCore.QRectF(self.x, self.y, self.wid, self.hei) # body
        painter.drawRect(rec)
        #painter.drawText(QPointF(self.x, self.y) - QPointF(fm.lineWidth(self.text)/2, 0), self.text)
        
    def hoverEnterEvent(self, event): # Tooltip
        text = "Time: "
        if self.date == None: text += str(self.time) + "\n"
        else: text += self.date.strftime("%Y/%m/%d %H:%M:%S") + "\n"
        text += "Open: " + str(self.ohlc[0]) + "\n"
        text += "High: " + str(self.ohlc[1]) + "\n"
        text += "Low: " + str(self.ohlc[2]) + "\n"
        text += "Close: " + str(self.ohlc[3])
        self.setToolTip(text)

class Triangle(QtWidgets.QGraphicsItem): # entry and sell triangle for backtests
    def __init__(self, x, y, up: bool, date=None, parent=None):
        super().__init__(parent)
        self.text = "Default"
        self.time = date
        self.x = x
        self.y = y
        self.up = up
        self.wid = 10
        self.hei = 10
        self.setAcceptHoverEvents(True)
        
    def convCoords(self, gridc, rx, ry, height):
        self.x = coordinate("x", self.x, gridc, rx, ry, height)
        self.y = coordinate("y", self.y, gridc, rx, ry, height) #abs(self.ohlc[0]-self.ohlc[3])*(gridc[2]/gridc[3]) # dp*px per np/ p per npx
        if self.up: 
            self.vertices = [QtCore.QPointF(self.x, self.y+self.hei), QtCore.QPointF(self.x+self.wid, self.y+self.hei), QtCore.QPointF(self.x+self.wid/2, self.y)]
        else:
            self.vertices = [QtCore.QPointF(self.x, self.y), QtCore.QPointF(self.x+self.wid, self.y), QtCore.QPointF(self.x+self.wid/2, self.y+self.hei)]

    def boundingRect(self): # important for boundaries
        return QtCore.QRectF(self.x, self.y, self.wid, self.hei) # rect
        
    def paint(self, painter, option, widget):
        if self.up: 
            c = QtGui.QColor(96, 228, 48) # lime
            painter.setPen(c)
            painter.setBrush(c)
        else: 
            c = QtGui.QColor(225, 0, 0) # red
            painter.setPen(c)
            painter.setBrush(c)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        tri = QtGui.QPolygonF(self.vertices) # triangle made out of vertices
        painter.drawPolygon(tri)
        
    def hoverEnterEvent(self, event): # Tooltip
        text = "Time: "
        text += str(self.time) + "\nEvent: "
        if self.up: text += "Bought"
        else: text += "Sold"
        self.setToolTip(text)

class Circle(QtWidgets.QGraphicsItem): # exit percentage circles
    def __init__(self, x, y, up: bool, perc:float, date=None, parent=None):
        super().__init__(parent)
        self.text = "Default"
        self.time = date
        self.x = x
        self.y = y
        self.up = up
        self.perc = perc
        self.wid = 10
        self.hei = 10
        self.setAcceptHoverEvents(True)
        
    def convCoords(self, gridc, rx, ry, height):
        self.x = coordinate("x", self.x, gridc, rx, ry, height)
        self.y = coordinate("y", self.y, gridc, rx, ry, height) #abs(self.ohlc[0]-self.ohlc[3])*(gridc[2]/gridc[3]) # dp*px per np/ p per npx

    def boundingRect(self): # important for boundaries
        return QtCore.QRectF(self.x, self.y, self.wid, self.hei) # rect
        
    def paint(self, painter, option, widget):
        if self.up: 
            c = QtGui.QColor(96, 228, 48) # lime
            painter.setPen(c)
            painter.setBrush(c)
        else: 
            c = QtGui.QColor(225, 0, 0) # red
            painter.setPen(c)
            painter.setBrush(c)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        cir = QtCore.QRectF(self.x, self.y, self.wid, self.hei) # define rect as outer boundaries of circle
        painter.drawEllipse(cir)
        
    def hoverEnterEvent(self, event): # Tooltip
        text = "Time: "
        text += str(self.time) + "\nEvent: Sold"
        text += "\nExit: "
        text += str(self.perc)
        self.setToolTip(text)

class PriceRect(QtWidgets.QGraphicsSimpleTextItem): # Rectangles on axes that display exact details on crosshair position
    def __init__(self, text: str, position: QtCore.QPointF):
        super().__init__()
        self.setText(text)
        self.position = position
        self.position.setY(position.y()+12.5) # equalize the bounding rect
        self.placed = False
    
    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(self.position.x(), self.position.y()-12.5, len(self.text())*10, 25)
    
    def paint(self, painter: QtGui.QPainter, option, widget):
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#ffffff"))) # surrounding rect
        painter.drawRect(QtCore.QRectF(self.position.x(), self.position.y()-12.5, len(self.text())*10, 25))
        painter.setRenderHint(QtGui.QPainter.RenderHint.VerticalSubpixelPositioning)
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#000000")))
        painter.drawText(self.position, self.text())

class Focus(QtWidgets.QGraphicsRectItem): # Focus that tells the user, what they've clicked on
    def __init__(self):
        super().__init__()
        self.setZValue(999)
        self.setPen(QtGui.QPen(QtGui.QColor(50, 240, 240)))
        self.placed = False
        self.time = 0

class View(QtWidgets.QGraphicsView): # Main Graphics window
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setScene(scene)
        self.mouseFunction = self.dummy # setup dummy functions to be overidden later
        self.infoFn = self.dummy
    
    def dummy(self, event):
        x = event.pos().x()
        y = event.pos().y()
    
    def setMouseFn(self, function): # for Crosshair
        self.mouseFunction = function

    def setInfoFn(self, function):
        self.infoFn = function
    
    def wheelEvent(self, event): # modify the scroll behavior of the scrolling so that shift scroll is horizontal scroll
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier:
            # Shift key pressed, scroll horizontally
            scroll = -int(event.angleDelta().y()*0.875)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + scroll)
        else:
            # No modifier key pressed, pass event to base class
            super().wheelEvent(event)
    
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton: self.infoFn(event)
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent): # for crosshair movement
        #print(event.pos())
        self.mouseFunction(event)
        return super().mouseMoveEvent(event)

class SmallView(QtWidgets.QGraphicsView): # small view window for condition creator
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QtWidgets.QGraphicsScene())
        self.mouseFunction = lambda: type(None) # setup dummy functions to be overidden later
        self.leftFn = lambda: type(None)
        self.pxSize = (300, 200)
        self.dMode = 0 # display mode | 0 is candlestick, 1 is graph, 2 is heikin-ashi
        self.candles = [] # candle data in ohlcv
        self.gridconv = []
        self.rangex = (240, 300) # only render last 60 candles for faster rendering
        self.rangey = []
        self.graphInds = [] # Indicators that have graph data such as sma
        self.annotations = [] # texts that will be placed on the scene; format: ("string", x, y)
        self.isVolume = False # whether to display volume
        self.colors = [] # list of colors to use in displaying | always has to be same length as number of things displayed
        self.ind = -1 # will keep track of index of edited condition; so basically does nothing here
        self.density = (10, 10)
        self.sizx = -1 # for main window smallview
    
    def setMouseFn(self, function): # for Crosshair
        self.mouseFunction = function

    def setInfoFn(self, function):
        self.leftFn = function
    
    def makeScene(self): # same as setScene for gui
        #sizx = ((self.rangex[1]-self.rangex[0])/self.gridconv[1])*self.gridconv[0] # ((t-t0)/how many t per pixel)*npixels
        sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
        self.heivar = sizy
        self.scene().clear()
        self.scene().setSceneRect(0, 0, self.pxSize[0]-10, self.pxSize[1]-10)
        grid = Grid(QtCore.QRectF(-5, -5, self.pxSize[0], self.pxSize[1]))
        grid.density = self.density
        self.scene().addItem(grid)
        if self.dMode == 0: # if Candlesticks is checked
            i = 230
            for c in self.candles[230:]: 
                can = Candle(i, c)
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                #print(can.x, can.y)
                self.scene().addItem(can)
                i += 1
            #print(can.y)
        elif self.dMode == 2: # heikin-ashi
            # first candle
            c = deepcopy(self.candles[230])
            last = Candle(0, c)
            last.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
            self.scene().addItem(last)
            i = 231
            for c in self.candles[231:]: # all except first one
                ohlc = deepcopy(last.ohlc)
                new = deepcopy(c)
                ohlc[0] = (ohlc[0] + ohlc[3])/2 # previous open + close /2
                ohlc[1] = max([new[0], new[1], new[3]]) # max of high open or close
                ohlc[2] = min([new[0], new[2], new[3]]) # min of low open or close
                ohlc[3] = (new[0] + new[1] + new[2] + new[3])/4
                if ohlc[0] > ohlc[1]: ohlc[1] = ohlc[0] # to prevent errors
                elif ohlc[0] < ohlc[2]: ohlc[2] = ohlc[0]
                can = Candle(i, ohlc)
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                last = can
                self.scene().addItem(can)
                i += 1
        
        # volume
        if self.isVolume: # only display volume bars
            vols = []
            for c in self.candles:
                vols.append(c[4])
            mx = max(vols) # max volume
            mn = min(vols) # min volume
            for i in range(len(vols)):
                hei = vols[i] - mn 
                hei = 50*(hei/(mx-mn)) # map to 1 - 50
                can = Candle(i, self.candles[i])
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                rect = QtCore.QRectF(can.x, self.scene().height()-hei, can.wid, hei)
                nopen = QtGui.QPen(QtCore.Qt.PenStyle.NoPen)
                self.scene().addRect(rect, nopen, self.colors[0])

        # indicators
        if len(self.graphInds) != 0: # if indicators are used
            j = 0
            for ind in self.graphInds: # for every graph indicator
                for i in range(230, len(self.candles)-1): # do same as graph
                    c = [self.candles[i], self.candles[i+1]] # for simplification
                    for e in range(2):
                        c[e] = Candle(i+e, c[e])
                        c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                    if i != len(self.candles)-1:
                        close1 = coordinate("y", ind[i], self.gridconv, self.rangex, self.rangey, self.heivar) # get positions
                        close2 = coordinate("y", ind[i+1], self.gridconv, self.rangex, self.rangey, self.heivar)
                    can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                    can.setPen(self.colors[j])
                    self.scene().addItem(can)
                j += 1

        # text annotations
        j = 0
        for a in self.annotations:
            tex = SimpleText(a[0], self.colors[j], QtCore.QPointF(a[1], a[2]))
            self.scene().addItem(tex)
            j += 0
    
    def regularScene(self): # for smallview in main window
        # gridconv has to be given
        mi = 1000000000000 # minimum value
        ma = -1000000000000 # maximum value
        if self.isVolume:
            # get max and min volume
            for c in self.candles:
                if c[4] > ma: ma = c[4]
                if c[4] < mi: mi = c[4]
            self.rangey = (mi, ma)
        else:
            for g in self.graphInds:
                gg = [x for x in g if not isnan(x)] # remove all nan values from list
                if min(gg) < mi: mi = min(gg)
                if max(gg) > ma: ma = max(gg)
            self.rangey = (mi, ma)
        # 150 is height of smallview
        # grc3 = (totran*grc2)/npx
        self.gridconv[3] = ((self.rangey[1]-self.rangey[0])*self.gridconv[2])/150
                

        sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
        self.heivar = sizy
        self.scene().clear()
        self.scene().setSceneRect(0, 0, self.sizx, 150)
        self.scene().addItem(Grid(QtCore.QRectF(0, 0, self.sizx, 150), self.gridconv))
        
        # volume
        if self.isVolume: # only display volume bars
            vols = []
            for c in self.candles:
                vols.append(c[4])
            mx = max(vols) # max volume
            mn = min(vols) # min volume
            for i in range(len(vols)):
                hei = vols[i] - mn 
                hei = 150*(hei/(mx-mn)) # map to 1 - 50
                can = Candle(i, self.candles[i])
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                rect = QtCore.QRectF(can.x, self.scene().height()-hei, can.wid, hei)
                nopen = QtGui.QPen(QtCore.Qt.PenStyle.NoPen)
                self.scene().addRect(rect, nopen, self.colors[0])

        # indicators
        if len(self.graphInds) != 0: # if indicators are used
            j = 0
            for ind in self.graphInds: # for every graph indicator
                for i in range(len(self.candles)-1): # do same as graph
                    c = [self.candles[i], self.candles[i+1]] # for simplification
                    for e in range(2):
                        c[e] = Candle(i+e, c[e])
                        c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                    if i != len(self.candles)-1:
                        close1 = coordinate("y", ind[i], self.gridconv, self.rangex, self.rangey, self.heivar) # get positions
                        close2 = coordinate("y", ind[i+1], self.gridconv, self.rangex, self.rangey, self.heivar)
                    can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                    can.setPen(self.colors[j])
                    self.scene().addItem(can)
                j += 1

        # text annotations
        j = 0
        for a in self.annotations:
            tex = SimpleText(a[0], self.colors[j], QtCore.QPointF(a[1], a[2]))
            self.scene().addItem(tex)
            j += 0

    def initScene(self): # same as newScene for gui
        #self.candles = [] # empty candles
        self.marked = [] # reset marked spots
        #mi = 10000 # minimum value
        #ma = 0 # maximum value
        avg = 0 # avg body size
        for t in range(60): # get last 60 candles
            t = -t-1
            #if self.candles[t][1] > ma: ma = self.candles[t][1]
            #if self.candles[t][2] < mi: mi = self.candles[t][2]
            avg += abs(self.candles[t][3] - self.candles[t][0])
            #l = [self.candles[t][0], self.candles[t][1], self.candles[t][2], self.candles[t][3]]
            #self.candles.append(l)
        avg /= 60
        tenpows = [0.0005]
        while tenpows[-1] < avg: # fill up the list
            if str(1000/tenpows[-1])[0] == "4": # multiple of 2.5
                tenpows.append(tenpows[-1]*2)
            else: tenpows.append(tenpows[-1]*5)
        contenders = [abs(avg/tenpows[-2]-1), abs(avg/tenpows[-1]-1)]
        if contenders[0] < contenders[1]: tenpow = tenpows[-2]
        else: tenpow = tenpows[-1]
        tenpow *= 2 # because it looked for square size 
        last = self.candles[-3][3] # last visible candle
        self.rangey = (last-last%tenpow-5*tenpow, last+(5*tenpow-last%tenpow)) # take last and go 10 squares in each direction
        self.gridconv = [25, 5, 25, tenpow]

        self.makeScene()

    def wheelEvent(self, event): # ignore all mouse scrolls
        return

class System(): # class for all of the neccessary data to display entire view
    def __init__(self):
        self.gridconv = []
        self.rangex = []
        self.rangey = []
        self.candles = []
        self.view = None
        self.heivar = None
        self.rawind = -1
        self.timeaxis = []
        self.live = [] # live data needed for current stock; ticker, period, interval etc.

class SimpleText(QtWidgets.QGraphicsSimpleTextItem): # Custom class because just changing the renderer is too complicated
    def __init__(self, text: str, color: QtGui.QColor, position: QtCore.QPointF):
        super().__init__()
        self.setText(text)
        self.color = color
        self.position = position
        self.position.setY(position.y()+12.5) # equalize the bounding rect
    
    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(self.position.x(), self.position.y()-12.5, len(self.text())*10, 25)
    
    def paint(self, painter: QtGui.QPainter, option, widget):
        painter.setRenderHint(QtGui.QPainter.RenderHint.VerticalSubpixelPositioning)
        painter.setPen(QtGui.QPen(self.color))
        painter.drawText(self.position, self.text())
        
class SubDock(QtWidgets.QDockWidget): # sub sub window
    def __init__(self):
        super().__init__()
        self.fn = lambda: type(None) # dummy
        self.setStyleSheet(dockstring)
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)

    def setFn(self, fn):
        self.fn = fn

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.fn()
        return super().closeEvent(event)

class IndButton(QtWidgets.QPushButton): # Indicator Button
    def __init__(self, parent=None, idd=0, ty="conds"):
        super().__init__(parent)
        self.delFn = None
        self.idd = idd
        self.clickFn = None
        self.renFn = None
        self.typ = ty
        self.stype = self.typ[0] # short type for simpler programming
        self.doPass = True # whether to also pass event
        self.debugFn = None
        self.runFn = None

    def setDelFn(self, fn): # right click delete
        self.delFn = fn
    
    def setRenFn(self, fn): # rename function
        self.renFn = fn
    
    def setClickFn(self, fn): # left click
        self.clickFn = fn
    
    def setDebugFn(self, fn): # directly start debug option
        self.debugFn = fn

    def setRunFn(self, fn): # run strategy without requiring to open dialog first
        self.runFn = fn
    
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.doPass: self.clickFn(e, self.idd, self.stype)
            else: self.clickFn(self.idd, self.stype)
        return super().mouseReleaseEvent(e)

    def contextMenuEvent(self, event):
        if self.delFn is None: return
        menu = QtWidgets.QMenu(self)
        if self.runFn is not None:
            act = menu.addAction("Run")
            act.triggered.connect(lambda: self.runFn(self.idd))
        if self.debugFn is not None:
            act = menu.addAction("Debug")
            act.triggered.connect(lambda: self.debugFn(self.idd))
        if self.renFn is not None:
            act = menu.addAction("Rename")
            act.triggered.connect(lambda: self.renFn(self.idd, self.stype))
        act = menu.addAction("Delete")
        act.triggered.connect(lambda: self.delFn(self.idd, self.typ))
        menu.setStyleSheet("color: white;")
        menu.exec(event.globalPos())

class AdvancedComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fn = None
        
        self.currentIndexChanged.connect(self.handle_index_changed)

    def setFn(self, fn): 
        self.fn = fn

    def handle_index_changed(self, index):
        if self.itemText(index) == "Advanced...":
            self.fn(index)

class StratList(QtWidgets.QListWidget): # custom list for strategies; makes it easier to get id of clicked thing
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fn = lambda: type(None)
        self.fn1 = lambda: type(None)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, pos): # right click on item
        item = self.itemAt(pos)
        if item is not None:
            menu = QtWidgets.QMenu()
            act = menu.addAction("Connect...")
            act.triggered.connect(lambda: self.fn(item))
            if item.typ == "cc": 
                act = menu.addAction("Delete")
                act.triggered.connect(lambda: self.fn1(item))
            menu.exec(self.mapToGlobal(pos))
    
    def setFn(self, fn, fn1): # right click commands
        self.fn = fn
        self.fn1 = fn1

class ListItem(QtWidgets.QListWidgetItem):
    def __init__(self, text, idd, parent=None, typ="ci"):
        super().__init__(text, parent)
        self.idd = idd
        self.typ = typ
        self.conns = [] # connected coditions / complex conditions

class Axis(QtWidgets.QGraphicsView): # x and y axis
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setScene(scene)
        self.mouseFunction = self.dummy # setup dummy function to be overidden later
    
    def dummy(self):
        pass
    
    def wheelEvent(self, event): # ignore all mouse scrolls
        return
    
    def setMouseFn(self, function):
        self.mouseFunction = function
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        #print(event.pos())
        if event.button() == QtCore.Qt.MouseButton.LeftButton: self.mouseFunction() # if doubleclicked with left, run fn
        return super().mouseMoveEvent(event)

class TabBar(QtWidgets.QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fn = None # plus fn
        self.fn2 = None # switch fn
        self.fn3 = None
    
    def setFn(self, fn, fn2, fn3):
        self.fn = fn
        self.fn2= fn2
        self.fn3 = fn3
    
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        index = self.tabAt(event.pos())
        if event.button() == QtCore.Qt.MouseButton.LeftButton: # left click
            if self.tabText(index) == "+":
                if self.fn(event):
                    return super().mousePressEvent(event)
            else: 
                self.fn2(event)
                return super().mousePressEvent(event)
        else:
            if self.tabText(index) != "+": # if tab is not the plus tab
                menu = QtWidgets.QMenu() # show context menu for delete
                act = menu.addAction("Delete")
                act.triggered.connect(lambda: self.fn3(index))
                menu.exec(self.mapToGlobal(event.pos()))

class Stats():
    def __init__(self):
        self.succ = 0 # success rate
        self.sf = 0 # success per failure rate | how much more a success is worth than a failure
        self.progress = 0 # how far it is
        self.active = False
        self.processed = 0 # number of stocks processed
        self.money = 0 # money remaining at the end
        self.finished = False # whether the side process has finished
        self.details = [] # list that will store dictionaries for each stock

class SideStats(): # stats such as variables etc that are displayed on the right window
    def __init__(self):
        self.strings = [] # list that stores all of the label texts
        self.new = False # whether the stats are new or not

    def display(self, parent): # display all of the lables
        self.new = True
        i = 0
        for s in self.strings:
            lab = QtWidgets.QLabel(s, parent)
            lab.setStyleSheet("border: none;")
            lab.move(2, 2+i*20)
            i += 1
    
    def reset(self):
        self.strings = [] # empty strings

class BackThread(): # thread that runs the backtests in the background
    def __init__(self, fn, increment, rawind, cons, indx):
        super().__init__()
        self.fn = fn
        self.inc = increment
        self.ind = indx
        self.money = 0
        self.time = 0
        self.rawind = rawind # index in raw reserved for this thread
        self.rawpoint = indx # current stock viewed
        self.conds = cons # list of conditions for efficiency
        self.condata = [] # condition data
        self.data = [] # final activation data
        self.risk = [] # copied from strategy
        self.calc = [] # also copied
        self.prefs = [] # also also
        self.operations = [] # list of active operations
        self.entexs = [] # entries and exits etc.
        self.process = None
        self.queue = None
    
    def start(self): # start the thread
        self.process = multiprocessing.Process(target=self.fn, args=(self.ind, self.queue)) # pass 2 args because tuple
        self.process.start()

class BackProcess(): # just for any processes in the future
    def __init__(self, fn, process:str):
        super().__init__()
        self.fn = fn
        self.name = process # name of process associated
        self.args = ()

    def start(self): # start the thread
        self.process = multiprocessing.Process(target=self.fn, args=self.args) 
        self.process.start()

class WidgetContainer(QtWidgets.QWidget): # container widget that has a setwidget method
    def __init__(self, parent=None):
        super().__init__(parent)
        if theme == "dark": self.setStyleSheet("background-color: #191919;")
        else: self.setStyleSheet("background-color: #FFFFFF;")
        self.changingLayout = QtWidgets.QVBoxLayout()
        self.changingLayout.setContentsMargins(0, 0, 0, 0)
        self.changingLayout.setSpacing(0)
        self.setLayout(self.changingLayout)
        self.currentWidget = None
    
    def setWidget(self, widget):
        if self.currentWidget:
            self.changingLayout.removeWidget(self.currentWidget)
            self.currentWidget.deleteLater()
        
        self.changingLayout.addWidget(widget)
        self.currentWidget = widget

class Slot(QtWidgets.QLineEdit): # slot that can either be filled with a number or a variable
    def __init__(self, parent=None, fn=None):
        super().__init__(parent)
        self._locked = False
        self._allowed_chars = "0123456789.-"
        self.requested = "V" # v for variable, e for expression
        self.requestRange = False # whether to also request range with variable
        self.spotVar = "" # stores str of spot or range e.g. "0", "5,0"
        self.var = None
        self.dragFn = fn
        self.multiFn = None # function to enter multiple variables
        self.pInd = -1 # parent id for custom drop box methods

    def setLocked(self, locked=True):
        self._locked = locked
        self.setReadOnly(locked)

    def setMultiFn(self, fn):
        self.multiFn = fn

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if ((event.modifiers().name == "ControlModifier" and self.requestRange) or
            type(self.var) == list and self.text() == "Multiple"): # if control is pressed and a range is requested; open multi variable selector
                if self.multiFn is None: return
                self.multiFn(self)
                return
            if self._locked:
                self.spotVar = ""
                self.setToolTip("")
                self.setText("") # empty text
                if self.requested == "V" and not self.requestRange: self.setLocked(False) # don't unlock for expressions or when var is required
                self.var = None
        super().mousePressEvent(event)

    def event(self, event):
        if self._locked:
            return super().event(event)

        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            text = event.text()

            if (key == QtCore.Qt.Key.Key_Backspace
                or key == QtCore.Qt.Key.Key_Delete
                or text in self._allowed_chars):
                return super().event(event)

            return True

        return super().event(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, a0): # when text is dropped in the box
        if self.dragFn is None: return
        self.dragFn(self)
        return super().dropEvent(a0)

class IndicatorVariable(): # variable used in slot or combobox for calculation
    def __init__(self, iName="", args=[], var="", idd=-1):
        self.name = "" # display name
        self.indName = iName # name of indicator used
        self.args = args # arguments for indicator
        self.var = var # name of variable
        self.val = None # value of the variable
        self.id = idd # identificator

class VariableEquation(): # equation that can be used as a variable
    def __init__(self, name="", typ="", args=[], idd=-1):
        self.name = name # name (optional) of equation
        self.type = typ # type of equation
        self.args = args # list of arguments
        self.val = None # value of the equation
        self.id = idd # identificator

class VariableExpression(): # expression with one or more variables
    def __init__(self, name="", typ="", args=[], idd=-1):
        self.name = name # name of expression
        self.type = typ # Type of expressions
        self.args = args # list of arguments
        self.val = None
        self.id = idd # identificator

class DragBox(QtWidgets.QComboBox): # combobox that allows dragging
    def __init__(self, parent=None, delfn=None, edfn=None):
        super().__init__(parent)
        self.vars = []
        self.delFn = delfn
        self.edFn = edfn
        self.rnFn = None
        self.doDrag = True
        self.boxType = "V" # v for variable, i for indicator
        self.currentTextChanged.connect(self.updateToolTip)

    def setIndicator(self): # indicators box doesn't allow drag
        self.doDrag = False
        self.boxType = "I"

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.doDrag: 
                self.startDrag()
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        if len(self.vars) == 0: return
        self.updateToolTip()
        if self.delFn is None or self.edFn is None: return # failsave
        menu = QtWidgets.QMenu(self)
        if self.rnFn is not None:
            act = menu.addAction("Rename")
            act.triggered.connect(self.rnFn)
        act = menu.addAction("Edit")
        act.triggered.connect(lambda: self.edFn(self.vars[self.currentIndex()]))
        act = menu.addAction("Delete")
        act.triggered.connect(lambda: self.delFn(self, self.vars[self.currentIndex()]))
        #menu.setStyleSheet("color: white;")
        menu.exec(event.globalPos())

    def startDrag(self):
        item_text = self.currentText()

        if item_text:
            mime_data = QtCore.QMimeData()
            mime_data.setText(item_text)

            drag = QtGui.QDrag(self)
            drag.setMimeData(mime_data)

            # Set the drag pixmap to be the current combo box content
            pixmap = self.grab()
            drag.setPixmap(pixmap)

            # Offset the drag position to the center of the combo box
            drag.setHotSpot(self.rect().center())

            # Start the drag operation
            drag.exec(QtCore.Qt.DropAction.CopyAction | QtCore.Qt.DropAction.MoveAction)
    
    def updateToolTip(self): # tooltip
        if len(self.vars) == 0: return
        var = self.vars[self.currentIndex()]
        text = ""
        if type(var) == IndicatorVariable: text += var.indName
        else: text += var.type
        if len(var.args) != 0: text += " ("
        i = 0
        for a in var.args:
            if i == 0: text += str(a)
            else: text += ", " + str(a)
            i += 1
        if len(var.args) != 0: text += ")"
        self.setToolTip(text)

class EdSaveBtn(QtWidgets.QPushButton): # button with extra state variables
    def __init__(self, text="", parent=None, fn=None):
        super().__init__(text, parent)
        self.fn = fn # cancel function
        self.active = False # whether button should remain when changing layout
        self.ind = -1 # ind for cancelling
        self.curr = -1 # currently edited variable index

    def setActive(self, act=True):
        self.active = act
        #self.setEnabled(act)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        act = menu.addAction("Cancel")
        act.triggered.connect(lambda: self.fn(self.ind))
        menu.exec(event.globalPos())

class StatGraph(QtWidgets.QGraphicsView): # View for displaying graph in stat calculation
    def __init__(self, parent=None):
        super().__init__(parent)
        # typical display variables
        self.gridconv = [10, 0, 5, 0.1] # px per dx, dx, px per dy, dy
        self.rangex = [-1, 1] # no rangey because always 0 to 1

        self.dots = [] # x and y coords that store the dots of the graph
        self.rendered = [] # dots that already have been added to scene
        self.axes = ["x", "y"] # names for the axes

        self.current = "" # whatever is currently displayed

    def makeScene(self, new): # asseses information and decides what to do with scene
        if new != self.current: # if new category
            self.current = new # change category
            self.newScene()
        else:
            rangex = [self.rangex[0], self.rangex[1]]
            for d in self.dots[len(self.rendered):]: # for all of the new dots
                if d[0] < rangex[0]: rangex[0] = d[0]
                if d[0] > rangex[1]: rangex[1] = d[0]
            if rangex[0] != self.rangex[0] or rangex[1] != self.rangex[1]: # if new dot is out of range
                tot = rangex[1]-rangex[0]
                nearest = 1/10000
                while True: # get nearest fitting size
                    if str(nearest*10000)[0] == 1:
                        nearest *= 2.5
                    else: nearest *= 4
                    if nearest > tot: break
                if str(nearest*10000)[0] == 1: nearest /= 10
                else: nearest /= 5
                rangex[0] = int(rangex[0]-rangex[0]%nearest) # get to nearest clean number
                rangex[1] = int(rangex[1]+nearest-rangex[1]%nearest)
                self.rangex = rangex
                self.newScene()
            else: self.changeScene()

    def newScene(self): # new scene
        self.rendered = []
        self.gridconv[1] = 10*((self.rangex[1]-self.rangex[0])/(self.width()-1)) # 10* (totalrange/pixelsavailable)
        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width()-5, self.height()-5)
        colors = [QtGui.QColor("#A30000"), QtGui.QColor("#AFAF1D"), QtGui.QColor("#267F00"), QtGui.QColor("#00D8B8")]
        for d in self.dots: # first add all of the dots
            for i in range(4): # for color
                if d[1] < 0.25*(i+1): break
            coords = (coordinate("x", d[0], self.gridconv, self.rangex, [0, 1], 50), coordinate("y", d[1], self.gridconv, self.rangex, [0, 1], 50))
            scene.addRect(QtCore.QRectF(coords[0]-1, coords[1]-1, 1, 1), colors[i])
            self.rendered.append(None)
        if theme == "dark": scene.addRect(QtCore.QRectF(0, 50, self.width(), 1), QtGui.QColor("#F0F0F0")) # x axis
        else: scene.addRect(QtCore.QRectF(0, 50, self.width(), 1), QtGui.QColor("#101010")) # x axis
        if theme == "dark": scene.addRect(QtCore.QRectF(0, 25, self.width(), 1), QtGui.QColor("#303030")) # 50%
        else: scene.addRect(QtCore.QRectF(0, 25, self.width(), 1), QtGui.QColor("#C0C0C0")) # 50%
        font = QtGui.QFont("Arial", 8)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.NoAntialias)

        if self.rangex[0] != 0:
            x0 = coordinate("x", 0, self.gridconv, self.rangex, [0, 1], 50)
            if theme == "dark": scene.addRect(QtCore.QRectF(x0, 0, 1, self.height()), QtGui.QColor("#F0F0F0")) # y axis
            else: scene.addRect(QtCore.QRectF(x0, 0, 1, self.height()), QtGui.QColor("#101010")) # y axis
            text = scene.addText("0")
            text.setPos(x0-1, 35)
            text.setFont(font)
        text = scene.addText(str(self.rangex[0]))
        text.setPos(-3, 35) 
        text.setFont(font)
        text = scene.addText(str(self.rangex[1]))
        text.setPos(scene.width()-(len(str(self.rangex[1]))*7)+1, 35) 
        text.setFont(font)

        self.setScene(scene)
    
    def changeScene(self): # add to existing scene
        colors = [QtGui.QColor("#A30000"), QtGui.QColor("#AFAF1D"), QtGui.QColor("#267F00"), QtGui.QColor("#00D8B8")]
        for d in self.dots[len(self.rendered):]:
            for i in range(4): # for color
                if d[1] < 0.25*(i+1): break
            coords = (coordinate("x", d[0], self.gridconv, self.rangex, [0, 1], 50), coordinate("y", d[1], self.gridconv, self.rangex, [0, 1], 50))
            self.scene().addRect(QtCore.QRectF(coords[0]-1, coords[1]-1, 1, 1), colors[i])
            self.rendered.append(None)

class ProcessManager(): # will keep track of multiprocessing | will not store processes themselves
    def __init__(self):
        self.processes = [] # not active processes but running / ran processes
        self.shown = None # currently shown process

    def register(self, process:str): # get id for process and save it in list
        # check if process is already registered
        for p in self.processes:
            if p[1] == process: return
        idd = 0
        i = 0
        while i < len(self.processes): # check if id is already in use
            if self.processes[i][0] == idd:
                idd += 1
                i = -1 # if id in use go up and restart process
            i += 1

        if len(self.processes) == 0: # if no process has been loaded set current process to this one
            self.shown = idd
        
        self.processes.append((idd, process)) # processes are saved as (id, processstring)
    
    def delist(self, process:str): # remove process of string
        pop = None
        for p in range(len(self.processes)):
            if self.processes[p][1] == process: pop = p
        
        if pop is not None: self.processes.pop(pop)

        if len(self.processes) == 0: self.shown = None # if no more processes exist, set current to none
    
    def current(self): # returns current process
        for p in self.processes:
            if p[0] == self.shown: return p[1]
        return None

    def remCurrent(self): # removes current process
        for p in self.processes:
            if p[0] == self.shown: break
        
        self.processes.remove(p) # remove current process

        # changes current process
        if len(self.processes) == 0: self.shown = None
        else: self.shown = self.processes[0][0]
    
    def switch(self): # switch current shown
        for ind in range(len(self.processes)):
            if self.processes[ind][0] == self.shown: break
        splits = split(self.processes, ind)

        if len(splits[1]) != 0: self.shown = splits[1][0][0] # set current shown to first in split list
        elif len(splits[0]) != 0: self.shown = splits[0][0][0] # else loop around
        # if both lists are empty; means no other processes exist
    
    def setCurrent(self, what): # set current to process with same name
        for p in self.processes:
            if p[1] == what: break
        
        self.shown = p[0]

procManager = ProcessManager() # global process manager

class Logic(): # class for all of the logic things needed in the gui
    def __init__(self):
        self.indicators = [] # data for the indicators | dict
        self.conditions = [] # data for the conditions | dict
        self.strategies = [] # dict
        self.systems = [] # stores all systems
        self.rawind = 0 # current shown raw
        self.entexs = [[], [], [], []] # predefinition
        self.currentSystem = 0 # stores current backtested system
        self.stats = Stats()
        self.stratPath = "" # string for storing currently edited strategies
        self.backthreads = [] # list for storing backtesting threads
        self.threads = [] # list for storing threads

    def getCondtitionData(self, variables=[], conid=None, stock=-1):
        # vars is list of all variables, conid is id of condition to get data, stock is what stock to get the data from
        # either enter variables or condition id to get list of variables for data
        if conid is not None:
            variables = self.conditions[self.find("c", conid)]["vars"]
            filters = self.conditions[self.find("c", conid)]["filters"]
        varsorted = [[], [], [], []] # v, e, x, i
        for var in variables:
            if type(var) == IndicatorVariable:
                if var.var == "": varsorted[3].append(var) # indicator
                else: varsorted[0].append(var)
            elif type(var) == VariableEquation: varsorted[1].append(var)
            elif type(var) == VariableExpression: varsorted[2].append(var)
            elif type(var) == list: filters = var # filters will be passed into variables
        
        # maybe skip this part if calc has already been loaded

        toplay = [] # top layer of expressions
        for ex in varsorted[2]: toplay.append(ex.id)

        for ex in varsorted[2]:
            for a in ex.args:
                if "%x" in str(a):
                    if int(a.split("%x")[1]) in toplay: toplay.remove(int(a.split("%x")[1])) # remove all expressions used to calculate another
        
        for i in range(len(toplay)):
            toplay[i] = ["x", toplay[i]]

        def find(typ, idd): # return index of item in typ list
            if typ == "i": search = varsorted[3]
            elif typ == "v": search = varsorted[0]
            elif typ == "e": search = varsorted[1]
            else: search = varsorted[2]

            for v in range(len(search)):
                if search[v].id == idd:
                    return v

        deps = []

        def downTree(typ, idd, org): # down tree to get complexity score of calculating expression
            if typ != "v": 
                if (typ, idd, org) not in deps: deps.append((typ, idd, org))
                else: # move to front so that it gets calculated earlier
                    deps.pop(deps.index((typ, idd, org)))
                    deps.append((typ, idd, org))
            if typ == "x": # expression
                if org.type == "Variable": # if exist expression check indicator first
                    for ir in varsorted[3]:
                        if ir.indName == org.args[0] and ir.args == org.args[1:]:
                            downTree("i", ir.id, ir)
                else:
                    for a in org.args:
                        if "%" in str(a):
                            # can be either variable with spot, equation or expression
                            sp = a.split("%")
                            for s in sp:
                                if not isint(s) and s != "": # if variable in str
                                    temp = ["v", "e", "x"]
                                    t = temp.index(s[0])
                                    downTree(s[0], int(s[1:]), varsorted[t][find(s[0], int(s[1:]))])
            elif typ == "e": # equation
                for a in org.args:
                    if "%" in str(a):
                        # it's either a variable with spot, multiple variables with spot or another equation
                        sps = a.split("|")
                        for spsps in sps:
                            sp = spsps.split("%")
                            for s in sp:
                                if "," in s: p = s.split(",")
                                else: p = [s]
                                for pp in p:
                                    if not isint(pp) and pp != "": # if variable in str
                                        temp = ["v", "e"]
                                        t = temp.index(pp[0])
                                        downTree(pp[0], int(pp[1:]), varsorted[t][find(pp[0], int(pp[1:]))])
            elif typ == "v": # if variable only pass onto indicator
                for ir in varsorted[3]:
                    if ir.indName == org.indName and ir.args == org.args:
                        downTree("i", ir.id, ir)
            elif typ == "i":
                for a in org.args:
                    if "%" in str(a):
                        # can be either variable with spot or equation
                        sp = a.split("%")
                        for s in sp:
                            if not isint(s) and s != "": # if variable in str
                                temp = ["v", "e"]
                                t = temp.index(s[0])
                                downTree(s[0], int(s[1:]), varsorted[t][find(s[0], int(s[1:]))])

        sortd = [[], []]
        for t in range(len(toplay)):
            deps = []
            #toplay[t] = [toplay[t]] # turn just ids into nested ids for sorting in the future
            downTree("x", toplay[t][1], varsorted[2][find("x", toplay[t][1])])
            toplay[t].append(len(deps)) # get how many variables the expression depends on
            if varsorted[2][find("x", toplay[t][1])].type == "Variable": sortd[0].append(toplay[t]) # sort by exist expression and 
            else: sortd[1].append(toplay[t]) # other
        
        for i in range(2):
            sortd[i] = sorted(sortd[i], key=lambda x: x[2]) # sort by least calculations to get

        toplay = sortd[0] + sortd[1]

        for i in range(len(toplay)):
            toplay[i] = (toplay[i][0], toplay[i][1]) # pop the calculation lengths and convert to tuple

        # now get all of the variables in order and save order in condition
        deps = []

        calc = [] # order of calculation
        for t in range(len(toplay)):
            deps = []
            downTree("x", toplay[t][1], varsorted[2][find("x", toplay[t][1])])
            deps.reverse()
            for d in deps: 
                if d not in calc: calc.append(d[:2])

        # calc[0] is the top layer, calc[1] is order that everything needs to be calculated in
        calc = [toplay, calc]
        if conid is not None: self.conditions[self.find("c", conid)]["calc"] = calc

        if stock == -1: stock = self.rawind # incase no stock is given, assume the base stock is used

        for vs in varsorted: # reset all values
            for v in vs:
                v.val = None
        # do every variable in order and check at every top layer expression for false
        data = []
        for t in range(len(raw[stock])):
            # t will keep track of time
            ended = False # will keep track whether a stop was initiated
            for c in calc[1]:
                if c[0] == "i": # indicator
                    var = varsorted[3][find("i", c[1])]
                    for a in var.args:
                        if "%" in str(a): var.val = None # recalculate everytime a variable is an argument
                    if not indinfo[var.indName]["once"] or var.val is None: # value needs to be calculated
                        # if once is true, get entire list and just adjust based on spot instead of calculating over and over again

                        # get arguments to also get values from variables
                        args = deepcopy(var.args)
                        for a in range(len(args)):
                            if "%" in str(args[a]):
                                sp = args[a].split("%") # split of variable in var and spot
                                if len(sp) == 2: sp.append("") # to allow full value returns
                                if not isint(sp[1]) and sp[1] != "": # if variable in str
                                    temp = ["v", "e"]
                                    i = temp.index(sp[1][0])
                                    var2 = varsorted[i][find(sp[1][0], int(sp[1][1:]))]
                                    if sp[1][0] == "e": args[a] = var2.val # get original variable and value from it
                                    else: # also check for spot in variable
                                        if indinfo[var2.indName]["vtypes"][indinfo[var2.indName]["vars"].index(var2.var)] == list: # if list check for spot
                                            # check whether spot is variable or int
                                            if not isint(sp[2]) and sp[2] != "": # variable for spot
                                                # can only be int variable or equation
                                                i = temp.index(sp[2][0]) 
                                                spot = varsorted[i][find(sp[2][0], int(sp[2][1:]))].val
                                            elif isint(sp[2]): spot = int(sp[2])
                                            if sp[2] != "":
                                                # convert spot to correct one with time | if spot incorrect make args to nan
                                                if spot > t or spot < -t-1: spot = "nan"
                                                elif spot < 0: # convert from total scale to truncated scale bc of time
                                                    spot = t + spot + 1
                                                if spot != "nan": args[a] = var2.val[spot]
                                                else: args[a] = float("nan")
                                            else: args[a] = var2.val # just take entire thing if no value is given
                                        else: # just take value
                                            args[a] = var2.val
                        
                        if indinfo[var.indName]["once"]: out = indicator(stock, var.indName, args, len(raw[stock])-1)
                        else: out = indicator(stock, var.indName, args, t)
                        if isinstance(out, tuple): # if multiple values were given
                            temp = []
                            for o in out:
                                temp.append(o)
                            out = temp
                        else: out = [out]
                        if indinfo[var.indName]["existcheck"]: # if existcheck also adjust exist expression
                            # get exist expression
                            for ex in varsorted[2]:
                                if ex.type == "Variable" and ex.args == [var.indName] + var.args: 
                                    ex.val = out[0]
                                    out = out[1:] # cut the exist bool out
                                    break
                        # distribute variables to children variables
                        var.val = out
                        for va in varsorted[0]:
                            if va.indName == var.indName and va.args == var.args:
                                va.val = out[indinfo[var.indName]["vars"].index(va.var)]
                elif c[0] == "e": # equation
                    var = varsorted[1][find("e", c[1])]
                    args = deepcopy(var.args)
                    for a in args:
                        if "|" in str(a): # if multiple variables
                            sps = a.split("|")
                            doList = True
                            args[args.index(a)] = []
                        else: 
                            sps = [a]
                            doList = False
                        if "%" in str(a):
                            for spsps in sps:
                                sp = spsps.split("%")
                                if len(sp) == 2: sp.append("") # to allow full value returns
                                if not isint(sp[1]) and sp[1] != "": # if variable in str
                                    temp = ["v", "e"]
                                    i = temp.index(sp[1][0])
                                    var2 = varsorted[i][find(sp[1][0], int(sp[1][1:]))]
                                    if sp[1][0] == "e": # get original variable and value from it
                                        if doList:
                                            args[args.index(a)].append(var2.val)
                                        else:
                                            args[args.index(a)] = var2.val 
                                    else: # also check for spot in variable
                                        multi = []
                                        if indinfo[var2.indName]["vtypes"][indinfo[var2.indName]["vars"].index(var2.var)] == list: # if list check for spot
                                            # check whether spot is variable or int
                                            if not isint(sp[2]) and sp[2] != "": # variable for spot
                                                # can only be int variable or equation
                                                multi = []
                                                if "," in sp[2]: # means range with either numbers or ! for variables
                                                    ranges = sp[2].split(",")
                                                    for r in ranges:
                                                        if not isint(r): # variable for range
                                                            i = temp.index(r[0]) 
                                                            multi.append(varsorted[i][find(r[0], int(r[1:]))].val)
                                                        else:
                                                            multi.append(int(r))
                                                    for m in range(len(multi)):
                                                        multi[m] = int(multi[m])
                                                        if multi[m] > t or multi[m] < -t-1: multi[m] = float("nan")
                                                        elif multi[m] < 0: # convert from total scale to truncated scale bc of time
                                                            multi[m] = t + multi[m] + 1
                                                    if not any(isnan(x) for x in multi): multi.sort()
                                                    multi[1] += 1 # to get correct range
                                                else:
                                                    i = temp.index(sp[2][0]) 
                                                    spot = varsorted[i][find(sp[2][0], int(sp[2][1:]))].val
                                            elif isint(sp[2]): spot = int(sp[2])
                                            if sp[2] != "":
                                                if len(multi) == 0:
                                                    # convert spot to correct one with time | if spot incorrect make args to nan
                                                    if spot > t or spot < -t-1: spot = "nan"
                                                    elif spot < 0: # convert from total scale to truncated scale bc of time
                                                        spot = t + spot + 1
                                                    if spot != "nan": val = var2.val[spot]
                                                    else: val = float("nan")
                                                    if doList:
                                                        args[args.index(a)].append(val)
                                                    else: args[args.index(a)] = val
                                                else: 
                                                    if any(isnan(x) for x in multi): # if an invalid argument was given
                                                        args[args.index(a)] = []
                                                    else:
                                                        args[args.index(a)] = var2.val[multi[0]:multi[1]]
                                            else:
                                                args[args.index(a)] = var2.val # take entire thing
                                        else: # just take value
                                            args[args.index(a)] = var2.val

                    out = equation(var.type, args)
                    var.val = out
                elif c[0] == "x": # expressions
                    var = varsorted[2][find("x", c[1])]
                    if var.type != "Variable": # skip variable because it has already been calculated
                        args = deepcopy(var.args)
                        for a in range(len(args)):
                            if "%" in str(args[a]):
                                sp = args[a].split("%") # split of variable in var and spot
                                if len(sp) == 2: sp.append("") # to allow full value returns
                                if not isint(sp[1]) and sp[1] != "": # if variable in str
                                    temp = ["v", "e", "x"]
                                    i = temp.index(sp[1][0])
                                    var2 = varsorted[i][find(sp[1][0], int(sp[1][1:]))]
                                    if sp[1][0] != "v": args[a] = var2.val # get original variable and value from it
                                    else: # also check for spot in variable
                                        if indinfo[var2.indName]["vtypes"][indinfo[var2.indName]["vars"].index(var2.var)] == list: # if list check for spot
                                            # check whether spot is variable or int
                                            if not isint(sp[2]) and sp[2] != "": # variable for spot
                                                # can only be int variable or equation
                                                i = temp.index(sp[2][0]) 
                                                spot = varsorted[i][find(sp[2][0], int(sp[2][1:]))].val
                                            elif isint(sp[2]): spot = int(sp[2])
                                            if sp[2] != "":
                                                # convert spot to correct one with time | if spot incorrect make args to nan
                                                if spot > t or spot < -t-1: spot = "nan"
                                                elif spot < 0: # convert from total scale to truncated scale bc of time
                                                    spot = t + spot + 1
                                                if spot != "nan" and spot < len(var2.val): args[a] = var2.val[spot]
                                                else: args[a] = float("nan")
                                            else: args[a] = var2.val # just take entire thing if no value is given
                                        else: # just take value
                                            args[a] = var2.val
                        
                        if var.type == "Dynamic Near": args.append(getAvgBody(raw[stock], t))
                        out = expression(var.type, args)
                        var.val = out
                if c in calc[0]:
                    if not var.val: # if top layer variable is false
                        # break and dont calculate rest because it doesnt matter
                        ended = True
                        break
            if ended: data.append(False)
            else:
                ands = []
                for c in calc[0]: # for every expression in top layer
                    var = varsorted[2][find("x", c[1])]
                    ands.append(var.val)
                data.append(not False in ands) # will be false if a single false appears, else true
        
        # first apply filter then offset
        # "True", "First True", "Last True", "Near"
        for x in [0]: 
            if filters[1] == "True": break # if all true return base list
            elif filters[1] == "First True":
                new = [data[0]] # exported list # start with same as data
                current = data[0]
                for i in data[1:]:
                    if i == current: new.append(False)
                    elif not current: # if not same and current was false; true
                        new.append(True)
                        current = True
                    else: # if true switches to false
                        new.append(False)
                        current = False
                data = new
                break
            elif filters[1] == "Last True":
                if filters[0] == -1: # same spot | all true is true
                    break
                new = [] # exported list
                current = data[0]
                for i in data[1:]:
                    if i == current: new.append(False)
                    elif not current: # if not same and current was false; false
                        new.append(False)
                        current = True
                    else: # if true switches to false
                        new.append(True)
                        current = False
                new.append(data[-1]) # if last one is true always return true
                data = new
                break
            elif filters[1] == "Near": # check two surrounding as well and return true if any of the three is true
                new = []
                if filters[0] == -1: # if spot is now
                    for i in range(len(data)):
                        current = False
                        if i == 0: 
                            current = data[0]
                        else: # check behind and itself
                            for j in range(2):
                                if data[i-j]: current = True
                        new.append(current)
                else:
                    for i in range(len(data)):
                        current = False
                        if i == 0 or i == len(data)-1: # checks behind/ infront and itself
                            if i == 0: mult = -1
                            else: mult = 1
                            for j in range(2):
                                if data[i-j*mult]: current = True
                        else: # check surrounding two and itself
                            for j in range(3):
                                if data[i-1+j]: current = True
                        new.append(current)
                data = new
                break
            else: # custom filter
                # first get relevant data for what is wanted, second run check whether everything fits
                # cbox2.addItems(["Last", "In A Row", "Nearby", "-"])
                ran = "" # what the range should be taken from
                parts = filters[1].split("True")
                if len(parts[1]) == 0: ran = "all"
                elif "In A Row" in parts[1]: ran = "row"
                elif "Nearby" in parts[1]: ran = int(parts[0].split(" ")[-2])
                elif "Last" in parts[1]: ran = "last " + parts[1].split(" ")[-1]
                check = parts[0].split(" ")[0]
                new = []
                for i in range(len(data)):
                    #current = False
                    # get range
                    look = []
                    count = 0
                    if ran == "all": 
                        look = data[:i+1]
                        count = look.count(True)
                    elif ran == "row": # if row just take amount of trues starting from now and going back
                        j = i
                        while j >= 0:
                            if data[j]: count += 1
                            else: break
                            j -= 1
                    elif "last" in str(ran):
                        last = int(ran.split(" ")[1])-1 # -1 to convert from len to index
                        if i < last: last = i
                        look = data[i-last:i+1]
                        count = look.count(True)
                    else:
                        # near range is 3*whatever is input in slot 1; so minimum 3 nearby is maximum ran of 9
                        # ran will fit itself to the offset so that 1.5* slot is to the left and the same amount to the right
                        limits = []
                        if i < int(1.5*ran): limits.append(0)
                        else: limits.append(i - int(1.5*ran))
                        if -filters[0]-1 < int(1.5*ran): limits.append(i-filters[0]-1)
                        else: limits.append(i+int(1.5*ran))
                        look = data[limits[0]: limits[1]+1]
                        count = look.count(True)
                    
                    if check == "Exactly": new.append(count == int(parts[0].split(" ")[1]))
                    elif check == "Minimum": new.append(count >= int(parts[0].split(" ")[1]))
                    elif check == "Maximum": new.append(count <= int(parts[0].split(" ")[1]))
                    else: # around
                        limit = floor(log10(int(parts[0].split(" ")[1])*2)+log10(int(parts[0].split(" ")[1])))
                        new.append(count <= int(parts[0].split(" ")[1])+limit and count >= int(parts[0].split(" ")[1])-limit)
                data = new
                break
        offset = -filters[0] - 1
        for i in range(offset):
            data.pop() # pops last
            data = [False] + data # append False to the beginning
        
        # if conid is not None:
        #     self.conditions[self.find("c", conid)]["data"] = data
        return data

    def getData(self, ind): # calculate data for conditions
        if len(self.conditions[ind]["deps"]) == 0: # if indicator condition
            if len(self.conditions[ind]["data"]) == 0: # check if data has not been calculated
                dat = self.getCondtitionData(conid=self.conditions[ind]["ID"])
                self.conditions[ind]["data"] = dat
        else: # complex condition (does not check for whether underlying conditions have been calculated)
            if len(self.conditions[ind]["data"]) == 0:
                if self.conditions[ind]["deps"][1] == "not": # not only needs one condition
                    dat = []
                    indx = self.find("c", self.conditions[ind]["deps"][0][1])
                    for d in self.conditions[indx]["data"]:
                        dat.append(not d) # invert true to false and false to true
                else:
                    dat = []
                    indx = []
                    for j in range(2): indx.append(self.find("c", self.conditions[ind]["deps"][j*2][1])) # get indexes
                    if self.conditions[ind]["deps"][1] == "xor":
                        for d in range(len(self.conditions[indx[0]]["data"])):
                            dat.append(self.conditions[indx[0]]["data"][d] ^ self.conditions[indx[1]]["data"][d]) # ^ is xor
                    else:
                        statement = "self.conditions[indx[0]][\"data\"][d] " + self.conditions[ind]["deps"][1] + " self.conditions[indx[1]][\"data\"][d]" # d0 and d1 | d0 or d1
                        for d in range(len(self.conditions[indx[0]]["data"])):
                            dat.append(eval(statement))
                # "True", "First True", "Last True", "Near"
                for x in [0]: # also filter for complex conditions
                    if self.conditions[ind]["filters"][1] == "True": break # if all true return base list
                    elif self.conditions[ind]["filters"][1] == "First True":
                        new = [dat[0]] # exported list # start with same as dat
                        current = dat[0]
                        for i in dat[1:]:
                            if i == current: new.append(False)
                            elif not current: # if not same and current was false; true
                                new.append(True)
                                current = True
                            else: # if true switches to false
                                new.append(False)
                                current = False
                        dat = new
                        break
                    elif self.conditions[ind]["filters"][1] == "Last True":
                        if self.conditions[ind]["filters"][0] == -1: # same spot | all true is true
                            break
                        new = [] # exported list
                        current = dat[0]
                        for i in dat[1:]:
                            if i == current: new.append(False)
                            elif not current: # if not same and current was false; false
                                new.append(False)
                                current = True
                            else: # if true switches to false
                                new.append(True)
                                current = False
                        new.append(dat[-1]) # if last one is true always return true
                        dat = new
                        break
                    elif self.conditions[ind]["filters"][1] == "Near": # check two surrounding as well and return true if any of the three is true
                        new = []
                        if self.conditions[ind]["filters"][0] == -1: # if spot is now
                            for i in range(len(dat)):
                                current = False
                                if i == 0: 
                                    current = dat[0]
                                else: # check behind and itself
                                    for j in range(2):
                                        if dat[i-j]: current = True
                                new.append(current)
                        else:
                            for i in range(len(dat)):
                                current = False
                                if i == 0 or i == len(dat)-1: # checks behind/ infront and itself
                                    if i == 0: mult = -1
                                    else: mult = 1
                                    for j in range(2):
                                        if dat[i-j*mult]: current = True
                                else: # check surrounding two and itself
                                    for j in range(3):
                                        if dat[i-1+j]: current = True
                                new.append(current)
                        dat = new
                        break
                self.conditions[ind]["data"] = dat

    def delUnusedConditions(self): # self explanatory
        keep = [] # whether to keep condition
        for c in self.conditions:
            if len(c["deps"]) != 0:
                keep.append(False) # assume that all complex conditions will be deleted
            else: keep.append(True)
        for s in self.strategies: # look whether complex conditions are used in strategy
            for c in s["conds"]:
                if c[0] == "cc": # if condition is in use
                    keep[self.find("c", c[1])] = True # keep condition
        
        poplist = []
        for i in range(len(keep)):
            if not keep[i]: poplist.append(i)
        
        poplist.reverse()
        for p in poplist:
            self.conditions.pop(p)

    def find(self, what, idd): # searches for index of object with id
        if what == "i": search = self.indicators
        elif what == "c": search = self.conditions
        elif what == "s": search = self.strategies
        elif what == "ci": # search conditions by indicator id
            for x in range(len(self.conditions)):
                if self.conditions[x]["indID"] == idd: return x

        for x in range(len(search)):
            if search[x]["ID"] == idd: return x

    def calcStrategy(self, idd): # calculate a strategy given the id
        sind = self.find("s", idd) # strategy index
        conds = self.strategies[sind]["conds"]
        
        calc = [] # reset calc because it could've been uninitialized
        for c in conds:
            calc.append(True) # make dummy calc list with all set to true
        i = -1
        while i != len(conds)-1: # while not all conditions were calculated
            i = len(conds)-1 # total amnt calculated
            for c in conds: # preinit
                if c[0] == "ci": # for indicator condition
                    ind = self.find("c", c[1]) # index
                    self.getData(ind)
                elif c[0] == "cc": # complex condition
                    ind = self.find("c", c[1])
                    if self.conditions[ind]["deps"][1] == "not": # way more easily to only do one
                        if self.conditions[ind]["deps"][0][0] == "ci":
                            self.getData(self.find("c", self.conditions[ind]["deps"][0][1])) # if indicator, just calculate ci and then cc
                            for c in conds:
                                if c[1] == self.conditions[ind]["deps"][0][1]: # get index of used indcator condition in list
                                    calc[conds.index(c)] = False # Dont use in activation calculation
                                    break
                            self.getData(ind)
                        else:
                            temp = self.find("c", self.conditions[ind]["deps"][0][1])
                            if len(self.conditions[temp]["data"]) != 0: # if underlying condition has been calculated
                                for c in conds:
                                    if c[1] == self.conditions[ind]["deps"][0][1]: # get index of used condition in list
                                        calc[conds.index(c)] = False # Dont use in activation calculation
                                        break
                                self.getData(ind)
                            else: i -= 1 # say that this one hasn't been calculated
                    else:
                        if self.conditions[ind]["deps"][0][0] == "ci" and self.conditions[ind]["deps"][2][0] == "ci": # both are indicator conditions
                            for j in range(2): 
                                self.getData(self.find("c", self.conditions[ind]["deps"][j*2][1]))
                                for c in conds:
                                    if c[1] == self.conditions[ind]["deps"][j*2][1]: # get index of used condition in list
                                        calc[conds.index(c)] = False # Dont use in activation calculation
                                        break
                            self.getData(ind)
                        elif self.conditions[ind]["deps"][0][0] == "cc" and self.conditions[ind]["deps"][2][0] == "cc": # both are complex conditions
                            temp = []
                            for j in range(2): 
                                temp.append(self.find("c", self.conditions[ind]["deps"][j*2][1])) # get indexes of both underlyers
                                for c in conds:
                                    if c[1] == self.conditions[ind]["deps"][j*2][1]: # get index of used condition in list
                                        calc[conds.index(c)] = False # Dont use in activation calculation
                                        break
                            if len(self.conditions[temp[0]]["data"]) != 0 and len(self.conditions[temp[1]]["data"]) != 0:
                                self.getData(ind)
                            else: i -= 1
                        else: # ci and cc
                            for j in range(2):
                                for c in conds:
                                    if c[1] == self.conditions[ind]["deps"][j*2][1]: # get index of used condition in list
                                        calc[conds.index(c)] = False # Dont use in activation calculation
                                        break
                            if self.conditions[ind]["deps"][0][0] == "cc": # figure out which is cc
                                temp = (0, self.find("c", self.conditions[ind]["deps"][0][1]))
                            else: 
                                temp = (1, self.find("c", self.conditions[ind]["deps"][2][1])) # get id of complex condition
                            self.getData(self.find("c", self.conditions[ind]["deps"][int(abs(temp[0]-1)*2)][1])) # get data from the ci
                            if len(self.conditions[self.find("c", temp[1])]["data"]) != 0:
                                self.getData(ind)
                            else: i -= 1

        data = []
        temp = False # already something in data
        for c in conds: # calculate final activation
            ind = self.find("c", c[1])
            if calc[conds.index(c)]: # if contition is part of final calculation
                for i in range(len(raw[self.rawind])): 
                    if not temp: # if first, only append data
                        data.append(self.conditions[ind]["data"][i])
                    else: # else check for and so that all conditions have to be true
                        data[i] = data[i] and self.conditions[ind]["data"][i]
                temp = True
        
        if len(data) == 0: # if data is empty create full false list
            for i in range(len(raw[self.rawind])): data.append(False)

        # save calculated things to strategy
        self.strategies[sind]["data"] = data
        self.strategies[sind]["calc"] = calc

        # rest has been moved to gui fn

    def getRisk(self, ind=-1, risk=[], getRecalc=False, once=False, stock=-1): # return risk values and also whether it needs to be recalculated
        # ind is index of strategy
        if ind != -1: risk = self.strategies[ind]["risk"]
        if getRecalc: # check whether risk has to be recalculated at every step
            used = []
            for r in risk[0]:
                if type(r) != list:
                    if "%" in str(r):
                        used.append(r)
                else:
                    for rr in r:
                        if "%" in str(rr):
                            used.append(rr)
            if len(used) == 0: return False # if no special variables are used
            
            # basic only number equations should also not be recalculated; if no variable is found; dont recalculate
            i = 0
            while i < len(risk[1]):
                if type(risk[1][i]) == IndicatorVariable: break
                i += 1
            if i == len(risk[1]): return False # if no variables were found
            
            # check if the variables are on static spots and if all are only calculate once
            vcounters = [0, 0] # 0 is number of variables, 1 is number of static variables
            for u in used:
                if u[1] == "v":
                    #vcounters[0] += 1
                    sp = u.split("%")
                    if int(sp[2]) >= 0: # if static spot
                        vcounters[1] += 1
            for v in risk[1]:
                if type(v) == IndicatorVariable and v.var != "": vcounters[0] += 1
            if vcounters[0] == vcounters[1]: return False
            return True # else just recalculate every time
        
        varsorted = [[], [], []] # variables, equations, indicators
        for v in risk[1]:
            if type(v) == VariableEquation: varsorted[1].append(v)
            else:
                varsorted[0].append(v)
                # also make support indicator and append to third list
                i = 0
                while i < len(varsorted[2]):
                    if varsorted[2][i].indName == v.indName and varsorted[2][i].args == v.args: break # check whether indicator already exists
                    i += 1
                if i == len(varsorted[2]): # if indicator wasnt found
                    varsorted[2].append(IndicatorVariable(v.indName, v.args, idd=i)) # add indicator

        used = []
        for r in risk[0]:
            if type(r) != list:
                if "%" in str(r):
                    used.append(r)
            else:
                for rr in r:
                    if "%" in str(rr):
                        used.append(rr)
        if len(used) == 0: # if no variables to calculate
            return [risk[0]] # return arguments as given by the user
        
        def find(typ, idd): # return index of item in typ list
            if typ == "i": search = varsorted[2]
            elif typ == "v": search = varsorted[0]
            elif typ == "e": search = varsorted[1]

            for v in range(len(search)):
                if search[v].id == idd:
                    return v

        deps = []

        def downTree(typ, idd, org): # down tree to get complexity score of calculating expression
            if typ != "v" and (typ, idd, org) not in deps: deps.append((typ, idd, org))
            if typ == "e": # equation
                for a in org.args:
                    if "%" in str(a):
                        # it's either a variable with spot, multiple variables with spot or another equation
                        sps = a.split("|")
                        for spsps in sps:
                            sp = spsps.split("%")
                            for s in sp:
                                if not isint(s) and s != "": # if variable in str
                                    temp = ["v", "e"]
                                    t = temp.index(s[0])
                                    downTree(s[0], int(s[1:]), varsorted[t][find(s[0], int(s[1:]))])
            elif typ == "v": # if variable only pass onto indicator
                for ir in varsorted[2]:
                    if ir.indName == org.indName and ir.args == org.args:
                        downTree("i", ir.id, ir)
            elif typ == "i":
                for a in org.args:
                    if "%" in str(a):
                        # can be either variable with spot or equation
                        sp = a.split("%")
                        for s in sp:
                            if not isint(s) and s != "": # if variable in str
                                temp = ["v", "e"]
                                t = temp.index(s[0])
                                downTree(s[0], int(s[1:]), varsorted[t][find(s[0], int(s[1:]))])

        if len(risk[2]) == 0:
            toplay = [] # top layer of expressions
            for u in used:
                # get indicators and equations of the top layer
                sp = u.split("%")
                if u[1] == "v": # get indicator and add it to top layer
                    for v in varsorted[0]:
                        if v.id == int(sp[1][1:]): break
                    for ir in varsorted[2]:
                        if ir.indName == v.indName and ir.args == v.args:
                            toplay.append(("i", ir.id))
                            break
                elif u[1] == "e":
                    toplay.append(("e", int(sp[1][1:])))
            
            calc = [] # order of calculation
            for t in range(len(toplay)):
                deps = []
                temp = ["v", "e", "i"]
                downTree(toplay[t][0], toplay[t][1], varsorted[temp.index(toplay[t][0])][find(toplay[t][0], toplay[t][1])])
                deps.reverse()
                for d in deps: 
                    if d not in calc: calc.append(d[:2])
            
            if ind != -1: self.strategies[ind]["risk"][2] = calc
        else:
            calc = risk[2]

        if stock == -1: stock = self.rawind # incase no stock is given, assume the base stock is used

        # get variable values for risk | get full list so that values only need to be gotten once
        for vs in varsorted: # reset all values
            for v in vs:
                v.val = None
        vals = []
        # time will keep track of time
        for time in range(len(raw[stock])):
            #ended = False # will keep track whether a stop was initiated
            for c in calc:
                if c[0] == "i": # indicator
                    var = varsorted[2][find("i", c[1])]
                    # for a in var.args:
                    #     if "%" in str(a): var.val = None # recalculate everytime a variable is an argument
                    if not indinfo[var.indName]["once"] or var.val is None: # value needs to be calculated
                        # if once is true, get entire list and just adjust based on spot instead of calculating over and over again

                        if indinfo[var.indName]["once"]: out = indicator(stock, var.indName, var.args, len(raw[stock])-1)
                        else: out = indicator(stock, var.indName, var.args, time)
                        if isinstance(out, tuple): # if multiple values were given
                            temp = []
                            for o in out:
                                temp.append(o)
                            out = temp
                        else: out = [out]
                        if indinfo[var.indName]["existcheck"]: # if existcheck also adjust exist expression
                            out = out[1:]
                        # distribute variables to children variables
                        var.val = out
                        for va in varsorted[0]:
                            if va.indName == var.indName and va.args == var.args:
                                va.val = out[indinfo[var.indName]["vars"].index(va.var)]
                elif c[0] == "e": # equation
                    var = varsorted[1][find("e", c[1])]
                    args = deepcopy(var.args)
                    for a in args:
                        if "|" in str(a): # if multiple variables
                            sps = a.split("|")
                            doList = True
                            args[args.index(a)] = []
                        else: 
                            sps = [a]
                            doList = False
                        if "%" in str(a):
                            for spsps in sps:
                                sp = spsps.split("%")
                                if len(sp) == 2: sp.append("") # to allow full value returns
                                if not isint(sp[1]) and sp[1] != "": # if variable in str
                                    temp = ["v", "e"]
                                    i = temp.index(sp[1][0])
                                    var2 = varsorted[i][find(sp[1][0], int(sp[1][1:]))]
                                    if sp[1][0] == "e": # get original variable and value from it
                                        if doList:
                                            args[args.index(a)].append(var2.val)
                                        else:
                                            args[args.index(a)] = var2.val 
                                    else: # also check for spot in variable
                                        multi = []
                                        if indinfo[var2.indName]["vtypes"][indinfo[var2.indName]["vars"].index(var2.var)] == list: # if list check for spot
                                            # check whether spot is variable or int
                                            if not isint(sp[2]) and sp[2] != "": # variable for spot
                                                # can only be int variable or equation
                                                multi = []
                                                if "," in sp[2]: # means range with either numbers or ! for variables
                                                    ranges = sp[2].split(",")
                                                    for r in ranges:
                                                        if not isint(r): # variable for range
                                                            i = temp.index(r[0]) 
                                                            multi.append(varsorted[i][find(r[0], int(r[1:]))].val)
                                                        else:
                                                            multi.append(int(r))
                                                    for m in range(len(multi)):
                                                        multi[m] = int(multi[m])
                                                        if multi[m] > time or multi[m] < -time-1: multi[m] = "nan"
                                                        elif multi[m] < 0: # convert from total scale to truncated scale bc of time
                                                            multi[m] = time + multi[m] + 1
                                                    multi.sort()
                                                    multi[1] += 1 # to get correct range
                                                else:
                                                    i = temp.index(sp[2][0]) 
                                                    spot = varsorted[i][find(sp[2][0], int(sp[2][1:]))].val
                                            elif isint(sp[2]): spot = int(sp[2])
                                            if sp[2] != "":
                                                if len(multi) == 0:
                                                    # convert spot to correct one with time | if spot incorrect make args to nan
                                                    if spot > time or spot < -time-1: spot = "nan"
                                                    elif spot < 0: # convert from total scale to truncated scale bc of time
                                                        spot = time + spot + 1
                                                    if spot != "nan": val = var2.val[spot]
                                                    else: val = float("nan")
                                                    if doList:
                                                        args[args.index(a)].append(val)
                                                    else: args[args.index(a)] = val
                                                else: 
                                                    if float("nan") in multi: # if an invalid argument was given
                                                        args[args.index(a)] = []
                                                    else:
                                                        args[args.index(a)] = var2.val[multi[0]:multi[1]]
                                            else:
                                                args[args.index(a)] = var2.val # take entire thing
                                        else: # just take value
                                            args[args.index(a)] = var2.val

                    out = equation(var.type, args)
                    var.val = out
            # assume all variables are already calculated and get risk for timeslot
            vals.append([])
            for r in risk[0]:
                if type(r) != list:
                    if "%" in str(r):
                        t = r[1]
                        temp = ["v", "e"]
                        if t == "v": # also use spot
                            sp = r.split("%")
                            v = varsorted[0][find(t, int(sp[1][1:]))]
                            spot = int(sp[2])
                            if spot < 0: spot = time+spot+1
                            vals[-1].append(v.val[spot])
                        else:
                            vals[-1].append(varsorted[1][find(t, int(r[2:]))].val)
                    else: vals[-1].append(r)
                else:
                    vals[-1].append([])
                    for rr in r:
                        if "%" in str(rr):
                            t = rr[1]
                            temp = ["v", "e"]
                            if t == "v": # also use spot
                                sp = rr.split("%")
                                v = varsorted[0][find(t, int(sp[1][1:]))]
                                spot = int(sp[2])
                                if spot < 0: spot = time+spot+1
                                vals[-1][-1].append(v.val[spot])
                            else:
                                vals[-1][-1].append(varsorted[1][find(t, int(rr[2:]))].val)
                        else: vals[-1][-1].append(rr)
            
            if once: return
        
        return vals

    def backtest(self, ind): # backtest strategy of id
        time = 0
        stock = self.systems[self.currentSystem].rawind # current viewed stock
        static = not self.getRisk(ind, getRecalc=True) # whether risk calculations have to only be done once per stock
        risk = self.getRisk(ind, once=static) # will return either a static len == 1 list or a len == len(stock)
        startmoney = risk[0][0] # balance
        stoptype = risk[0][1] # what kind of operation will be started
        stopvals = risk[0][2]
        amnt = int(ceil(risk[0][3]/raw[stock][0][3]))
        fees = risk[0][4]
        starterror = False
        if startmoney < 0: starterror = True
        operations = []
        money = startmoney
        timeframe = len(raw[stock])-1
        self.entexs = [[], [], [], []] # [ent, ext, extpercs, liqmoney] | entries, exits, exitpercentages and liquid money
        while time < timeframe: # timeframe for stock simulation
            if starterror: break # if something went wrong in the risk values; dont start
            error = False
            if not static:
                startmoney = risk[time][0] # balance
                stoptype = risk[time][1] # what kind of operation will be started
                stopvals = risk[time][2]
                amnt = int(ceil(risk[time][3]/raw[stock][0][3]))
                fees = risk[time][4]
                error = False
                if startmoney < 0: error = True
                if stoptype == "Trailing Stop" and stopvals < 0:  error = True
                if stoptype == "Stop Limit":
                    if stopvals[0] > raw[stock][time][3] or stopvals[1] < raw[stock][time][3]: # if stop above price or limit below price
                        error = True
                if risk[time][3] < 0 or risk[time][3] > startmoney: error = True
                if fees < 0: error = True
            if not error:
                poplist = [] # operations that have finished
                for op in operations:
                    if op.type == "Stop Limit":
                        if raw[op.ind][time][3] <= op.stop: # if stop loss is reached
                            money += op.sell(time)
                            poplist.append(operations.index(op))
                        elif raw[op.ind][time][3] >= op.take: # if take profit is reached
                            money += op.sell(time)
                            poplist.append(operations.index(op))
                    else: # trailing stop
                        if raw[op.ind][time][3]*(1-op.trai) > op.stopprice: op.stopprice = raw[op.ind][time][3]*(1-op.trai) # if price went up, follow price
                        elif raw[op.ind][time][3] <= op.stopprice: # if price went down and touched stopprice
                            money += op.sell(time)
                            poplist.append(operations.index(op))
                poplist.reverse() # reverse list, so that later indexes are removed first
                sold = False
                for p in poplist: # remove finished operations
                    if operations[p].type != "Stop Limit":
                        self.entexs[2].append((time, 100*(operations[p].stopprice/(fees+operations[p].buyprice)-1))) # append exitprc using trailing stop, time and buy price
                    else: # stop limit
                        self.entexs[2].append((time, 100*(raw[operations[p].ind][time][3]/(fees+operations[p].buyprice)-1))) 
                    sold = True # if operation is removed; something is sold
                    operations.pop(p)
                
                bought = False
                if self.strategies[ind]["data"][time]: # if strategy here is true
                    if money >= fees+amnt*raw[stock][time][3]: 
                        bought = True
                        money -= fees+amnt*raw[stock][time][3] # subtract money
                        if stoptype == "Trailing Stop": 
                            operations.append(Operation(stock, "Trailing Stop", amnt, time, perc=stopvals, fee=fees)) # append 1% trailing stop operation
                        else: # stop limit
                            operations.append(Operation(stock, "Stop Limit", amnt, time, stlo=stopvals[0], tapr=stopvals[1], fee=fees))
                self.entexs[0].append(bought) # same as marked but for entries / exits
                self.entexs[1].append(sold)
                time += 1
                liquidtotal = money
                for o in operations: # for each operation add how much they would give if sold right now
                    liquidtotal += o.amnt*raw[stock][time][3]
                self.entexs[3].append(liquidtotal/startmoney) # append percentage of money made
        for o in operations:
            money += o.sell(time)
        operations = []

        # set stats
        self.stats.active = True
        self.stats.money = money
        self.stats.details = []
        succ = 0 # positive exits/ num exits
        for e in self.entexs[2]: # get number of positive exits
            if e[1] > 0: succ += 1
        if len(self.entexs[2]) != 0: succ /= len(self.entexs[2]) # get percentage of positive exits
        else: succ = 0
        sf = [0, 0] # sum of success percentages/ sum of failure percentages
        for e in self.entexs[2]:
            if e[1] > 0: sf[0] += e[1] # successes
            else: sf[1] += e[1] # failures
        # if sf[1] != 0: sf = sf[0]/abs(sf[1])
        # else: sf = sf[0]
        # set starting values
        self.stats.succ = succ
        self.stats.sf = sf
        self.stats.progress = 100/len(stocks) # set progress to 100%
        self.stats.processed = 1 

    def backthread(self, ind, queue): # function run by each backthread
        global raw
        back = self.backthreads[ind] # shortcut for convenience
        #elapsed = now() # get time when function is called
        back.condata = []
        for c in back.conds:
            back.condata.append([]) # make empty list for condition data
        
        # where to get chart data from
        uselive = False
        avstocks = stocks
        if len(back.prefs) != 0: # if live data
            if back.prefs[2] == "":
                global sp500
                table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies') # get s&p 500 tickers
                df = table[0]
                sp500 = df["Symbol"].to_list()
                avstocks = sp500 # use s&p 500 tickers
                uselive = True
            else:
                uselive = True
                if back.prefs[2].count("/") > back.prefs[2].count("\\"): count = back.prefs[2].count("/") # a filepath should contain at least one / or \
                else: count = back.prefs[2].count("\\")
                if count >= 1: isFile = True
                else: isFile = False
                if isFile:
                    try:
                        with open(back.prefs[2]) as file:
                            lines = file.readlines()
                        
                        # preprocess strings
                        final = []
                        for line in lines:
                            st = ""
                            for s in line:
                                if s not in " \n": # keep everything except space and linebreak
                                    st += s
                            spl = st.split(",")
                            for s in spl:
                                if len(s) != 0:
                                    final.append(s)
                        avstocks = final
                    except: # if file doesnt exist use preexisting stocks
                        uselive = False
                    
                else:
                    spl = back.prefs[2].split(",")
                    while "" in spl: # remove empty strings from list
                        spl.remove("")
                

        # for multiprocessing
        if "__name__" != "__main__":
            raw = [[]]
            back.rawind = 0

        def getData(ind): # redefine getdata to deglobalize variables
            # ind is index of condition in back.conds
            cind = self.find("c", back.conds[ind][1])
            if len(self.conditions[cind]["deps"]) == 0: # if indicator condition
                if len(back.condata[ind]) == 0: # check if data has not been calculated
                    dat = self.getCondtitionData(conid=self.conditions[cind]["ID"], stock=back.rawind) # change what stock is used
                    back.condata[ind] = dat
            else: # complex condition (does not check for whether underlying conditions have been calculated)
                if len(back.condata[ind]) == 0:
                    if self.conditions[cind]["deps"][1] == "not": # not only needs one condition
                        dat = []
                        # depencency data index
                        for c in back.conds:
                            if c[1] == self.conditions[cind]["deps"][0][1]:
                                indx = back.conds.index(c)
                                break

                        for d in back.condata[indx]:
                            dat.append(not d) # invert true to false and false to true
                        back.condata[ind] = dat
                    else:
                        dat = []
                        indx = []
                        for j in range(2):
                            for c in back.conds:
                                if c[1] == self.conditions[cind]["deps"][j*2][1]:
                                    indx.append(back.conds.index(c))
                                    break
                        if self.conditions[cind]["deps"][1] == "xor":
                            for d in range(len(back.condata[indx[0]])):
                                dat.append(back.condata[indx[0]][d] ^ back.condata[indx[1]][d]) # ^ is xor
                        else:
                            statement = "back.condata[indx[0]][d] " + self.conditions[cind]["deps"][1] + " back.condata[indx[1]][d]" # d0 and d1 | d0 or d1
                            for d in range(len(back.condata[indx[0]])):
                                dat.append(eval(statement))
                        back.condata[ind] = dat

        # reset values
        self.stats.succ = 0
        self.stats.sf = [0, 0]
        self.stats.progress = 0 # set progress to 100%
        self.stats.processed = 0

        while back.rawpoint < len(avstocks) -1:
            # get raw data
            priceavg = 0
            if not uselive: raw[back.rawind] = read(avstocks[back.rawpoint])
            else: # use live data
                raw[back.rawind] = stock_data(avstocks[back.rawpoint], period=back.prefs[0], interval=back.prefs[1])[0]
                if len(raw[back.rawind]) != 0 and raw[back.rawind][0] == "Delisted":
                    raw[back.rawind] = []
            if len(raw[back.rawind]) != 0: # not nothing has been loaded
                priceavg = [100000, 0] # low, high
                for i in raw[back.rawind]:
                    if i[2] < priceavg[0]: priceavg[0] = i[2]
                    if i[1] > priceavg[1]: priceavg[1] = i[1]
                priceavg = (priceavg[0]+priceavg[1])/2 # avg price for stock
                # get condition data
                for c in back.conds:
                    back.condata[back.conds.index(c)] = [] # reset
                i = -1
                while i != len(back.conds)-1: # while not all conditions were calculated
                    i = len(back.conds)-1 # total amnt calculated
                    for c in back.conds: # preinit
                        ind = self.find("c", c[1]) # index
                        if c[0] == "ci": # for indicator condition
                            getData(back.conds.index(c))
                        elif c[0] == "cc": # complex condition
                            if self.conditions[ind]["deps"][1] == "not": # way more easily to only do one
                                if self.conditions[ind]["deps"][0][0] == "ci":
                                    for cc in back.conds: # get index 
                                        if cc[1] == self.conditions[ind]["deps"][0][1]:
                                            indx = back.conds.index(cc)
                                            break
                                    getData(indx) # if indicator, just calculate ci and then cc
                                    getData(back.conds.index(c)) # cc data
                                else:
                                    for cc in back.conds: # get index 
                                        if cc[1] == self.conditions[ind]["deps"][0][1]:
                                            indx = back.conds.index(cc)
                                            break
                                    if len(back.condata[indx]) != 0: # if underlying condition has been calculated
                                        getData(back.conds.index(c))
                                    else: i -= 1 # say that this one hasn't been calculated
                            else:
                                if self.conditions[ind]["deps"][0][0] == "ci" and self.conditions[ind]["deps"][2][0] == "ci": # both are indicator conditions
                                    for j in range(2): 
                                        for cc in back.conds: # get index 
                                            if cc[1] == self.conditions[ind]["deps"][j*2][1]:
                                                indx = back.conds.index(cc)
                                                break
                                        getData(indx)
                                    getData(back.conds.index(c))
                                elif self.conditions[ind]["deps"][0][0] == "cc" and self.conditions[ind]["deps"][2][0] == "cc": # both are complex conditions
                                    temp = []
                                    for j in range(2): 
                                        for cc in back.conds: # get index 
                                            if cc[1] == self.conditions[ind]["deps"][j*2][1]:
                                                temp.append(back.conds.index(cc))
                                                break # get indexes of both underlyers
                                    if len(back.condata[temp[0]]) != 0 and len(back.condata[temp[1]]) != 0: # if both are loaded
                                        getData(back.conds.index(c))
                                    else: i -= 1
                                else: # ci and cc
                                    if self.conditions[ind]["deps"][0][0] == "cc": # figure out which is cc
                                        for cc in back.conds: # get index 
                                            if cc[1] == self.conditions[ind]["deps"][0][1]:
                                                indx = back.conds.index(cc)
                                                break
                                        temp = (0, indx)
                                    else: 
                                        for cc in back.conds: # get index 
                                            if cc[1] == self.conditions[ind]["deps"][2][1]:
                                                indx = back.conds.index(cc)
                                                break
                                        temp = (1, indx) # get id of complex condition
                                    for cc in back.conds: # get index of ci
                                        if cc[1] == self.conditions[ind]["deps"][int(abs(temp[0]-1)*2)][1]:
                                            indx = back.conds.index(cc)
                                            break
                                    getData(indx) # get data from the ci
                                    if len(back.condata[temp[1]]) != 0:
                                        getData(back.conds.index(c))
                                    else: i -= 1

                back.data = []
                temp = False # already something in data
                for c in back.conds: # calculate final activation
                    ind = back.conds.index(c)
                    if back.calc[ind]: # if contition is part of final calculation
                        for i in range(len(raw[back.rawind])): 
                            if not temp: # if first, only append data
                                back.data.append(back.condata[ind][i])
                            else: # else check for and so that all conditions have to be true
                                back.data[i] = back.data[i] and back.condata[ind][i]
                        temp = True
                
                if len(back.data) == 0: # if data is empty create full false list
                    for i in range(len(raw[back.rawind])): back.data.append(False)
            
                # global time, money, operations
                time = 0
                stock = back.rawind # current viewed stock
                static = not self.getRisk(risk=back.risk, getRecalc=True, stock=stock) # whether risk calculations have to only be done once per stock
                risk = self.getRisk(risk=back.risk, once=static, stock=stock) # will return either a static len == 1 list or a len == len(stock)
                startmoney = risk[0][0] # balance
                stoptype = risk[0][1] # what kind of operation will be started
                stopvals = risk[0][2]
                amnt = int(ceil(risk[0][3]/raw[stock][0][3]))
                fees = risk[0][4]
                starterror = False
                if startmoney < 0: starterror = True
                back.operations = []
                money = startmoney
                timeframe = len(back.data)
                back.entexs = [[], [], [], []] # [ent, ext, extpercs, liqmoney] | entries, exits, exitpercentages and liquid money
                while time < timeframe: # timeframe for stock simulation
                    if starterror: break # if something went wrong in the risk values; dont start
                    error = False
                    if not static:
                        startmoney = risk[time][0] # balance
                        stoptype = risk[time][1] # what kind of operation will be started
                        stopvals = risk[time][2]
                        amnt = int(ceil(risk[time][3]/raw[stock][0][3]))
                        fees = risk[time][4]
                        if startmoney < 0: error = True
                        if stoptype == "Trailing Stop" and stopvals < 0:  error = True
                        if stoptype == "Stop Limit":
                            if stopvals[0] > raw[stock][time][3] or stopvals[1] < raw[stock][time][3]: # if stop above price or limit below price
                                error = True
                        if risk[time][3] < 0 or risk[time][3] > startmoney: error = True
                        if fees < 0: error = True
                    if not error:
                        poplist = []
                        for op in back.operations:
                            if op.type == "Stop Limit":
                                if raw[op.ind][time][3] <= op.stop: # if stop loss is reached
                                    money += op.sell(time)
                                    poplist.append(back.operations.index(op))
                                elif raw[op.ind][time][3] >= op.take: # if take profit is reached
                                    money += op.sell(time)
                                    poplist.append(back.operations.index(op))
                            else: # trailing stop
                                if raw[op.ind][time][3]*(1-op.trai) > op.stopprice: op.stopprice = raw[op.ind][time][3]*(1-op.trai) # if price went up, follow price
                                elif raw[op.ind][time][3] <= op.stopprice: # if price went down and touched stopprice
                                    money += op.sell(time)
                                    poplist.append(back.operations.index(op))
                        poplist.reverse() # reverse list, so that later indexes are removed first
                        sold = False
                        for p in poplist: # remove finished operations
                            if back.operations[p].type != "Stop Limit": # append exitprc using trailing stop, time and buy price
                                back.entexs[2].append((time, 100*(back.operations[p].stopprice/(fees+back.operations[p].buyprice)-1))) 
                            else: # stop limit
                                back.entexs[2].append((time, 100*(raw[back.operations[p].ind][time][3]/(fees+back.operations[p].buyprice)-1))) 
                            sold = True # if operation is removed; something is sold
                            back.operations.pop(p)
                        
                        bought = False
                        if back.data[time]: # if strategy here is true
                            if money >= fees+amnt*raw[stock][time][3]: # if buyable
                                bought = True
                                money -= fees+amnt*raw[stock][time][3] # subract money
                                if stoptype == "Trailing Stop":
                                    back.operations.append(Operation(stock, "Trailing Stop", amnt, time, perc=stopvals, fee=fees)) # append 1% trailing stop operation
                                else: # stop limit
                                    back.operations.append(Operation(stock, "Stop Limit", amnt, time, stlo=stopvals[0], tapr=stopvals[1], fee=fees))
                        back.entexs[0].append(bought) # same as marked but for entries / exits
                        back.entexs[1].append(sold)
                        liquidtotal = money
                        for o in back.operations: # for each operation add how much they would give if sold right now
                            liquidtotal += o.amnt*raw[stock][time][3]
                        back.entexs[3].append(liquidtotal/startmoney) # append percentage of money made
                        time += 1
                for o in back.operations:
                    money += o.sell(time)
                back.operations = []

                # set stats
                self.stats.active = True
                succ = 0 # positive exits, num exits
                for e in back.entexs[2]: # get number of positive exits
                    if e[1] > 0: succ += 1
                if len(back.entexs[2]) != 0: succ /= len(back.entexs[2]) # get percentage of positive exits
                else: succ = 0
                sf = [0, 0] # sum of success percentages/ sum of failure percentages
                for e in back.entexs[2]:
                    if e[1] > 0: sf[0] += e[1] # successes
                    else: sf[1] += e[1] # failures
                # if sf[1] != 0: sf = sf[0]/abs(sf[1])
                # else: sf = sf[0]
                self.stats.succ += succ
                self.stats.sf[0] += sf[0]
                self.stats.sf[1] += sf[1]
                self.stats.progress += 100/len(avstocks)
                if len(back.entexs[2]) != 0: self.stats.processed += 1 # if nothing was traded then dont add to denominator
            else: # if nothing was loaded then just add normal progress
                succ = 0 # positive exits, num exits
                sf = 0
                #self.stats.succ += succ
                self.stats.progress += 100/len(avstocks)
                #self.stats.processed += 1
            outs = [self.stats] # if further things need to be passed in
            self.stats.details.append({"success": succ, "rawind":back.rawpoint, "price":priceavg, "s/f":sf})
            queue.put((outs, back.ind))
            back.rawpoint += back.inc
            #print(back.rawpoint)
        self.stats.progress = 100
        self.stats.finished = True
        queue.put(([self.stats], back.ind))
        # print("Finished in ")
        # print(str(now()-elapsed) + "s.")

    def updateStrategies(self, idd, what="del"): # updates all strategies after conditions have been changed
        if what == "del": # if a condition was deleted
            poplist = []
            for s in self.strategies:
                for c in s["conds"]:
                    if c[1] == idd: poplist.append(self.strategies.index(s)) # if strategy uses deleted condition, add to poplist
            poplist.reverse()
            for p in poplist:
                self.strategies.pop(p)
            
            poplist = []
            for cc in self.conditions:
                if len(cc["deps"]) != 0: # if it's a complex condition
                    if cc["deps"][0][1] == idd: poplist.append(self.conditions.index(cc)) # if the condition uses deleted condition, add to poplist
                    elif cc["deps"][1] != "not": # if not not also check other condition
                        if cc["deps"][2][1] == idd: poplist.append(self.conditions.index(cc))
            poplist.reverse()
            for p in poplist:
                self.updateStrategies(self.conditions[p]["ID"]) # say that this condition will get deleted and check other dependencies
                self.conditions.pop(p)

    def saveStrategy(self, what=""): # saves a strategy
        if self.stratPath == "" or what == "as": # if no path for the saved file has yet been selected or save as has been selected
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save As", "", "Strategy Pickle File (*.pkl)")
            if file_path == "":
                return 
            self.stratPath = file_path
        # get every strategy in a dict
        dataDict = {}
        for s in self.strategies:
            dataDict[s["name"]] = s
        dataDict["Conditions"] = self.conditions # also store conditions
        with open(self.stratPath, 'wb') as file: 
                pickle.dump(dataDict, file)

logic = Logic() # main logic object

class GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Simulator")
        self.setWindowIcon(QtGui.QIcon(os.path.join(root_dir, "read", "Icon.ico")))
        self.setMinimumSize(800, 600)
        self.showMaximized()
        self.loading = False
        self.candles = [] # [[time, [o, h, l, c]], ...]
        self.inputs = [None, None, None, None] # placeholder for dialog line edits
        self.timeaxis = [] # will store dates
        self.moved = False # When the screen has been moved, dont activate mouse functions
        self.docks = [] # predefinition
        self.marked = [] # what spots are marked
        self.mode = QtWidgets.QComboBox() # Will keep track of current mode
        self.dialog = None # condition dialog window 
        self.tangent = None # tangent object
        self.prefs = [] # ("Name of setting", bool)
        self.queue = multiprocessing.Queue() # queue for backthreads
        self.progs = [] # list of objects used to display progress
        self.stopbackgs = False # whether to stop all background operations
        self.threads = [] # predefinition
        self.sideStats = SideStats()
        self.selected = [] # list of ids of selected conditions 
        self.generals = [None, None, None] # widgets from the general dock
        self.spots = [] # selected spots for condition seeker
        self.processes = [] # for all non backthread processes
        #self.pricerects = [None, None] # rects on x and y axis that display where exactly crosshair is pointing to
        self.debugvar = [False, -1, -1, False] # [whether debug is enabled, current rawind, stategy ind, whether to adjust to first marked]
        self.cornerBtn = WidgetContainer() # Button in bottom right corner of view to change scale
        self.tempInds = [] # list of temporaty indicators for peek | [[qgraphicsobjects]]

        self.create_widgets()

        # debug setup
        self.readstocks("0", "quick", "+")
    
    def create_widgets(self): # init function
        main = self.menuBar()

        file = main.addMenu("File")
        act = file.addAction("Open...")
        act.triggered.connect(self.open)
        act = file.addAction("Quick open...")
        act.triggered.connect(self.quickopen)
        act = file.addAction("Download...")
        act.triggered.connect(self.download)
        file.addSeparator()
        act = file.addAction("Save")
        act.triggered.connect(logic.saveStrategy)
        act = file.addAction("Save As...")
        act.triggered.connect(lambda: logic.saveStrategy("as"))
        file.addSeparator()
        act = file.addAction("Load...")
        act.triggered.connect(self.loadStrategy)
        file.addSeparator()
        act = file.addAction("Preferences...")
        act.triggered.connect(self.showPrefs)
        file.addSeparator()
        act = file.addAction("Close")
        act.triggered.connect(self.close)

        # preferences menu
        self.prefs = []
        self.prefs.append(["Calculate strategies on all available data", True])
        self.prefs.append(["Recalculate strategies after editing conditions", True])
        self.prefs.append(["Calculate strategies on live data", True])
        self.prefs.append(["Ask to name variables", False])
        self.prefs.append(["When debugging skip to next marked stock", True])

        view = main.addMenu("View")
        self.chartchecks = [] # 0 is for candlestick checkbox | 1 is for graph
        self.chartchecks.append(view.addAction("Candlestick"))
        self.chartchecks[0].setCheckable(True)
        self.chartchecks[0].setChecked(True)
        self.chartchecks[0].triggered.connect(lambda: self.chartCheck(0))
        view.addAction(self.chartchecks[0])
        self.chartchecks.append(view.addAction("Graph"))
        self.chartchecks[1].setCheckable(True)
        self.chartchecks[1].triggered.connect(lambda: self.chartCheck(1))
        view.addAction(self.chartchecks[1])
        self.chartchecks.append(view.addAction("Heikin-Ashi"))
        self.chartchecks[2].setCheckable(True)
        self.chartchecks[2].triggered.connect(lambda: self.chartCheck(2))
        view.addAction(self.chartchecks[2])
        view.addSeparator()
        act = view.addAction("Indicators...")
        act.triggered.connect(self.indicatorDialog)
        act = view.addAction("Condition Creator...")
        act.triggered.connect(self.conditionCreator)
        act = view.addAction("Strategies...")
        act.triggered.connect(self.strategyDialog)
        act = view.addAction("Unmark All")
        act.triggered.connect(self.unmarkAll)

        help = main.addMenu("Help")
        act = help.addAction("About")
        act.triggered.connect(self.about)

        self.labely = QtWidgets.QLabel("", self)
        self.labely.move(0, 300)
        self.labelx = QtWidgets.QLabel("", self)
        self.labelx.move(400, 575)

        self.gridconv = [40, 5, 40, 1] # (dx, corresponds to dt timeframes, dy, corresponds to dp price difference) 
        self.rangex = (0, 0) # timeframe
        self.rangey = (0, 0) # price range

        self.heivar = 0 

        self.draw_scene()
        
        # Add the axes widgets to a layout
        self.tabs = TabBar(self)
        self.tabs.setFn(self.tabClicked, self.tabChanged, self.deleteTab)
        self.tabs.addTab("+")
        layout1 = QtWidgets.QVBoxLayout()
        layout1.addWidget(self.view)
        layout1.addWidget(self.sview, 1) # stretch factor to make it disappear
        layout1.addWidget(self.xview)
        layout1.setSpacing(0)
        layout1.setContentsMargins(0, 0, 0, 0)
        axes_widget = QtWidgets.QWidget(self)
        axes_widget.setLayout(layout1)

        # for y axis spacing in lower right corner
        y_layout = QtWidgets.QVBoxLayout()
        y_layout.addWidget(self.yview)
        y_layout.addWidget(self.syview, 1)
        self.cornerBtn = WidgetContainer()
        self.cornerBtn.setFixedSize(35, 25)
        y_layout.setSpacing(0)
        y_layout.addWidget(self.cornerBtn)
        y_layout.setContentsMargins(0, 0, 0, 0)
        y_widget = QtWidgets.QWidget(self)
        y_widget.setLayout(y_layout)
        
        # Add the main graphics view and axes layout to the view widget
        view_layout = QtWidgets.QHBoxLayout()
        view_layout.addWidget(axes_widget)
        view_layout.addWidget(y_widget)
        view_layout.setSpacing(0)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_widget = QtWidgets.QWidget()
        view_widget.setLayout(view_layout)
        
        self.docks = []

        # create the dock widgets
        self.docks.append(QtWidgets.QDockWidget("General", self))
        self.docks[0].setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.docks[0].setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.docks[0].setStyleSheet(dockstring)
        # self.docks[0].set(QtWidgets.QFrame.Shape.WinPanel)
        for i in range(3): # set the general layouts with one single widget per
            self.generals[i] = WidgetContainer() # widgetcontainer to chanhge widget after initializing it
            self.generals[i].setWidget(QtWidgets.QWidget())
        self.generals[0].setFixedHeight(200)
        self.generals[2].setFixedHeight(200)
        wid = QtWidgets.QWidget()
        lab = QtWidgets.QLabel(wid)
        lab.setStyleSheet("border: none;")
        lab.setText("Mode")
        lab.move(2, 2)
        self.mode = QtWidgets.QComboBox(wid)
        self.mode.move(40, 2)
        self.mode.setStyleSheet("border: none;")
        self.mode.addItems(["Base Graph", "Conditions/Indicators", "Strategies"])
        self.mode.currentTextChanged.connect(self.modeChanged)
        self.generals[0].setWidget(wid)
        lay = QtWidgets.QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        for i in range(3): # pack generals in widgets and put them in the layout
            lay.addWidget(self.generals[i])
        wid = QtWidgets.QFrame()
        wid.setLayout(lay)
        wid.setStyleSheet("QFrame {border: 2px inset #A0A0A0;}")
        self.docks[0].setWidget(wid)

        side1 = QtWidgets.QMainWindow(self)
        side1.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.docks[0])
        side1.setFixedWidth(200)

        self.docks.append(QtWidgets.QDockWidget("Variables", self))
        self.docks[1].setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.docks[1].setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.docks[1].setStyleSheet(dockstring)
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        self.docks[1].setWidget(wid)

        side2 = QtWidgets.QMainWindow(self)
        side2.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.docks[1])
        side2.setFixedWidth(200)

        self.docks.append(QtWidgets.QDockWidget("Conditions", self))
        self.docks[2].setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.docks[2].setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.docks[2].setStyleSheet(dockstring)
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        self.docks[2].setWidget(wid)

        side3 = QtWidgets.QMainWindow(self)
        side3.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.docks[2])
        side3.setFixedHeight(200)

        # Graphics view + Bottom window
        big_view_layout = QtWidgets.QVBoxLayout()
        big_view_layout.addWidget(self.tabs)
        big_view_layout.addWidget(view_widget)
        big_view_layout.addWidget(side3)
        big_view_layout.setContentsMargins(0, 0, 0, 0)
        big_view_layout.setSpacing(0)
        big_widget = QtWidgets.QWidget(self)
        big_widget.setLayout(big_view_layout)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(side1)
        main_layout.addWidget(big_widget)
        main_layout.addWidget(side2)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)
    
    def tabClicked(self, event): # function that runs when the plus tab is selected
        if self.tabs.tabText(self.tabs.currentIndex()) in ["Backtest", "Exit Percentages", "Benchmark Comparison"]: return
        cont = QtWidgets.QMenu()
        act = cont.addAction("Open...")
        act.triggered.connect(lambda: self.open("+"))
        act = cont.addAction("Quickopen...")
        act.triggered.connect(lambda: self.quickopen("+"))
        act = cont.addAction("Download...")
        act.triggered.connect(lambda: self.download("+"))
        cont.exec(self.tabs.mapToGlobal(event.pos()))

    def tabChanged(self, event): # when a different tab is selected
        index = self.tabs.tabAt(event.pos())
        if index == self.tabs.currentIndex(): return # if current tab was selected, don't do anything
        if self.tabs.tabText(index) != "+" and event.button() == QtCore.Qt.MouseButton.LeftButton: # if tab is left clicked and tab is not the plus tab
            # reset focus
            self.focus.placed = False
            self.moved = False
            if self.tabs.tabText(index) in ["Backtest", "Exit Percentages", "Benchmark Comparison"]:
                self.setBackScene(self.tabs.tabText(index))
            else:
                self.mode.setEnabled(True)
                self.gridconv = deepcopy(logic.systems[index].gridconv)
                self.rangex = deepcopy(logic.systems[index].rangex)
                self.rangey = deepcopy(logic.systems[index].rangey)
                self.candles = deepcopy(logic.systems[index].candles)
                logic.rawind = logic.systems[index].rawind
                self.timeaxis = deepcopy(logic.systems[index].timeaxis)
                self.reinitIndicators()
                self.setScene()

    def newTab(self, tName="Stock"):
        tc = self.tabs.count() - 1
        self.tabs.removeTab(tc) # remove last tab (+)
        self.tabs.addTab(tName)
        self.tabs.setCurrentIndex(tc)
        self.tabs.addTab("+")  

    def deleteTab(self, index): # delete tab at cursor
        global raw
        backrem = self.tabs.tabText(index) in ["Backtest", "Exit Percentages", "Benchmark Comparison"] # whether it's a backtest being removed
        debug = "Debug" in self.tabs.tabText(index) # debug tab removed
        tup = [] # (index, rawind)
        for s in logic.systems:
            tup.append((logic.systems.index(s), s.rawind)) # get index of system and their corresponding rawids

        if index == self.tabs.currentIndex(): self.tabs.setCurrentIndex(index-1) # if current index would be removed, change current index

        if backrem:
            self.stopButton() # stop all background threads if still running
            logic.stats.active = False
            procManager.delist("backthreads")
            self.mode.setEnabled(True)
            self.resetBacktest()
            self.displayStats() # aka reset left window
            for t in range(self.tabs.count()): # check tabs if debug is also open
                if self.tabs.tabText(t).split(" ")[0] == "Debug": 
                    debug = True
                    break # t is kept as debug index
            if debug: # if debug is also open
                self.debugvar = [False, -1, -1, False]
                for tu in tup:
                    if tu[1] > logic.systems[t].rawind: # if the id is above the one deleted
                        logic.systems[tu[0]].rawind -= 1 # shift id one down
                raw.pop(logic.systems[t].rawind) # remove now unused raw
                logic.systems.pop(t) # remove debug system as well
                self.tabs.removeTab(t)
                self.tabs.setCurrentIndex(0) # set to default index
                # also always go to parent tab
            if self.tabs.tabText(self.tabs.currentIndex()) in ["Backtest", "Exit Percentages", "Benchmark Comparison"] or debug: # if backtest was selected
                self.tabs.setCurrentIndex(logic.currentSystem)
                self.gridconv = deepcopy(logic.systems[logic.currentSystem].gridconv)
                self.rangex = deepcopy(logic.systems[logic.currentSystem].rangex)
                self.rangey = deepcopy(logic.systems[logic.currentSystem].rangey)
                self.candles = deepcopy(logic.systems[logic.currentSystem].candles)
                logic.rawind = logic.systems[logic.currentSystem].rawind
                self.timeaxis = deepcopy(logic.systems[logic.currentSystem].timeaxis)
                self.reinitIndicators()
                self.setScene()
            return
        self.tabs.removeTab(index) # remove tab

        for t in tup:
            if t[1] > logic.systems[index].rawind: # if the id is above the one deleted
                logic.systems[t[0]].rawind -= 1 # shift id one down
        raw.pop(logic.systems[index].rawind) # remove now unused raw
        logic.systems.pop(index) # remove system as well

        if debug: # if debug is removed
            self.debugvar = [False, -1, -1, False] # reset debug if removed
            procManager.delist("backthreads")
            self.stopButton("backthreads")
            self.resetBacktest() # remove backtest
            self.mode.setEnabled(True)
            self.displayStats()

        # if no more stocks are loaded
        if self.tabs.tabText(self.tabs.currentIndex()) == "+": 
            self.candles = [] # reset candles
            self.marked = []
            self.setScene() # load blank scene

    def showPrefs(self): # show preferences
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Preferences")
        dbox.setFixedSize(500, 375)
        i = 0
        self.inputs[0] = []
        for pref in self.prefs:
            self.inputs[0].append(QtWidgets.QCheckBox(pref[0], dbox))
            self.inputs[0][-1].setChecked(pref[1])
            self.inputs[0][-1].setGeometry(10+(i%2)*240, 10+(i//2)*30, 230, 22)
            i += 1
        acc = QtWidgets.QPushButton("OK", dbox)
        acc.clicked.connect(lambda: self.prefProcess(dbox))
        acc.move(235, 345)
        dbox.exec()

    def prefProcess(self, parent=None): # save perferences
        for i in range(len(self.inputs[0])):
            self.prefs[i][1] = self.inputs[0][i].isChecked() # save inputs to prefs
        parent.close()

    def findPref(self, string): # return index of preference given the string
        for p in range(len(self.prefs)):
            if self.prefs[p][0] == string: return p

    def modeChanged(self): # when a different mode was selected
        if len(self.selected) != 0: # multimarking
            self.selected = []
            self.marked = []
            self.resetGeneral(1)
        elif len(self.spots) != 0: # condition seeker
            self.spots = []
            self.resetGeneral(1)
        self.setScene()
    
    def open(self, how=""): # open file dialog
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open stock data file", "", "Text files (*.txt);;All files (*.*)")[0] # get filename
        if filename == "": return # if no file was selected
        self.readstocks(filename, "open", how)

    def quickopen(self, how=""): # quick open dialogue box
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Quick open...")
        dbox.setFixedSize(150, 85)
        label1 = QtWidgets.QLabel(dbox)
        label1.setGeometry(10, 10, 85, 25)
        self.inputs[0] = QtWidgets.QLineEdit(dbox)
        self.inputs[0].setGeometry(75, 10, 50, 25)
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(40, 52)
        label1.setText("Ticker/ID")
        btn.pressed.connect(lambda: self.quickchange("quick", dbox, how))
        dbox.exec()

    def quickchange(self, what, parent, how=""): # Execute quickopen/open code
        if what == "quick": # when quickopen was run before
            self.readstocks(self.inputs[0].text(), "quick", how)
        else:
            pass
        parent.close()
    
    def download(self, how=""): # download dialog box
        self.dialog = QtWidgets.QDialog(self)
        self.dialog.setWindowTitle("Download...")
        self.dialog.setFixedSize(300, 200)
        self.dialog.setLayout(QtWidgets.QVBoxLayout())
        self.downloadLayout(how, True) # create layout
        
        self.dialog.exec()

    def downloadLayout(self, how, first=False): # layout for download dialog | for combobox change
        inp = []
        if not first: 
            cur = self.inputs[1][1].currentText()
            tik = self.inputs[0].text()
        else: 
            cur = "Dynamic"
            tik = ""
        if "Live" in self.tabs.tabText(self.tabs.currentIndex()) and how == "live":
            tik = logic.systems[logic.currentSystem].live[0]
            inp = logic.systems[logic.currentSystem].live[1:]
            if len(inp) == 7: cur = "Fixed"
            elif len(inp) == 2: cur = "Dynamic"
        wid = QtWidgets.QWidget()
        label1 = QtWidgets.QLabel("Ticker", wid)
        label1.setGeometry(10, 10, 85, 25)
        self.inputs[0] = QtWidgets.QLineEdit(tik, wid)
        self.inputs[0].setGeometry(60, 10, 50, 25)
        label2 = QtWidgets.QLabel("Period", wid)
        label2.setGeometry(10, 40, 85, 25)
        self.inputs[1] = []
        self.inputs[1].append(QtWidgets.QComboBox(wid))
        if cur == "Fixed": avail = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"] # available intervals
        else: avail = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] # available periods
        for a in avail: self.inputs[1][0].addItem(a)
        if cur == "Fixed": self.inputs[1][0].setGeometry(60, 40, 75, 23)
        else: self.inputs[1][0].move(60, 40)
        label3 = QtWidgets.QLabel(wid)
        label3.setGeometry(10, 75, 85, 25)
        avail = [2022, 1, 27] # example date
        rans = [(2000, 3000), (1, 12), (1, 31)] # ranges for the different spinboxes
        if cur == "Fixed":
            for j in range(2):
                self.inputs[2+j] = []
                for i in range(3):
                    self.inputs[2+j].append(QtWidgets.QSpinBox(wid))
                    self.inputs[2+j][-1].setGeometry(60+55*i, 75+j*40, 50, 25)
                    self.inputs[2+j][-1].setRange(rans[i][0], rans[i][1])
                    self.inputs[2+j][-1].setValue(avail[i]+j)
        else:
            lab = QtWidgets.QLabel("Interval", wid)
            lab.move(10, 75)
            self.inputs[2] = QtWidgets.QComboBox(wid)
            avail = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
            self.inputs[2].addItems(avail)
            self.inputs[2].setCurrentText("1d")
            self.inputs[2].move(60, 75)
        label4 = QtWidgets.QLabel(wid)
        label4.setGeometry(10, 115, 85, 25)
        self.inputs[1].append(QtWidgets.QComboBox(wid))
        self.inputs[1][1].addItem("Dynamic")
        self.inputs[1][1].addItem("Fixed")
        self.inputs[1][1].move(175, 10)
        self.inputs[1][1].setCurrentText(cur)
        self.inputs[1][1].currentTextChanged.connect(lambda: self.downloadLayout(how))
        btn = QtWidgets.QPushButton("OK", wid)
        btn.move(110, 160)
        if cur == "Fixed":
            label2.setText("Interval")
            label3.setText("Start")
            label4.setText("End")
            if len(inp) != 0:
                i = 0
                for ip in inp[:-1]:
                    self.inputs[2+i//3][i%3].setValue(int(ip))
                    i += 1
                self.inputs[1][0].setCurrentText(inp[-1])
        else:
            if len(inp) != 0:
                self.inputs[1][0].setCurrentText(inp[0])
                self.inputs[2].setCurrentText(inp[1])
        btn.pressed.connect(lambda: self.downloadChange(self.dialog, how))
        
        lay = self.dialog.layout()
        while lay.count(): # delete all widgets currently in use
            w = lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        lay.addWidget(wid)
        #lay.addWidget(btn)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.dialog.setLayout(lay) # sets layout of dbox

    def downloadChange(self, parent, how=""): # download data and load scene
        global raw
        st = self.inputs[0].text().upper() + ","
        if self.inputs[1][1].currentText() == "Fixed": # fixed date procedure
            try:
                start = dt.datetime(self.inputs[2][0].value(), self.inputs[2][1].value(), self.inputs[2][2].value())
                end = dt.datetime(self.inputs[3][0].value(), self.inputs[3][1].value(), self.inputs[3][2].value())
            except ValueError:
                self.errormsg("Date is invalid.")
                return
            if start > end: 
                self.errormsg("Start date is more recent than end date.")
                return
            if self.inputs[1][0].currentText() == "1m": # 1 Minute
                if start < dt.datetime.now() - dt.timedelta(days=30):
                    self.errormsg("Date range too big. (Maximum = 30)")
                    return
                elif end-start > dt.timedelta(days=7):
                    self.errormsg("Only 7 consecutive days allowed.")
                    return
            elif self.inputs[1][0].currentText() == "15m": # 15 Minutes
                if start < dt.datetime.now() - dt.timedelta(days=60):
                    self.errormsg("Date range too big. (Maximum = 60)")
                    return
            elif self.inputs[1][0].currentText() == "1h": # 1 hour
                if start < dt.datetime.now() - dt.timedelta(days=730):
                    self.errormsg("Date range too big. (Maximum = 730)")
                    return
            for j in range(2):
                for i in range(3):
                    st += str(self.inputs[2+j][i].value()) + ","
            st += self.inputs[1][0].currentText()
            red, dat = stock_data(self.inputs[0].text(), start, end, self.inputs[1][0].currentText()) # get data and date
        else:
            avail1 = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"] # available intervals
            if self.inputs[1][0].currentText() == "ytd":
                inv = self.inputs[2].currentText()
                comps = avail1[:avail1.index("60m")] # make interval range
                if inv in comps:
                    self.errormsg("Interval too small for period.")
                    return
            elif self.inputs[1][0].currentText() == "max":
                inv = self.inputs[2].currentText()
                comps = avail1[:avail1.index("1d")] # make interval range
                if inv in comps:
                    self.errormsg("Interval too small for period.")
                    return
            else:
                if self.inputs[1][0].currentText()[-1] == "d": # day range
                    if self.inputs[2].currentText() in avail1[avail1.index("1d"):]:
                        self.errormsg("Interval too big for period.")
                        return
                elif self.inputs[1][0].currentText()[-1] == "o": # month range
                    inv = self.inputs[2].currentText()
                    comps = avail1[:avail1.index("60m")] # make interval range
                    if inv in comps:
                        self.errormsg("Interval too small for period.")
                        return
                else: # year range
                    if int(self.inputs[1][0].currentText()[:-1]) <= 2: # max 2 years
                        if self.inputs[2].currentText() in avail1[:avail1.index("1h")]:
                            self.errormsg("Interval too small for period.")
                            return
                    else: # above 2 years
                        if self.inputs[2].currentText() in avail1[:avail1.index("1d")]:
                            self.errormsg("Interval too small for period.")
                            return
                st += self.inputs[1][0].currentText() + "," + self.inputs[2].currentText()
            red, dat = stock_data(self.inputs[0].text(), period=self.inputs[1][0].currentText(), interval=self.inputs[2].currentText())
        if len(red) == 1:
            if type(red[0]) == str:
                self.errormsg(self.inputs[0].text() + " hasn't been found.")
                return
        elif len(red) == 0:
            self.errormsg("Range too big or ticker not found.")
            return
        self.timeaxis = dat
        if how == "+":
            raw.append(red)
        else: raw[logic.rawind] = red
        self.newScene(how, "Live " + self.inputs[0].text().upper(), st)
        parent.close()

    def chartCheck(self, who): # will control the checkboxes of the chart in view menu
        if self.tabs.tabText(self.tabs.currentIndex()) in ["Backtest", "Exit Percentages", "Benchmark Comparison"]: # if backtest tab open
            # reverse check
            self.chartchecks[who].setChecked(not self.chartchecks[who].isChecked())
            return
        if not self.chartchecks[who].isChecked(): # reverse
            if who == 0:
                self.chartchecks[0].setChecked(False)
                self.chartchecks[1].setChecked(True)
            else:
                self.chartchecks[0].setChecked(True)
                self.chartchecks[who].setChecked(False)
        else: # if not checked; uncheck the one checked
            for c in self.chartchecks:
                if c.isChecked(): c.setChecked(False)
            self.chartchecks[who].setChecked(True)
        self.setScene()
    
    def cornerSet(self, visible): # sets the corner button to either visible or not
        if visible:
            btn = QtWidgets.QPushButton("⚙")
            btn.clicked.connect(lambda: self.download("live"))
            btn.setStyleSheet(widgetstring)
            self.cornerBtn.setWidget(btn)
        else:
            self.cornerBtn.setWidget(QtWidgets.QWidget()) # blank widget

    def pickColor(self): # color dialog
        sender = self.sender()
        # Open the color picker dialog and get the selected color
        color = QtWidgets.QColorDialog.getColor()

        # If the user selected a color, update the button's background color
        if color.isValid():
            sender.setStyleSheet("background-color: %s;" % color.name())


    def ctrlButton(self, event, idd, typ): # pass method to check whether ctrl is pressed before
        # idd is id of object of button and typ is type of object of button (i, c, s)
        if self.tabs.tabText(self.tabs.currentIndex()) == "+":
            self.errormsg("Please load a stock first.")
            return
        if event.modifiers().name == "ControlModifier": # execute multi marking
            if typ == "c":
                ind = logic.find("c", idd) 
                if len(logic.conditions[ind]["data"]) == 0: # if data hasn't yet been loaded
                    logic.getCondtitionData(conid=idd) # dont check for complex because it can only be indicator
                if idd not in self.selected: # if the button wasn't already selected
                    self.selected.append(idd)
                else: # if button has already been selected; remove from list
                    self.selected.remove(idd)
                self.multiMark()
                if len(self.selected) == 0: self.resetGeneral(1) # if nothing is selected anymore; reset
                else: self.multiShow() # update side window
            elif typ == "i":
                # reverse show
                logic.indicators[logic.find("i", idd)]["show"] = not logic.indicators[logic.find("i", idd)]["show"]
            elif typ == "s":
                data = logic.strategies[logic.find("s", idd)]["data"]
                self.marked = []
                for d in data:
                    if d: self.marked.append("#40ff7700")
                    else: self.marked.append(None)
            self.setScene()
        else: # default dialog
            if typ == "c": self.conditionCreator(idd) 
            elif typ == "i": self.indicatorDialog(idd)
            elif typ == "s": self.strategyDialog(idd)

    def selectButton(self, event, idd=0, typ="c"): # pass method to check whether ctrl is pressed before
        if event.modifiers().name == "ControlModifier": # reverse activation of marking
            pass # maybe add reverse activation here
        else: # remove selected indicator from list
            self.selected.remove(idd) # remove index from selected list
            self.multiMark() # change what is marked
            if len(self.selected) == 0: self.resetGeneral(1) # if nothing is selected anymore; reset
            else: self.multiShow() # update side window
            self.setScene()

    def conditionCreator(self, idd=-1): # will later replace original conditon dialog
        if self.tabs.tabText(self.tabs.currentIndex()) == "+": 
            self.errormsg("Please load a stock first.")
            return
        # idd is id of condition edited; -1 means no condition is edited
        self.dialog = QtWidgets.QDialog(self)
        self.dialog.setWindowTitle("Condition Creator")
        self.dialog.setFixedSize(630, 400)
        self.dialog.setLayout(QtWidgets.QVBoxLayout())
        if type(idd) == int and idd != -1: ind = logic.find("c", idd)
        else: ind = -1
        self.conditionCreatorLayout(True, ind)
        self.dialog.exec()

    def conditionCreatorLayout(self, first=False, ind=-1): # layout for condion creator
        # ind is index of condition edited
        if type(ind) != int: ind = -1
        olds = [] # old current texts from inputs[0]
        its = [[], [], [], []] # item texts (temporary)
        olvars = [] # old vars from drag boxes
        vind = -1 # index of last vars
        savs = [] # activation of buttons
        olvw = None # old view
        color = None
        mode = True # true means advanced and false means simplified
        modechanged = False # whether the mode was changed
        filtrrs = ["True", "First True", "Last True", "Near", "Advanced..."] # will keep track of filters

        if not first:
            if type(self.inputs[0]) == list: # advanced mode
                for inp in self.inputs[0]:
                    olds.append(inp.currentText())
                inds = [1, 2, 5, 6]
                for i in inds:
                    its[inds.index(i)] = [self.inputs[0][i].itemText(indx) for indx in range(self.inputs[0][i].count())]
                olvars = [self.inputs[0][1].vars, self.inputs[0][2].vars, self.inputs[0][5].vars, self.inputs[0][6].vars]
                vind = 0
                for b in self.inputs[2]:
                    savs.append(b.active)
                olvw = []
                for i in range(2):
                    olvw.append([])
                    olvw[i].append(self.inputs[3][i].rangex) # 0
                    olvw[i].append(self.inputs[3][i].rangey) # 1
                    olvw[i].append(self.inputs[3][i].gridconv) # 2
                    olvw[i].append(self.inputs[3][i].candles) # 3
                    olvw[i].append(self.inputs[3][i].scene()) # 4
                    olvw[i].append(self.inputs[3][i].ind)
                color = self.inputs[3][3].styleSheet().split(" ")[1][:-1]
                filtrrs = [self.inputs[3][5].itemText(indx) for indx in range(self.inputs[3][5].count())]
                filters = [self.inputs[3][4].text(), self.inputs[3][5].currentText()]
                mode = self.inputs[3][6].isChecked()
                if not mode: modechanged = True
            else: # simplified mode
                mode = self.inputs[0].isChecked()
                olvars = self.inputs[1].vars
                color = self.inputs[2][0].styleSheet().split(" ")[1][:-1]
                filtrrs = [self.inputs[2][2].itemText(indx) for indx in range(self.inputs[2][2].count())]
                filters = [self.inputs[2][1].text(), self.inputs[2][2].currentText()]
                if mode: modechanged = True
        wid = QtWidgets.QWidget()
        if mode: # if advanced
            if modechanged: # if last mode was simplified
                # split vars into seperate lists
                variables = [[], [], [], []] # 0 is v, 1 is e, 2 is x, 3 is i 
                # unpack variables into different types
                for var in olvars:
                    if type(var) == IndicatorVariable:
                        if var.var == "": variables[3].append(var) # indicator
                        else: variables[0].append(var)
                    elif type(var) == VariableEquation: variables[1].append(var)
                    elif type(var) == VariableExpression: variables[2].append(var)
                olvars = variables
                vind = 0
                i = 0
                for i in range(4):
                    j = 0
                    for v in variables[i]:
                        if i != 0 and i != 3: its[i].append(v.name)
                        elif i == 0: its[i].append(v.var)
                        else:
                            its[i].append(indargs[v.indName]["name"] + " " + str(j))
                        #its[i].vars.append(v)
                        j += 1
                    i += 1
            QtWidgets.QLabel("Add an Indicator", wid).move(311, 16)
            self.inputs[0] = []
            self.inputs[0].append(QtWidgets.QComboBox(wid))
            for i in avinds:
                self.inputs[0][0].addItem(indargs[i]["name"])
            currind = "ohlcv"
            if len(olds) != 0:
                self.inputs[0][0].setCurrentText(olds[0])
                for key in avinds: # find key corresponding to combobox text
                    if indargs[key]["name"] == olds[0]: break
                currind = key
            self.inputs[0][0].setGeometry(311, 32, 120, 22)
            self.inputs[0][0].currentTextChanged.connect(lambda: self.creatorNewLayout("ip"))
            self.inputs[2] = []
            self.inputs[2].append(EdSaveBtn("Add", wid))
            self.inputs[2][0].setGeometry(437, 32, 73, 23)
            sav = False
            if len(savs) != 0:
                if savs[0]:
                    self.inputs[2][0].setActive()
                    self.inputs[2][0].setText("Save")
                sav = savs[0]
            if sav: self.inputs[2][0].clicked.connect(lambda: self.addButton("Indicator", True))
            else: self.inputs[2][0].clicked.connect(lambda: self.addButton("Indicator"))
            self.inputs[1] = [[], [], []]
            for i in range(len(indargs[currind]["args"])):
                QtWidgets.QLabel(indargs[currind]["args"][i][0], wid).move(311+100*i, 61)
                self.inputs[1][0].append(Slot(wid, self.dropBox))
                self.inputs[1][0][i].setGeometry(311+100*i, 77, 35, 22)
                self.inputs[1][0][i].setText(str(indargs[currind]["args"][i][1]))
                self.inputs[1][0][i].textEdited.connect(lambda: self.creatorNewLayout("ic"))
            self.inputs[3] = []
            self.inputs[3].append(SmallView(wid)) # big window
            self.inputs[3][0].setGeometry(311, 126, 300, 200)
            if first or modechanged:
                self.inputs[3][0].ind = ind
                self.inputs[3][0].scene().setSceneRect(0, 0, 290, 190)
                grid = Grid(QtCore.QRectF(-5, -5, 300, 200))
                grid.density = (10, 10)
                self.inputs[3][0].scene().addItem(grid)
                # dummy candles
                if len(presets[0]) == 0:
                    cans = []
                    op = 25000
                    for i in range(300):
                        vals = []
                        lh = [randint(op-500, op+500), randint(op-500, op+500)]
                        lh.sort()
                        vals.append(op/100)
                        lh.reverse()
                        for v in lh:
                            vals.append(v/100)
                        lh.reverse()
                        vals.append(randint(lh[0], lh[1])/100)
                        cans.append(vals)
                        op = int(vals[-1]*100)
                else:
                    cans = presets[0]
                self.inputs[3][0].candles = cans
                self.inputs[3][0].initScene()
            else:
                self.inputs[3][0].rangex = olvw[0][0]
                self.inputs[3][0].rangey = olvw[0][1]
                self.inputs[3][0].gridconv = olvw[0][2]
                self.inputs[3][0].candles = olvw[0][3]
                self.inputs[3][0].setScene(olvw[0][4])
                self.inputs[3][0].ind = olvw[0][5]
            self.inputs[3].append(SmallView(wid)) # small window
            self.inputs[3][1].setGeometry(311, 331, 300, 50)
            self.inputs[3][1].pxSize = (300, 50)
            self.inputs[3][1].dMode = -1
            if first or modechanged:
                self.inputs[3][1].scene().setSceneRect(0, 0, 290, 40)
                grid = Grid(QtCore.QRectF(-5, -5, 300, 50))
                grid.density = (10, 10)
                self.inputs[3][1].scene().addItem(grid)
                self.inputs[3][1].candles = cans
                self.inputs[3][1].rangey = (0, 10)
                self.inputs[3][1].gridconv = [25, 5, 25, 5]
                self.inputs[3][1].isVolume = True
                self.inputs[3][1].colors.append(QtGui.QColor("#ffffff"))
                self.inputs[3][1].initScene()
            else:
                self.inputs[3][1].rangex = olvw[1][0]
                self.inputs[3][1].rangey = olvw[1][1]
                self.inputs[3][1].gridconv = olvw[1][2]
                self.inputs[3][1].candles = olvw[1][3]
                self.inputs[3][1].setScene(olvw[1][4])
            self.inputs[3].append([])
            temp = [(105, 100), (200, 100), (10, 100), (515, 55)] # 1, 2, 5, 6
            for t in temp:
                l = QtWidgets.QLabel(wid)
                l.move(t[0], t[1])
                f = QtGui.QFont()
                f.setPointSizeF(6.5)
                l.setFont(f)
                self.inputs[3][2].append(l)

            def labelText(ind): # change the label text below dragbox
                if ind == 0: # variables
                    if len(self.inputs[0][1].vars) == 0: return
                    t = indargs[self.inputs[0][1].vars[self.inputs[0][1].currentIndex()].indName]["name"]
                    for arg in self.inputs[0][1].vars[self.inputs[0][1].currentIndex()].args:
                        if "%" not in str(arg): t += " " + str(arg) # not variable
                        else: 
                            ty = arg[1]
                            idd = int(arg.split("%")[1].split(ty)[1])
                            if ty == "v": search = self.inputs[0][1].vars
                            elif ty == "e": search = self.inputs[0][2].vars
                            if len(search) == 0: return
                            for v in search:
                                if v.id == idd: break
                            if ty == "v": t += " " + v.var
                            else: t += " " + v.name
                    self.inputs[3][2][0].setText(t)
                elif ind == 1: # equations
                    if len(self.inputs[0][2].vars) == 0: return
                    t = ""
                    beg = True # begin without space
                    for arg in self.inputs[0][2].vars[self.inputs[0][2].currentIndex()].args:
                        if "%" not in str(arg): t += " " + str(arg) # not variable
                        else: 
                            ty = arg[1]
                            idd = int(arg.split("%")[1].split(ty)[1])
                            if ty == "v": search = self.inputs[0][1].vars
                            elif ty == "e": search = self.inputs[0][2].vars
                            if len(search) == 0: return
                            for v in search:
                                if v.id == idd: break
                            if ty == "v": t += " " + v.var
                            else: t += " " + v.name
                        if beg: 
                            t = t[1:]  # clip space
                            beg = False
                    self.inputs[3][2][1].setText(t)
                elif ind == 2: # expressions
                    if len(self.inputs[0][5].vars) == 0: return
                    t = ""
                    beg = True # begin without space
                    for arg in self.inputs[0][5].vars[self.inputs[0][5].currentIndex()].args:
                        if "%" not in str(arg): t += " " + str(arg) # not variable
                        else: 
                            ty = arg[1]
                            idd = int(arg.split("%")[1].split(ty)[1])
                            if ty == "v": search = self.inputs[0][1].vars
                            elif ty == "e": search = self.inputs[0][2].vars
                            else: search = self.inputs[0][5].vars
                            if len(search) == 0: return
                            for v in search:
                                if v.id == idd: break
                            if ty == "v": t += " " + v.var
                            else: t += " " + v.name
                        if beg: 
                            t = t[1:]  # clip space
                            beg = False
                    self.inputs[3][2][2].setText(t)
                elif ind == 3: # indicators
                    if len(self.inputs[0][6].vars) == 0: return
                    t = indargs[self.inputs[0][6].vars[self.inputs[0][6].currentIndex()].indName]["name"]
                    for arg in self.inputs[0][6].vars[self.inputs[0][6].currentIndex()].args:
                        if "%" not in str(arg): t += " " + str(arg) # not variable
                        else: 
                            ty = arg[1]
                            idd = int(arg.split("%")[1].split(ty)[1])
                            if ty == "v": search = self.inputs[0][1].vars
                            elif ty == "e": search = self.inputs[0][2].vars
                            if len(search) == 0: return
                            for v in search:
                                if v.id == idd: break
                            if ty == "v": t += " " + v.var
                            else: t += " " + v.name
                    self.inputs[3][2][3].setText(t)

            if first: color = "background-color: %s;" % QtGui.QColor(randint(0, 255), randint(0, 255), randint(0, 255)).name() # rng color
            else: color = "background-color: " + color + ";"
            self.inputs[3].append(QtWidgets.QPushButton(wid))
            self.inputs[3][3].setGeometry(598, 4, 20, 20)
            self.inputs[3][3].setStyleSheet(color)
            self.inputs[3][3].clicked.connect(self.pickColor)

            QtWidgets.QLabel("Variables", wid).move(104, 61)
            self.inputs[0].append(DragBox(wid, self.delVariable, self.editVariable))
            self.inputs[0][1].setGeometry(104, 77, 92, 22)
            self.inputs[0][1].addItems(its[0])
            if vind != -1: 
                self.inputs[0][1].vars = olvars[vind]
                vind += 1
            QtWidgets.QLabel("Equations", wid).move(198, 61)
            self.inputs[0].append(DragBox(wid, self.delVariable, self.editVariable))
            self.inputs[0][2].setGeometry(198, 77, 92, 22)
            self.inputs[0][2].addItems(its[1])
            self.inputs[0][2].rnFn = lambda: self.renVariable("e")
            if vind != -1: 
                self.inputs[0][2].vars = olvars[vind]
                vind += 1
            QtWidgets.QLabel("Create an Equation", wid).move(10, 109)

            self.inputs[0].append(QtWidgets.QComboBox(wid))
            self.inputs[0][3].setGeometry(10, 125, 110, 22)
            self.inputs[0][3].addItems(["Basic", "Constants", "Trigonometric", "Aggregates", "Round", "Spot of", "Functions"])#, "Time"])
            if len(olds) != 0:
                self.inputs[0][3].setCurrentText(olds[3])
            self.inputs[0][3].currentTextChanged.connect(lambda: self.creatorNewLayout())

            if self.inputs[0][3].currentText() == "Basic":
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][0].setGeometry(10, 155, 110, 22)
                self.inputs[1][1].append(QtWidgets.QComboBox(wid))
                self.inputs[1][1][1].setGeometry(122, 155, 43, 22)
                self.inputs[1][1][1].addItems(["+", "-", "*", "/", "%", "//", "**"])
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][2].setGeometry(167, 155, 110, 22)
            elif self.inputs[0][3].currentText() == "Constants":
                self.inputs[1][1].append(QtWidgets.QComboBox(wid))
                self.inputs[1][1][0].move(10, 155)
                self.inputs[1][1][0].addItems(["π", "e", "ϕ"])
            elif self.inputs[0][3].currentText() == "Trigonometric":
                self.inputs[1][1].append(QtWidgets.QComboBox(wid))
                self.inputs[1][1][0].move(10, 155)
                self.inputs[1][1][0].addItems(["Sin", "Asin", "Cos", "Acos", "Tan", "Atan"])
                QtWidgets.QLabel("of", wid).move(85, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][1].move(110, 155)
            elif self.inputs[0][3].currentText() == "Aggregates":
                self.inputs[1][1].append(QtWidgets.QComboBox(wid))
                self.inputs[1][1][0].move(10, 155)
                self.inputs[1][1][0].addItems(["Max", "Min", "Average", "Sum"])
                QtWidgets.QLabel("of", wid).move(90, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][1].move(110, 155)
                self.inputs[1][1][1].requestRange = True
                self.inputs[1][1][1].setMultiFn(self.multiVar)
                self.inputs[1][1][1].setLocked(True)
            elif self.inputs[0][3].currentText() == "Round":
                QtWidgets.QLabel("Round", wid).move(10, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][0].move(60, 155)
                QtWidgets.QLabel(",", wid).move(180, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][1].move(195, 155)
            elif self.inputs[0][3].currentText() == "Spot of":
                QtWidgets.QLabel("Spot of", wid).move(10, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][0].move(60, 155)
                QtWidgets.QLabel("in", wid).move(180, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][1].move(195, 155)
                self.inputs[1][1][1].requestRange = True
                self.inputs[1][1][1].setMultiFn(self.multiVar)
                self.inputs[1][1][1].setLocked(True)
            elif self.inputs[0][3].currentText() == "Functions":
                self.inputs[1][1].append(QtWidgets.QComboBox(wid))
                self.inputs[1][1][0].move(10, 155)
                self.inputs[1][1][0].addItems(["Floor", "Ceil", "Abs"])
                QtWidgets.QLabel("of", wid).move(85, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][1].move(110, 155)
            elif self.inputs[0][3].currentText() == "Time":
                self.inputs[1][1].append(QtWidgets.QComboBox(wid))
                self.inputs[1][1][0].move(10, 155)
                self.inputs[1][1][0].addItems(["Year", "Month", "Day", "Hour", "Minute", "Second"])
                QtWidgets.QLabel("of", wid).move(85, 155)
                self.inputs[1][1].append(Slot(wid, self.dropBox))
                self.inputs[1][1][1].move(110, 155)
            
            self.inputs[2].append(EdSaveBtn("Add", wid))
            self.inputs[2][1].setGeometry(236, 124, 75, 24)
            sav = False
            if len(savs) != 0:
                if savs[1]:
                    self.inputs[2][1].setActive()
                    self.inputs[2][1].setText("Save")
                sav = savs[1]
            if sav: self.inputs[2][1].clicked.connect(lambda: self.addButton("Equation", True))
            else: self.inputs[2][1].clicked.connect(lambda: self.addButton("Equation"))

            QtWidgets.QLabel("Create an Expression", wid).move(10, 208)
            self.inputs[0].append(QtWidgets.QComboBox(wid))
            self.inputs[0][4].setGeometry(10, 224, 108, 22)
            self.inputs[0][4].addItems(["Compare", "Combine", "Not", "Dynamic Near"])
            if len(olds) != 0:
                self.inputs[0][4].setCurrentText(olds[4])
            self.inputs[0][4].currentTextChanged.connect(lambda: self.creatorNewLayout())
            
            if self.inputs[0][4].currentText() in ["Compare", "Combine"]:
                self.inputs[1][2].append(Slot(wid, self.dropBox))
                self.inputs[1][2][0].setGeometry(10, 254, 110, 22)
                self.inputs[1][2].append(QtWidgets.QComboBox(wid))
                self.inputs[1][2][1].setGeometry(122, 254, 48, 22)
                self.inputs[1][2].append(Slot(wid, self.dropBox))
                self.inputs[1][2][2].setGeometry(172, 254, 110, 22)
                if self.inputs[0][4].currentText() == "Compare": self.inputs[1][2][1].addItems(["==", "<", "<=", ">", ">="])
                else: 
                    self.inputs[1][2][1].addItems(["and", "or", "xor"])
                    self.inputs[1][2][0].requested = "E" 
                    self.inputs[1][2][0].setLocked(True)
                    self.inputs[1][2][2].requested = "E" 
                    self.inputs[1][2][2].setLocked(True)
            elif self.inputs[0][4].currentText() == "Not":
                QtWidgets.QLabel("not", wid).move(10, 254)
                self.inputs[1][2].append(Slot(wid, self.dropBox))
                self.inputs[1][2][0].move(50, 254)
                self.inputs[1][2][0].requested = "E" 
                self.inputs[1][2][0].setLocked(True)
            elif self.inputs[0][4].currentText() == "Dynamic Near":
                QtWidgets.QLabel("Near", wid).move(10, 254)
                self.inputs[1][2].append(Slot(wid, self.dropBox))
                self.inputs[1][2][0].move(50, 254)
                self.inputs[1][2].append(Slot(wid, self.dropBox))
                self.inputs[1][2][1].move(175, 254)
            
            QtWidgets.QLabel("Expressions", wid).move(10, 61)
            self.inputs[0].append(DragBox(wid, self.delVariable, self.editVariable))
            self.inputs[0][5].setGeometry(10, 77, 92, 22)
            self.inputs[0][5].addItems(its[2])
            self.inputs[0][5].rnFn = lambda: self.renVariable("x")
            #if len(savs) != 0: self.inputs[0][5].setEnabled(not savs[2])
            if vind != -1: 
                self.inputs[0][5].vars = olvars[vind]
                vind += 1

            self.inputs[2].append(EdSaveBtn("Add", wid))
            self.inputs[2][2].setGeometry(236, 223, 75, 24)
            sav = False
            if len(savs) != 0:
                if savs[2]:
                    self.inputs[2][2].setActive()
                    self.inputs[2][2].setText("Save")
                sav = savs[2]
            if sav: self.inputs[2][2].clicked.connect(lambda: self.addButton("Expression", True))
            else: self.inputs[2][2].clicked.connect(lambda: self.addButton("Expression"))
            
            QtWidgets.QLabel("Indicators", wid).move(515, 16)
            self.inputs[0].append(DragBox(wid, self.delVariable, self.editVariable))
            self.inputs[0][6].setGeometry(515, 32, 81, 22)
            self.inputs[0][6].setIndicator()
            self.inputs[0][6].addItems(its[3])
            if vind != -1: 
                self.inputs[0][6].vars = olvars[vind]
                vind += 1
            
            def treeview(): # displays the treeview dialog window
                dbox = QtWidgets.QDialog(self.dialog)
                dbox.setWindowTitle("Condition Tree View")
                dbox.setFixedSize(300, 250)
                tree = QtWidgets.QTreeWidget(dbox)
                tree.setGeometry(10, 10, 280, 230)

                toplay = [] # top layer of expressions
                for ex in self.inputs[0][5].vars: toplay.append(ex.id)

                for ex in self.inputs[0][5].vars:
                    for a in ex.args:
                        if "%x" in str(a):
                            if int(a.split("%x")[1]) in toplay: toplay.remove(int(a.split("%x")[1])) # remove all expressions used to calculate another

                def find(typ, idd): # return index of item in typ list
                    if typ == "i": search = self.inputs[0][6].vars
                    elif typ == "v": search = self.inputs[0][1].vars
                    elif typ == "e": search = self.inputs[0][2].vars
                    else: search = self.inputs[0][5].vars

                    for v in range(len(search)):
                        if search[v].id == idd:
                            return v

                deps = []

                def downTree(typ, idd, org, branch): # down tree to get complexity score of calculating expression
                    bra = QtWidgets.QTreeWidgetItem(branch)
                    if typ != "v": 
                        if typ != "i": bra.setText(0, org.name)
                        else: bra.setText(0, org.indName)
                        if (typ, idd, org) not in deps: deps.append((typ, idd, org))
                        else: # move to front so that it gets calculated earlier
                            deps.pop(deps.index((typ, idd, org)))
                            deps.append((typ, idd, org))
                    else:
                        bra.setText(0, org.var)
                    if typ == "x": # expression
                        if org.type == "Variable": # if exist expression check indicator first
                            for ir in self.inputs[0][6].vars:
                                if ir.indName == org.args[0] and ir.args == org.args[1:]:
                                    downTree("i", ir.id, ir, bra)
                        else:
                            for a in org.args:
                                if "%" in str(a):
                                    # can be either variable with spot, equation or expression
                                    sp = a.split("%")
                                    for s in sp:
                                        if not isint(s) and s != "": # if variable in str
                                            temp = ["v", "e", "x"]
                                            temp2 = [1, 2, 5]
                                            t = temp2[temp.index(s[0])]
                                            downTree(s[0], int(s[1:]), self.inputs[0][t].vars[find(s[0], int(s[1:]))], bra)
                    elif typ == "e": # equation
                        for a in org.args:
                            if "%" in str(a):
                                # it's either a variable with spot, multiple variables with spot or another equation
                                sps = a.split("|")
                                for spsps in sps:
                                    sp = spsps.split("%")
                                    for s in sp:
                                        if "," in s: p = s.split(",")
                                        else: p = [s]
                                        for pp in p:
                                            if not isint(pp) and pp != "": # if variable in str
                                                temp = ["v", "e"]
                                                temp2 = [1, 2]
                                                t = temp2[temp.index(pp[0])]
                                                downTree(pp[0], int(pp[1:]), self.inputs[0][t].vars[find(pp[0], int(pp[1:]))], bra)
                    elif typ == "v": # if variable only pass onto indicator
                        for ir in self.inputs[0][6].vars:
                            if ir.indName == org.indName and ir.args == org.args:
                                downTree("i", ir.id, ir, bra)
                    elif typ == "i":
                        for a in org.args:
                            if "%" in str(a):
                                # can be either variable with spot or equation
                                sp = a.split("%")
                                for s in sp:
                                    if not isint(s) and s != "": # if variable in str
                                        temp = ["v", "e"]
                                        temp2 = [1, 2]
                                        t = temp2[temp.index(s[0])]
                                        downTree(s[0], int(s[1:]), self.inputs[0][t].vars[find(s[0], int(s[1:]))], bra)
                
                for t in toplay:
                    downTree("x", t, self.inputs[0][5].vars[find("x", t)], tree)
                dbox.exec()

            btn = QtWidgets.QPushButton("Tree View", wid)
            btn.move(10, 284)
            btn.clicked.connect(treeview)

            QtWidgets.QLabel("Offset", wid).move(10, 347)
            self.inputs[3].append(QtWidgets.QLineEdit("-1", wid))
            self.inputs[3][4].move(10, 360)
            if not first: self.inputs[3][4].setText(filters[0])

            self.inputs[3].append(AdvancedComboBox(wid))
            self.inputs[3][5].setGeometry(223, 359, 75, 22)
            self.inputs[3][5].addItems(filtrrs)
            if "Advanced..." not in filtrrs: self.inputs[3][5].addItem("Advanced...")

            def advancedFilter(indx): # displays dbox for making advanced filter statements
                dbox = QtWidgets.QDialog(self.dialog)
                dbox.setWindowTitle("Add advanced filter...")
                dbox.setFixedSize(450, 100)

                # two comboboxes and 2 slots (numbers only)
                cbox = QtWidgets.QComboBox(dbox)
                cbox.move(10, 10)
                cbox.addItems(["Minimum", "Maximum", "Exactly", "Around"])

                slot = Slot(dbox)
                slot.move(110, 10)
                slot._allowed_chars = "0123456789"

                cbox2 = QtWidgets.QComboBox(dbox)
                cbox2.move(230, 10)
                cbox2.addItems(["Last", "In A Row", "Nearby", "-"])

                slot2 = Slot(dbox)
                slot2.move(320, 10)
                slot2._allowed_chars = "0123456789"

                def ok():
                    if slot.text() == "":
                        self.errormsg("No amount given.")
                        return
                    if cbox2.currentText() == "Last" and slot2.text() == "":
                        self.errormsg("Range requested but not given.")
                        return
                    stringg = cbox.currentText() # form string out of items in cbox
                    stringg += " " + slot.text() + " True"
                    if cbox2.currentText() == "Last":
                        stringg += " " + cbox2.currentText()
                        stringg += " " + slot2.text()
                    elif cbox2.currentText() != "-":
                        stringg += " " + cbox2.currentText()
                    
                    # add string to combobox of filters and make sure to select it
                    self.inputs[3][5].setCurrentIndex(0) # just so that this box doesn't trigger again
                    self.inputs[3][5].insertItem(indx, stringg)
                    self.inputs[3][5].setCurrentIndex(indx)

                    dbox.close()

                btn = QtWidgets.QPushButton("OK", dbox)
                btn.move(195, 65)
                btn.clicked.connect(ok)

                def finish():
                    self.inputs[3][5].setCurrentIndex(0) # just so that this box doesn't trigger again

                dbox.finished.connect(finish)
                dbox.exec()

            self.inputs[3][5].setFn(advancedFilter) # sets what happens when advanced is selected
            if not first: self.inputs[3][5].setCurrentText(filters[1])

            if first and ind != -1: # if a condition is being edited and the editor was just opened
                variables = [[], [], [], []] # 0 is v, 1 is e, 2 is x, 3 is i 
                # unpack variables into different types
                for var in logic.conditions[ind]["vars"]:
                    if type(var) == IndicatorVariable:
                        if var.var == "": variables[3].append(var) # indicator
                        else: variables[0].append(var)
                    elif type(var) == VariableEquation: variables[1].append(var)
                    elif type(var) == VariableExpression: variables[2].append(var)
                i = 0
                for t in [1, 2, 5, 6]:
                    for v in variables[i]:
                        if t != 0 and t != 6: self.inputs[0][t].addItem(v.name)
                        elif t == 0: self.inputs[0][t].addItem(v.var)
                        else:
                            self.inputs[0][t].addItem(indargs[v.indName]["name"] + " " + str(len(self.inputs[0][6].vars)))
                        self.inputs[0][t].vars.append(v)
                    i += 1
                self.inputs[3][3].setStyleSheet("background-color: " + logic.conditions[ind]["color"] + ";")
                self.inputs[3][4].setText(str(logic.conditions[ind]["filters"][0]))
                if logic.conditions[ind]["filters"][1] not in filtrrs: # if a custom filter was used
                    self.inputs[3][5].insertItem(self.inputs[3][5].count() - 1, logic.conditions[ind]["filters"][1])
                self.inputs[3][5].setCurrentText(logic.conditions[ind]["filters"][1])
                
            if len(self.inputs[0][1].vars) != 0:
                labelText(0)
                self.inputs[0][1].currentTextChanged.connect(lambda: labelText(0))
            if len(self.inputs[0][2].vars) != 0:
                labelText(1)
                self.inputs[0][2].currentTextChanged.connect(lambda: labelText(1))
            if len(self.inputs[0][5].vars) != 0:
                labelText(2)
                self.inputs[0][5].currentTextChanged.connect(lambda: labelText(2))
            if len(self.inputs[0][6].vars) != 0:
                labelText(3)
                self.inputs[0][6].currentTextChanged.connect(lambda: labelText(3))
            
            btn = QtWidgets.QPushButton("OK", wid)
            btn.setGeometry(134, 359, 75, 24)
            btn.clicked.connect(lambda: self.creatorExecute(self.dialog))
            #btn.clicked.connect(self.dialog.close)

            self.inputs[3].append(QtWidgets.QCheckBox("Advanced Mode", wid))
            self.inputs[3][6].move(505, 106)
            self.inputs[3][6].setChecked(mode)
            self.inputs[3][6].toggled.connect(lambda: self.creatorNewLayout())
        
        if mode: # for being able to use the same definitions twice
            QtWidgets.QLabel("Templates", wid).move(10, 16)
            cbox = QtWidgets.QComboBox(wid)
            cbox.setGeometry(10, 32, 74, 22)
        else:
            QtWidgets.QLabel("Add an expression", wid).move(10, 16)
            cbox = QtWidgets.QComboBox(wid)
            cbox.setGeometry(10, 32, 74, 22)

        try:
            with open('templates.pkl', 'rb') as file: # if file already exist, copy whatever is written and just add onto it
                data_dict = pickle.load(file)
            cbox.addItems(list(data_dict.keys()))
        except:
            pass

        def saveTemplate(): # save all of the variables in a single string and put it into a file
            # get all of the variables in a single list
            if mode:
                variables = []
                temp = [1, 2, 5, 6]
                for t in temp:
                    for v in self.inputs[0][t].vars:
                        variables.append(v)
            else: variables = self.inputs[1].vars
            
            dbox = QtWidgets.QDialog(self.dialog)
            dbox.setWindowTitle("Template Name...")
            dbox.setFixedSize(200, 120)
            QtWidgets.QLabel("Enter a name for this template", dbox).move(10, 10)
            tbox = QtWidgets.QLineEdit(dbox)
            tbox.setGeometry(10, 30, 130, 22)
            btn = QtWidgets.QPushButton("OK", dbox)
            btn.move(65, 75)
            btn.clicked.connect(dbox.close)
            dbox.exec()
            if tbox.text() == "":
                self.errormsg("No name was entered. Please enter a name.")
                return
            else: name = tbox.text()

            # append variables to dict in file
            try:
                with open('templates.pkl', 'rb') as file: # if file already exist, copy whatever is written and just add onto it
                    data_dict = pickle.load(file)
            except FileNotFoundError:
                data_dict = {}
            
            if name in list(data_dict.keys()):
                threading.Thread(target=lambda:playsound("Exclamation")).start()
                result = QtWidgets.QMessageBox.question(self, "Name already in use", "Do you want to replace the template of the same name?", 
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                    return
            
            data_dict[name] = variables
            cbox.addItem(name)
            cbox.setCurrentText(name)
            
            with open('templates.pkl', 'wb') as file: 
                pickle.dump(data_dict, file)

        def processDict(variables): # definition becaused used more than once
            varsorted = [[], [], [], []] # 0 is v, 1 is e, 2 is x, 3 is i 
            # unpack variables into different types
            ids = []
            for var in variables:
                if type(var) == IndicatorVariable:
                    if var.var == "": 
                        varsorted[3].append(var) # indicator
                        typ = "i"
                    else: 
                        varsorted[0].append(var)
                        typ = "v"
                elif type(var) == VariableEquation: 
                    varsorted[1].append(var)
                    typ = "e"
                elif type(var) == VariableExpression: 
                    varsorted[2].append(var)
                    typ = "x"
                ids.append((typ, var.id)) # check for ids when unpacking

            if mode:
                i = 0
                for t in [1, 2, 5, 6]:
                    self.inputs[0][t].vars = []
                    self.inputs[0][t].clear()
                    for v in varsorted[i]:
                        if t != 0 and t != 6: self.inputs[0][t].addItem(v.name)
                        elif t == 0: self.inputs[0][t].addItem(v.var)
                        else:
                            self.inputs[0][t].addItem(indargs[v.indName]["name"] + " " + str(len(self.inputs[0][6].vars)))
                        self.inputs[0][t].vars.append(v)
                    i += 1
            else:
                self.inputs[1].vars = variables
                self.conditionCreatorLayout()

        def importTemplate(): # takes variables from template and adds them to cboxes
            if mode:
                lenvar = 0
                temp = [1, 2, 5, 6]
                for t in temp:
                    lenvar += len(self.inputs[0][t].vars)
            else:
                lenvar = len(self.inputs[1].vars)
            if lenvar != 0: # warning if other variables in use
                threading.Thread(target=lambda:playsound("Exclamation")).start()
                result = QtWidgets.QMessageBox.question(self, "Are You Sure?", "Importing will overwrite every variable currently in use. Continue?", 
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                    return
            with open('templates.pkl', 'rb') as file: # if file already exist, copy whatever is written and just add onto it
                data_dict = pickle.load(file)
            processDict(data_dict[cbox.currentText()])
        
        def importFrom(): # opens a file dialog window and displays a dialog window for which variable should be displayed
            filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open template pickle file...", "", "Pickle files (*.pkl);;All files (*.*)")[0] # get filename
            if filename == "": return # if no file was selected
            try:
                with open(filename, 'rb') as file: # if file already exist, copy whatever is written and just add onto it
                    data_dict = pickle.load(file)
            except:
                self.errormsg("File invalid.")
                return
            
            if type(data_dict) != dict:
                self.errormsg("Invalid pickle file provided.")
                return
            
            dbox = QtWidgets.QDialog(self.dialog)
            dbox.setFixedSize(150, 100)
            dbox.setWindowTitle("Select Template to open...")
            cbox2 = QtWidgets.QComboBox(dbox)
            cbox2.move(10, 10)
            cbox2.addItems(list(data_dict.keys()))
            btn = QtWidgets.QPushButton("OK", dbox)
            btn.move(35, 60)

            def contin():
                if mode:
                    lenvar = 0
                    temp = [1, 2, 5, 6]
                    for t in temp:
                        lenvar += len(self.inputs[0][t].vars)
                else:
                    lenvar = len(self.inputs[1].vars)
                if lenvar != 0: # warning if other variables in use
                    threading.Thread(target=lambda:playsound("Exclamation")).start()
                    result = QtWidgets.QMessageBox.question(self, "Are You Sure?", "Importing will overwrite every variable currently in use. Continue?", 
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                    if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                        return
                processDict(data_dict[cbox2.currentText()])
                dbox.close()
            
            btn.clicked.connect(contin)
            dbox.exec()

        if mode:
            btn = QtWidgets.QPushButton("Import", wid)
            btn.setGeometry(86, 31, 75, 24)
            btn.clicked.connect(importTemplate)

            btn = QtWidgets.QPushButton("Save as...", wid)
            btn.setGeometry(161, 31, 75, 24)
            btn.clicked.connect(saveTemplate)

            btn = QtWidgets.QPushButton("Import from...", wid)
            btn.setGeometry(236, 31, 75, 24)
            btn.clicked.connect(importFrom)
        else: # simplified

            btn = QtWidgets.QPushButton("Import", wid)
            btn.setGeometry(86, 31, 75, 24)
            btn.clicked.connect(importTemplate)

            btn = QtWidgets.QPushButton("Save as...", wid)
            btn.setGeometry(161, 31, 75, 24)
            btn.clicked.connect(saveTemplate)

            btn = QtWidgets.QPushButton("Import from...", wid)
            btn.setGeometry(236, 31, 75, 24)
            btn.clicked.connect(importFrom)

            self.inputs[0] = QtWidgets.QCheckBox("Advanced Mode", wid)
            self.inputs[0].move(505, 106)
            self.inputs[0].setChecked(mode)
            self.inputs[0].toggled.connect(lambda: self.creatorNewLayout())

            QtWidgets.QLabel("Expressions", wid).move(10, 61)
            self.inputs[1] = DragBox(wid)#, #self.delVariable, self.editVariabdle)
            self.inputs[1].setGeometry(10, 77, 92, 22)

            def find(idd): # return index of item in typ list
                search = self.inputs[1].vars

                for v in range(len(search)):
                    if type(search[v]) == VariableExpression and search[v].id == idd:
                        return v

            if modechanged: # if changed from advanced
                allvars = []
                for o in olvars:
                    allvars += o
                self.inputs[1].vars = allvars # put all variables into expressions window
            elif not first:
                self.inputs[1].vars = olvars
            
            # display only names of top level expressions
            toplay = [] # top layer of expressions
            for ex in self.inputs[1].vars: 
                if type(ex) == VariableExpression: toplay.append(ex.id)

            for ex in self.inputs[1].vars:
                for a in ex.args:
                    if "%x" in str(a):
                        if int(a.split("%x")[1]) in toplay: toplay.remove(int(a.split("%x")[1])) # remove all expressions used to calculate another
            
            for i in range(len(toplay)):
                self.inputs[1].addItem(self.inputs[1].vars[find(toplay[i])].name)
            
            self.inputs[2] = []

            if first: color = "background-color: %s;" % QtGui.QColor(randint(0, 255), randint(0, 255), randint(0, 255)).name() # rng color
            else: color = "background-color: " + color + ";"
            self.inputs[2].append(QtWidgets.QPushButton(wid))
            self.inputs[2][0].setGeometry(598, 4, 20, 20)
            self.inputs[2][0].setStyleSheet(color)
            self.inputs[2][0].clicked.connect(self.pickColor)

            QtWidgets.QLabel("Offset", wid).move(10, 347)
            self.inputs[2].append(QtWidgets.QLineEdit("-1", wid))
            self.inputs[2][1].move(10, 360)
            if not first: self.inputs[2][1].setText(filters[0])

            self.inputs[2].append(QtWidgets.QComboBox(wid))
            self.inputs[2][2].move(223, 359)
            if "Advanced..." in filtrrs: self.inputs[2][2].addItems(filtrrs[:-1])
            else: self.inputs[2][2].addItems(filtrrs)
            if not first: self.inputs[2][2].setCurrentText(filters[1])

            btn = QtWidgets.QPushButton("OK", wid)
            btn.setGeometry(134, 359, 75, 24)
            btn.clicked.connect(lambda: self.creatorExecute(self.dialog))

        lay = self.dialog.layout()
        while lay.count(): # delete all widgets currently in use
            w = lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        lay.addWidget(wid)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.dialog.setLayout(lay) # sets layout of dbox

    def creatorNewLayout(self, who=""): # updates the view window when needed and also the layout
        # who[0] is what area was changed
        # who[1] is what was done; p for another option picked, c for value changed
        for x in [0]: # to allow breaking similar to returning
            if who == "": break
            if who[0] == "i": # if indicator was changed
                self.inputs[3][0].graphInds = []
                self.inputs[3][1].graphInds = []
                # quick error check
                def isType(thing, typ): # pass thing and check if it's the type
                    if typ == str: return True
                    elif typ == int: return isint(thing)
                    elif typ == float: return isfloat(thing)
                
                for key in avinds: # find key corresponding to combobox text
                    if indargs[key]["name"] == self.inputs[0][0].currentText(): break
                
                # error code
                errd = False
                if who[1] == "c":
                    for i in range(len(indargs[key]["args"])):
                        if self.inputs[1][0][i].var is None: # only for non variables
                            value = self.inputs[1][0][i].text()
                            c = indargs[key]["args"][i][1:] # 0 is default; 1 is type; 2 is minimum; 3 is maximum
                            
                            if not isType(value, c[1]): 
                                errd = True
                                break
                            
                            if c[2] != "-inf": # if it has a bottom limit
                                chk = c[2]
                                if chk == "nan": chk = -300 # nan means -len(stock)
                                if c[1](value) < chk:
                                    errd = True
                                    break
                            
                            maxx = c[3]
                            if maxx == "nan": maxx = 299 # nan means len(stock)-1
                            if maxx != "inf":
                                if c[1](value) > maxx:
                                    errd = True
                                    break
                if errd: break # dont continue if error

                # change view window
                if key == "ohlcv":
                    self.inputs[3][0].dMode = 0
                    if len(presets[0]) != 0: 
                        self.inputs[3][0].candles = presets[0]
                        self.inputs[3][0].initScene()
                        self.inputs[3][1].colors.append(QtGui.QColor("#ffffff"))
                        self.inputs[3][1].isVolume = True
                elif key == "extra":
                    self.inputs[3][0].dMode = 0
                    self.inputs[3][1].colors.append(QtGui.QColor("#ffffff"))
                    self.inputs[3][1].isVolume = True
                elif key == "heikin-ashi":
                    self.inputs[3][0].dMode = 2
                    self.inputs[3][1].colors.append(QtGui.QColor("#ffffff"))
                    self.inputs[3][1].isVolume = True
                elif key == "time":
                    self.inputs[3][0].dMode = 0
                    for i in range(8):
                        self.inputs[3][1].colors.append(QtGui.QColor("#ffffff"))
                        self.inputs[3][1].annotations.append((str(240+i*10), coordinate("x", 240+i*10, self.inputs[3][1].gridconv,
                                                                                        self.inputs[3][1].rangex, self.inputs[3][1].rangey, 50), 10))
                elif key == "sma":
                    self.inputs[3][0].dMode = 0
                    if who[1] == "p": ma = 200
                    else: ma = int(self.inputs[1][0][0].text())
                    self.inputs[3][0].colors.append(QtGui.QColor("#ff0044"))
                    temp = pd.DataFrame(self.inputs[3][0].candles)
                    self.inputs[3][0].graphInds.append(temp.rolling(window=ma).mean()[3].reset_index(drop=True).to_list())
                elif key == "ema":
                    self.inputs[3][0].dMode = 0
                    if who[1] == "p": ma = 200
                    else: ma = int(self.inputs[1][0][0].text())
                    self.inputs[3][0].colors.append(QtGui.QColor("#44ff00"))
                    temp = pd.DataFrame(self.inputs[3][0].candles)
                    self.inputs[3][0].graphInds.append(temp.ewm(span=ma, adjust=False).mean()[3].reset_index(drop=True).to_list())
                elif key == "vwap":
                    if who[1] == "p": ma = 60
                    else: ma = int(self.inputs[1][0][0].text())
                    self.inputs[3][0].colors.append(QtGui.QColor("#666666"))
                    temp = []
                    prods = [] # price * volume of all
                    for i in range(len(self.inputs[3][0].candles)): 
                        prods.append(self.inputs[3][0].candles[i][3] * self.inputs[3][0].candles[i][4])
                    for i in range(ma): temp.append(float("nan")) # no value for first few values
                    for i in range(ma, len(self.inputs[3][0].candles)):
                        cumsum = 0
                        vols = 0 # all volumes
                        for m in range(ma): # for every window
                            cumsum += prods[i-m]
                            vols += self.inputs[3][0].candles[i-m][4]
                        temp.append(cumsum/vols)
                    self.inputs[3][0].graphInds.append(temp)
                elif key == "rsi":
                    ma = 14
                    if who[1] == "c": ma = int(self.inputs[1][0][0].text())
                    self.inputs[3][1].colors.append(QtGui.QColor("#cc5555"))
                    rss = [] # multiple rsi
                    for spot in range(len(self.inputs[3][0].candles)):
                        closes = []
                        x = spot - ma
                        if x < 0: x = 0
                        for st in self.inputs[3][0].candles[x:spot+1]:
                            closes.append(st[3]) # get all closes in range
                        prices = np.asarray(closes)
                        deltas = np.diff(prices)
                        gains = np.where(deltas >= 0, deltas, 0)
                        losses = np.where(deltas < 0, -deltas, 0)
                        if len(gains) == 0: avg_gain = 0
                        else: avg_gain = np.mean(gains[:ma])
                        if len(losses) == 0: avg_loss = 0
                        else: avg_loss = np.mean(losses[:ma])
                        if avg_loss != 0:
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs)) # on a scale of 0-100
                        else: rsi = 50 # if divide by 0 default to 50
                        rss.append(rsi)
                    self.inputs[3][1].graphInds.append(rss)
                    self.inputs[3][1].gridconv = [25, 5, 25, 40]
                    self.inputs[3][1].rangey = (10, 90)
                    
                elif key == "macd":
                    self.inputs[3][1].colors.append(QtGui.QColor("#ffff00")) # macd
                    self.inputs[3][1].colors.append(QtGui.QColor("#ff0000")) # signal
                    temp = pd.DataFrame(self.inputs[3][0].candles)
                    ema12 = temp.ewm(span=12, adjust=False).mean()[3].reset_index(drop=True).to_list()
                    ema26 = temp.ewm(span=26, adjust=False).mean()[3].reset_index(drop=True).to_list()
                    macd = []
                    for e in range(len(ema12)):
                        macd.append(ema12[e]-ema26[e])
                    temp = pd.DataFrame(macd)
                    signal = temp.ewm(span=9, adjust=False).mean()[0].reset_index(drop=True).to_list()
                    self.inputs[3][1].graphInds.append(macd)
                    self.inputs[3][1].graphInds.append(signal)
                    self.inputs[3][1].gridconv = [25, 5, 25, 1]
                    self.inputs[3][1].rangey = (-0.5, 0.5)
                elif key == "bollinger":
                    if who[1] == "p": ma = 20
                    else: ma = int(self.inputs[1][0][0].text())
                    if who[1] == "p": k = 2
                    else: k = int(self.inputs[1][0][1].text())
                    for i in [0, 1, 2]: self.inputs[3][0].colors.append(QtGui.QColor("#00ffaa"))
                    temp = bollinger(self.inputs[3][0].candles, ma, k)
                    for t in temp: self.inputs[3][0].graphInds.append(t)
                elif key == "gaussian":
                    if who[1] == "p": ma = 50
                    else: ma = int(self.inputs[1][0][0].text())
                    if who[1] == "p": k = 1
                    else: k = int(self.inputs[1][0][1].text())
                    for i in [0, 1, 2]: self.inputs[3][0].colors.append(QtGui.QColor("#00ffaa"))
                    temp = gaussian(self.inputs[3][0].candles, ma, k)
                    for t in temp: self.inputs[3][0].graphInds.append(t)
                elif key == "v":
                    if len(presets[1]) != 0: self.inputs[3][0].candles = presets[1]
                    else:
                        pass
                        # add a file missing for when the preview wasnt found
                    self.inputs[3][0].initScene()
                elif key == "ʌ":
                    if len(presets[2]) != 0: self.inputs[3][0].candles = presets[2]
                    else:
                        pass
                        # add a file missing for when the preview wasnt found
                    self.inputs[3][0].initScene()
                elif key == "m":
                    if len(presets[3]) != 0: self.inputs[3][0].candles = presets[3]
                    else:
                        pass
                        # add a file missing for when the preview wasnt found
                    self.inputs[3][0].initScene()
                elif key == "w":
                    if len(presets[4]) != 0: self.inputs[3][0].candles = presets[4]
                    else:
                        pass
                        # add a file missing for when the preview wasnt found
                    self.inputs[3][0].initScene()
                elif key == "shs":
                    if len(presets[5]) != 0: self.inputs[3][0].candles = presets[5]
                    else:
                        pass
                        # add a file missing for when the preview wasnt found
                    self.inputs[3][0].initScene()
                elif key == "trend":
                    if who[1] == "p": ma = 20
                    else: ma = int(self.inputs[1][0][0].text())
                    self.inputs[3][0].colors.append(QtGui.QColor("#00ffff"))
                    x = list(range(ma))
                    y = self.inputs[3][0].candles[299-ma:299] # get last ma price points
                    y.reverse() # so that the tangent will fixate on last price point
                    coeffs = polyfit(x, y, 1) # if y = mx + b then coeffs[0][3] = m, coeffs[1][3] = b
                    m = -1*coeffs[0][3] # reverse m because y was reversed in condition

                    # make line with m and price
                    line = []
                    for i in range(len(self.inputs[3][0].candles)):
                        line.append((i-298)*m+self.inputs[3][0].candles[298][3])

                    self.inputs[3][0].graphInds.append(line)
                elif key == "support":
                    for breakloop in [0]:
                        avg = (self.inputs[3][0].rangey[1]-self.inputs[3][0].rangey[0])/10

                        closes = []
                        for i in self.inputs[3][0].candles[279:299]: # get closes
                            closes.append(i[3])
                        i = closes.index(min(closes)) # get index of valley
                        i = 279+i # global index
                        touches = [i] # when the line has been touched
                        cooldown = 0 # set to 3 if a touch has been detected to avoid detecting 3 of the same touch
                        s = 297
                        while s >= 0 and 298-s < 200: # look for intersections
                            if cooldown == 0 and abs(self.inputs[3][0].candles[s][3]-self.inputs[3][0].candles[i][3]) <= avg/2: # if the line has been touched
                                cooldown = 3
                                touches.append(s)
                            elif cooldown > 0: cooldown -= 1
                            if len(touches) == 3: break
                            s -= 1
                        
                        if len(touches) != 3: break # if no three touches; cant be a resistance line
                        x = 298-touches[-1] # range of resistance
                        for j in range(2):
                            if touches[j]-touches[j+1] < x/3: break # minimum distance
                        
                        add = 0
                        for j in range(x):
                            if self.inputs[3][0].candles[298-j][3] > self.inputs[3][0].candles[i][3]: add += 1 # if above line
                        
                        line = []
                        for j in range(300):
                            line.append(self.inputs[3][0].candles[i][3])
                        self.inputs[3][0].colors.append(QtGui.QColor("#ffffff"))
                        
                        self.inputs[3][0].graphInds.append(line)
                elif key == "resistance":
                    for breakloop in [0]:
                        avg = (self.inputs[3][0].rangey[1]-self.inputs[3][0].rangey[0])/10

                        closes = []
                        for i in self.inputs[3][0].candles[279:299]: # get closes
                            closes.append(i[3])
                        i = closes.index(max(closes)) # get index of peak
                        i = 279+i # global index
                        touches = [i] # when the line has been touched
                        cooldown = 0 # set to 3 if a touch has been detected to avoid detecting 3 of the same touch
                        s = 297
                        while s >= 0 and 298-s < 200: # look for intersections
                            if cooldown == 0 and abs(self.inputs[3][0].candles[s][3]-self.inputs[3][0].candles[i][3]) <= avg/2: # if the line has been touched
                                cooldown = 3
                                touches.append(s)
                            elif cooldown > 0: cooldown -= 1
                            if len(touches) == 3: break
                            s -= 1
                        
                        if len(touches) != 3: break # if no three touches; cant be a resistance line
                        x = 298-touches[-1] # range of resistance
                        for j in range(2):
                            if touches[j]-touches[j+1] < x/3: break # minimum distance
                        
                        add = 0
                        for j in range(x):
                            if self.inputs[3][0].candles[298-j][3] < self.inputs[3][0].candles[i][3]: add += 1 # if below line
                        
                        line = []
                        for j in range(300):
                            line.append(self.inputs[3][0].candles[i][3])
                        self.inputs[3][0].colors.append(QtGui.QColor("#ffffff"))
                        
                        self.inputs[3][0].graphInds.append(line)
                elif key == "line":
                    if who[1] == "p": 
                        ma = 0.5
                        k = 299
                    else: 
                        ma = float(self.inputs[1][0][1].text())
                        k = int(self.inputs[1][0][0].text())
                    self.inputs[3][0].colors.append(QtGui.QColor("#ff0099"))
                    
                    # make line with m and price
                    if k < 0: k += 300
                    line = []
                    for i in range(len(self.inputs[3][0].candles)):
                        line.append((i-k)*ma+self.inputs[3][0].candles[k][3])

                    self.inputs[3][0].graphInds.append(line)
                self.inputs[3][0].makeScene()
                self.inputs[3][1].makeScene()

        if "c" not in who: self.conditionCreatorLayout(False)

    def cancelEdit(self, ind): # cancels the edit state
        self.inputs[2][ind].setActive(False)
        self.conditionCreatorLayout()

    def dropBox(self, box: Slot): # what happens when a variable is dropped in a slot
        # box is slot the item is dropped into
        foc = self.dialog.focusWidget() # current combobox
        vind = foc.currentIndex() # index of variable
        if box.requested == "E" and type(foc.vars[vind]) != VariableExpression:
            box.setText("") # reset text
            self.errormsg("Slot requests Expression.")
            return
        if box.requested == "V" and type(foc.vars[vind]) == VariableExpression:
            box.setText("") # reset text
            self.errormsg("Slot requests Variable/Equation.")
            return
        if box.requestRange: # if range is requested
            if type(foc.vars[vind]) == VariableEquation:
                box.setText("") # reset text
                self.errormsg("Range cannot be entered for an equation.")
                return
            elif type(foc.vars[vind]) == VariableExpression:
                box.setText("") # reset text
                self.errormsg("Range cannot be entered for an expression.")
                return
            else: # if indicator variable
                dbox = QtWidgets.QDialog(self.dialog)
                dbox.setWindowTitle("Enter range...")
                dbox.setFixedSize(220, 150)
                dbox.setWindowFlags(dbox.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint) # keep all but close button
                QtWidgets.QLabel("Enter relative range provided", dbox).move(10, 10)
                cbox = DragBox(dbox)
                cbox.setGeometry(80, 30, 60, 22)
                cbox.doDrag = False
                tbox1 = Slot(dbox)
                tbox1.setGeometry(10, 60, 60, 22)
                tbox1.setText("-1")
                tbox2 = Slot(dbox)
                tbox2.setGeometry(150, 60, 60, 22)
                tbox2.setText("-1")
                its = []
                for indx in range(self.inputs[0][1].count()):
                    var = self.inputs[0][1].vars[indx]
                    if indinfo[var.indName]["vtypes"][indinfo[var.indName]["vars"].index(var.var)] == int: # if type of variable is int
                        its.append(self.inputs[0][1].itemText(indx))
                        cbox.vars.append(self.inputs[0][1].vars[indx])
                cbox.addItems(its)
                its = [self.inputs[0][2].itemText(indx) for indx in range(self.inputs[0][2].count())]
                cbox.addItems(its)
                cbox.vars.append(self.inputs[0][2].vars)
                def use(what): # puts selected option in correct tbox
                    if len(cbox.vars) == 0: return
                    if what == 1: tbox = tbox1
                    elif what == 2: tbox = tbox2
                    tbox.setText(cbox.currentText())
                    tbox.setLocked()
                    tbox.var = cbox.vars[cbox.currentIndex()]
                use1 = QtWidgets.QPushButton("Use", dbox)
                use1.setGeometry(10, 29, 60, 22)
                use1.clicked.connect(lambda: use(1))
                use2 = QtWidgets.QPushButton("Use", dbox)
                use2.setGeometry(150, 29, 60, 22)
                use2.clicked.connect(lambda: use(2))
                btn = QtWidgets.QPushButton("OK", dbox)
                btn.move(70, 115)
                def check():
                    if tbox1.var is None and not isint(tbox1.text()):
                        self.errormsg("First box doesn't contain a valid number.")
                        return
                    if tbox2.var is None and not isint(tbox2.text()):
                        self.errormsg("Second box doesn't contain a valid number.")
                        return
                    st = ""
                    if tbox1.var is not None:
                        if type(tbox1.var) == IndicatorVariable: t = "v"
                        else: t = "e"
                        st += t + str(tbox1.var.id)
                    else: st += tbox1.text()
                    st += ","
                    if tbox2.var is not None:
                        if type(tbox2.var) == IndicatorVariable: t = "v"
                        else: t = "e"
                        st += t + str(tbox2.var.id)
                    else: st += tbox2.text()
                    box.spotVar = st

                    dbox.close()
                btn.clicked.connect(check)
                dbox.exec()
        elif type(foc.vars[vind]) == IndicatorVariable: # if no range is requested and variable was given
            if indinfo[foc.vars[vind].indName]["vtypes"][indinfo[foc.vars[vind].indName]["vars"].index(foc.vars[vind].var)] == list: # if a spot can be selected
                dbox = QtWidgets.QDialog(self.dialog)
                dbox.setWindowTitle("Enter spot...")
                dbox.setFixedSize(200, 120)
                dbox.setWindowFlags(dbox.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint) # keep all but close button
                QtWidgets.QLabel("Enter spot in python form", dbox).move(10, 10)
                slot = Slot(dbox)
                slot.setGeometry(10, 30, 130, 22)
                slot.setText("-1")
                btn = QtWidgets.QPushButton("OK", dbox)
                btn.move(65, 75)
                def spotvar(): # spot variable dialog box
                    wid = QtWidgets.QDialog(dbox)
                    wid.setFixedSize(300, 150)
                    wid.setWindowTitle("Advanced Spot...")
                    QtWidgets.QLabel("Select a variable for spot", wid).move(10, 10)

                    foc = None
                    def store(w): # whenever text is changed; store current focussed widget
                        nonlocal foc # means global for nested functions
                        foc = w

                    QtWidgets.QLabel("Variables", wid).move(10, 40)
                    cbox1 = DragBox(wid)
                    cbox1.doDrag = False
                    cbox1.move(10, 70)
                    its = []
                    for indx in range(self.inputs[0][1].count()):
                        var = self.inputs[0][1].vars[indx]
                        if indinfo[var.indName]["vtypes"][indinfo[var.indName]["vars"].index(var.var)] == int: # if type of variable is int
                            its.append(self.inputs[0][1].itemText(indx))
                            cbox1.vars.append(self.inputs[0][1].vars[indx])
                    cbox1.focusInEvent = lambda event: store(cbox1)
                    cbox1.addItems(its)
                    QtWidgets.QLabel("Equations", wid).move(100, 40)
                    cbox2 = DragBox(wid)
                    cbox2.doDrag = False
                    cbox2.move(100, 70)
                    its = [self.inputs[0][2].itemText(indx) for indx in range(self.inputs[0][2].count())]
                    cbox2.addItems(its)
                    cbox2.vars = self.inputs[0][2].vars
                    cbox2.focusInEvent = lambda event: store(cbox2)
                    btn = QtWidgets.QPushButton("Select", wid)
                    btn.move(115, 115)
                    def ok():
                        if len(foc.vars) != 0:
                            var = foc.vars[foc.currentIndex()]
                            if type(var) == IndicatorVariable: slot.setText(var.var)
                            elif type(var) == VariableEquation: slot.setText(var.name)
                            slot.var = var
                            slot.setLocked()
                        wid.close()
                    btn.clicked.connect(ok)
                    wid.exec()
                # show some option to show advanced spot options
                abtn = QtWidgets.QPushButton("Adv.", dbox)
                abtn.setGeometry(155, 29, 35, 24)
                abtn.clicked.connect(spotvar)
                def check():
                    if slot.var is not None: # if a variable is used
                        if type(slot.var) == IndicatorVariable: t = "v"
                        elif type(slot.var) == VariableEquation: t = "e"
                        box.spotVar = t + str(slot.var.id)
                    else:
                        num = slot.text()
                        if not isint(num):
                            self.errormsg("Spot has to be an integer.")
                            return
                        box.spotVar = num
                    dbox.close()
                btn.clicked.connect(check)
                dbox.exec()

        box.setLocked(True)
        box.var = deepcopy(foc.vars[vind]) # set box variable to current cbox variable
        if type(box.var) == IndicatorVariable: 
            if box.spotVar != "":
                box.setToolTip(box.spotVar)
            box.setText(box.var.var)
        elif type(box.var) == VariableEquation: box.setText(box.var.name)
        elif type(box.var) == VariableExpression: box.setText(box.var.name)

    def multiVar(self, caller : Slot): # dialog window to enter multiple variables for an equation
        dbox = QtWidgets.QDialog(self.dialog)
        dbox.setFixedSize(300, 200)
        dbox.setWindowTitle("Enter multiple variables...")

        spotstore = []
        if caller.spotVar != "": # check if something has already been loaded
            sp = caller.spotVar.split(",")
            for s in sp:
                spotstore.append(s)

        pre = []
        if type(caller.var) == list: # get any variables that were previously in use
            for v in caller.var:
                pre.append(v)

        foc = None
        def store(wid): # whenever text is changed; store current focussed widget
            nonlocal foc # means global for nested functions
            foc = wid
        
        QtWidgets.QLabel("Variables", dbox).move(10, 10)
        cbox1 = DragBox(dbox)
        cbox1.doDrag = False
        cbox1.move(10, 40)
        its = [self.inputs[0][1].itemText(indx) for indx in range(self.inputs[0][1].count())]
        cbox1.focusInEvent = lambda event: store(cbox1)
        cbox1.addItems(its)
        cbox1.vars = self.inputs[0][1].vars
        QtWidgets.QLabel("Equations", dbox).move(100, 10)
        cbox2 = DragBox(dbox)
        cbox2.doDrag = False
        cbox2.move(100, 40)
        its = [self.inputs[0][2].itemText(indx) for indx in range(self.inputs[0][2].count())]
        cbox2.addItems(its)
        cbox2.vars = self.inputs[0][2].vars
        cbox2.focusInEvent = lambda event: store(cbox2)
        btn = QtWidgets.QPushButton("Add", dbox)
        btn.setGeometry(200, 39, 75, 25)
        
        cbox = DragBox(dbox)
        cbox.move(10, 100)
        cbox.doDrag = False
        cbox.vars = pre
        for v in pre:
            if type(v) == IndicatorVariable: cbox.addItem(v.var)
            elif type(v) == VariableEquation: cbox.addItem(v.name)

        def add(): # add currently selected thing to cbox
            nonlocal spotstore
            if type(foc) != DragBox: return
            if len(foc.vars) == 0: return
            vind = foc.currentIndex()
            
            if type(foc.vars[vind]) == IndicatorVariable:
                if indinfo[foc.vars[vind].indName]["vtypes"][indinfo[foc.vars[vind].indName]["vars"].index(foc.vars[vind].var)] == list:
                    sbox = QtWidgets.QDialog(dbox)
                    sbox.setWindowTitle("Enter spot...")
                    sbox.setFixedSize(200, 120)
                    sbox.setWindowFlags(sbox.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint) # keep all but close button
                    QtWidgets.QLabel("Enter spot in python form", sbox).move(10, 10)
                    slot = Slot(sbox)
                    slot.setGeometry(10, 30, 130, 22)
                    slot.setText("-1")
                    btn = QtWidgets.QPushButton("OK", sbox)
                    btn.move(65, 75)
                    def spotvar(): # spot variable dialog box
                        wid = QtWidgets.QDialog(sbox)
                        wid.setFixedSize(300, 150)
                        wid.setWindowTitle("Advanced Spot...")
                        QtWidgets.QLabel("Select a variable for spot", wid).move(10, 10)

                        fo = None
                        def stor(w): # whenever text is changed; store current focussed widget
                            nonlocal fo # means global for nested functions
                            fo = w

                        QtWidgets.QLabel("Variables", wid).move(10, 40)
                        c1 = DragBox(wid)
                        c1.doDrag = False
                        c1.move(10, 70)
                        its = []
                        for indx in range(self.inputs[0][1].count()):
                            var = self.inputs[0][1].vars[indx]
                            if indinfo[var.indName]["vtypes"][indinfo[var.indName]["vars"].index(var.var)] == int: # if type of variable is int
                                its.append(self.inputs[0][1].itemText(indx))
                                c1.vars.append(self.inputs[0][1].vars[indx])
                        c1.focusInEvent = lambda event: stor(c1)
                        c1.addItems(its)
                        QtWidgets.QLabel("Equations", wid).move(100, 40)
                        c2 = DragBox(wid)
                        c2.doDrag = False
                        c2.move(100, 70)
                        its = [self.inputs[0][2].itemText(indx) for indx in range(self.inputs[0][2].count())]
                        c2.addItems(its)
                        c2.vars = self.inputs[0][2].vars
                        c2.focusInEvent = lambda event: stor(c2)
                        btn = QtWidgets.QPushButton("Select", wid)
                        btn.move(115, 115)
                        def okk():
                            if len(fo.vars) != 0:
                                var = fo.vars[fo.currentIndex()]
                                if type(var) == IndicatorVariable: slot.setText(var.var)
                                elif type(var) == VariableEquation: slot.setText(var.name)
                                slot.var = var
                                slot.setLocked()
                            wid.close()
                        btn.clicked.connect(okk)
                        wid.exec()
                    # show some option to show advanced spot options
                    abtn = QtWidgets.QPushButton("Adv.", sbox)
                    abtn.setGeometry(155, 29, 35, 24)
                    abtn.clicked.connect(spotvar)
                    def check():
                        if slot.var is not None: # if a variable is used
                            if type(slot.var) == IndicatorVariable: t = "v"
                            elif type(slot.var) == VariableEquation: t = "e"
                            spotstore.append("!" + t + str(slot.var.id))
                        else:
                            num = slot.text()
                            if not isint(num):
                                self.errormsg("Spot has to be an integer.")
                                return
                            #box.spotVar = num
                            spotstore.append(num) # save spot to nonlocal
                        sbox.close()
                    btn.clicked.connect(check)
                    sbox.exec()

            cbox.addItem(foc.currentText())
            cbox.vars.append(foc.vars[vind])

        btn.clicked.connect(add)

        def ok():
            if len(cbox.vars) < 2: # if too little variables entered
                self.errormsg("Too few values entered.")
                return
            caller.var = [] # turn single var into multiple
            for v in cbox.vars:
                caller.var.append(v)
            caller.spotVar = "" # store spot as multiple seperated by commas
            for s in spotstore:
                caller.spotVar += s + ","
            caller.setText("Multiple")
            caller.setLocked()
            dbox.close()

        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(115, 160)
        btn.clicked.connect(ok)
        dbox.exec()

    def delVariable(self, cbox : DragBox, var): # delete variable from cbox
        # check if variable is currently being edited
        if type(var) == IndicatorVariable and self.inputs[2][0].active: # if variable is indicator or variable and a variable is being edited
            cu = self.inputs[2][0].curr  # indicator currently edited
            if var.indName == self.inputs[0][6].vars[cu].indName and var.args == self.inputs[0][6].vars[cu].args:
                self.errormsg("Can't delete the variable currently edited.")
                return
        elif type(var) == VariableEquation and self.inputs[2][1].active: # if equation and equation edited
            if self.inputs[0][2].vars.index(var) == self.inputs[2][1].curr:
                self.errormsg("Can't delete the equation currently edited.")
                return
        elif type(var) == VariableExpression and self.inputs[2][2].active: # if equation and equation edited
            if self.inputs[0][5].vars.index(var) == self.inputs[2][2].curr:
                self.errormsg("Can't delete the expression currently edited.")
                return

        # get tree of what would also be deleted (get dependencies)
        deps = []
        def upTree(typ, idd, org): # checks dependencies of other variables from given variable
            # org is original variable
            if typ == "i": # indicator
                for va in self.inputs[0][1].vars: # for every variable
                    # check if ind and args align
                    if va.indName == org.indName and va.args == org.args:
                        if ("v", va.id) not in deps: deps.append(("v", va.id))
                        upTree("v", va.id, va) # check if this would also affect other upper variables
                for ex in self.inputs[0][5].vars: # if variable has exist expression
                    if ex.type == "Variable":
                        if ex.args[0] == org.indName:
                            if len(ex.args) != 1:
                                if ex.args[1:] != org.args: break # if arguments dont fit; not same indicator
                            if ("x", ex.id) not in deps: deps.append(("x", ex.id))
                            upTree("x", ex.id, ex)

            elif typ == "v": # variable
                # check if used in either indicator, expression or equation
                for ir in self.inputs[0][6].vars: # for every indicator
                    for a in ir.args:
                        if type(a) == str and"%v" in a:
                            sp = a.split("%")
                            if int(sp[1].split("v")[1]) == idd: # if id used
                                if ("i", ir.id) not in deps: deps.append(("i", ir.id))
                                upTree("i", ir.id, ir)
                for eq in self.inputs[0][2].vars: # for every equation
                    for a in eq.args:
                        if type(a) == str and "|" in a: # if multiple variables in arguments
                            sps = a.split("|")
                            for p in sps:
                                sp = p.split("%")
                                if "%v" in p: # only for variables
                                    if int(sp[1].split("v")[1]) == idd: # if variable id is used
                                        if ("e", eq.id) not in deps: deps.append(("e", eq.id))
                                        upTree("e", eq.id, eq)
                                    elif "v" in p: # check if spot is determined by variable
                                        ppp = sp[2].split(",")
                                        for pp in ppp:
                                            if not isint(pp):
                                                t = pp[0]
                                                i = int(pp[1:])
                                                if t == "v" and i == idd:
                                                    if ("e", eq.id) not in deps: deps.append(("e", eq.id))
                                                    upTree("e", eq.id, eq)
                        elif type(a) == str and "%v" in a: # if a variable is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("v")[1]) == idd: # if variable id is used
                                if ("e", eq.id) not in deps: deps.append(("e", eq.id))
                                upTree("e", eq.id, eq)
                        elif type(a) == str and "v" in a: # check if spot is determined by variable
                            ppp = a.split("%")[2].split(",") # only get spot
                            for pp in ppp:
                                if "v" in pp:
                                    t = pp[1] # assuming ! is at 0
                                    i = int(pp[2:])
                                    if t == "v" and i == idd:
                                        if ("e", eq.id) not in deps: deps.append(("e", eq.id))
                                        upTree("e", eq.id, eq)
                for ex in self.inputs[0][5].vars: # for every expression
                    for a in ex.args:
                        if type(a) == str and "%v" in a: # if a variable is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("v")[1]) == idd: # if variable id is used
                                if ("x", ex.id) not in deps: deps.append(("x", ex.id))
                                upTree("x", ex.id, ex)
            elif typ == "e": # equation
                # check if used in either indicator, expression or equation
                for ir in self.inputs[0][6].vars: # for every indicator
                    for a in ir.args:
                        if "%e" in str(a):
                            sp = a.split("%")
                            if int(sp[1].split("e")[1]) == idd: # if id used
                                if ("i", ir.id) not in deps: deps.append(("i", ir.id))
                                upTree("i", ir.id, ir)
                for eq in self.inputs[0][2].vars: # for every equation
                    for a in eq.args:
                        if type(a) == str and "|" in a: # if multiple variables in arguments
                            sps = a.split("|")
                            for p in sps:
                                sp = p.split("%")
                                if "%e" in p: # only for equations
                                    if int(sp[1].split("e")[1]) == idd: # if equation id is used
                                        if ("e", eq.id) not in deps: deps.append(("e", eq.id))
                                        upTree("e", eq.id, eq)
                        elif type(a) == str and "%e" in a: # if a equation is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("e")[1]) == idd: # if equation id is used
                                if ("e", eq.id) not in deps: deps.append(("e", eq.id))
                                upTree("e", eq.id, eq)
                for ex in self.inputs[0][5].vars: # for every expression
                    for a in ex.args:
                        if type(a) == str and "%e" in a: # if a equation is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("e")[1]) == idd: # if equation id is used
                                if ("x", ex.id) not in deps: deps.append(("x", ex.id))
                                upTree("x", ex.id, ex)
            elif typ == "x": # expression
                # check if used in another expression
                for ex in self.inputs[0][5].vars: # for every expression
                    for a in ex.args:
                        if type(a) == str and "%x" in a: # if a expression is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("x")[1]) == idd: # if expression id is used
                                if ("x", ex.id) not in deps: deps.append(("x", ex.id))
                                upTree("x", ex.id, ex)

        def downTree(ind, args): # if variable is deleted; also delete indicator and check consequences
            for indi in self.inputs[0][6].vars: # for every indicator
                if indi.indName == ind and indi.args == args:
                    if ("i", indi.id) not in deps: deps.append(("i", indi.id))
                    upTree("i", indi.id, indi)

        def find(typ, idd): # return index of item in typ list
            if typ == "i": search = self.inputs[0][6].vars
            elif typ == "v": search = self.inputs[0][1].vars
            elif typ == "e": search = self.inputs[0][2].vars
            else: search = self.inputs[0][5].vars

            for v in range(len(search)):
                if search[v].id == idd:
                    return v

        typ = ""
        try:
            if type(var) == IndicatorVariable and var.var != "": # if variable do downtree to also delete entire indicator
                downTree(var.indName, var.args)
                typ = "v"
            elif type(var) == VariableExpression and var.type == "Variable": # if exist expression and expression deleted also delete indicator
                for ir in self.inputs[0][6].vars: # for every indicator
                    if ir.indName == var.args[0]:
                        if len(var.args) != 1:
                            if var.args[1:] != ir.args: break # if arguments dont fit; not same indicator
                        if ("i", ir.id) not in deps: deps.append(("i", ir.id))
                        upTree("i", ir.id, ir)
                typ = "x"
            else:
                if type(var) == IndicatorVariable: typ = "i" # indicator
                elif type(var) == VariableEquation: typ = "e" # equation
                else: typ = "x" # expression
                upTree(typ, var.id, var) # get dependent variables
        except RecursionError:
            if type(var) == IndicatorVariable: 
                if var.var == "": typ = "i" # indicator
                else: typ = "v"
            elif type(var) == VariableEquation: typ = "e" # equation
            else: typ = "x" # expression
            #return
        
        # delete self if self in deps
        if (typ, var.id) in deps: deps.remove((typ, var.id))

        # ask user whether to delete (which would also delete depencencies)
        rep = {"i":6, "v":1, "e":2, "x":5} # replace type with these
        if len(deps) != 0:
            st = ""
            for d in deps:
                st += self.inputs[0][rep[d[0]]].vars[find(d[0], d[1])].name + "\n" # get str with all names of variables

            threading.Thread(target=lambda:playsound("Exclamation")).start()
            result = QtWidgets.QMessageBox.question(self, "Are you sure?", "Deleting this would also delete Variables:\n" + st, 
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
            if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                return
        # delete variable + dependent variables

        dels = {"i":[], "v":[], "e":[], "x":[]}
        keys = ["i", "v", "e", "x"]

        for d in deps:
            dels[d[0]].append(find(d[0], d[1])) # get indexes of all in right category
        
        for key in keys:
            dels[key].sort()
            dels[key].reverse() # reverse so that pop can easily remove
            for p in dels[key]:
                self.inputs[0][rep[key]].vars.pop(p)
                self.inputs[0][rep[key]].removeItem(p)

        cbox.removeItem(cbox.vars.index(var))
        cbox.vars.remove(var)

        # reset condition creator to not allow ghost variables
        self.conditionCreatorLayout()

    def renVariable(self, what): # asks whether to change both cbox text and current variable name
        dbox = QtWidgets.QDialog(self.dialog)
        dbox.setWindowTitle("Change Name...")
        dbox.setFixedSize(200, 120)
        QtWidgets.QLabel("Please enter a new name", dbox).move(10, 10)
        tbox = QtWidgets.QLineEdit(dbox)
        tbox.setGeometry(10, 30, 130, 22)
        isOK = False # whether ok was pressed or the window was closed
        def ok():
            nonlocal isOK
            isOK = True
            dbox.close()
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(65, 75)
        btn.clicked.connect(ok)
        dbox.exec()
        name = tbox.text()
        if what == "e": i = 2
        elif what == "x": i = 5
        if isOK:
            self.inputs[0][i].setItemText(self.inputs[0][i].currentIndex(), name)
            self.inputs[0][i].vars[self.inputs[0][i].currentIndex()].name = name

    def editVariable(self, var): # reshow variable with all arguments and change add button to save
        if type(var) == IndicatorVariable: # indicator or variable
            self.inputs[0][0].setCurrentText(indargs[var.indName]["name"]) # set cbox to indicator
            for v in self.inputs[0][6].vars: # get index of indicator in indicator box
                if v.indName == var.indName and v.args == var.args: break
            self.inputs[0][6].setCurrentIndex(self.inputs[0][6].vars.index(v))
            #self.inputs[0][6].setEnabled(False) # lock indicators
            self.inputs[2][0].clicked.disconnect()
            self.inputs[2][0].clicked.connect(lambda: self.addButton("Indicator", True))
            self.inputs[2][0].setText("Save")
            self.inputs[2][0].curr = self.inputs[0][6].vars.index(v)
            #self.inputs[2][0].setEnabled(True)
            
            i = 0
            for a in self.inputs[1][0]:
                if type(a) == Slot:
                    if type(var.args[i]) != str: a.setText(str(var.args[i])) # for each argument change text of the inputs
                    else: # "%" not in var.args[i]
                        sp = var.args[i].split("%")
                        t = sp[1][0]
                        if t == "v": search = self.inputs[0][1]
                        else: search = self.inputs[0][2]
                        for s in search.vars:
                            if s.id == int(sp[1].split(t)[1]): break # get variable referenced
                        a.setLocked()
                        if t == "v": a.setText(s.var)
                        else: a.setText(s.name)
                        a.var = s

                    i += 1
        elif type(var) == VariableEquation: # equation
            self.inputs[0][3].setCurrentText(var.type) # set equation box to correct one
            #self.inputs[0][2].setEnabled(False) # lock equations
            self.inputs[2][1].setActive(True)
            self.inputs[2][1].clicked.disconnect()
            self.inputs[2][1].clicked.connect(lambda: self.addButton("Equation", True))
            self.inputs[2][1].setText("Save")
            self.inputs[2][1].curr = self.inputs[0][2].vars.index(var)

            i = 0
            for a in self.inputs[1][1]:
                if type(a) == Slot: # either variable or number in slot
                    if type (var.args[i]) == str and "%" in var.args[i]: # variable
                        if "|" in var.args[i]: # multiple variables in str
                            sp = var.args[i].split("|")
                            spotvar = ""
                            a.var = []
                            a.setLocked()
                            for s in sp:
                                sps = s.split("%")
                                t = sps[1][0] # type
                                if t == "v": 
                                    spotvar += sps[2] + "," # reconvert spots into spotvar with commas
                                    search = self.inputs[0][1] # variable
                                else: search = self.inputs[0][2] # other equation
                                for ind in range(len(search.vars)):
                                    if search.vars[ind].id == int(sps[1][1:]): break # get index of variable in own list
                                # if vtype == "v": 
                                #     a.setText(search.vars[ind].var)
                                # else: a.setText(search.vars[ind].name)
                                a.var.append(search.vars[ind]) # get variables back into slot
                            a.setText("Multiple")
                        else:
                            sp = var.args[i].split("%")
                            vtype = sp[1][0]
                            vid = int(sp[1][1:])
                            if vtype == "v": search = self.inputs[0][1] # variable
                            else: search = self.inputs[0][2] # other equation
                            for ind in range(len(search.vars)):
                                if search.vars[ind].id == vid: break # get index of variable in own list
                            if vtype == "v": 
                                a.setText(search.vars[ind].var)
                                a.spotVar = sp[2]
                            else: a.setText(search.vars[ind].name)
                            a.setLocked()
                            a.var = search.vars[ind]
                    else: # number
                        a.setText(str(var.args[i]))
                elif type(a) == QtWidgets.QComboBox: # combobox args
                    a.setCurrentText(var.args[i])
                i += 1
        elif type(var) == VariableExpression: # expression
            # also check whether an expression is part of a variable and then run
            if var.type == "Variable":
                # find indicator variable and run edit method
                for ir in self.inputs[0][6].vars:
                    if ir.indName == var.args[0] and ir.args == var.args[1:]: # find indicator
                        self.editVariable(ir)
                        return
            self.inputs[0][4].setCurrentText(var.type)
            #self.inputs[0][5].setEnabled(False) # lock expressions
            self.inputs[2][2].setActive(True)
            self.inputs[2][2].clicked.disconnect()
            self.inputs[2][2].clicked.connect(lambda: self.addButton("Expression", True))
            self.inputs[2][2].setText("Save")
            self.inputs[2][2].curr = self.inputs[0][5].vars.index(var)

            i = 0
            for a in self.inputs[1][2]:
                if type(a) == Slot: # either variable or number in slot
                    if type (var.args[i]) == str and "%" in var.args[i]: # variable
                        sp = var.args[i].split("%")
                        vtype = sp[1][0]
                        vid = int(sp[1][1:])
                        if vtype == "v": search = self.inputs[0][1] # variable
                        elif vtype == "e": search = self.inputs[0][2] # equation
                        else: search = self.inputs[0][5] # other expression
                        for ind in range(len(search.vars)):
                            if search.vars[ind].id == vid: break # get index of variable in own list
                        if vtype == "v": 
                            a.setText(search.vars[ind].var)
                            a.spotVar = sp[2]
                        else: a.setText(search.vars[ind].name)
                        a.setLocked()
                        a.var = search.vars[ind]
                    else: # number
                        a.setText(str(var.args[i]))
                elif type(a) == QtWidgets.QComboBox: # combobox args
                    a.setCurrentText(var.args[i])
                i += 1

    def getName(self, typ, extra=[]): # gets name for given variable using its type and args
        # variables = []
        # temp = [1, 2, 5]
        # for t in temp: variables += self.inputs[0][t].vars
        name = ""
        if typ == "e":
            if self.inputs[0][3].currentText() == "Basic":
                name += self.inputs[1][1][0].text()
                if type(self.inputs[1][1][0].var) == IndicatorVariable:
                    if str(self.inputs[1][1][0].spotVar) != "-1": name += "(" + str(self.inputs[1][1][0].spotVar) + ")"
                name += self.inputs[1][1][1].currentText()
                name += self.inputs[1][1][2].text()
                if type(self.inputs[1][1][2].var) == IndicatorVariable:
                    if str(self.inputs[1][1][2].spotVar) != "-1": name += "(" + str(self.inputs[1][1][2].spotVar) + ")"
            elif self.inputs[0][3].currentText() == "Constants":
                name = self.inputs[1][1][0].currentText()
            elif self.inputs[0][3].currentText() in ["Trigonometric", "Functions"]:
                name += self.inputs[1][1][0].currentText() + "("
                name += self.inputs[1][1][1].text()
                if type(self.inputs[1][1][1].var) == IndicatorVariable:
                    if str(self.inputs[1][1][1].spotVar) != "-1": name += "(" + str(self.inputs[1][1][1].spotVar) + ")"
                name += ")"
            elif self.inputs[0][3].currentText() == "Aggregates":
                name += self.inputs[1][1][0].currentText() + "("
                if type(self.inputs[1][1][1].var) == IndicatorVariable: 
                    name += self.inputs[1][1][1].text()
                    name += "(" + str(self.inputs[1][1][1].spotVar) + ")"
                elif type(self.inputs[1][1][1].var) == list:
                    for v in self.inputs[1][1][1].var:
                        name += v.name[0] + ","
                name += ")"
            elif self.inputs[0][3].currentText() == "Round":
                name += "Round("
                name += self.inputs[1][1][0].text()
                if type(self.inputs[1][1][0].var) == IndicatorVariable:
                    if str(self.inputs[1][1][0].spotVar) != "-1": name += "(" + str(self.inputs[1][1][0].spotVar) + ")"
                name += ", "
                name += self.inputs[1][1][1].text()
                if type(self.inputs[1][1][1].var) == IndicatorVariable:
                    if str(self.inputs[1][1][1].spotVar) != "-1": name += "(" + str(self.inputs[1][1][1].spotVar) + ")"
                name += ")"
            elif self.inputs[0][3].currentText() == "Spot of":
                name += "Spot of "
                name += self.inputs[1][1][0].text()
                if type(self.inputs[1][1][0].var) == IndicatorVariable:
                    if str(self.inputs[1][1][0].spotVar) != "-1": name += "(" + str(self.inputs[1][1][0].spotVar) + ")"
                name += "in "
                if type(self.inputs[1][1][1].var) == IndicatorVariable: 
                    name += self.inputs[1][1][1].text()
                    name += "(" + str(self.inputs[1][1][1].spotVar) + ")"
                elif type(self.inputs[1][1][1].var) == list:
                    for v in self.inputs[1][1][1].var:
                        name += v.name[0] + ","
            if name == "": name = self.inputs[0][3].currentText() + " " + str(len(self.inputs[0][2].vars)) # failsave
        elif typ == "x":
            if self.inputs[0][4].currentText() in ["Compare", "Combine"]:
                name += self.inputs[1][2][0].text()
                if type(self.inputs[1][2][0].var) == IndicatorVariable:
                    if str(self.inputs[1][2][0].spotVar) != "-1": name += "(" + str(self.inputs[1][2][0].spotVar) + ")"
                name += self.inputs[1][2][1].currentText()
                name += self.inputs[1][2][2].text()
                if type(self.inputs[1][2][2].var) == IndicatorVariable:
                    if str(self.inputs[1][2][2].spotVar) != "-1": name += "(" + str(self.inputs[1][2][2].spotVar) + ")"
            elif self.inputs[0][4].currentText() == "Not":
                name += "Not "
                name += self.inputs[1][2][0].name
            elif self.inputs[0][4].currentText() == "Dynamic Near":
                name += "Near("
                name += self.inputs[1][2][0].text()
                if type(self.inputs[1][2][0].var) == IndicatorVariable:
                    if str(self.inputs[1][2][0].spotVar) != "-1": name += "(" + str(self.inputs[1][2][0].spotVar) + ")"
                    name += ", "
                name += self.inputs[1][2][1].text()
                if type(self.inputs[1][2][1].var) == IndicatorVariable:
                    if str(self.inputs[1][2][1].spotVar) != "-1": name += "(" + str(self.inputs[1][2][1].spotVar) + ")"
                name += ")"
            if name == "": name = self.inputs[0][4].currentText() + " " + str(len(self.inputs[0][5].vars)) # failsave
        elif typ == "re": # risk equations
            # extra is [type, arg[0], arg[1], arg[2]]
            if extra[0] == "Basic":
                name += extra[1].text()
                if type(extra[1].var) == IndicatorVariable:
                    if str(extra[1].spotVar) != "-1": name += "(" + str(extra[1].spotVar) + ")"
                name += extra[2].currentText()
                name += extra[3].text()
                if type(extra[3].var) == IndicatorVariable:
                    if str(extra[3].spotVar) != "-1": name += "(" + str(extra[3].spotVar) + ")"
            elif extra[0] == "Constants":
                name = extra[1].currentText()
            elif extra[0] in ["Trigonometric", "Functions"]:
                name += extra[1].currentText() + "("
                name += extra[2].text()
                if type(extra[2].var) == IndicatorVariable:
                    if str(extra[2].spotVar) != "-1": name += "(" + str(extra[2].spotVar) + ")"
                name += ")"
            elif extra[0] == "Aggregates":
                name += extra[1].currentText() + "("
                if type(extra[2].var) == IndicatorVariable: 
                    name += extra[2].text()
                    name += "(" + str(extra[2].spotVar) + ")"
                elif type(extra[2].var) == list:
                    for v in extra[2].var:
                        name += v.name[0] + ","
                name += ")"
            elif extra[0] == "Round":
                name += "Round("
                name += extra[1].text()
                if type(extra[1].var) == IndicatorVariable:
                    if str(extra[1].spotVar) != "-1": name += "(" + str(extra[1].spotVar) + ")"
                name += ", "
                name += extra[2].text()
                if type(extra[2].var) == IndicatorVariable:
                    if str(extra[2].spotVar) != "-1": name += "(" + str(extra[2].spotVar) + ")"
                name += ")"
            elif extra[0] == "Spot of":
                name += "Spot of "
                name += extra[1].text()
                if type(extra[1].var) == IndicatorVariable:
                    if str(extra[1].spotVar) != "-1": name += "(" + str(extra[1].spotVar) + ")"
                name += "in "
                if type(extra[2].var) == IndicatorVariable: 
                    name += extra[2].text()
                    name += "(" + str(extra[2].spotVar) + ")"
                elif type(extra[2].var) == list:
                    for v in extra[2].var:
                        name += v.name[0] + ","
            if name == "": name = extra[0] + " -1" # failsave
        return name

    def addButton(self, what, edit=False): # different add buttons in conditon creator
        if what == "Indicator":
            # check if indicator args are valid and add indicator variables
            def isType(thing, typ): # pass thing and check if it's the type
                if typ == str: return True
                elif typ == int: return isint(thing)
                elif typ == float: return isfloat(thing)
            
            for key in avinds: # find key corresponding to combobox text
                if indargs[key]["name"] == self.inputs[0][0].currentText(): break
            
            # error code
            for i in range(len(indargs[key]["args"])):
                if self.inputs[1][0][i].var is None: # only for non variables
                    value = self.inputs[1][0][i].text()
                    c = indargs[key]["args"][i][1:]
                    
                    if not isType(value, c[1]): 
                        self.errormsg(value + " is not of type " + str(c[1]).split("\'")[1] + ".")
                        return
                    
                    minn = c[2]
                    if minn == "nan": minn = -len(raw[logic.rawind])
                    if c[2] != "-inf": # if it has a bottom limit
                        if c[1](value) < minn:
                            self.errormsg(value + " is out of range.")
                            return
                    
                    maxx = c[3]
                    if maxx == "nan": maxx = len(raw[logic.rawind])-1 # nan means len(stock)
                    if maxx != "inf":
                        if c[1](value) > maxx:
                            self.errormsg(value + " is out of range.")
                            return
            
            # get args
            args = []
            i = 0
            for a in self.inputs[1][0]:
                c = indargs[key]["args"][i][1:]
                if a.var is None: 
                    args.append(c[1](a.text()))
                else:
                    if type(a.var) == IndicatorVariable: t = "v"
                    else: t = "e"
                    st = "%" + t + str(a.var.id)
                    if a.spotVar != "":
                        st += "%" + a.spotVar
                    if edit and t == "v": # avoid self reference when editing variables
                        # get indicator of slot variable
                        for ir in self.inputs[0][6].vars:
                            if ir.indName == a.var.indName and ir.args == a.var.args: break
                        # check whether indicator id is same as parent variable
                        if ir.id == self.inputs[0][6].vars[self.inputs[0][6].currentIndex()].id:
                            self.errormsg("Self reference error.")
                            return
                        # maybe also add advanced check for equations that use the indicator and reject that
                    args.append(st)
                i += 1

            # check if exact indicator already exists
            if not edit:
                for ind in self.inputs[0][6].vars:
                    if ind.args == args and ind.indName == key:
                        self.errormsg("Same Indicator already exists.")
                        return
            else:
                for ind in self.inputs[0][6].vars:
                    if ind.args == args and ind.indName == key and self.inputs[0][6].vars.index(ind) != self.inputs[0][6].currentIndex(): # allow current variable to stay
                        self.errormsg("Same Indicator already exists.")
                        return

            # add variables to combobox
            varChanged = False
            if not edit:
                self.inputs[0][1].addItems(indinfo[key]["vars"]) # variables
                self.inputs[0][6].addItem(self.inputs[0][0].currentText() + " " + str(len(self.inputs[0][6].vars))) # indicators
                if indinfo[key]["existcheck"]: # if a check is first needed
                    self.inputs[0][5].addItem(self.inputs[0][0].currentText() + " " + str(len(self.inputs[0][6].vars))) # expression with same name as indicator
            else: # if variable was edited
                old = deepcopy(self.inputs[0][6].vars[self.inputs[2][0].curr]) # old variable
                if key != self.inputs[0][6].vars[self.inputs[2][0].curr].indName: # if variable type was changed
                    varChanged = True
                    # delete all prior variables from indicator
                    count = 0
                    for v in self.inputs[0][6].vars:
                        if old.args == v.args and old.indName == v.indName: count += 1 # count occurences of variable
                    poplist = []
                    if count > 1: # if there are more than one; leave one set of variables
                        varSet = []
                        i = 0
                        for v in self.inputs[0][1].vars:
                            if old.args == v.args and old.indName == v.indName: # if variable is part of indicator to be deleted
                                if v.var not in varSet: varSet.append(v.var) # if first occurence of variable
                                else: poplist.append(i)
                                i += 1
                    
                    else: # only one occurrence of variable
                        i = 0
                        for v in self.inputs[0][1].vars:
                            if old.args == v.args and old.indName == v.indName: # check for old variables
                                poplist.append(i)
                                i += 1
                        
                    poplist.reverse()
                    for p in poplist: # remove duplicates
                        self.inputs[0][1].vars.pop(p)
                        self.inputs[0][1].removeItem(p)

                    # add new variables and replace indicator text
                    self.inputs[0][1].addItems(indinfo[key]["vars"])
                    self.inputs[0][6].setItemText(self.inputs[2][0].curr, self.inputs[0][0].currentText() + " " + str(len(self.inputs[0][6].vars)))

            if varChanged or not edit: # either if variable type has changed or no variable is being edited
                # get ids
                ids = [0, []] # 0 is for indicator, 1 is for variables

                # indicator id
                idd = 0
                i = 0
                while i < len(self.inputs[0][6].vars): # check if id is already in use
                    if self.inputs[0][6].vars[i].id == idd:
                        idd += 1
                        i = -1 # if id in use go up and restart process
                    i += 1
                ids[0] = idd

                # variable ids
                used = [] # already used ids
                for v in self.inputs[0][1].vars:
                    used.append(v.id)

                idd = 0 # don't reset id in loop for performance reasons
                for v in indinfo[key]["vars"]: # get ids for every variable
                    i = 0
                    while i < len(used): # check if id is already in use
                        if used[i] == idd:
                            idd += 1
                            i = -1 # if id in use go up and restart process
                        i += 1
                    used.append(idd)
                    ids[1].append(idd)
                
                if indinfo[key]["existcheck"]:
                    # expression id
                    idd = 0
                    i = 0
                    while i < len(self.inputs[0][5].vars): # check if id is already in use
                        if self.inputs[0][5].vars[i].id == idd:
                            idd += 1
                            i = -1 # if id in use go up and restart process
                        i += 1
                    ids.append(idd)

            i = 0
            if not edit or varChanged:
                for v in indinfo[key]["vars"]:
                    self.inputs[0][1].vars.append(IndicatorVariable(key, args, v, ids[1][i]))
                    self.inputs[0][1].vars[-1].name = v
                    i += 1
            elif edit and not varChanged: # if only variable args changed
                self.inputs[0][6].vars[self.inputs[2][0].curr].args = args
                for v in self.inputs[0][1].vars:
                    if old.args == v.args and old.indName == v.indName:
                        v.args = args
            
            if not edit: self.inputs[0][6].vars.append(IndicatorVariable(key, args, idd=ids[0]))
            elif varChanged: self.inputs[0][6].vars[-1].name = self.inputs[0][0].currentText() + " " + str(len(self.inputs[0][6].vars))

            if not edit and indinfo[key]["existcheck"]:
                self.inputs[0][5].vars.append(VariableExpression(typ="Variable", args=[key]+args, idd=ids[2]))
                self.inputs[0][5].vars[-1].name = self.inputs[0][0].currentText() + " " + str(len(self.inputs[0][6].vars)-1)
            elif edit and indinfo[key]["existcheck"]:
                # search for expression and edit args
                for i in range(len(self.inputs[0][5].vars)):
                    ex = self.inputs[0][5].vars[i]
                    if ex.type == "Variable":
                        if ex.args[0] == key and ex.args[1:] == old.args:
                            self.inputs[0][5].vars[i].args = [key]+args

            if edit: # also reset button and lock
            #     self.inputs[0][6].setEnabled(True)
            #     self.inputs[2][0].move(-200, -50)
                self.inputs[2][0].setActive(False)
                self.conditionCreatorLayout()

        elif what == "Equation":
            if self.prefs[self.findPref("Ask to name variables")][1]:
                dbox = QtWidgets.QDialog(self.dialog)
                dbox.setWindowTitle("Equation Name...")
                dbox.setFixedSize(200, 120)
                QtWidgets.QLabel("Name this new equation? (Optional)", dbox).move(10, 10)
                tbox = QtWidgets.QLineEdit(dbox)
                tbox.setGeometry(10, 30, 130, 22)
                btn = QtWidgets.QPushButton("OK", dbox)
                btn.move(65, 75)
                btn.clicked.connect(dbox.close)
                dbox.exec()
                #if tbox.text() == "": name = self.inputs[0][3].currentText() + " " + str(len(self.inputs[0][2].vars))
                if tbox.text() == "": name = self.getName("e")
                else: name = tbox.text()
            else: name = self.getName("e")
            args = []
            #vars = [] # vars is list of variables in equation
            for inp in self.inputs[1][1]:
                if type(inp) != Slot: # cbox
                    args.append(inp.currentText())
                else:
                    if inp.var is not None: # variable in slot
                        doList = False
                        if type(inp.var) == IndicatorVariable: t = "v" # variable
                        elif type(inp.var) == VariableEquation: t = "e" # equation
                        else: # list with multiple variables
                            doList = True
                        if not doList: # anything but a list
                            if edit and t == "e" and inp.var.id == self.inputs[0][2].vars[self.inputs[2][1].curr].id: # avoid self reference when editing variables
                                self.errormsg("Self reference error.")
                                return
                            if t != "v": args.append("%"+ t + str(inp.var.id)) # equation or expression
                            else: args.append("%" + t + str(inp.var.id) + "%" + inp.spotVar)

                            #vars.append(inp.var.id)
                        else:
                            st = ""
                            i = -1
                            for v in inp.var:
                                st += "%"
                                if type(v) == IndicatorVariable: t = "v" # variable
                                elif type(v) == VariableEquation: t = "e" # equation
                                st += t
                                st += str(inp.var.id)
                                if t == "v": # also include spot
                                    i += 1 # only advance i here because spots were only recorded from variables
                                    st += "%"
                                    st += inp.spotVar.split(",")[i]
                                elif t == "e": # else check for self reference
                                    if edit and v.id == self.inputs[0][2].vars[self.inputs[2][1].curr].id: # avoid self reference when editing variables
                                        self.errormsg("Self reference error.")
                                        return
                                if inp.var.index(v) != len(inp.var) - 1: # add seperator for all except last one
                                    st += "|"
                                #vars.append(v.id)
                            args.append(st)
                    else:
                        if not isfloat(inp.text()):
                            self.errormsg(str(inp.text()) + "is not a valid number.")
                            return
                        args.append(float(inp.text()))
            
            # get new unused id
            i = 0
            idd = 0
            while i < len(self.inputs[0][2].vars): # check if id is already in use
                if self.inputs[0][2].vars[i].id == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1

            if not edit:
                self.inputs[0][2].vars.append(VariableEquation(name, self.inputs[0][3].currentText(), args, idd))
                self.inputs[0][2].addItem(name)
            else:
                self.inputs[0][2].vars[self.inputs[2][1].curr].type = self.inputs[0][3].currentText()
                self.inputs[0][2].vars[self.inputs[2][1].curr].args = args
                #self.inputs[0][2].vars[self.inputs[2][1].curr].vars = vars
                self.inputs[0][2].vars[self.inputs[2][1].curr].name = name
                self.inputs[0][2].setItemText(self.inputs[2][1].curr, name)
                #self.inputs[0][2].setEnabled(True)
                #self.inputs[2][1].move(-200, -50)
                self.inputs[2][1].setActive(False)
                self.conditionCreatorLayout()
            
        elif what == "Expression":
            if self.prefs[self.findPref("Ask to name variables")][1]:
                dbox = QtWidgets.QDialog(self.dialog)
                dbox.setWindowTitle("Expression Name...")
                dbox.setFixedSize(200, 120)
                QtWidgets.QLabel("Name this new expression? (Optional)", dbox).move(10, 10)
                tbox = QtWidgets.QLineEdit(dbox)
                tbox.setGeometry(10, 30, 130, 22)
                btn = QtWidgets.QPushButton("OK", dbox)
                btn.move(65, 75)
                btn.clicked.connect(dbox.close)
                dbox.exec()
                # if tbox.text() == "": name = self.inputs[0][4].currentText() + " " + str(len(self.inputs[0][5].vars))
                if tbox.text() == "": name = self.getName("x")
                else: name = tbox.text()
            else: name = self.getName("x")
            args = []
            #vars = []
            for inp in self.inputs[1][2]:
                if type(inp) != Slot: # cbox
                    args.append(inp.currentText())
                else:
                    if inp.var is not None: # variable in slot
                        if type(inp.var) == IndicatorVariable: t = "v" # variable
                        elif type(inp.var) == VariableEquation: t = "e" # equation
                        else: t = "x" # expression
                        if edit and t == "x" and inp.var.id == self.inputs[0][5].vars[self.inputs[2][2].curr].id: # avoid self reference when editing variables
                            self.errormsg("Self reference error.")
                            return
                        if t != "v": args.append("%"+ t + str(inp.var.id)) # equation or expression
                        else: args.append("%" + t + str(inp.var.id) + "%" + inp.spotVar)
                        #vars.append(inp.var.id)
                    else:
                        if not isfloat(inp.text()):
                            self.errormsg(str(inp.text()) + "is not a valid number.")
                            return
                        args.append(float(inp.text()))
            
            # get id
            i = 0
            idd = 0
            while i < len(self.inputs[0][5].vars): # check if id is already in use
                if self.inputs[0][5].vars[i].id == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1

            if not edit:
                self.inputs[0][5].vars.append(VariableExpression(name, self.inputs[0][4].currentText(), args, idd))
                self.inputs[0][5].addItem(name)
            else:
                self.inputs[0][5].vars[self.inputs[2][2].curr].type = self.inputs[0][4].currentText()
                self.inputs[0][5].vars[self.inputs[2][2].curr].args = args
                #self.inputs[0][5].vars[self.inputs[2][2].curr].vars = vars
                self.inputs[0][5].vars[self.inputs[2][2].curr].name = name
                self.inputs[0][5].setItemText(self.inputs[2][2].curr, name)
                #self.inputs[0][5].setEnabled(True)
                #self.inputs[2][2].move(-200, -50)
                self.inputs[2][2].setActive(False)
                self.conditionCreatorLayout()

    def creatorExecute(self, parent): # checks for errors and adds condition to conditions 
        ind = self.inputs[3][0].ind # stored here bc why not

        if type(self.inputs[0]) == list: mode = True
        else: mode = False

        if mode:
            varsorted = []
            temp = [1, 2, 5, 6]
            for t in temp:
                varsorted.append(self.inputs[0][t].vars)
            filoffcol = [self.inputs[3][5].currentText(), self.inputs[3][4].text(), self.inputs[3][3].styleSheet().split(" ")[1][:-1]]
        else:
            varsorted = [[], [], [], []]
            for var in self.inputs[1].vars:
                if type(var) == IndicatorVariable:
                    if var.var == "": varsorted[3].append(var) # indicator
                    else: varsorted[0].append(var)
                elif type(var) == VariableEquation: varsorted[1].append(var)
                elif type(var) == VariableExpression: varsorted[2].append(var)
            filoffcol = [self.inputs[2][2].currentText(), self.inputs[2][1].text(), self.inputs[2][0].styleSheet().split(" ")[1][:-1]]

        # error code
        # check whether complex self reference was made i.e. a variable is dependent of equation of same variable
        def upTree(typ, idd, org): # checks dependencies of other variables from given variable
            # org is original variable
            if typ == "i": # indicator
                for va in varsorted[0]: # for every variable
                    # check if ind and args align
                    if va.indName == org.indName and va.args == org.args:
                        upTree("v", va.id, va) # check if this would also affect other upper variables
                for ex in varsorted[2]: # if variable has exist expression
                    if ex.type == "Variable":
                        if ex.args[0] == org.indName:
                            if len(ex.args) != 1:
                                if ex.args[1:] != org.args: break # if arguments dont fit; not same indicator
                            upTree("x", ex.id, ex)

            elif typ == "v": # variable
                # check if used in either indicator, expression or equation
                for ir in varsorted[3]: # for every indicator
                    for a in ir.args:
                        if type(a) == str and"%v" in a:
                            sp = a.split("%")
                            if int(sp[1].split("v")[1]) == idd: # if id used
                                upTree("i", ir.id, ir)
                for eq in varsorted[1]: # for every equation
                    for a in eq.args:
                        if type(a) == str and "|" in a: # if multiple variables in arguments
                            sps = a.split("|")
                            for p in sps:
                                sp = p.split("%")
                                if "%v" in p: # only for variables
                                    if int(sp[1].split("v")[1]) == idd: # if variable id is used
                                        upTree("e", eq.id, eq)
                                    elif "v" in p: # check if spot is determined by variable
                                        ppp = sp[2].split(",")
                                        for pp in ppp:
                                            if "v" in pp:
                                                t = pp[1] # assuming ! is at 0
                                                i = int(pp[2:])
                                                if t == "v" and i == idd:
                                                    upTree("e", eq.id, eq)
                        elif type(a) == str and "%v" in a: # if a variable is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("v")[1]) == idd: # if variable id is used
                                upTree("e", eq.id, eq)
                        elif type(a) == str and "v" in a: # check if spot is determined by variable
                            ppp = a.split("%")[2].split(",") # only get spot
                            for pp in ppp:
                                if "v" in pp:
                                    t = pp[1] # assuming ! is at 0
                                    i = int(pp[2:])
                                    if t == "v" and i == idd:
                                        upTree("e", eq.id, eq)
                for ex in varsorted[2]: # for every expression
                    for a in ex.args:
                        if type(a) == str and "%v" in a: # if a variable is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("v")[1]) == idd: # if variable id is used
                                upTree("x", ex.id, ex)
            elif typ == "e": # equation
                # check if used in either indicator, expression or equation
                for ir in varsorted[3]: # for every indicator
                    for a in ir.args:
                        if "%e" in str(a):
                            sp = a.split("%")
                            if int(sp[1].split("e")[1]) == idd: # if id used
                                upTree("i", ir.id, ir)
                for eq in varsorted[1]: # for every equation
                    for a in eq.args:
                        if type(a) == str and "|" in a: # if multiple variables in arguments
                            sps = a.split("|")
                            for p in sps:
                                sp = p.split("%")
                                if "%e" in p: # only for equations
                                    if int(sp[1].split("e")[1]) == idd: # if equation id is used
                                        upTree("e", eq.id, eq)
                        elif type(a) == str and "%e" in a: # if a equation is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("e")[1]) == idd: # if equation id is used
                                upTree("e", eq.id, eq)
                for ex in varsorted[2]: # for every expression
                    for a in ex.args:
                        if type(a) == str and "%e" in a: # if a equation is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("e")[1]) == idd: # if equation id is used
                                upTree("x", ex.id, ex)
            elif typ == "x": # expression
                # check if used in another expression
                for ex in varsorted[2]: # for every expression
                    for a in ex.args:
                        if type(a) == str and "%x" in a: # if a expression is in arguments
                            sp = a.split("%")
                            if int(sp[1].split("x")[1]) == idd: # if expression id is used
                                upTree("x", ex.id, ex)

        def downTree(ind, args): # if variable is deleted; also delete indicator and check consequences
            for indi in varsorted[3]: # for every indicator
                if indi.indName == ind and indi.args == args:
                    upTree("i", indi.id, indi)

        try:
            variabls = [] # will store all kinds of variables from condition creator
            # temp = [1, 2, 5, 6]
            for i in range(4):
                for v in varsorted[i]: variabls.append(v)
            
            for var in variabls:
                if type(var) == IndicatorVariable and var.var != "": # if variable do downtree to also delete entire indicator
                    downTree(var.indName, var.args)
                elif type(var) == VariableExpression and var.type == "Variable": # if exist expression and expression deleted also delete indicator
                    for ir in varsorted[3]: # for every indicator
                        if ir.indName == var.args[0]:
                            if len(var.args) != 1:
                                if var.args[1:] != ir.args: break # if arguments dont fit; not same indicator
                            upTree("i", ir.id, ir)
                else:
                    if type(var) == IndicatorVariable: typ = "i" # indicator
                    elif type(var) == VariableEquation: typ = "e" # equation
                    else: typ = "x" # expression
                    upTree(typ, var.id, var) # get dependent variables
        except RecursionError:
            self.errormsg("Recursion Error. Check for complex self references.")
            return

        if not isint(filoffcol[1]): 
            self.errormsg("Offset is not a valid number.")
            return
        elif int(filoffcol[1]) >= 0:
            self.errormsg("Future Error.\nOffset only works for relative (negative) values.")
            return

        if ind == -1:
            idd = 0
            i = 0
            while i < len(logic.conditions): # check if id is already in use
                if logic.conditions[i]["ID"] == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1
        
            # also get name
            dbox = QtWidgets.QDialog(self.dialog)
            dbox.setWindowTitle("Condition Name...")
            dbox.setFixedSize(200, 120)
            QtWidgets.QLabel("Name this new condition? (Optional)", dbox).move(10, 10)
            tbox = QtWidgets.QLineEdit(dbox)
            tbox.setGeometry(10, 30, 130, 22)
            btn = QtWidgets.QPushButton("OK", dbox)
            btn.move(65, 75)
            btn.clicked.connect(dbox.close)
            dbox.exec()
            if tbox.text() == "": name = "Condition " + str(len(logic.conditions))
            else: name = tbox.text()
        else:
            idd = logic.conditions[ind]["ID"]
            # also get name
            dbox = QtWidgets.QDialog(self.dialog)
            dbox.setWindowTitle("Condition Name...")
            dbox.setFixedSize(200, 120)
            QtWidgets.QLabel("Change name of this condition? (None will keep last)", dbox).move(10, 10)
            tbox = QtWidgets.QLineEdit(dbox)
            tbox.setGeometry(10, 30, 130, 22)
            btn = QtWidgets.QPushButton("OK", dbox)
            btn.move(65, 75)
            btn.clicked.connect(dbox.close)
            dbox.exec()
            if tbox.text() == "": name = logic.conditions[ind]["name"]
            else: name = tbox.text()
        
        self.mode.setCurrentText("Conditions/Indicators")

        color = filoffcol[2] # color in hex
        condict = {"ID":idd, "vars":variabls, "data":[], "color":color, "name":name, "filters":[int(filoffcol[1]), filoffcol[0]], "deps":[]}
        if ind == -1: logic.conditions.append(condict)
        else: logic.conditions[ind] = condict 

        data = logic.getCondtitionData(conid=idd)
        logic.conditions[ind]["data"] = data
        self.marked = []
        for d in data:
            if d: self.marked.append("#40ff7700")
            else: self.marked.append(None)
        
        for s in logic.strategies: # check if changed condition is in a strategy
            for c in s["conds"]:
                if c[1] == idd: # if condition in strategy
                    for cond in s["conds"]:
                        logic.conditions[logic.find("c", cond[1])]["data"] = [] # empty all data for strategy
                    break

        # if it should update strategies and not mark
        if self.prefs[self.findPref("Recalculate strategies after editing conditions")][1]: #and not self.inputs[2][0].isChecked():
            for s in logic.strategies:
                edit = False
                for c in s["conds"]:
                    if c[1] == idd: edit = True
                if edit: # if a strategy was indirectly edited
                    self.calcStrategy(s["ID"])

        self.setScene()
        parent.close()

    def indicatorDialog(self, idd=False): # Dialogbox for viewing conditions
        if self.tabs.tabText(self.tabs.currentIndex()) == "+": 
            self.errormsg("Please load a stock first.")
            return
        # cancel any selections if made 
        if len(self.selected) != 0:
            self.selected = []
            self.marked = []
            self.resetGeneral(1)
            self.setScene()
        # if ind is given; means that 
        self.dialog = QtWidgets.QDialog(self)
        self.dialog.setFixedSize(400, 325)
        self.dialog.setWindowTitle("Add an Indicator...")
        if type(idd) == int: # if an indicator is being changed
            self.dialog.setWindowTitle("Change Indicator...")
        self.dialog.setLayout(QtWidgets.QVBoxLayout())
        self.indicatorLayout(idd, True) # set layout to custom function so it changes with whatever is selected
        self.dialog.exec()

    def indicatorLayout(self, idd=False, first=False): # to change the appearing inputs with whatever is selected
        ind = None
        if not first: # If the layout is not being defined for the first time
            current = "volume"
            for key in visinds: # find key corresponding to combobox text
                if indargs[key]["name"] == self.inputs[0].currentText(): break
            current = key
        else: 
            if type(idd) == int: 
                ind = logic.find("i", idd)
                current = logic.indicators[ind]["indName"]
            else: 
                current = visinds[0] # default is condition at spot 0
        wid = QtWidgets.QWidget()
        lab = QtWidgets.QLabel("Indicator", wid)
        lab.move(5, 5)
        self.inputs[0] = QtWidgets.QComboBox(wid)
        for n in visinds:
            self.inputs[0].addItem(indargs[n]["name"])
        self.inputs[0].setGeometry(60, 2, 120, 22)
        self.inputs[0].setCurrentText(indargs[current]["name"]) # set current selected to last selected
        self.inputs[0].currentTextChanged.connect(lambda: self.indicatorLayout(idd)) # connect text change to self
        args = []
        inps = []
        for a in indargs[current]["args"]:
            args.append(a[0])
            inps.append(a[1])
        
        if first and type(ind) == int:
            for i in range(len(logic.indicators[ind]["args"])):
                inps[i] = logic.indicators[ind]["args"][i]

        self.inputs[1] = []
        for i in range(3):
            if i < len(args):
                QtWidgets.QLabel(args[i], wid).move(5, 30+40*i)
                self.inputs[1].append(QtWidgets.QLineEdit(wid))
                self.inputs[1][i].setText(str(inps[i])) # ma
                self.inputs[1][i].setGeometry(5, 45+40*i, 35, 22)
            else:
                self.inputs[1].append(None)

        should = True # checkbox states
        if first and type(ind) == int:
            should = logic.indicators[ind]["show"]
        elif not first:
            should = self.inputs[2][0].isChecked()

        self.inputs[2] = []
        self.inputs[2].append(QtWidgets.QCheckBox("Show Indicator", wid))
        self.inputs[2][0].move(295, 270)
        self.inputs[2][0].setChecked(should)

        if first: color = "background-color: %s;" % QtGui.QColor(randint(0, 255), randint(0, 255), randint(0, 255)).name() # rng color
        else: color = self.inputs[3].styleSheet() # dont always regenerate color
        self.inputs[3] = QtWidgets.QPushButton(wid)
        self.inputs[3].setGeometry(380, 5, 20, 20)
        self.inputs[3].setStyleSheet(color)

        if first and type(ind) == int: self.inputs[3].setStyleSheet("background-color: %s;" % logic.indicators[ind]["color"]) # preset color

        self.inputs[3].clicked.connect(self.pickColor)

        view = SmallView(wid)
        view.setGeometry(90, 35, 280, 175)
        view.scene().setSceneRect(0, 0, 270, 165)
        grid = Grid(QtCore.QRectF(-5, -5, 280, 175))
        grid.density = (10, 10)
        view.scene().addItem(grid)
        view.pxSize = (280, 175)
        # dummy candles
        if len(presets[0]) == 0:
            cans = []
            op = 25000
            for i in range(300):
                vals = []
                lh = [randint(op-500, op+500), randint(op-500, op+500)]
                lh.sort()
                vals.append(op/100)
                lh.reverse()
                for v in lh:
                    vals.append(v/100)
                lh.reverse()
                vals.append(randint(lh[0], lh[1])/100)
                cans.append(vals)
                op = int(vals[-1]*100)
        else:
            cans = presets[5]
        view.candles = cans

        view2 = SmallView(wid)
        view2.setGeometry(90, 215, 280, 50)
        view2.pxSize = (280, 50)
        view2.dMode = -1
        view2.scene().setSceneRect(0, 0, 270, 40)
        grid = Grid(QtCore.QRectF(-5, -5, 280, 50))
        grid.density = (10, 10)
        view2.scene().addItem(grid)
        view2.candles = cans
        view2.rangey = (0, 10)
        view2.gridconv = [25, 5, 25, 5]
        if current == "volume":
            view2.isVolume = True
            view2.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
        elif current == "sma":
            ma = 200
            view.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            temp = pd.DataFrame(view.candles)
            view.graphInds.append(temp.rolling(window=ma).mean()[3].reset_index(drop=True).to_list())
        elif current == "ema":
            ma = 200
            view.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            temp = pd.DataFrame(view.candles)
            view.graphInds.append(temp.ewm(span=ma, adjust=False).mean()[3].reset_index(drop=True).to_list())
        elif current == "vwap":
            ma = 60
            view.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            temp = []
            prods = [] # price * volume of all
            for i in range(len(view.candles)): 
                prods.append(view.candles[i][3] * view.candles[i][4])
            for i in range(ma): temp.append(float("nan")) # no value for first few values
            for i in range(ma, len(view.candles)):
                cumsum = 0
                vols = 0 # all volumes
                for m in range(ma): # for every window
                    cumsum += prods[i-m]
                    vols += view.candles[i-m][4]
                temp.append(cumsum/vols)
            view.graphInds.append(temp)
        elif current == "bollinger":
            for i in [0, 1, 2]: view.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            temp = bollinger(view.candles, 20, 2)
            for t in temp: view.graphInds.append(t)
        elif current == "gaussian":
            for i in [0, 1, 2]: view.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            temp = gaussian(view.candles, 50, 1)
            for t in temp: view.graphInds.append(t)
        elif current == "atr":
            view2.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            atrVals = []

            for i in range(300):
                if i == 0:
                    atrVals.append(view.candles[i][1] - view.candles[i][2])
                else:
                    tr1 = view.candles[i][1] - view.candles[i][2]
                    tr2 = abs(view.candles[i][1] - view.candles[i-1][3])
                    tr3 = abs(view.candles[i][2] - view.candles[i-1][3])
                    truerange = max(tr1, tr2, tr3)
                    atrVals.append(truerange)

            atr = [sum(atrVals[:14]) / 14]  # Initial ATR value
            for i in range(14, len(atrVals)):
                atrval = (atrVals[i] - atrVals[i - 1]) / 14 + atr[-1]
                atr.append(atrval)
            
            atr = [float("nan")]*14 + atr # append nan to beginning to correctly fit the graph
            view2.graphInds.append(atr)
            view2.gridconv = [25, 5, 25, 1]
            view2.rangey = (0, 2)
        elif current == "rsi":
            ma = 14
            # if who[1] == "c": ma = int(self.inputs[1][0][0].text())
            view2.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            rss = [] # multiple rsi
            for spot in range(len(view.candles)):
                closes = []
                x = spot - ma
                if x < 0: x = 0
                for st in view.candles[x:spot+1]:
                    closes.append(st[3]) # get all closes in range
                prices = np.asarray(closes)
                deltas = np.diff(prices)
                gains = np.where(deltas >= 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                if len(gains) == 0: avg_gain = 0
                else: avg_gain = np.mean(gains[:ma])
                if len(losses) == 0: avg_loss = 0
                else: avg_loss = np.mean(losses[:ma])
                if avg_loss != 0:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs)) # on a scale of 0-100
                else: rsi = 50 # if divide by 0 default to 50
                rss.append(rsi)
            view2.graphInds.append(rss)
            view2.gridconv = [25, 5, 25, 40]
            view2.rangey = (10, 90)
            
        elif current == "macd":
            view2.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1])) # macd
            view2.colors.append(QtGui.QColor("#ff0000")) # signal
            temp = pd.DataFrame(view.candles)
            ema12 = temp.ewm(span=12, adjust=False).mean()[3].reset_index(drop=True).to_list()
            ema26 = temp.ewm(span=26, adjust=False).mean()[3].reset_index(drop=True).to_list()
            macd = []
            for e in range(len(ema12)):
                macd.append(ema12[e]-ema26[e])
            temp = pd.DataFrame(macd)
            signal = temp.ewm(span=9, adjust=False).mean()[0].reset_index(drop=True).to_list()
            view2.graphInds.append(macd)
            view2.graphInds.append(signal)
            view2.gridconv = [25, 5, 25, 1]
            view2.rangey = (-0.5, 0.5)
        view.initScene()
        view2.initScene()

        btn = QtWidgets.QPushButton()
        btn.setText("OK")
        btn.setFocus()
        btn.clicked.connect(lambda: self.indicatorExecute(self.dialog, idd))
        lay = self.dialog.layout()
        while lay.count(): # delete all widgets currently in use
            w = lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        lay.addWidget(wid)
        lay.addWidget(btn)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.dialog.setLayout(lay) # sets layout of dbox

    def indicatorExecute(self, parent, idd=False): # mark spots that the condition is true for
        for key in visinds: # find key corresponding to combobox text
            if indargs[key]["name"] == self.inputs[0].currentText(): break
        current = key

        def isType(thing, typ): # pass thing and check if it's the type
            if typ == str: return True
            elif typ == int: return isint(thing)
            elif typ == float: return isfloat(thing)

        # error code
        for i in range(len(indargs[current]["args"])):
            value = self.inputs[1][i].text()
            c = indargs[current]["args"][i][1:]
            
            if not isType(value, c[1]): 
                self.errormsg(value + " is not of type " + str(c[1]).split("\'")[1] + ".")
                return
            
            if c[2] != "-inf": # if it has a bottom limit
                if c[1](value) < c[2]:
                    self.errormsg(value + " is out of range.")
                    return
            
            maxx = c[3]
            if maxx == "nan": maxx = len(raw[logic.rawind])-1 # nan means len(stock)
            if maxx != "inf":
                if c[1](value) > maxx:
                    self.errormsg(value + " is out of range.")
                    return

        # get inputs
        old = None
        if type(idd) == int: # if it modified an old indicator; replace in list
            old = logic.find("i", idd)

        inps = [] 

        for i in range(len(self.inputs[1])):
            if i < len(indargs[current]["args"]): inps.append(indargs[current]["args"][i][2](self.inputs[1][i].text())) # append input converted to correct type

        t = len(raw[logic.rawind])-1
        out = indicator(logic.rawind, current, inps, t)
        if isinstance(out, tuple): # if multiple values were given
            temp = []
            for o in out:
                temp.append(o)
            out = temp
        else: out = [out]

        self.mode.setCurrentText("Conditions/Indicators")

        end = False
        dMode = 0
        if current in ["sma", "ema", "vwap", "bollinger", "gaussian"]: dMode = 1 # graph
        elif current in ["macd", "rsi", "atr"]: dMode = 2 # second view graph
        elif current in ["volume"]: dMode = 3 # volume display
            
        if old is None: # if a new id is needed
            # add to indicators
            newidd = 0

            i = 0
            while i < len(logic.indicators): # check if id is already in use
                if logic.indicators[i]["ID"] == newidd:
                    newidd += 1
                    i = -1 # if id in use go up and restart process
                i += 1
        
        else: newidd = idd # else keep old id
        color = self.inputs[3].styleSheet().split(" ")[1][:-1] # color in hex
        name = ""
        name += indargs[current]["name"]
        for inp in inps:
            name += " " + str(inp)

        indict = {"ID":newidd, "name":name, "indName":current, "args":inps, "dMode":dMode, "data":out, "color":color, "show":self.inputs[2][0].isChecked()}
        if old is None: 
            logic.indicators.append(indict) # all of the info necessary for an indicator
        else: # if old indicator/condition is changed
            logic.indicators[old] = indict # replace old indicator

        self.setScene()
        parent.close()

    def seekConditions(self): # look for contitions that apply to selected spots only 
        self.processes.append(BackProcess(logic.seekConditions, "condseeker"))
        self.processes[-1].args = (deepcopy(self.spots), deepcopy(raw[logic.rawind]))
        self.processes[-1].start()
        procManager.register("condseeker")
        procManager.setCurrent("condseeker")
        self.displayStats()

    def strategyDialog(self, idd=False): # dialog box for running strategies
        if self.tabs.tabText(self.tabs.currentIndex()) == "+": 
            self.errormsg("Please load a stock first.")
            return
        if type(idd) == int: ind = logic.find("s", idd)
        else: ind = None
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Add a Strategy...")
        dbox.setFixedSize(280, 315)
        lab1 = QtWidgets.QLabel("Conditions", dbox)
        lab1.move(170, 5)
        lab1 = QtWidgets.QLabel("Strategy", dbox)
        lab1.move(25, 5)
        
        self.inputs[1] = ["2y", "1h", ""] # period, interval and stock file path
        self.inputs[3] = [] # set 3 to blank to prevent errors

        self.inputs[0] = []
        self.inputs[0].append(StratList(dbox))

        def delCondition(item): # delete unbound complex condition given the item
            self.inputs[0][0].takeItem(self.inputs[0][0].row(item)) # take item out of list
            logic.conditions.pop(logic.find("c", item.idd)) # pop item out of conditions

        self.inputs[0][0].setFn(self.connectDialog, delCondition) # connect, delete
        self.inputs[0][0].setGeometry(25, 25, 75, 155)

        self.inputs[0].append(QtWidgets.QListWidget(dbox))
        self.inputs[0][1].setGeometry(170, 25, 75, 155)

        used = [] # used indicator conditions
        # l is text for list objects
        if type(ind) == int: # if previous strategy is edited
            for c in logic.strategies[ind]["conds"]:
                indx = logic.find("c", c[1])
                if indx is None: # if a condition doesn't exist anymore
                    self.errormsg("Strategy can't be loaded; Condition is missing.")
                    return
                if c[0] == "ci": used.append(c[1]) # if an indiactor condition is used; 
                if len(logic.conditions[indx]["deps"]) != 0: # for complex condition
                    l = str(c[1]) + " " + logic.conditions[indx]["deps"][1] # ID + operator for cc
                    self.inputs[0][0].addItem(ListItem(l, c[1], typ="cc"))
                else: # indicator condition
                    l = logic.conditions[indx]["name"] # append indicator condition to strategy list
                    self.inputs[0][0].addItem(ListItem(l, c[1]))
            # append all unused conditions to right list
            for c in logic.conditions:
                if len(c["deps"]) == 0 and c["ID"] not in used: # if id has not been used yet
                    l = c["name"] # append condition to list
                    self.inputs[0][1].addItem(ListItem(l, c["ID"]))
            if len(logic.strategies[ind]["risk"]) != 0: # if risk has been changed
                self.inputs[3] = logic.strategies[ind]["risk"]
            self.inputs[1] = logic.strategies[ind]["prefs"]
        else: # new strategy
            if len(self.selected) != 0: # if conditions have already been selected
                temp = []
                for s in self.selected: # add all selected conditons to left list
                    # s is id of condition selected
                    indx = logic.find("c", s)
                    l = logic.conditions[indx]["name"]
                    temp.append(s) # save id
                    self.inputs[0][0].addItem(ListItem(l, logic.conditions[indx]["ID"]))
                for c in logic.conditions:
                    if len(c["deps"]) == 0 and c["ID"] not in temp: # if id has not been used yet
                        l = c["name"] # append condition to list
                        self.inputs[0][1].addItem(ListItem(l, c["ID"]))
            else:
                for c in logic.conditions:
                    if len(c["deps"]) == 0: # only indicator conditions
                        l = c["name"] # append condition to list
                        self.inputs[0][1].addItem(ListItem(l, c["ID"]))
        # self.inputs[0][1].addItems(l)

        self.inputs[2] = []
        self.inputs[2].append(QtWidgets.QCheckBox("Mark True Spots", dbox))
        self.inputs[2][0].move(145, 188)
        self.inputs[2][0].setChecked(True)
        self.inputs[2].append(QtWidgets.QCheckBox("Debug Mode", dbox))
        self.inputs[2][1].move(145, 217)
        self.inputs[2][1].setChecked(False)
        if type(ind) == int: # if previous strategy; also include stock prefs
            for i in range(len(logic.strategies[ind]["prefs"])):
                self.inputs[2].append(logic.strategies[ind]["prefs"][i])

        def moveCondition(direction): # move conditions between boxes
            if direction == "add":
                item = self.inputs[0][1].currentItem()
                self.inputs[0][1].takeItem(self.inputs[0][1].row(item))
                self.inputs[0][0].addItem(item)
            elif direction == "remove":
                item = self.inputs[0][0].currentItem()
                self.inputs[0][0].takeItem(self.inputs[0][0].row(item))
                self.inputs[0][1].addItem(item)

        btn = QtWidgets.QPushButton("←", dbox)
        btn.setGeometry(122, 45, 26, 26)
        btn.clicked.connect(lambda: moveCondition("add"))
        btn2 = QtWidgets.QPushButton("→", dbox)
        btn2.setGeometry(122, 125, 26, 26)
        btn2.clicked.connect(lambda: moveCondition("remove"))
        btn3 = QtWidgets.QPushButton("OK", dbox)
        btn3.move(100, 280)
        btn3.clicked.connect(lambda: self.strategyExecute(dbox, ind))
        btn4 = QtWidgets.QPushButton("Tree View", dbox)
        btn4.move(25, 185)
        btn4.clicked.connect(lambda: self.treeView(dbox))
        btn5 = QtWidgets.QPushButton("Risk Mgmt.", dbox)
        btn5.move(25, 214)

        # self.inputs[3] = []
        def isType(thing, typ): # pass thing and check if it's the type
            if typ == str: return True
            elif typ == int: return isint(thing)
            elif typ == float: return isfloat(thing)

        def riskDialog(): # dialog for risk management
            dbox2 = QtWidgets.QDialog(dbox)
            dbox2.setFixedSize(450, 200)
            dbox2.setWindowTitle("Risk Management...")

            old = []
            if len(self.inputs[3]) != 0: # if something has already been set
                old = self.inputs[3]
                self.inputs[3] = []

            def dropBox(box: Slot): # what happens when a variable is dropped in a slot
                # box is slot the item is dropped into
                if box.pInd == 0: foc = dbox2.focusWidget() # current combobox
                else: foc = self.dialog.focusWidget()
                vind = foc.currentIndex() # index of variable
                if box.requested == "V" and type(foc.vars[vind]) == VariableExpression:
                    box.setText("") # reset text
                    self.errormsg("Slot requests Variable/Equation.")
                    return
                if box.requestRange: # if range is requested
                    if type(foc.vars[vind]) == VariableEquation:
                        box.setText("") # reset text
                        self.errormsg("Range cannot be entered for an equation.")
                        return
                    else: # if indicator variable
                        dbox = QtWidgets.QDialog(self.dialog)
                        dbox.setWindowTitle("Enter range...")
                        dbox.setFixedSize(200, 120)
                        dbox.setWindowFlags(dbox.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint) # keep all but close button
                        QtWidgets.QLabel("Enter relative range provided", dbox).move(10, 10)
                        tbox = QtWidgets.QLineEdit(dbox)
                        tbox.setGeometry(10, 30, 130, 22)
                        btn = QtWidgets.QPushButton("OK", dbox)
                        btn.move(65, 75)
                        def check():
                            sp = tbox.text().split(",")
                            if len(sp) != 2:
                                self.errormsg("Invalid range format.")
                                return
                            ran = []
                            for s in sp:
                                num = ""
                                for char in range(len(s)):
                                    if s[char] in "-0123456789":
                                        num += s[char] # get all numbers in str
                                if num == "":
                                    self.errormsg("No valid number entered.")
                                    return
                                ran.append(num)
                            num += ran[0] + "," + ran[1]
                            box.spotVar = num
                            dbox.close()
                        btn.clicked.connect(check)
                        dbox.exec()
                elif type(foc.vars[vind]) == IndicatorVariable: # if no range is requested and variable was given
                    if indinfo[foc.vars[vind].indName]["vtypes"][indinfo[foc.vars[vind].indName]["vars"].index(foc.vars[vind].var)] == list: # if a spot can be selected
                        dbox = QtWidgets.QDialog(self.dialog)
                        dbox.setWindowTitle("Enter spot...")
                        dbox.setFixedSize(200, 120)
                        dbox.setWindowFlags(dbox.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint) # keep all but close button
                        QtWidgets.QLabel("Enter spot in python form", dbox).move(10, 10)
                        slot = Slot(dbox)
                        slot.setGeometry(10, 30, 130, 22)
                        slot.setText("-1")
                        btn = QtWidgets.QPushButton("OK", dbox)
                        btn.move(65, 75)
                        def check():
                            if slot.var is not None: # if a variable is used
                                if type(slot.var) == IndicatorVariable: t = "v"
                                elif type(slot.var) == VariableEquation: t = "e"
                                box.spotVar = "!" + t + str(slot.var.id)
                            else:
                                num = slot.text()
                                if not isint(num):
                                    self.errormsg("Spot has to be an integer.")
                                    return
                                box.spotVar = num
                            dbox.close()
                        btn.clicked.connect(check)
                        dbox.exec()

                box.setLocked(True)
                box.var = deepcopy(foc.vars[vind]) # set box variable to current cbox variable
                if type(box.var) == IndicatorVariable: box.setText(box.var.var)
                elif type(box.var) == VariableEquation: box.setText(box.var.name)
                elif type(box.var) == VariableExpression: box.setText(box.var.name)

            lab = QtWidgets.QLabel("Balance in $", dbox2)
            lab.move(10, 10)
            self.inputs[3].append(Slot(dbox2, dropBox))
            self.inputs[3][0].setGeometry(125, 10, 85, 22)
            self.inputs[3][0].setText("10000")
            self.inputs[3][0].pInd = 0
            lab = QtWidgets.QLabel("Order Type", dbox2)
            lab.move(10, 35)
            btn = QtWidgets.QPushButton("Change", dbox2)
            btn.setGeometry(125, 34, 85, 22)
            QtWidgets.QLabel("Current:", dbox2).move(10, 60)
            self.inputs[3].append("Trailing Stop")
            self.inputs[3].append(0.01)
            labchange = QtWidgets.QLabel(dbox2)
            labchange.move(125, 60)
            lab = QtWidgets.QLabel("$ per Order", dbox2)
            lab.move(10, 85)
            self.inputs[3].append(Slot(dbox2, dropBox))
            self.inputs[3][3].setGeometry(125, 85, 85, 22)
            self.inputs[3][3].setText("200")
            self.inputs[3][3].pInd = 0
            lab = QtWidgets.QLabel("Fees per Trade in $", dbox2)
            lab.move(10, 110)
            self.inputs[3].append(Slot(dbox2, dropBox))
            self.inputs[3][4].setGeometry(125, 110, 85, 22)
            self.inputs[3][4].setText("0")
            self.inputs[3][4].pInd = 0

            def displayOrder(): # makes label for order
                st = ""
                st += self.inputs[3][1] + " "
                if self.inputs[3][1] == "Trailing Stop": # only one value
                    st += str(self.inputs[3][2])
                else: # two values
                    for s in self.inputs[3][2]:
                        st += str(s) + " "
                labchange.setText(st)
            
            displayOrder()

            def orderDBox(): # displays order dialog box
                self.dialog = QtWidgets.QDialog(dbox2)
                self.dialog.setFixedSize(400, 100)
                self.dialog.setWindowTitle("Change Order...")
                QtWidgets.QLabel("Variables", self.dialog).move(10, 10)
                varcopy = DragBox(self.dialog)
                varcopy.setGeometry(10, 26, 110, 22)
                its = [vrs.itemText(indx) for indx in range(vrs.count())]
                varcopy.addItems(its)
                varcopy.vars = vrs.vars
                QtWidgets.QLabel("Equations", self.dialog).move(10, 50)
                eqcopy = DragBox(self.dialog)
                eqcopy.setGeometry(10, 66, 110, 22)
                its = [eqs.itemText(indx) for indx in range(eqs.count())]
                eqcopy.addItems(its)
                eqcopy.vars = eqs.vars
                QtWidgets.QLabel("Trailing Stop", self.dialog).move(125, 26)
                QtWidgets.QLabel("Trailing in decimal", self.dialog).move(195, 10)
                slot1 = Slot(self.dialog, dropBox)
                slot1.setGeometry(195, 26, 75, 22)
                QtWidgets.QLabel("Stop Limit", self.dialog).move(125, 66)
                QtWidgets.QLabel("Stop Price", self.dialog).move(195, 50)
                QtWidgets.QLabel("Limit Price", self.dialog).move(255, 50)
                slot2 = Slot(self.dialog, dropBox)
                slot2.setGeometry(195, 66, 50, 22)
                slot3 = Slot(self.dialog, dropBox)
                slot3.setGeometry(255, 66, 50, 22)

                def find(what, idd):
                    if what == "v": search = vrs.vars
                    else: search = eqs.vars

                    for s in range(len(search)):
                        if search[s].id == idd: return s

                if self.inputs[3][1] == "Trailing Stop":
                    if isfloat(self.inputs[3][2]):
                        slot1.setText(str(self.inputs[3][2]))
                    else: # for variable
                        t = self.inputs[3][2][1]
                        sp = self.inputs[3][2].split("%")
                        if t == "v": 
                            var = vrs.vars[find(t, int(sp[1][1:]))]
                            slot1.setText(var.var)
                            slot1.spotVar = sp[2]
                            slot1.setToolTip(sp[2])
                        else: 
                            var = eqs.vars[find(t, int(sp[1][1:]))]
                            slot1.setText(var.name)
                        slot1.var = var
                        slot1.setLocked()
                elif self.inputs[3][1] == "Stop Limit":
                    i = 0
                    for sl in [slot2, slot3]:
                        if isfloat(self.inputs[3][2][i]):
                            sl.setText(str(self.inputs[3][2][i]))
                        else: # for variable
                            t = self.inputs[3][2][i][1]
                            sp = self.inputs[3][2][i].split("%")
                            if t == "v": 
                                var = vrs.vars[find(t, int(sp[1][1:]))]
                                sl.setText(var.var)
                                sl.spotVar = sp[2]
                                sl.setToolTip(sp[2])
                            else: 
                                var = eqs.vars[find(t, int(sp[1][1:]))]
                                sl.setText(var.name)
                            sl.var = var
                            sl.setLocked()
                        i += 1
                
                def choose(what): # checks for errors and stores the values
                    if what == "t": # trailing stop
                        st = slot1.text()
                        if slot1.var is None:
                            if not isfloat(st):
                                self.errormsg(st + " is not a valid number.")
                                return
                            elif float(st) < 0:
                                self.errormsg("Trailing must be at least 0.")
                                return
                            self.inputs[3][1] = "Trailing Stop"
                            self.inputs[3][2] = float(st)
                        else:
                            self.inputs[3][1] = "Trailing Stop"
                            if type(slot1.var) == IndicatorVariable: t = "v"
                            else: t = "e"
                            st = "%" + t + str(slot1.var.id)
                            if t == "v":
                                st += "%" + str(slot1.spotVar)
                            self.inputs[3][2] = st
                    elif what == "sl": # stop limit
                        for sl in [slot2, slot3]: # error check
                            st = sl.text()
                            if sl.var is None:
                                if not isfloat(st):
                                    self.errormsg(st + " is not a valid number.")
                                    return
                                elif float(st) < 0:
                                    self.errormsg("Limits can't be negative.")
                                    return
                        self.inputs[3][2] = ["", ""]
                        i = 0
                        for sl in [slot2, slot3]: # setting values
                            st = sl.text()
                            if sl.var is None:
                                self.inputs[3][2][i] = float(st)
                            else:
                                if type(sl.var) == IndicatorVariable: t = "v"
                                else: t = "e"
                                st = "%" + t + str(sl.var.id)
                                if t == "v":
                                    st += "%" + str(sl.spotVar)
                                self.inputs[3][2][i] = st
                            i += 1
                        self.inputs[3][1] = "Stop Limit"
                    displayOrder()
                    self.dialog.close()

                btn = QtWidgets.QPushButton("Choose", self.dialog)
                btn.move(310, 25)
                btn.clicked.connect(lambda: choose("t"))
                
                btn = QtWidgets.QPushButton("Choose", self.dialog)
                btn.move(310, 65)
                btn.clicked.connect(lambda: choose("sl"))

                self.dialog.exec()
            
            btn.clicked.connect(orderDBox)

            QtWidgets.QLabel("Add Indicator", dbox2).move(225, 10)
            addinds = QtWidgets.QComboBox(dbox2)
            for i in avinds:
                if not indinfo[i]["existcheck"]: addinds.addItem(indargs[i]["name"])
            addinds.setGeometry(225, 26, 120, 22)

            def indDialog(): # opens a dialog window with correct fields displayed for making a variable
                nonlocal vrs
                args = []
                key = ""
                dbox3 = None
                def addInd():
                    nonlocal vrs
                    # error code
                    for i in range(len(indargs[key]["args"])):
                        value = args[i].text()
                        c = indargs[key]["args"][i][1:]
                        
                        if not isType(value, c[1]): 
                            self.errormsg(value + " is not of type " + str(c[1]).split("\'")[1] + ".")
                            return
                        
                        if c[2] != "-inf": # if it has a bottom limit
                            if c[1](value) < c[2]:
                                self.errormsg(value + " is out of range.")
                                return
                        
                        maxx = c[3]
                        if maxx == "nan": maxx = len(raw[logic.rawind])-1 # nan means len(stock)
                        if maxx != "inf":
                            if c[1](value) > maxx:
                                self.errormsg(value + " is out of range.")
                                return
                    
                    # get args
                    argnums = []
                    i = 0
                    for a in args:
                        c = indargs[key]["args"][i][1:]
                        argnums.append(c[1](a.text()))
                        i += 1

                    # check if exact indicator already exists
                    for v in vrs.vars:
                        if v.indName == key and v.args == argnums:
                            self.errormsg("Variables already exists.")
                            return

                    # add variables to combobox
                    vrs.addItems(indinfo[key]["vars"]) # variables

                    # get ids
                    ids = []

                    # variable ids
                    used = [] # already used ids
                    for v in vrs.vars:
                        used.append(v.id)

                    idd = 0 # don't reset id in loop for performance reasons
                    for v in indinfo[key]["vars"]: # get ids for every variable
                        i = 0
                        while i < len(used): # check if id is already in use
                            if used[i] == idd:
                                idd += 1
                                i = -1 # if id in use go up and restart process
                            i += 1
                        used.append(idd)
                        ids.append(idd)
                    
                    i = 0
                    for v in indinfo[key]["vars"]:
                        vrs.vars.append(IndicatorVariable(key, argnums, v, ids[i]))
                        vrs.vars[-1].name = v
                        i += 1
                    if dbox3 is not None : dbox3.close()

                for key in avinds: # find key corresponding to combobox text
                    if indargs[key]["name"] == addinds.currentText(): break
                if len(indargs[key]["args"]) == 0: # if no arguments needed
                    addInd()
                    return

                dbox3 = QtWidgets.QDialog(dbox2)
                dbox3.setWindowTitle("Add " + addinds.currentText() + "...")
                dbox3.setFixedSize(310, 100)
                args = []
                for i in range(len(indargs[key]["args"])):
                    QtWidgets.QLabel(indargs[key]["args"][i][0], dbox3).move(10+100*i, 10)
                    args.append(Slot(dbox3, dropBox))
                    args[i].setGeometry(10+100*i, 26, 35, 22)
                    args[i].setText(str(indargs[key]["args"][i][1]))
                btn = QtWidgets.QPushButton("Add", dbox3)
                btn.move(115, 70)
                btn.clicked.connect(addInd)
                dbox3.exec()
            add = EdSaveBtn("Add...", dbox2)
            add.setGeometry(350, 26, 73, 23)
            add.clicked.connect(indDialog)

            QtWidgets.QLabel("Add Equation", dbox2).move(225, 50)
            addeqs = QtWidgets.QComboBox(dbox2)
            addeqs.addItems(["Basic", "Constants", "Trigonometric", "Aggregates", "Round", "Spot of", "Functions"])#, "Time"])
            addeqs.setGeometry(225, 66, 120, 22)

            def eqDialog(): # add equation dialog
                nonlocal eqs
                typ = addeqs.currentText()
                args = []
                def addEq():
                    nonlocal eqs
                    if self.prefs[self.findPref("Ask to name variables")][1]:
                        dbox = QtWidgets.QDialog(self.dialog)
                        dbox.setWindowTitle("Equation Name...")
                        dbox.setFixedSize(200, 120)
                        QtWidgets.QLabel("Name this new equation? (Optional)", dbox).move(10, 10)
                        tbox = QtWidgets.QLineEdit(dbox)
                        tbox.setGeometry(10, 30, 130, 22)
                        btn = QtWidgets.QPushButton("OK", dbox)
                        btn.move(65, 75)
                        btn.clicked.connect(dbox.close)
                        dbox.exec()
                        if tbox.text() == "": name = self.getName("re", [typ]+args)
                        else: name = tbox.text()
                    else: name = self.getName("re", [typ]+args)
                    argvals = []
                    #vars = [] # vars is list of variables in equation
                    for inp in args:
                        if type(inp) != Slot: # cbox
                            argvals.append(inp.currentText())
                        else:
                            if inp.var is not None: # variable in slot
                                doList = False
                                if type(inp.var) == IndicatorVariable: t = "v" # variable
                                elif type(inp.var) == VariableEquation: t = "e" # equation
                                else: # list with multiple variables
                                    doList = True
                                if not doList: # anything but a list
                                    if t != "v": argvals.append("%"+ t + str(inp.var.id)) # equation or expression
                                    else: argvals.append("%" + t + str(inp.var.id) + "%" + inp.spotVar)

                                    #vars.append(inp.var.id)
                                else:
                                    st = ""
                                    i = -1
                                    for v in inp.var:
                                        st += "%"
                                        if type(v) == IndicatorVariable: t = "v" # variable
                                        elif type(v) == VariableEquation: t = "e" # equation
                                        st += t
                                        st += str(inp.var.id)
                                        if t == "v": # also include spot
                                            i += 1 # only advance i here because spots were only recorded from variables
                                            st += "%"
                                            st += inp.spotVar.split(",")[i]
                                        if inp.var.index(v) != len(inp.var) - 1: # add seperator for all except last one
                                            st += "|"
                                        #vars.append(v.id)
                                    argvals.append(st)
                            else:
                                if not isfloat(inp.text()):
                                    self.errormsg(str(inp.text()) + "is not a valid number.")
                                    return
                                argvals.append(float(inp.text()))
                    
                    # get new unused id
                    i = 0
                    idd = 0
                    while i < len(eqs.vars): # check if id is already in use
                        if eqs.vars[i].id == idd:
                            idd += 1
                            i = -1 # if id in use go up and restart process
                        i += 1

                    eqs.vars.append(VariableEquation(name, typ, argvals, idd))
                    eqs.addItem(name)
                    self.dialog.close()

                self.dialog = QtWidgets.QDialog(dbox2)
                self.dialog.setWindowTitle("Add " + typ + "...")
                self.dialog.setFixedSize(310, 150)
                args = []
                if typ == "Basic":
                    args.append(Slot(self.dialog, dropBox))
                    args[0].setGeometry(10, 10, 110, 22)
                    args.append(QtWidgets.QComboBox(self.dialog))
                    args[1].setGeometry(122, 10, 43, 22)
                    args[1].addItems(["+", "-", "*", "/", "%", "//", "**"])
                    args.append(Slot(self.dialog, dropBox))
                    args[2].setGeometry(167, 10, 110, 22)
                elif typ == "Constants":
                    args.append(QtWidgets.QComboBox(self.dialog))
                    args[0].move(10, 10)
                    args[0].addItems(["π", "e", "ϕ"])
                elif typ == "Trigonometric":
                    args.append(QtWidgets.QComboBox(self.dialog))
                    args[0].move(10, 10)
                    args[0].addItems(["Sin", "Asin", "Cos", "Acos", "Tan", "Atan"])
                    QtWidgets.QLabel("of", self.dialog).move(85, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[1].move(110, 10)
                elif typ == "Aggregates":
                    args.append(QtWidgets.QComboBox(self.dialog))
                    args[0].move(10, 10)
                    args[0].addItems(["Max", "Min", "Average", "Sum"])
                    QtWidgets.QLabel("of", self.dialog).move(90, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[1].move(110, 10)
                    args[1].requestRange = True
                    args[1].setLocked(True)
                elif typ == "Round":
                    QtWidgets.QLabel("Round", self.dialog).move(10, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[0].move(60, 10)
                    QtWidgets.QLabel(",", self.dialog).move(180, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[1].move(195, 10)
                elif typ == "Spot of":
                    QtWidgets.QLabel("Spot of", self.dialog).move(10, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[0].move(60, 10)
                    QtWidgets.QLabel("in", self.dialog).move(180, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[1].move(195, 10)
                    args[1].requestRange = True
                    args[1].setLocked(True)
                elif typ == "Functions":
                    args.append(QtWidgets.QComboBox(self.dialog))
                    args[0].move(10, 10)
                    args[0].addItems(["Floor", "Ceil", "Abs"])
                    QtWidgets.QLabel("of", self.dialog).move(85, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[1].move(110, 10)
                elif typ == "Time":
                    args.append(QtWidgets.QComboBox(self.dialog))
                    args[0].move(10, 10)
                    args[0].addItems(["Year", "Month", "Day", "Hour", "Minute", "Second"])
                    QtWidgets.QLabel("of", self.dialog).move(85, 10)
                    args.append(Slot(self.dialog, dropBox))
                    args[1].move(110, 10)
                QtWidgets.QLabel("Variables", self.dialog).move(10, 50)
                varcopy = DragBox(self.dialog)
                varcopy.setGeometry(10, 66, 110, 22)
                its = [vrs.itemText(indx) for indx in range(vrs.count())]
                varcopy.addItems(its)
                varcopy.vars = vrs.vars
                QtWidgets.QLabel("Equations", self.dialog).move(125, 50)
                eqcopy = DragBox(self.dialog)
                eqcopy.setGeometry(125, 66, 110, 22)
                its = [eqs.itemText(indx) for indx in range(eqs.count())]
                eqcopy.addItems(its)
                eqcopy.vars = eqs.vars
                btn = QtWidgets.QPushButton("Add", self.dialog)
                btn.move(115, 120)
                btn.clicked.connect(addEq)
                self.dialog.exec()

            add = EdSaveBtn("Add...", dbox2)
            add.setGeometry(350, 66, 73, 23)
            add.clicked.connect(eqDialog)

            QtWidgets.QLabel("Variables", dbox2).move(225, 94)
            vrs = DragBox(dbox2)
            vrs.setGeometry(225, 110, 110, 22)

            QtWidgets.QLabel("Equations", dbox2).move(340, 94)
            eqs = DragBox(dbox2)
            eqs.setGeometry(340, 110, 110, 22)

            if len(old) != 0: # if risk is being edited
                i = 0
                for o in old[0]:
                    if i not in [1, 2]:
                        if type(o) == str: 
                            if "%" in o: # variable
                                sp = o.split("%") # split into id, type and spot and then assign correct variable to slot
                                t = sp[1][0]
                                idd = int(sp[1][1:])
                                for v in old[1]:
                                    if type(v) == IndicatorVariable: ty = "v"
                                    else: ty = "e"
                                    if v.id == idd and ty == t: 
                                        self.inputs[3][i].var = v
                                        self.inputs[3][i].setLocked()
                                        if t == "v": 
                                            self.inputs[3][i].spotVar = sp[2]
                                            self.inputs[3][i].setText(v.var)
                                        else:
                                            self.inputs[3][i].setText(v.name)
                            else:
                                self.inputs[3][i].setCurrentText(o)
                        else:
                            self.inputs[3][i].setText(str(o))
                    else:
                        self.inputs[3][i] = o
                    i += 1
                evs = [[], []] # equations, variables
                for o in old[1]:
                    if type(o) == IndicatorVariable: 
                        vrs.addItem(o.var)
                        evs[1].append(o)
                    else: 
                        eqs.addItem(o.name)
                        evs[0].append(o)
                vrs.vars = evs[1]
                eqs.vars = evs[0]
                displayOrder()
            
            def reset(): # deletes all variables and sets risk variables to default
                vrs.vars = []
                vrs.clear()
                eqs.vars = []
                eqs.clear()
                self.inputs[3][0].setText("10000")
                self.inputs[3][0].var = None
                self.inputs[3][0].setLocked(False)
                self.inputs[3][1] = "Trailing Stop"
                self.inputs[3][2] = "0.01"
                self.inputs[3][3].setText("200")
                self.inputs[3][3].var = None
                self.inputs[3][3].setLocked(False)
                self.inputs[3][4].setText("0")
                self.inputs[3][4].var = None
                self.inputs[3][4].setLocked(False)

            btn = QtWidgets.QPushButton("Reset", dbox2)
            btn.move(350, 170)
            btn.clicked.connect(reset)
            okk = False

            def ok():
                nonlocal okk
                # error code
                errd = False
                for i in range(len(self.inputs[3])):
                    if i not in [1, 2]: # not combobox which has to be string
                        if self.inputs[3][i].var is None and not isfloat(self.inputs[3][i].text()): errd = True
                if errd:
                    self.errormsg("Invalid risk management number type.")
                    return
                
                # balance
                if self.inputs[3][0].var is None:
                    bal = float(self.inputs[3][0].text())
                    if bal < 0:
                        self.errormsg("Balance must be at least 0.")
                        return
                
                # $ per order
                if self.inputs[3][3].var is None:
                    num = float(self.inputs[3][3].text())
                    if num < 0 or num > bal:
                        self.errormsg("Money per order is out of range.")
                        return
                
                # fees
                if self.inputs[3][4].var is None:
                    num = float(self.inputs[3][4].text())
                    if num < 0:
                        self.errormsg("Fees must be at least 0.")
                        return
                refs = []
                for inp in self.inputs[3]:
                    if type(inp) == Slot: # get all of the reference values i.e. %v4 or just numbers
                        if inp.var is not None:
                            if type(inp.var) == IndicatorVariable: t = "v"
                            else: t = "e"
                            st = "%" + t + str(inp.var.id)
                            if inp.spotVar != "":
                                st += "%" + inp.spotVar
                        else: 
                            st = inp.text()
                            if not isfloat(st):
                                self.errormsg(st + " is not a number.")
                                return
                            st = float(st)
                    else: st = inp
                    refs.append(st)
                self.inputs[3] = [refs, []]
                for v in vrs.vars:
                    self.inputs[3][1].append(v)
                for e in eqs.vars:
                    self.inputs[3][1].append(e)
                okk = True
                dbox2.close()

            def close(): # when the window is closed without pressing ok
                if not okk: self.inputs[3] = []
            
            dbox2.finished.connect(close)

            btn = QtWidgets.QPushButton("OK", dbox2)
            btn.move(90, 170)
            btn.clicked.connect(ok)
            dbox2.show()

        btn5.clicked.connect(riskDialog)
        btn6 = QtWidgets.QPushButton("Stock Prfs.", dbox)
        btn6.move(25, 243)
        btn6.clicked.connect(lambda: self.stockDialog(dbox))
        dbox.exec()

    def treeView(self, parent=None): # view strategy as tree in seperate dbox
        dbox = QtWidgets.QDialog(parent)
        dbox.setWindowTitle("Strategy Tree View")
        dbox.setFixedSize(300, 250)
        tree = QtWidgets.QTreeWidget(dbox)
        tree.setGeometry(10, 10, 280, 230)

        # add tree containing all of the conditions and how they're linked
        items = self.inputs[0][0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
        calc = [] # list whether condition is needed in final calculation

        conds = [] # get list of every condition
        for item in items:
            conds.append((item.typ, item.idd))
            calc.append(True)

        for c in conds:
            if c[0] == "cc": # if complex condition
                ind = logic.find("c", c[1]) # index
                if logic.conditions[ind]["deps"][1] == "not": # only check one
                    for i in range(len(conds)):
                        if conds[i][1] == logic.conditions[ind]["deps"][0][1]: # if id in list is id used
                            calc[i] = False
                else:
                    for j in range(2): # check 2
                        for i in range(len(conds)):
                            if conds[i][1] == logic.conditions[ind]["deps"][j*2][1]: # if id in list is id used
                                calc[i] = False

        treelist = []
        for c in range(len(calc)):
            if calc[c]: treelist.append([conds[c], []]) # make list of top conditions with empty list for possible branches

        def branch(twig, parent): # sub function that is ran for every condition in treelist
            indx = logic.find("c", twig[0][1])
            if len(logic.conditions[indx]["deps"]) != 0: # change how text is gotten based on condition
                l = str(logic.conditions[indx]["ID"]) + " " + logic.conditions[indx]["deps"][1]
            else:
                l = logic.conditions[indx]["name"]
            a = QtWidgets.QTreeWidgetItem(parent, [l]) # make entry on parent branch and save new branch point as a
            if twig[0][0] == "cc":
                # add new branch for cc
                if logic.conditions[indx]["deps"][1] == "not":
                    # only use deps[0]
                    indx = logic.find("c", logic.conditions[indx]["deps"][0][1]) # change indx just for checking
                    if indx is None: # no id was found
                        self.errormsg("Condition " + str(twig[0][1]) + " can't be processed because of missing subcondition.")
                        return
                    if len(logic.conditions[indx]["deps"]) != 0: typ = "cc"
                    else: typ = "ci"
                    twig[1].append([(typ, logic.conditions[indx]["ID"]), []]) # add new to treelist
                    branch(twig[1][-1], a) # continue branch from here
                else:
                    indx = [logic.find("c", logic.conditions[indx]["deps"][0][1]), logic.find("c", logic.conditions[indx]["deps"][2][1])]
                    for j in range(2):
                        if indx[j] is None:
                            self.errormsg("Condition " + str(twig[0][1]) + " can't be processed because of missing subcondition.")
                            return
                        if len(logic.conditions[indx[j]]["deps"]) != 0: typ = "cc"
                        else: typ = "ci"
                        twig[1].append([(typ, logic.conditions[indx[j]]["ID"]), []]) # add new to treelist
                        branch(twig[1][-1], a) # continue branch from here

        for t in treelist: branch(t, tree) # make fully filled treelist

        dbox.exec()

    def stockDialog(self, parent): # dialog for stock settings in strategy
        #perinv = [] # past period and interval
        #perinv = self.inputs[1]
        dbox = QtWidgets.QDialog(parent)
        dbox.setFixedSize(200, 150)
        dbox.setWindowTitle("Stock Preferences")
        avail0 = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] # available periods
        avail1 = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"] # available intervals
        # if len(self.inputs[2]) != 2: # because of space look whether new inputs have already been loaded in
        #     self.inputs[2] = self.inputs[2][:2] # only take ones from strategy dialog
        lab = QtWidgets.QLabel("Period", dbox)
        lab.move(10, 10)
        pbox = QtWidgets.QComboBox(dbox)
        pbox.setGeometry(70, 10, 75, 22)
        pbox.addItems(avail0)
        lab = QtWidgets.QLabel("Interval", dbox)
        lab.move(10, 35)
        ibox = QtWidgets.QComboBox(dbox)
        ibox.setGeometry(70, 35, 75, 22)
        ibox.addItems(avail1)

        QtWidgets.QLabel("Enter stocks to use only\n(empty: default)\n", dbox).move(10, 60)
        tbox = QtWidgets.QLineEdit(dbox)
        tbox.setGeometry(10, 95, 180, 22)
        tbox.setToolTip("Seperated by comma\n(Can also be file path)")
        
        pbox.setCurrentText(self.inputs[1][0])
        ibox.setCurrentText(self.inputs[1][1])
        tbox.setText(self.inputs[1][2])

        def stockError(): # check whether errors were made before closing stock dialog
            # for reference ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] # available periods
            avail1 = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"] # available intervals
            if pbox.currentText() == "ytd":
                inv = ibox.currentText()
                comps = avail1[:avail1.index("60m")] # make interval range
                if inv in comps:
                    self.errormsg("Interval too small for period.")
                    return
            elif pbox.currentText() == "max":
                inv = ibox.currentText()
                comps = avail1[:avail1.index("1d")] # make interval range
                if inv in comps:
                    self.errormsg("Interval too small for period.")
                    return
            else:
                if pbox.currentText()[-1] == "d": # day range
                    if ibox.currentText() in avail1[avail1.index("1d"):]:
                        self.errormsg("Interval too big for period.")
                        return
                elif pbox.currentText()[-1] == "o": # month range
                    inv = ibox.currentText()
                    comps = avail1[:avail1.index("60m")] # make interval range
                    if inv in comps:
                        self.errormsg("Interval too small for period.")
                        return
                else: # year range
                    if int(pbox.currentText()[:-1]) <= 2: # max 2 years
                        if ibox.currentText() in avail1[:avail1.index("1h")]:
                            self.errormsg("Interval too small for period.")
                            return
                    else: # above 2 years
                        if ibox.currentText() in avail1[:avail1.index("1d")]:
                            self.errormsg("Interval too small for period.")
                            return
            if tbox.text().count("/") > tbox.text().count("\\"): count = tbox.text().count("/") # a filepath should contain at least one / or \
            else: count = tbox.text().count("\\")
            if count >= 1: isFile = True
            else: isFile = False
            if isFile:
                try:
                    open(tbox.text()) # simple check to see if file exists
                except:
                    self.errormsg("File not found. Please check if the name is correct.")
                    return
            else:
                # preprocess string
                st = ""
                for s in tbox.text():
                    if s not in " \n": # keep everything except space and linebreak
                        st += s
            # save text only
            self.inputs[1][0] = pbox.currentText()
            self.inputs[1][1] = ibox.currentText()
            self.inputs[1][2] = tbox.text()
            dbox.close()
        
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(70, 120)
        btn.clicked.connect(stockError)
        dbox.exec()

    def strategyExecute(self, parent, indx=False): # ok button | adds strategy to list
        if type(indx) == int: name = logic.strategies[indx]["name"]
        else: name = None
        dbox = QtWidgets.QDialog(parent)
        dbox.setWindowTitle("Strategy Name...")
        dbox.setFixedSize(200, 120)
        if name is None: QtWidgets.QLabel("Name this new strategy? (Optional)", dbox).move(10, 10)
        else: QtWidgets.QLabel("Change name of strategy? (Optional)", dbox).move(10, 10)
        tbox = QtWidgets.QLineEdit(dbox)
        tbox.setGeometry(10, 30, 130, 22)
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(65, 75)
        btn.clicked.connect(dbox.close)
        dbox.exec()
        self.mode.setCurrentText("Strategies")
        self.stopButton() # stop all threads to prepare for new strategy

        conds = [] # what determines the activation of the strategy
        items = self.inputs[0][0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
        for item in items:
            conds.append((item.typ, item.idd)) # condition ("c", condID)
        
        data = []
        if self.inputs[2][0].isChecked(): # mark strategy
            calc = []
            for c in conds:
                calc.append(True) # make dummy calc list with all set to true
            i = -1
            while i != len(conds)-1: # while not all conditions were calculated
                i = len(conds)-1 # total amnt calculated
                for c in conds: # preinit
                    if c[0] == "ci": # for indicator condition
                        ind = logic.find("c", c[1]) # index
                        logic.getData(ind)
                    elif c[0] == "cc": # complex condition
                        ind = logic.find("c", c[1])
                        if logic.conditions[ind]["deps"][1] == "not": # way more easily to only do one
                            if logic.conditions[ind]["deps"][0][0] == "ci":
                                logic.getData(logic.find("c", logic.conditions[ind]["deps"][0][1])) # if indicator, just calculate ci and then cc
                                for item in items:
                                    if item.idd == logic.conditions[ind]["deps"][0][1]: # get index of used indcator condition in list
                                        calc[items.index(item)] = False # Dont use in activation calculation
                                        break
                                logic.getData(ind)
                            else:
                                temp = logic.find("c", logic.conditions[ind]["deps"][0][1])
                                if temp is None: 
                                    self.errormsg("Condition " + str(c[1]) + " can't be processed because of missing subcondition.")
                                    return
                                if len(logic.conditions[temp]["data"]) != 0: # if underlying condition has been calculated
                                    for item in items:
                                        if item.idd == logic.conditions[ind]["deps"][0][1]: # get index of used condition in list
                                            calc[items.index(item)] = False # Dont use in activation calculation
                                            break
                                    logic.getData(ind)
                                else: i -= 1 # say that this one hasn't been calculated
                        else:
                            if logic.conditions[ind]["deps"][0][0] == "ci" and logic.conditions[ind]["deps"][2][0] == "ci": # both are indicator conditions
                                for j in range(2): 
                                    logic.getData(logic.find("c", logic.conditions[ind]["deps"][j*2][1]))
                                    for item in items:
                                        if item.idd == logic.conditions[ind]["deps"][j*2][1]: # get index of used condition in list
                                            calc[items.index(item)] = False # Dont use in activation calculation
                                            break
                                logic.getData(ind)
                            elif logic.conditions[ind]["deps"][0][0] == "cc" and logic.conditions[ind]["deps"][2][0] == "cc": # both are complex conditions
                                temp = []
                                for j in range(2): 
                                    temp.append(logic.find("c", logic.conditions[ind]["deps"][j*2][1])) # get indexes of both underlyers
                                    if temp[-1] is None:
                                        self.errormsg("Condition " + str(c[1]) + " can't be processed because of missing subcondition.")
                                        return
                                    for item in items:
                                        if item.idd == logic.conditions[ind]["deps"][j*2][1]: # get index of used condition in list
                                            calc[items.index(item)] = False # Dont use in activation calculation
                                            break
                                if len(logic.conditions[temp[0]]["data"]) != 0 and len(logic.conditions[temp[1]]["data"]) != 0:
                                    logic.getData(ind)
                                else: i -= 1
                            else: # ci and cc
                                for j in range(2):
                                    for item in items:
                                        if item.idd == logic.conditions[ind]["deps"][j*2][1]: # get index of used condition in list
                                            calc[items.index(item)] = False # Dont use in activation calculation
                                            break
                                if logic.conditions[ind]["deps"][0][0] == "cc":
                                    temp = (0, logic.find("c", logic.conditions[ind]["deps"][0][1]))
                                    if temp[1] is None: 
                                        self.errormsg("Condition " + str(c[1]) + " can't be processed because of missing subcondition.")
                                        return
                                else: 
                                    temp = (1, logic.find("c", logic.conditions[ind]["deps"][2][1])) # get id of complex condition
                                    if temp[1] is None: 
                                        self.errormsg("Condition " + str(c[1]) + " can't be processed because of missing subcondition.")
                                        return
                                logic.getData(logic.find("c", logic.conditions[ind]["deps"][int(abs(temp[0]-1)*2)][1])) # get data from the ci
                                if len(logic.conditions[logic.find("c", temp[1])]["data"]) != 0:
                                    logic.getData(ind)
                                else: i -= 1

            temp = False # already something in data
            for c in conds: # calculate final activation
                ind = logic.find("c", c[1])
                if calc[conds.index(c)]: # if contition is part of final calculation
                    for i in range(len(raw[logic.rawind])): 
                        if not temp: # if first, only append data
                            data.append(logic.conditions[ind]["data"][i])
                        else: # else check for and so that all conditions have to be true
                            data[i] = data[i] and logic.conditions[ind]["data"][i]
                    temp = True
            
            if len(data) == 0: # if data is empty create full false list
                for i in range(len(raw[logic.rawind])): data.append(False)

            self.marked = []
            for d in data:
                if d: self.marked.append("#40ff7700")
                else: self.marked.append(None)
        
        # risk management
        if len(self.inputs[3]) != 0: # if risk management has been edited
            risk = self.inputs[3] + [[]]
        else:
            risk = [[10000, "Trailing Stop", 0.01, 200, 0], [], []]

        # stock preferences
        prefs = []
        if self.prefs[self.findPref("Calculate strategies on live data")][1]:
            if len(self.inputs[1]) == 0: # no inputs loaded
                prefs = ["2y", "1h", ""] # default | [period, interval]
            else:
                prefs = [self.inputs[1][0], self.inputs[1][1], self.inputs[1][2]]

        idd = 0
        if type(indx) == int: idd = logic.strategies[indx]["ID"] # to replace older strategy
        else:
            i = 0
            while i < len(logic.strategies): # check if id is already in use
                if logic.strategies[i]["ID"] == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1
        if name is None:
            if tbox.text() == "" or tbox.text() == "Conditions": name = "Strategy " + str(idd)
            else: name = tbox.text()
        else: 
            if tbox.text() not in ["", "Conditions"]: name = tbox.text() # change name if new name is given

        strict = {"ID":idd, "name":name, "conds":conds, "data":data, "show":True, "calc":calc, "risk":risk, "prefs":prefs}
        if type(indx) == int: logic.strategies[indx] = strict # overwrite older strategy
        else: logic.strategies.append(strict)

        # backtest
        logic.currentSystem = self.tabs.currentIndex() # stores current index for correct displaying of backtest
        self.resetBacktest() # reset any backtest that might still be on screen
        dont = False # dont do 
        if self.inputs[2][1].isChecked(): # debug mode
            self.debugvar = [True, 0, idd, True]
            dont = True
            self.readstocks("0", "debug", "+") # add debug tab
        else:
            self.debugvar = [False, -1, -1, False]
        self.backtest(idd)
        global sp500 
        if self.prefs[self.findPref("Calculate strategies on live data")][1]:
            # refresh s&p 500 to not have it desync with subprocess
            table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies') # get s&p 500 tickers
            df = table[0]
            sp500 = df["Symbol"].to_list()
        else: 
            sp500 = [] # unload for the future
        if self.prefs[self.findPref("Calculate strategies on all available data")][1] and not dont:
            self.multiback(idd)
        self.tabs.addTab("Backtest")
        self.tabs.addTab("Exit Percentages")
        self.tabs.addTab("Benchmark Comparison")

        parent.close()
        self.setScene()

    def calcStrategy(self, idd): # calculate a strategy given the id
        # run subfunction (does the same as previous fn)
        self.stopButton() # stop all threads to prepare for new strategy
        logic.calcStrategy(idd)
        
        if logic.strategies[logic.find("s", idd)]["show"]: # if strategy should be marked
            self.marked = []
            for d in logic.strategies[logic.find("s", idd)]["data"]:
                if d: self.marked.append("#40ff7700")
                else: self.marked.append(None)

        # backtest
        logic.currentSystem = self.tabs.currentIndex() # stores current index for correct displaying of backtest
        self.resetBacktest() # reset any backtest that might still be on screen
        self.backtest(idd)
        global sp500 
        if self.prefs[self.findPref("Calculate strategies on live data")][1]:
            # refresh s&p 500 to not have it desync with subprocess
            table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies') # get s&p 500 tickers
            df = table[0]
            sp500 = df["Symbol"].to_list()
        else: 
            sp500 = [] # unload for the future
        if self.prefs[self.findPref("Calculate strategies on all available data")]:
            self.multiback(idd)
        self.tabs.addTab("Backtest")
        self.tabs.addTab("Exit Percentages")
        self.tabs.addTab("Benchmark Comparison")

        self.setScene()

    def backtest(self, ind): # backtest strategy of id
        logic.backtest(ind) # fn has been moved here
        procManager.register("backthreads") # register process because it will be shown
        procManager.setCurrent("backthreads")
        if self.prefs[self.findPref("Calculate strategies on all available data")]:
            logic.stats.finished = False # for multiprocessing
        else: logic.stats.finished = True
        self.displayStats()

    def multiback(self, idd): # will run multiple backtests of strategy
        global raw
        # setup function
        self.stopbackgs = False # dont stop all background tasks
        inc = 1 # increment and number of threads
        logic.backthreads = []

        for i in range(inc):
            logic.backthreads.append(BackThread(logic.backthread, inc, len(raw), deepcopy(logic.strategies[logic.find("s", idd)]["conds"]), i)) # make new backthreads
            logic.backthreads[-1].calc = deepcopy(logic.strategies[logic.find("s", idd)]["calc"])
            logic.backthreads[-1].risk = deepcopy(logic.strategies[logic.find("s", idd)]["risk"])
            if self.prefs[self.findPref("Calculate strategies on live data")][1]: logic.backthreads[-1].prefs = deepcopy(logic.strategies[logic.find("s", idd)]["prefs"])
            logic.backthreads[-1].queue = self.queue # set queue to main queue
        
        for b in logic.backthreads: # start backthreads
            b.start()
        
        self.threads = []
        self.threads.append(QtCore.QThread(self))
        self.threads[-1].started.connect(self.updateStats)
        self.threads[-1].finished.connect(self.threads[-1].quit)
        self.threads[-1].finished.connect(self.threads[-1].deleteLater)
        self.threads[-1].start()

    def resetBacktest(self): # resets backtest data in memory
        if self.tabs.tabText(self.tabs.count() - 1) == "Benchmark Comparison": # if backtests were done
            logic.entexs = [[], [], [], []]
            for i in range(3): # remove the last 3 tabs (backtest tabs)
                tc = self.tabs.count() - 1
                self.tabs.removeTab(tc)

    def loadStrategy(self): # load strategy
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open strategy file...", "", "Strategy Pickle File (*.pkl)")[0] # get filename
        if filename == "": return # if no file was selected
        try:
            with open(filename, 'rb') as file: # if file already exist, copy whatever is written and just add onto it
                data_dict = pickle.load(file)
        except:
            self.errormsg("File invalid.")
            return
        
        if type(data_dict) != dict:
            self.errormsg("Invalid pickle file provided.")
            return
        self.mode.setCurrentText("Strategies")
        if "Conditions" not in list(data_dict.keys()):
            self.errormsg("Invalid pickle file provided.")
            return
        conds = data_dict["Conditions"]
        # check whether the conditions' ids are already in use
        usids = []
        for c in logic.conditions:
            usids.append(c["ID"])
        duples = [] # lists with old and new
        dupes = [] # just the old ids that need replacement
        for c in conds:
            if c["ID"] in usids: 
                duples.append([c["ID"]])
                dupes.append(c["ID"])
            else: usids.append(c["ID"])
        
        idd = 0
        for d in duples:
            i = 0
            while i < len(usids): # check if id is already in use
                if usids[i] == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1
            d.append(idd) # get new id for these conditions
        
        for c in conds:
            if c["ID"] in dupes:
                ind = dupes.index(c["ID"])
                c["ID"] = duples[ind][1]
            if len(c["deps"]) != 0: # complex condition
                deps = deepcopy(c["deps"])
                deps.pop(1) # pop the operator
                for d in deps:
                    if d[1] in dupes: # if id needs to be replaced
                        ind = deps.index(d)*2
                        dind = dupes.index(d[1])
                        c["deps"][ind] = duples[dind][1]

        strats = []
        for key in list(data_dict.keys()):
            if key != "Conditions":
                strats.append(data_dict[key])
        
        for s in strats:
            for c in s["conds"]:
                if c[1] in dupes: # id has to be replaced
                    ind = dupes.index(c[1])
                    s["conds"][s["conds"].index(c)] = (c[0], duples[ind][1])
        
        # also reassign ids of strategies
        usids = []
        dupes = []
        duples = []
        for s in logic.strategies:
            usids.append(s["ID"])
        for s in strats:
            if s["ID"] in usids: 
                duples.append([s["ID"]])
                dupes.append(s["ID"])
            else: usids.append(s["ID"])
        
        idd = 0
        for d in duples:
            i = 0
            while i < len(usids): # check if id is already in use
                if usids[i] == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1
            d.append(idd) # get new id for these strategies
        
        for s in strats:
            if s["ID"] in dupes:
                ind = dupes.index(s["ID"])
                s["ID"] = duples[ind][1]
            
        for s in strats:
            logic.strategies.append(s)
        for c in conds:
            logic.conditions.append(c)
        self.setScene()

    def connectDialog(self, item): # dialog for connecting / editing conditions
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Connect...")
        dbox.setFixedSize(150, 175)

        lab1 = QtWidgets.QLabel("Connect", dbox)
        lab1.move(8, 10)
        lab2 = QtWidgets.QLabel("To", dbox)
        lab2.move(8, 60)

        conds = [] 
        items = self.inputs[0][0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
        for i in items:
            conds.append(i.text()) # if condition ("c", condID)

        cboxes = []
        for i in range(2):
            cboxes.append(QtWidgets.QComboBox(dbox))
            cboxes[i].setGeometry(65, 7+50*i, 75, 22)
            cboxes[i].addItems(conds)
        cboxes[0].setCurrentText(item.text())

        cboxes.append(QtWidgets.QComboBox(dbox))
        cboxes[2].setGeometry(65, 32, 75, 22)
        cboxes[2].addItems(["Not", "And", "Or", "Xor"])

        QtWidgets.QLabel("Filter", dbox).move(8, 95)
        cbox = QtWidgets.QComboBox(dbox)
        cbox.setGeometry(65, 95, 75, 22)
        cbox.addItems(["True", "First True", "Last True", "Near"])

        def connectExec():
            nonlocal cboxes
            # hide original conditions from calculation and only calc new connected one
            conds = [] 
            items = self.inputs[0][0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
            for i in items:
                conds.append(i.text()) # if condition ("c", condID)
            indx = [conds.index(cboxes[0].currentText())] # get indexes of selected items
            indx.append(conds.index(cboxes[1].currentText()))

            idd = items[indx[0]].idd # get conid
            logic.conditions[logic.find("c", idd)]["calc"] = False # dont calculate

            cidd = 0 # get id of new condition
            i = 0
            while i < len(logic.conditions): # check if id is already in use
                if logic.conditions[i]["ID"] == cidd:
                    cidd += 1
                    i = -1 # if id in use go up and restart process
                i += 1

            deps = [] # dependencies of new condition
            if len(logic.conditions[logic.find("c", idd)]["deps"]) != 0: deps.append(("cc", idd)) # if condition is dependent; append cc (complex condition)
            else: deps.append(("ci", idd)) # else append ci (condition indicator)
            deps.append(cboxes[2].currentText().lower())

            if cboxes[2].currentText() != "Not": # if not only exclude the first one and add new condition
                logic.conditions[logic.find("c", items[indx[1]].idd)]["calc"] = False # else also disable second one
                if len(logic.conditions[logic.find("c", items[indx[1]].idd)]["deps"]) != 0: deps.append(("cc", items[indx[1]].idd)) # if condition is dependent; append cc (complex condition)
                else: deps.append(("ci", items[indx[1]].idd)) # else append ci (condition indicator)
                name = cboxes[0].currentText() + " " + cboxes[2].currentText().lower() + " " + cboxes[1].currentText()
            else:
                name = cboxes[2].currentText().lower() + " " + cboxes[0].currentText()
            condict = {"ID":cidd, "vars":[], "color":"#ffffff", "name":name, "filters":[-1, cbox.currentText()], "data":[], "deps":deps}
            logic.conditions.append(condict)
            self.inputs[0][0].addItem(ListItem(name, cidd, typ="cc")) # add item to strategy condition list
            dbox.close()

        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(37, 140)
        btn.clicked.connect(connectExec)

        dbox.exec()

    def unmarkAll(self, clearIndicators=False): # removes all of the markings
        self.marked = []
        if clearIndicators: logic.indicators = []
        self.selected = []
        self.resetGeneral(1)
        self.setScene()

    def multiMark(self): # mark all of the selected spots
        self.marked = []
        cols = [] # store first color that fills this spot
        ands = [] # true false list to look for whether all of the condtions are true

        first = True # first run through

        for s in self.selected:
            cind = logic.find("c", s)
            color = logic.conditions[cind]["color"]
            data = logic.conditions[cind]["data"]
            # cols
            for d in range(len(data)):
                if data[d]:
                    if first: cols.append(color)
                    elif cols[d] is None: cols[d] = color # replace none with color
                else:
                    if first: cols.append(None)
            first = False
            # ands
            if len(ands) == 0: ands = deepcopy(data) # if none have been loaded yet, copy first data
            else:
                for d in range(len(data)): # all datas have to be true
                    ands[d] = ands[d] and data[d]
        for a in range(len(ands)):
            if ands[a]: # if all conditions are true here
                cols[a] = "#8000ffff" # mark in light blue
            elif cols[a] is not None: # if a normal color is passed in
                cols[a] = QtGui.QColor(cols[a])
                cols[a].setAlpha(32) # change alpha
                cols[a] = cols[a].name(QtGui.QColor.NameFormat.HexArgb) # reconvert back to string

        self.marked = cols

    def about(self): # about window
        mbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, "About Stock Sim", "Version: " + version, QtWidgets.QMessageBox.StandardButton.Ok, self)
        mbox.exec()
    
    def errormsg(self, msg): # Simple Message box that tells the user whats wrong instead of crashing the program
        mbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, "Error", msg, QtWidgets.QMessageBox.StandardButton.Ok, self)
        threading.Thread(target=playsound).start()
        mbox.exec()

    def gridBox(self, what): # dialog box for grid variables
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Grid settings")
        dbox.setFixedSize(200, 150)
        label1 = QtWidgets.QLabel(dbox)
        label1.setGeometry(10, 10, 85, 25)
        self.inputs[0] = QtWidgets.QLineEdit(dbox)
        self.inputs[0].setGeometry(100, 10, 50, 25)
        label2 = QtWidgets.QLabel(dbox)
        label2.setGeometry(10, 60, 85, 25)
        self.inputs[1] = QtWidgets.QLineEdit(dbox)
        self.inputs[1].setGeometry(100, 60, 50, 25)
        self.inputs[1].setFocus()
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(100, 100)
        if what == 'x': # x axis
            label1.setText("px per t")
            label2.setText("t per ↑px")
            self.inputs[0].setText(str(self.gridconv[0]))
            self.inputs[1].setText(str(self.gridconv[1]))
            btn.pressed.connect(lambda: self.gridChanges("x", dbox))
        elif what == 'y': # y axis
            label1.setText("py per P")
            label2.setText("P per ↑py")
            self.inputs[0].setText(str(self.gridconv[2]))
            self.inputs[1].setText(str(self.gridconv[3]))
            btn.pressed.connect(lambda: self.gridChanges("y", dbox))
        dbox.exec()

    def gridChanges(self, what, parent): # change the variables based on the inputs
        # error code
        for j in range(2):
            if not isfloat(self.inputs[j].text()): # if something else is given
                self.errormsg(self.inputs[j].text() + " is not a number.")
                return
        
        for j in range(2):
            if float(self.inputs[j].text()) < 0: # out of range
                self.errormsg(self.inputs[j].text() + " is out of range.")
                return

        self.loading = True
        if what == "x":
            self.gridconv[0] = float(self.inputs[0].text())
            self.gridconv[1] = float(self.inputs[1].text())
        elif what == "y":
            self.gridconv[2] = float(self.inputs[0].text())
            self.gridconv[3] = float(self.inputs[1].text())
        parent.close()
        if self.tabs.tabText(self.tabs.currentIndex()) in ["Backtest", "Exit Percentages", "Benchmark Comparison"]: # if tab is backtest tab 
            self.setBackScene(self.tabs.tabText(self.tabs.currentIndex()), "change")
        else: 
            logic.systems[logic.currentSystem].gridconv = deepcopy(self.gridconv) # save changes to system to keep between tabs
            self.setScene()

    def debugButton(self, idd): # start the debug process without selecting debug first
        self.stopButton() # stop all threads to prepare for new strategy
        logic.currentSystem = self.tabs.currentIndex() # stores current index for correct displaying of backtest
        self.resetBacktest() # reset any backtest that might still be on screen
        self.debugvar = [True, 0, idd, True]
        self.readstocks("0", "debug", "+") # add debug tab
        self.backtest(idd)
        global sp500 
        if self.prefs[self.findPref("Calculate strategies on live data")][1]:
            # refresh s&p 500 to not have it desync with subprocess
            table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies') # get s&p 500 tickers
            df = table[0]
            sp500 = df["Symbol"].to_list()
        self.tabs.addTab("Backtest")
        self.tabs.addTab("Exit Percentages")
        self.tabs.addTab("Benchmark Comparison")

    def renameButton(self, idd, styp): # renames the object and the button
        # idd is id of object and styp is one letter string for type
        dbox = QtWidgets.QDialog(self.dialog)
        dbox.setWindowTitle("Change Name...")
        dbox.setFixedSize(200, 120)
        QtWidgets.QLabel("Please enter a new name", dbox).move(10, 10)
        tbox = QtWidgets.QLineEdit(dbox)
        tbox.setGeometry(10, 30, 130, 22)
        isOK = False # whether ok was pressed or the window was closed
        def ok():
            nonlocal isOK
            isOK = True
            dbox.close()
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(65, 75)
        btn.clicked.connect(ok)
        dbox.exec()
        #if tbox.text() == "": name = self.inputs[0][3].currentText() + " " + str(len(self.inputs[0][2].vars))
        name = tbox.text()
        if styp == "c": search = logic.conditions
        elif styp == "s": search = logic.strategies
        elif styp == "i": search = logic.indicators
        if name != "" and isOK: search[logic.find(styp, idd)]["name"] = name 
        self.resetWindows()

    def deleteButton(self, idd, typ="conds"): # deletes the button
        # idd is id and typ is type; obviously
        poplist = []
        if typ == "inds":
            for i in range(len(logic.indicators)):
                if logic.indicators[i]["ID"] == idd: # if indicator has said id
                    poplist.append(i)
            
            poplist.reverse() # pop in reverse
            for p in poplist:
                logic.indicators.pop(p)
            
            poplist = []
        elif typ == "conds":
            endangered = []
            # check if a strategy would be deleted as well
            for s in logic.strategies:
                for c in s["conds"]:
                    if c[1] == idd:
                        endangered.append(s["ID"])

            if len(endangered) > 0: # if a strategy is endangered
                st = ""
                for e in endangered:
                    st += str(e) + "\n"
                threading.Thread(target=lambda:playsound("Exclamation")).start()
                result = QtWidgets.QMessageBox.question(self, "Are you sure?", "Deleting this would also delete Strategies:\n" + st, 
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                    return
            
            for i in range(len(logic.conditions)):
                if logic.conditions[i]["ID"] == idd: # if indicator has said id
                    poplist.append(i)
        
            poplist.reverse() # pop in reverse
            for p in poplist:
                logic.conditions.pop(p) # pop condition as well
        
            # also unselect if something was selected
            if len(self.selected) != 0:
                self.selected = []
                self.resetGeneral(1)
                self.marked = []
                self.setScene()

            logic.updateStrategies(idd) # update all strategies that used the now deleted condition
        elif typ == "strats":
            for i in range(len(logic.strategies)):
                if logic.strategies[i]["ID"] == idd: # if strategy has said id
                    poplist.append(i)
            
            poplist.reverse() # pop in reverse
            for p in poplist:
                logic.strategies.pop(p)
            logic.delUnusedConditions() # delete obsolete conditions
        
        self.setScene()
    
    def stopButton(self, what="all"): # button to stop background tasks
        # stop all processes / check whether they've finished
        if what == "all" or what == "backthreads":
            self.stopbackgs = True
            for b in logic.backthreads:
                b.process.join(timeout=0) # check whether process is finished by trying to join and finishing immediately
                if b.process.is_alive(): # if process is still running
                    b.process.terminate() # kill process
        
            for t in self.threads:
                t.quit()
            self.threads = []

            logic.backthreads = []

    def debugNext(self): # next button in debug mode
        if self.tabs.tabText(self.tabs.currentIndex()).split(" ")[0] != "Debug": # if debug tab not focused
            for t in range(self.tabs.count()):
                if self.tabs.tabText(t).split(" ")[0] == "Debug": 
                    self.tabs.setCurrentIndex(t)
        
        if self.debugvar[1] + 1 >= len(stocks) and len(logic.strategies[logic.find("s", self.debugvar[2])]["prefs"]) == 0: return # if every stock has been read
        elif self.debugvar[1] + 1 >= len(sp500): return # for live data
        self.debugvar[1] += 1
        self.debugvar[3] = True
        if len(logic.strategies[logic.find("s", self.debugvar[2])]["prefs"]) == 0: # do this because same check is done in backthreads
            self.readstocks(str(self.debugvar[1]), "debug") # load new data
        else:
            global raw
            raw[logic.rawind], self.timeaxis = stock_data(sp500[self.debugvar[1]], period=logic.strategies[logic.find("s", self.debugvar[2])]["prefs"][0],
                                            interval=logic.strategies[logic.find("s", self.debugvar[2])]["prefs"][1])
            if len(raw[logic.rawind]) == 0 or raw[logic.rawind][0] == "Delisted":
                self.debugNext() # if stock doesnt exist, go to next
                return
            self.newScene("", "Debug " + sp500[self.debugvar[1]], sp500[self.debugvar[1]])

        logic.currentSystem = self.tabs.currentIndex()
        for c in logic.strategies[logic.find("s", self.debugvar[2])]["conds"]: # unload all data
            logic.conditions[logic.find("c", c[1])]["data"] = []
        logic.calcStrategy(self.debugvar[2])
        
        self.marked = [] # mark strategy spots
        n = 0
        for d in logic.strategies[logic.find("s", self.debugvar[2])]["data"]:
            if d: 
                self.marked.append("#40ff7700")
                n += 1
            else: self.marked.append(None)
        
        if n == 0:
            if self.prefs[self.findPref("When debugging skip to next marked stock")][1]:
                self.debugNext()
                return
        wid = QtWidgets.QWidget() # stats
        wid.setStyleSheet(widgetstring)
        self.sideStats.reset()
        self.sideStats.strings.append("Number Marked: " + str(n))

        self.backtest(self.debugvar[2])

        self.sideStats.strings.append("Money: " + str(round(logic.stats.money, 2)) + "$")
        self.sideStats.display(wid)
        self.docks[1].setWidget(wid)
        
        self.setScene()

    def sideRemove(self): # remove current shown in generals[2] | x button in bottom left
        cur = procManager.current()
        if cur == "backthreads": self.debugvar = [False, -1, -1, False] # reset debug if removed
        procManager.remCurrent()
        self.stopButton(cur)
        self.displayStats()

    def toCoord(self, what, value): # shortcut for coordinate conversion
        return coordinate(what=what, value=value, gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)

    def draw_scene(self): # draws the graphical component

        # main graphic window
        self.view = View(QtWidgets.QGraphicsScene(self), self)
        self.sview = SmallView() # predefinition
        self.syview = Axis(QtWidgets.QGraphicsScene(self)) # predefinition
        self.tabs = None # predefinition
        self.setScene()
        self.view.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.view.horizontalScrollBar().valueChanged.connect(self.whenchangedx)
        self.view.verticalScrollBar().valueChanged.connect(self.whenchangedy)

        # smaller graphic window for indicators
        self.sview = SmallView(self)
        self.sview.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        self.sview.setFixedHeight(150)
        self.sview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sview.setVisible(False)

        # y axis for smaller graphic window
        self.syview = Axis(QtWidgets.QGraphicsScene(self), self)
        self.syview.setFixedWidth(35)
        self.syview.setFixedHeight(150)
        self.syview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.syview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.syview.setVisible(False)
        #self.syview.setMouseFn(lambda: self.gridBox("y"))

        # y axis that will show price
        self.yview = Axis(QtWidgets.QGraphicsScene(self), self)
        self.yview.setFixedWidth(35)
        self.yview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.yview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.yview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding)
        self.yview.setMouseFn(lambda: self.gridBox("y"))

        # x axis that will show time
        self.xview = Axis(QtWidgets.QGraphicsScene(self), self)
        self.xview.setFixedHeight(25)
        self.xview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.xview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.xview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.xview.setMouseFn(lambda: self.gridBox("x"))

        # # preset price rects
        # for i in range(2):
        #     self.pricerects[i] = PriceRect("default", QtCore.QPointF(-100, -100))

    def whenchangedx(self): # update x axis
        if not self.loading:
            if self.sview.isVisible(): self.sview.horizontalScrollBar().setValue(self.view.horizontalScrollBar().value())
            self.moved = True
            self.view.scene().removeItem(self.crosshairx)
            self.view.scene().removeItem(self.crosshairy)
            #self.pricerects[0].placed = False # because scene is cleared
            self.xview.scene().clear()
            self.xview.scene().setSceneRect(0, 0, self.view.width(), 25)
            col = None
            first = 0
            for x in range(int((self.view.width()+self.view.horizontalScrollBar().value()%self.gridconv[0])/self.gridconv[0])+1): # int((width+scroll%gridconv)/grid)
                offset = self.view.horizontalScrollBar().value()%self.gridconv[0]
                ind = self.view.horizontalScrollBar().value()-offset+x*self.gridconv[0] # values on the axis i.e. base-offset+x*grid
                val = int((ind/self.gridconv[0])*self.gridconv[1])+self.rangex[0] # convert from coordinate to time using (x/gridx)*gridt and add offset from range
                if x == 0: first = val

                if len(self.timeaxis) != 0 and val < len(self.timeaxis): # when a time axis is present
                    shorts = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    dat = self.timeaxis[val].to_pydatetime() # get date from date list
                    lastdat = self.view.horizontalScrollBar().value()-offset+(x-1)*self.gridconv[0] # ind
                    lastdat = int((lastdat/self.gridconv[0])*self.gridconv[1])+self.rangex[0] # val
                    if lastdat < 0: # if index out of range
                        val = dat.year
                        if theme == "dark": col = QtGui.QColor("#00bbff")
                        else: col = QtGui.QColor("#3366ff")
                    else:
                        lastdat = self.timeaxis[lastdat].to_pydatetime() # else get date of said index
                        if dat.year > lastdat.year: # year changed
                            val = dat.year
                            if theme == "dark": col = QtGui.QColor("#00bbff")
                            else: col = QtGui.QColor("#3366ff")
                        elif dat.month > lastdat.month: # month changed
                            val = shorts[dat.month-1]
                            if theme == "dark": col = QtGui.QColor("#00ffbb")
                            else: col = QtGui.QColor("00bb44")
                        elif dat.day > lastdat.day: # day changed
                            val = str(dat.day)
                            if theme == "dark": col = QtGui.QColor(QtCore.Qt.GlobalColor.white)
                            else: col = QtGui.QColor(QtCore.Qt.GlobalColor.black)
                            if int(val)%10 == 1 and val != "11": val += "st"
                            elif int(val)%10 == 2 and val != "12": val += "nd"
                            elif int(val)%10 == 3 and val != "13": val += "rd"
                            else: val += "th"
                        elif dat.hour > lastdat.hour: # hour changed
                            val = str(dat.hour) + "h"
                            if theme == "dark": col = QtGui.QColor("#cccccc")
                            else: col = QtGui.QColor("333333")
                        elif dat.minute > lastdat.minute: # minute changed
                            val = str(dat.minute) + "min"
                            if theme == "dark": col = QtGui.QColor("#999999")
                            else: col = QtGui.QColor("#666666")
                        elif dat.second > lastdat.second: # second changed
                            val = str(dat.second) + "s"
                            if theme == "dark": col = QtGui.QColor("#666666")
                            else: col = QtGui.QColor("#999999")
                    offset += len(str(val))/2*5
                elif val < 10: # for centering without time axis
                    offset += 2.5
                elif val < 100:
                    offset += 5
                elif val < 1000:
                    offset += 7.5
                elif val < 10000:
                    offset += 10
                
                if col == None:
                    if theme == "light": col = QtGui.QColor(0, 0, 0)
                    else: col = QtGui.QColor(255, 255, 255)
                tex = SimpleText(str(val), col, QtCore.QPointF(x*self.gridconv[0]-offset, 0))

                self.xview.scene().addItem(tex)
                pen = None
            self.view.scene().addItem(self.crosshairy)
            self.view.scene().addItem(self.crosshairx)

    def whenchangedy(self): # update y axis
        if not self.loading:
            self.moved = True
            self.view.scene().removeItem(self.crosshairx)
            self.view.scene().removeItem(self.crosshairy)
            #self.pricerects[1].placed = False # because scene is cleared
            self.yview.scene().clear()
            self.yview.scene().setSceneRect(0, 0, 35, self.view.height())
            for y in range(int((self.view.height()+self.view.verticalScrollBar().value()%self.gridconv[2])/self.gridconv[2])+1): # int((height+scroll%gridconv)/grid)
                offset = self.view.verticalScrollBar().value()%self.gridconv[2]
                ind = self.view.verticalScrollBar().value()-offset+y*self.gridconv[2]
                val = int(self.view.scene().height()-ind) # first convert to normal coordinates (y up, screen up)
                val = (val/self.gridconv[2])*self.gridconv[3]+self.rangey[0]
                offset += 7.5
                offx = 0
                if self.gridconv[3] < 0.5: # for really small prices
                    offx -= 7.5
                if val < 10: # for centering
                    offx += 9
                elif val < 100:
                    offx += 5
                elif val < 1000:
                    offx += 3
                if val%1 == 0: val = int(val) # if not float / no decimal part
                if theme == "light": tex = SimpleText(str(val), QtGui.QColor(0, 0, 0), QtCore.QPointF(offx, y*self.gridconv[2]-offset))
                else: tex = SimpleText(str(val), QtGui.QColor(255, 255, 255), QtCore.QPointF(offx, y*self.gridconv[2]-offset))
                
                self.yview.scene().addItem(tex)
            self.view.scene().addItem(self.crosshairy)
            self.view.scene().addItem(self.crosshairx)
    
    def setScene(self): # set the Scene (reset, remake grid and candles)
        self.loading = True
        sizx = ((self.rangex[1]-self.rangex[0])/self.gridconv[1])*self.gridconv[0] # ((t-t0)/how many t per pixel)*npixels
        sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
        if sizy < self.view.height():
            self.gridconv[3] /= 2 # half the square size
            sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2]
        sizx += self.view.width()/2 # buffer
        self.heivar = sizy
        self.view.scene().clear()
        self.view.scene().setSceneRect(0, 0, sizx, sizy)
        self.view.scene().addItem(Grid(self.view.scene().sceneRect(), self.gridconv))
        can = QtWidgets.QGraphicsLineItem(sizx-self.view.width()/2, 0, sizx-self.view.width()/2, sizy) # now line
        if theme == "light": can.setPen(QtGui.QColor("#000000"))
        else: can.setPen(QtGui.QColor("#ffffff"))
        self.view.scene().addItem(can)
        if self.chartchecks[0].isChecked(): # if Candlesticks is checked
            for c in self.candles: 
                can = Candle(c[0], c[1])
                if len(self.timeaxis) != 0: 
                    dat = self.timeaxis[c[0]-self.rangex[0]].to_pydatetime()
                    can.date = dat
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                self.view.scene().addItem(can)
        elif self.chartchecks[1].isChecked(): # graph depiction
            for i in range(len(self.candles)-1): # one less because always draws line to the next
                c = [self.candles[i], self.candles[i+1]] # for simplification
                for e in range(2):
                    c[e] = Candle(c[e][0], c[e][1])
                    c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                if c[0].up: close1 = c[0].y
                else: close1 = c[0].y+c[0].hei # this means the close is down so add height
                if c[1].up: close2 = c[1].y
                else: close2 = c[1].y + c[1].hei
                can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                if theme == "light": can.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.blue))
                else: can.setPen(QtGui.QPen(QtGui.QColor(50, 240, 240)))
                self.view.scene().addItem(can)
        else: # heikin-ashi
            # first candle
            c = deepcopy(self.candles[0])
            last = Candle(c[0], c[1])
            if len(self.timeaxis) != 0: 
                dat = self.timeaxis[c[0]-self.rangex[0]].to_pydatetime()
                last.date = dat
            last.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
            self.view.scene().addItem(last)
            for c in self.candles[1:]: # all except first one
                ohlc = deepcopy(last.ohlc)
                new = deepcopy(c[1])
                ohlc[0] = (ohlc[0] + ohlc[3])/2 # previous open + close /2
                ohlc[1] = max([new[0], new[1], new[3]]) # max of high open or close
                ohlc[2] = min([new[0], new[2], new[3]]) # min of low open or close
                ohlc[3] = (new[0] + new[1] + new[2] + new[3])/4
                if ohlc[0] > ohlc[1]: ohlc[1] = ohlc[0] # to prevent errors
                elif ohlc[0] < ohlc[2]: ohlc[2] = ohlc[0]
                can = Candle(c[0], ohlc)
                if len(self.timeaxis) != 0: 
                    dat = self.timeaxis[c[0]-self.rangex[0]].to_pydatetime()
                    can.date = dat
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                last = can
                self.view.scene().addItem(can)
        
        #if self.mode.currentText() == "Conditions/Indicators" or self.mode.currentText() == "Strategies":
        # indicators
        self.sview.setVisible(False) # default
        self.syview.setVisible(False)
        changey = False # whether to change y axis of smallview
        if len(logic.indicators) != 0: # if indicators are used
            self.sview.colors = [] # empty colors
            self.sview.graphInds = []
            self.sview.isVolume = False
            self.sview.marked = []
            self.sview.density = (20, 20)
            self.sview.sizx = sizx
            self.sview.rangex = self.rangex
            for ind in logic.indicators: # for every indicator
                if ind["show"]: # if should show graph
                    for obj in ind["data"]: # in case of bollinger e.g. show all graphs
                        if ind["dMode"] == 1: # if displayMode = Graph
                            for i in range(len(self.candles)-1): # do same as graph
                                c = [self.candles[i], self.candles[i+1]] # for simplification
                                for e in range(2):
                                    c[e] = Candle(c[e][0], c[e][1])
                                    c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                if i != len(self.candles)-1:
                                    close1 = self.toCoord("y", obj[i]) # get positions
                                    close2 = self.toCoord("y", obj[i+1])
                                can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                                can.setPen(QtGui.QColor(ind["color"]))
                                self.view.scene().addItem(can)
                        elif ind["dMode"] == 2: # display graph on bottom view
                            self.sview.setVisible(True)
                            self.syview.setVisible(True)
                            if ind["data"].index(obj) == 0: 
                                if ind["indName"] == "rsi":
                                    self.sview.colors.append(QtGui.QColor("#888888"))
                                    fifties = []
                                    for i in range(len(self.candles)):
                                        fifties.append(50)
                                    self.sview.graphInds.append(fifties)
                                elif ind["indName"] == "macd":
                                    self.sview.colors.append(QtGui.QColor("#888888"))
                                    zeroes = []
                                    for i in range(len(self.candles)):
                                        zeroes.append(0)
                                    self.sview.graphInds.append(zeroes)
                                elif ind["indName"] == "atr":
                                    pass

                                self.sview.colors.append(QtGui.QColor(ind["color"]))
                            else:
                                col = QtGui.QColor(ind["color"])
                                col.setRed(255-col.red())
                                col.setGreen(255-col.green())
                                col.setBlue(255-col.blue())
                                self.sview.colors.append(col)
                            self.sview.graphInds.append(obj)
                            self.sview.gridconv = deepcopy(self.gridconv)
                            self.sview.regularScene()
                            changey = True
                        elif ind["dMode"] == 3: # volume
                            self.sview.colors.append(QtGui.QColor(ind["color"]))
                            self.sview.isVolume = True
                            self.sview.setVisible(True)
                            self.syview.setVisible(True)
                            self.sview.gridconv = deepcopy(self.gridconv)
                            self.sview.regularScene()
                            changey = True
            if changey:
                self.syview.scene().clear()
                self.syview.scene().setSceneRect(0, 0, 35, self.sview.height())
                for y in range(int((self.sview.height()+self.sview.verticalScrollBar().value()%self.sview.gridconv[2])/self.sview.gridconv[2])+1): # int((height+scroll%gridconv)/grid)
                    offset = self.sview.verticalScrollBar().value()%self.sview.gridconv[2]
                    ind = self.sview.verticalScrollBar().value()-offset+y*self.sview.gridconv[2]
                    val = int(self.sview.scene().height()-ind) # first convert to normal coordinates (y up, screen up)
                    val = (val/self.sview.gridconv[2])*self.sview.gridconv[3]+self.sview.rangey[0]
                    offset += 7.5
                    offx = 0
                    if self.sview.gridconv[3] < 0.5: # for really small prices
                        offx -= 7.5
                    if val < 10: # for centering
                        offx += 9
                    elif val < 100:
                        offx += 5
                    elif val < 1000:
                        offx += 3
                    if val%1 == 0: val = int(val) # if not float / no decimal part
                    if val > 1000000: 
                        val /= 1000000
                        val = str(round(val, 1)) + "M"
                    elif val > 1000: 
                        val /= 1000
                        val = str(round(val, 1)) + "K"
                    if theme == "light": tex = SimpleText(str(val), QtGui.QColor(0, 0, 0), QtCore.QPointF(offx, y*self.sview.gridconv[2]-offset))
                    else: tex = SimpleText(str(val), QtGui.QColor(255, 255, 255), QtCore.QPointF(offx, y*self.sview.gridconv[2]-offset))
                    
                    self.syview.scene().addItem(tex)
        # marked
        for m in range(len(self.marked)):
            if self.marked[m] is not None: # if spot is marked
                can = Candle(self.candles[m][0], self.candles[m][1])
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                rect = QtCore.QRectF(can.x+1, 2, can.wid-1, self.view.scene().height()-2)
                self.view.scene().addRect(rect, QtGui.QColor(self.marked[m]), QtGui.QColor(self.marked[m]))
        if self.mode.currentText() == "Base Graph": # base graph
            for s in self.spots: # show selected spots
                can = Candle(self.candles[s][0], self.candles[s][1])
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                rect = QtCore.QRectF(can.x, can.top-50, can.wid, can.tip-can.top+100)
                self.view.scene().addRect(rect, QtGui.QColor("#ffff00"))

        # adjust scrollbar
        if len(self.candles) != 0:
            offset = self.view.horizontalScrollBar().value()%self.gridconv[0]
            if self.debugvar[3] and len(self.marked) != 0: # first adjust
                self.debugvar[3] = False
                no = False
                for i in range(len(self.marked)): # get first marked
                    if self.marked[i] is not None: break
                    if i == len(self.marked) - 1: no = True # if no value has been found
                if not no:
                    ind = ((i-self.rangex[0])*self.gridconv[0])/self.gridconv[1] # scroll from time
                    self.view.horizontalScrollBar().setValue(int(ind))
                    yval = self.toCoord("y", self.candles[i][1][3]) - self.view.height()/2
                    self.view.verticalScrollBar().setValue(int(yval))
            else:
                ind = self.view.horizontalScrollBar().value()-offset
                val = int((ind/self.gridconv[0])*self.gridconv[1])+self.rangex[0] # time from horizontal scrollbar
                yval = self.toCoord("y", self.candles[val][1][3]) - self.view.height()/2
                self.view.verticalScrollBar().setValue(int(yval))

        # crosshair
        if theme == "light": pen = QtGui.QPen(QtCore.Qt.GlobalColor.black)
        else: pen = QtGui.QPen(QtCore.Qt.GlobalColor.white)
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        self.crosshairy = QtWidgets.QGraphicsLineItem(-5, 0, 5, 0)
        self.crosshairy.setPen(pen)
        self.crosshairy.setZValue(1000) # always in front
        self.crosshairx = QtWidgets.QGraphicsLineItem(-5, 0, 5, 0)
        self.crosshairx.setPen(pen)
        self.crosshairx.setZValue(1000) # always in front
        self.view.scene().addItem(self.crosshairy)
        self.view.scene().addItem(self.crosshairx)
        self.view.setMouseFn(self.updateCrosshair)
        self.view.setInfoFn(self.updateInfo) # also change info function

        # corner button
        if self.tabs is not None:
            self.cornerSet("Live" in self.tabs.tabText(self.tabs.currentIndex()))

        # selection rectangle for showing what candle is selected
        self.focus = Focus()
        self.tangent = None # Line that shows current trend
        self.tempInds = [] # reset temporary indicators

        self.resetWindows()

        self.loading = False

    def setBackScene(self, what, how=""):
        self.mode.setCurrentText("Base Graph")
        self.mode.setEnabled(False)
        self.loading = True
        if what == "Backtest":
            if how == "": # if no change to gridconv is made
                self.rangey = deepcopy(logic.systems[logic.currentSystem].rangey)
                self.gridconv = deepcopy(logic.systems[logic.currentSystem].gridconv)
            sizx = ((self.rangex[1]-self.rangex[0])/self.gridconv[1])*self.gridconv[0] # ((t-t0)/how many t per pixel)*npixels
            sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
            if sizy < self.view.height():
                self.gridconv[3] /= 2 # half the square size
                sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2]
            self.heivar = sizy
            self.view.scene().clear()
            self.view.scene().setSceneRect(0, 0, sizx, sizy)
            self.view.scene().addItem(Grid(self.view.scene().sceneRect(), self.gridconv))
            # graph depiction
            for i in range(len(self.candles)-1): # one less because always draws line to the next
                c = [self.candles[i], self.candles[i+1]] # for simplification
                for e in range(2):
                    c[e] = Candle(c[e][0], c[e][1])
                    c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                if c[0].up: close1 = c[0].y
                else: close1 = c[0].y+c[0].hei # this means the close is down so add height
                if c[1].up: close2 = c[1].y
                else: close2 = c[1].y + c[1].hei
                can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                if theme == "light": can.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.blue))
                else: can.setPen(QtGui.QPen(QtGui.QColor(50, 240, 240)))
                self.view.scene().addItem(can)
            
            # triangles
            for e in range(len(logic.entexs[0])): # for every entry and exit
                tim = e
                if len(self.timeaxis) != 0:
                    tim = self.timeaxis[e]
                
                if logic.entexs[0][e]:
                    tri = Triangle(e, raw[logic.rawind][e][3], True, tim)
                    tri.convCoords(self.gridconv, self.rangex, self.rangey, self.heivar)
                    self.view.scene().addItem(tri)
                if logic.entexs[1][e]:
                    tri = Triangle(e, raw[logic.rawind][e][3], False, tim)
                    tri.convCoords(self.gridconv, self.rangex, self.rangey, self.heivar)
                    self.view.scene().addItem(tri)
            
        elif what == "Exit Percentages":
            if how == "": # if no change to gridconv is made
                exitpercs = [] # just for range purposes
                for e in logic.entexs[2]:
                    exitpercs.append(e[1])
                if len(logic.entexs[2]) == 0: self.rangey = (-1, 1) # if no exits exist
                else: self.rangey = (floor(min(exitpercs)), ceil(max(exitpercs))) # percent range
                self.gridconv = [40, 5, 40, 0.1]
            sizx = ((self.rangex[1]-self.rangex[0])/self.gridconv[1])*self.gridconv[0] # ((t-t0)/how many t per pixel)*npixels
            sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
            if sizy < self.view.height():
                self.gridconv[3] /= 2 # half the square size
                sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2]
            self.heivar = sizy
            self.view.scene().clear()
            self.view.scene().setSceneRect(0, 0, sizx, sizy)
            self.view.scene().addItem(Grid(self.view.scene().sceneRect(), self.gridconv))
            
            # 0 line
            ycor = self.toCoord("y", 0)
            line = QtCore.QLineF(0, ycor, self.view.scene().width(), ycor)
            if theme == "dark": self.view.scene().addLine(line, QtGui.QColor("#ffffff"))
            else: self.view.scene().addLine(line, QtGui.QColor("#000000"))

            # circles
            for e in logic.entexs[2]: # for every exit
                tim = e[0]
                if len(self.timeaxis) != 0:
                    tim = self.timeaxis[e[0]]
                cir = Circle(e[0], e[1], e[1] > 0, e[1], tim)
                cir.convCoords(self.gridconv, self.rangex, self.rangey, self.heivar)
                self.view.scene().addItem(cir)
        elif what == "Benchmark Comparison":
            if how == "":
                self.gridconv = [40, 5, 40, 0.1]
                self.rangey = (0, 2)
            sizx = ((self.rangex[1]-self.rangex[0])/self.gridconv[1])*self.gridconv[0] # ((t-t0)/how many t per pixel)*npixels
            sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
            self.heivar = sizy
            self.view.scene().clear()
            self.view.scene().setSceneRect(0, 0, sizx, sizy)
            self.view.scene().addItem(Grid(self.view.scene().sceneRect(), self.gridconv))

            closepercs = []
            for t in raw[logic.systems[logic.currentSystem].rawind]:
                closepercs.append(t[3]/raw[logic.systems[logic.currentSystem].rawind][0][3]) # how much you would've had if you held on to the stock until that time
            
            # graph depiction
            for t in range(len(raw[logic.systems[logic.currentSystem].rawind])-2): # for every stock time point minus one because graph
                # benchmark
                lin = QtWidgets.QGraphicsLineItem(self.toCoord("x", t+0.5), self.toCoord("y", closepercs[t]), self.toCoord("x", t+1.5), self.toCoord("y", closepercs[t+1]))
                if theme == "dark": lin.setPen(QtGui.QColor(50, 240, 240))
                else: lin.setPen(QtGui.QColor("#0000CC"))
                self.view.scene().addItem(lin)
                # strategy
                lin = QtWidgets.QGraphicsLineItem(self.toCoord("x", t+0.5), self.toCoord("y", logic.entexs[3][t]), self.toCoord("x", t+1.5), self.toCoord("y", logic.entexs[3][t+1]))
                if theme == "dark": lin.setPen(QtGui.QColor("#fff023"))
                else: lin.setPen(QtGui.QColor("#23f023"))
                self.view.scene().addItem(lin)

        # crosshair
        if theme == "light": pen = QtGui.QPen(QtCore.Qt.GlobalColor.black)
        else: pen = QtGui.QPen(QtCore.Qt.GlobalColor.white)
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        self.crosshairy = QtWidgets.QGraphicsLineItem(-5, 0, 5, 0)
        self.crosshairy.setPen(pen)
        self.crosshairy.setZValue(1000) # always in front
        self.crosshairx = QtWidgets.QGraphicsLineItem(-5, 0, 5, 0)
        self.crosshairx.setPen(pen)
        self.crosshairx.setZValue(1000) # always in front
        self.view.scene().addItem(self.crosshairy)
        self.view.scene().addItem(self.crosshairx)
        self.view.setMouseFn(self.updateCrosshair)
        self.view.setInfoFn(self.updateInfo) # also change info function
        self.resetWindows()
        self.loading = False

        # side stats
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        self.sideStats.reset()
        self.sideStats.strings.append("Money: " + str(round(logic.stats.money, 2)) + "$")
        self.sideStats.display(wid)
        self.docks[1].setWidget(wid)

    def updateCrosshair(self, event): # update the crosshair when mouse moved, fn will be passed on
        pointf = QtCore.QPointF(event.pos().x(), event.pos().y()) # preconvert because else it wont accept
        scene_pos = self.view.mapFromScene(pointf)

        dx = self.view.horizontalScrollBar().value()*2 # also add the change of the scrolling to the crosshair
        dy = self.view.verticalScrollBar().value()*2 # why *2 dont ask me

        # crosshair placement
        self.crosshairy.setLine(scene_pos.x()+dx, scene_pos.y()-1500+dy, scene_pos.x()+dx, scene_pos.y()+1500+dy)
        self.crosshairx.setLine(scene_pos.x()-2000+dx, scene_pos.y()+dy, scene_pos.x()+2000+dx, scene_pos.y()+dy)

        # doesn't work because qtgraphics suck
        # # price rect placement
        # if not self.moved:
        #     for p in range(len(self.pricerects)):
        #         if not self.pricerects[p].placed:
        #             if p == 0:
        #                 self.pricerects[p] = PriceRect(str(scene_pos.x()), QtCore.QPointF(pointf.x(), 0))
        #                 self.pricerects[p].placed = True
        #                 self.pricerects[p].setZValue(1000)
        #                 self.xview.scene().addItem(self.pricerects[p])
        #             else:
        #                 self.pricerects[p] = PriceRect(str(scene_pos.y()), QtCore.QPointF(0, pointf.y()))
        #                 self.pricerects[p].placed = True
        #                 self.pricerects[p].setZValue(1000)
        #                 self.yview.scene().addItem(self.pricerects[p])
        #         else:
        #             print("s", scene_pos.x(), scene_pos.y())
        #             print("p", pointf.x(), pointf.y())
        #             if p == 0: # x rect
        #                 self.pricerects[p].setText(str(scene_pos.x()))
        #                 self.pricerects[p].setX(pointf.x()-9)
        #                 self.pricerects[p].setY(0)
        #             else: # y rect
        #                 self.pricerects[p].setText(str(scene_pos.y()))
        #                 self.pricerects[p].setX(0)
        #                 self.pricerects[p].setY(pointf.y()-9)
            

    def updateInfo(self, event): # updates Condition info about candle
        # i = 0
        # for p in self.pricerects:
        #     if p.placed:
        #         if i == 0: self.xview.scene().removeItem(p)
        #         else: self.yview.scene().removeItem(p)
        #     p.placed = False
        #     i += 1
        if not self.moved and self.mode.currentText() == "Base Graph": # no accidental drag clicking
            canclick = False # if candle has been clicked on
            self.tempIndicator(False) # reset all temporary indicators 
            dx = self.view.horizontalScrollBar().value() # scrolling
            dy = self.view.verticalScrollBar().value()

            pointf = QtCore.QPointF(event.pos().x()+dx, event.pos().y()+dy) # get good coordinates
            items = self.view.scene().items(pointf)
            if items is not None: # skip if no items have been clicked on
                for item in items:
                    if type(item) == Candle:
                        if event.modifiers().name == "ControlModifier": 
                            if item.time not in self.spots: # put spot in or out of list
                                self.spots.append(item.time) # save spot
                            else:
                                self.spots.remove(item.time)
                            # if len(self.spots) == 0: self.resetGeneral(1)
                            # else: self.displaySelected() # show stats about selected spots
                            self.setScene()
                        else:
                            self.peek(item)
                            canclick = True
            if not canclick and self.focus.placed:
                self.view.scene().removeItem(self.focus)
                self.view.scene().removeItem(self.tangent)
                self.tangent = None
                self.focus.placed = False
                self.resetWindows()
        elif not self.moved and self.mode.currentText() != "Base Graph" and len(self.selected) != 0: # for multi select
            self.unmarkAll() # unmark all if not base graph
            self.resetGeneral(1)
        self.moved = False

    def peek(self, candle: Candle): # runs the command when a candle is clicked
        # put selected rect on candle
        if self.focus.placed: # if placed remove previous
            self.view.scene().removeItem(self.focus)
        self.focus.setRect(candle.x, candle.top, candle.wid, candle.tip-candle.top)
        self.focus.placed = True
        self.view.scene().addItem(self.focus)

        # change the variables window
        spot = candle.time
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        self.sideStats.reset() # reset current info
        ls = ["Open", "High", "Low", "Close"] # for simplicity
        if len(self.timeaxis) != 0: # if date is given
            dat = deepcopy(self.timeaxis[candle.time-self.rangex[0]])
            dat = dat.strftime("%Y/%m/%d %H:%M:%S")
            self.sideStats.strings.append("Date: " + dat)
        else: self.sideStats.strings.append("Time: " + str(candle.time))
        for i in range(4): # ohlc
            self.sideStats.strings.append(ls[i] + ": " + str(candle.ohlc[i]))
        
        self.sideStats.strings.append("Volume: " + str(raw[logic.rawind][spot][4]))

        out = indicator(logic.rawind, "extra", [], len(raw[logic.rawind])-1)

        temp = ["Top", "Bottom", "Average Body"]
        i = 0
        for t in temp:
            if i < 2: self.sideStats.strings.append(t + ": " + str(out[i][spot]))
            else: self.sideStats.strings.append(t + ": " + str(out[i]))
            i += 1
        
        out = indicator(logic.rawind, "macd", [], len(raw[logic.rawind])-1)
        temp = ["MACD", "Signal"]
        i = 0
        for t in temp:
            self.sideStats.strings.append(t + ": " + str(out[i][spot]))
            i += 1
        # alpha
        if spot >= 1: 
            start = spot - 20 # so it wont wrap around
            if start <= 0: 
                start = 0
                x = list(range(spot+1))
                y = raw[logic.rawind][start:spot+1]
            else: 
                x = list(range(20))
                y = raw[logic.rawind][start+1:spot+1] # get last 100 price points
            y.reverse() # so that the tangent will fixate on last price point
            coeffs = polyfit(x, y, 1) # if y = mx + b then coeffs[0][3] = m, coeffs[1][3] = b
            m = coeffs[0][3] # get slope instead of condition
        else: m = 0 
        m *= -1 # reverse m because y was reversed in condition
        m *= self.gridconv[1] # convert to coordinates
        angle = atan(m)*180/pi
        width = self.gridconv[0]
        m *= width
        if angle > 180: angle = 360 - angle # ability to get negative angles
        self.sideStats.strings.append("ɑ=" + str(round(angle, 2)) + "°")

        self.sideStats.display(wid) # display all of the labels

        if type(self.tangent) == QtWidgets.QGraphicsLineItem:
            self.view.scene().removeItem(self.tangent)
        self.tangent = QtCore.QLineF(candle.x-width*-100, candle.y-100*m, candle.x-width*100, candle.y+100*m)
        self.tangent = QtWidgets.QGraphicsLineItem(self.tangent)
        self.tangent.setPen(QtGui.QColor(50, 240, 240))
        self.view.scene().addItem(self.tangent)

        self.docks[1].setWidget(wid)

        # change conditions window
        # i.e. get all of the used variables for each condition and show their values at spot
        # for each of the calc variables, make a label, telling its value and name
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        pos = 2
        for cond in logic.conditions:
            if len(cond["deps"]) == 0: # only indicator conditions
                varsorted = [[], [], [], []] # v, e, x, i
                for var in cond["vars"]:
                    if type(var) == IndicatorVariable:
                        if var.var == "": varsorted[3].append(var) # indicator
                        else: varsorted[0].append(var)
                    elif type(var) == VariableEquation: varsorted[1].append(var)
                    elif type(var) == VariableExpression: varsorted[2].append(var)
                    #elif type(var) == list: filters = var # filters will be passed into variables

                def find(typ, idd): # return index of item in typ list
                    if typ == "i": search = varsorted[3]
                    elif typ == "v": search = varsorted[0]
                    elif typ == "e": search = varsorted[1]
                    else: search = varsorted[2]

                    for v in range(len(search)):
                        if search[v].id == idd:
                            return v
                time = candle.time
                what = [] # stores what variables were used exactly
                stock = logic.systems[logic.currentSystem].rawind
                for c in cond["calc"][1]:
                    if c[0] != "i" and (c[0], c[1]) not in what: what.append((c[0], c[1]))
                    if c[0] == "i": # indicator
                        var = varsorted[3][find("i", c[1])]
                        for a in var.args:
                            if "%" in str(a): var.val = None # recalculate everytime a variable is an argument
                        if not indinfo[var.indName]["once"] or var.val is None: # value needs to be calculated
                            # if once is true, get entire list and just adjust based on spot instead of calculating over and over again

                            # get arguments to also get values from variables
                            args = deepcopy(var.args)
                            for a in range(len(args)):
                                if "%" in str(args[a]):
                                    sp = args[a].split("%") # split of variable in var and spot
                                    if len(sp) == 2: sp.append("") # to allow full value returns
                                    if not isint(sp[1]) and sp[1] != "": # if variable in str
                                        temp = ["v", "e"]
                                        i = temp.index(sp[1][0])
                                        var2 = varsorted[i][find(sp[1][0], int(sp[1][1:]))]
                                        if sp[1][0] == "e": args[a] = var2.val # get original variable and value from it
                                        else: # also check for spot in variable
                                            if indinfo[var2.indName]["vtypes"][indinfo[var2.indName]["vars"].index(var2.var)] == list: # if list check for spot
                                                # check whether spot is variable or int
                                                if not isint(sp[2]) and sp[2] != "": # variable for spot
                                                    # can only be int variable or equation
                                                    i = temp.index(sp[2][0]) 
                                                    spot = varsorted[i][find(sp[2][0], int(sp[2][1:]))].val
                                                    if (sp[2][0], int(sp[2][1:])) not in what: what.append((sp[2][0], int(sp[2][1:])))
                                                elif isint(sp[2]): spot = int(sp[2])
                                                if sp[2] != "":
                                                    # convert spot to correct one with time | if spot incorrect make args to nan
                                                    if spot > time or spot < -time-1: spot = "nan"
                                                    elif spot < 0: # convert from total scale to truncated scale bc of time
                                                        spot = time + spot + 1
                                                    if spot != "nan": args[a] = var2.val[spot]
                                                    else: args[a] = float("nan")
                                                    if (sp[1][0], int(sp[1][1:]), spot) not in what: what.append((sp[1][0], int(sp[1][1:]), spot))
                                                else: 
                                                    args[a] = var2.val # just take entire thing if no value is given
                                            else: # just take value
                                                args[a] = var2.val
                                                if (sp[1][0], int(sp[1][1:])) not in what: what.append((sp[1][0], int(sp[1][1:])))

                            if indinfo[var.indName]["once"]: out = indicator(stock, var.indName, args, len(raw[stock])-1)
                            else: out = indicator(stock, var.indName, args, time)
                            if isinstance(out, tuple): # if multiple values were given
                                temp = []
                                for o in out:
                                    temp.append(o)
                                out = temp
                            else: out = [out]
                            if indinfo[var.indName]["existcheck"]: # if existcheck also adjust exist expression
                                # get exist expression
                                for ex in varsorted[2]:
                                    if ex.type == "Variable" and ex.args == [var.indName] + var.args: 
                                        ex.val = out[0]
                                        out = out[1:] # cut the exist bool out
                                        break
                            # distribute variables to children variables
                            var.val = out
                            for va in varsorted[0]:
                                if va.indName == var.indName and va.args == var.args:
                                    va.val = out[indinfo[var.indName]["vars"].index(va.var)]
                    elif c[0] == "e": # equation
                        var = varsorted[1][find("e", c[1])]
                        args = deepcopy(var.args)
                        for a in args:
                            if "|" in str(a): # if multiple variables
                                sps = a.split("|")
                                doList = True
                                args[args.index(a)] = []
                            else: 
                                sps = [a]
                                doList = False
                            if "%" in str(a):
                                for spsps in sps:
                                    sp = spsps.split("%")
                                    if len(sp) == 2: sp.append("") # to allow full value returns
                                    if not isint(sp[1]) and sp[1] != "": # if variable in str
                                        temp = ["v", "e"]
                                        i = temp.index(sp[1][0])
                                        var2 = varsorted[i][find(sp[1][0], int(sp[1][1:]))]
                                        if sp[1][0] == "e": # get original variable and value from it
                                            if doList:
                                                args[args.index(a)].append(var2.val)
                                            else:
                                                args[args.index(a)] = var2.val 
                                        else: # also check for spot in variable
                                            multi = []
                                            if indinfo[var2.indName]["vtypes"][indinfo[var2.indName]["vars"].index(var2.var)] == list: # if list check for spot
                                                # check whether spot is variable or int
                                                if not isint(sp[2]) and sp[2] != "": # variable for spot
                                                    # can only be int variable or equation
                                                    multi = []
                                                    if "," in sp[2]: # means range with either numbers or ! for variables
                                                        ranges = sp[2].split(",")
                                                        for r in ranges:
                                                            if not isint(r): # variable for range
                                                                i = temp.index(r[0])
                                                                multi.append(varsorted[i][find(r[0], int(r[1:]))].val)
                                                                if (r[0], int(r[1:])) not in what: what.append((r[0], int(r[1:])))
                                                            else:
                                                                multi.append(int(r))
                                                        for m in range(len(multi)):
                                                            multi[m] = int(multi[m])
                                                            if multi[m] > time or multi[m] < -time-1: multi[m] = float("nan")
                                                            elif multi[m] < 0: # convert from total scale to truncated scale bc of time
                                                                multi[m] = time + multi[m] + 1
                                                        if not any(isnan(x) for x in multi): multi.sort()
                                                        multi[1] += 1 # to get correct range
                                                    else:
                                                        i = temp.index(sp[2][0]) 
                                                        spot = varsorted[i][find(sp[2][0], int(sp[2][1:]))].val
                                                        if (sp[2][0], int(sp[2][1:])) not in what: what.append((sp[2][0], int(sp[2][1:])))
                                                elif isint(sp[2]): spot = int(sp[2])
                                                if sp[2] != "":
                                                    if len(multi) == 0:
                                                        # convert spot to correct one with time | if spot incorrect make args to nan
                                                        if spot > time or spot < -time-1: spot = "nan"
                                                        elif spot < 0: # convert from total scale to truncated scale bc of time
                                                            spot = time + spot + 1
                                                        if spot != "nan": val = var2.val[spot]
                                                        else: val = float("nan")
                                                        if doList:
                                                            args[args.index(a)].append(val)
                                                        else: args[args.index(a)] = val
                                                        if (sp[1][0], int(sp[1][1:]), spot) not in what: what.append((sp[1][0], int(sp[1][1:]), spot))
                                                    else: 
                                                        if any(isnan(x) for x in multi): # if an invalid argument was given
                                                            args[args.index(a)] = []
                                                        else:
                                                            args[args.index(a)] = var2.val[multi[0]:multi[1]]
                                                        if (sp[1][0], int(sp[1][1:], (multi[0],multi[1]))) not in what: what.append((sp[1][0], int(sp[1][1:], (multi[0],multi[1]))))
                                                else:
                                                    args[args.index(a)] = var2.val # take entire thing
                                            else: # just take value
                                                args[args.index(a)] = var2.val
                                                if (sp[1][0], int(sp[1][1:])) not in what: what.append((sp[1][0], int(sp[1][1:])))

                        out = equation(var.type, args)
                        var.val = out
                    elif c[0] == "x": # expressions
                        var = varsorted[2][find("x", c[1])]
                        if var.type != "Variable": # skip variable because it has already been calculated
                            args = deepcopy(var.args)
                            for a in range(len(args)):
                                if "%" in str(args[a]):
                                    sp = args[a].split("%") # split of variable in var and spot
                                    if len(sp) == 2: sp.append("") # to allow full value returns
                                    if not isint(sp[1]) and sp[1] != "": # if variable in str
                                        temp = ["v", "e", "x"]
                                        i = temp.index(sp[1][0])
                                        var2 = varsorted[i][find(sp[1][0], int(sp[1][1:]))]
                                        if sp[1][0] != "v": args[a] = var2.val # get original variable and value from it
                                        else: # also check for spot in variable
                                            if indinfo[var2.indName]["vtypes"][indinfo[var2.indName]["vars"].index(var2.var)] == list: # if list check for spot
                                                # check whether spot is variable or int
                                                if not isint(sp[2]) and sp[2] != "": # variable for spot
                                                    # can only be int variable or equation
                                                    i = temp.index(sp[2][0]) 
                                                    spot = varsorted[i][find(sp[2][0], int(sp[2][1:]))].val
                                                    if (sp[2][0], int(sp[2][1:])) not in what: what.append((sp[2][0], int(sp[2][1:])))
                                                elif isint(sp[2]): spot = int(sp[2])
                                                if sp[2] != "":
                                                    # convert spot to correct one with time | if spot incorrect make args to nan
                                                    if spot > time or spot < -time-1: spot = "nan"
                                                    elif spot < 0: # convert from total scale to truncated scale bc of time
                                                        spot = time + spot + 1
                                                    if spot != "nan" and spot < len(var2.val): args[a] = var2.val[spot]
                                                    else: args[a] = float("nan")
                                                    if (sp[1][0], int(sp[1][1:]), spot) not in what: what.append((sp[1][0], int(sp[1][1:]), spot))
                                                else: args[a] = var2.val # just take entire thing if no value is given
                                            else: # just take value
                                                args[a] = var2.val
                                                if (sp[1][0], int(sp[1][1:])) not in what: what.append((sp[1][0], int(sp[1][1:])))
                            
                            if var.type == "Dynamic Near": args.append(getAvgBody(raw[stock], time))
                            out = expression(var.type, args)
                            var.val = out
                ands = []
                for c in cond["calc"][0]: # for every expression in top layer
                    var = varsorted[2][find("x", c[1])]
                    ands.append(var.val)
                if not False in ands and not True in ands: # if neither false nor true in ands
                    act = None
                else: act = not False in ands # will be false if a single false appears, else true

                # make label and add all of the variables to the dock widget
                lab = QtWidgets.QLabel(wid)
                lab.move(2, pos)
                if act: lab.setStyleSheet("border: none; color: #00ff00;")
                else: lab.setStyleSheet("border: none; color: #ff0000;")
                st = cond["name"] + ": " + str(act) + " ("
                for w in what:
                    temp = ["v", "e", "x", "i"]
                    var = varsorted[temp.index(w[0])][find(w[0], w[1])]
                    if w[0] != "v":
                        st += var.name + ": "
                        st += str(var.val) + ", "
                    else:
                        st += var.var + ": "
                        if len(w) == 3 and type(w[2]) == int: st += str(var.val[w[2]]) + ", "
                        elif len(w) == 2: st += str(var.val) + ", "
                        else: st += "nan, "
                st = st[:-2] + ")"
                lab.setText(st)
                pos += 20
        
        self.tempIndicator(True, candle)
        #self.setScene()

        self.docks[2].setWidget(wid)
    
    def tempIndicator(self, add, candle=None): # shows or removes temporary indicators
        dispInds = ["sma", "ema", "bollinger", "gaussian", "v", "ʌ", "w", "m", "shs", "trend", "support", "resistance", "line"] # indicators that will be displayed
        if add:
            for cond in logic.conditions:
                #cond = logic.conditions[logic.find("c", ind[0])]
                for var in cond["vars"]:
                    #if type(var) == IndicatorVariable and var.var == "" and var.id == ind[1]: break # break at correct indicator
                    if type(var) == IndicatorVariable and var.var == "" and var.indName in dispInds and var.val is not None:
                        self.tempInds.append([])
                        if var.indName in ["sma", "ema", "bollinger", "gaussian"]:
                            for obj in var.val: # in case of bollinger e.g. show all graphs
                                for i in range(len(self.candles)-1): # do same as graph
                                    c = [self.candles[i], self.candles[i+1]] # for simplification
                                    for e in range(2):
                                        c[e] = Candle(c[e][0], c[e][1])
                                        c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                    if i != len(self.candles)-1:
                                        close1 = self.toCoord("y", obj[i]) # get positions
                                        close2 = self.toCoord("y", obj[i+1])
                                    self.tempInds[-1].append(QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2))
                                    self.tempInds[-1][-1].setPen(QtGui.QColor(cond["color"]))
                                    self.view.scene().addItem(self.tempInds[-1][-1])
                        elif var.indName in ["v", "ʌ", "w", "m", "shs"]: # for shapes just draw the shape
                            points = var.val[:-1] # cut off the size
                            if var.indName == "shs": points.pop() # remove neckline
                            for p in range(len(points)-1):
                                c = [self.candles[points[p]], self.candles[points[p+1]]] # for simplification
                                for e in range(2):
                                    c[e] = Candle(c[e][0], c[e][1])
                                    c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                # if points[p] != len(self.candles)-1:
                                #     close1 = self.toCoord("y", obj[points[p]]) # get positions
                                #     close2 = self.toCoord("y", obj[points[p+1]])
                                self.tempInds[-1].append(QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, c[0].y+c[0].hei/2, c[1].x+c[1].wid/2, c[1].y+c[1].hei/2))
                                self.tempInds[-1][-1].setPen(QtGui.QColor(cond["color"]))
                                self.view.scene().addItem(self.tempInds[-1][-1])
                        elif var.indName in ["trend", "support", "resistance", "line"]: # line indicators
                            if var.indName in ["support", "resistance"]:
                                c = var.val[0]
                                m = var.val[1]
                                size = var.val[2]
                            elif var.indName == "line":
                                c = var.val[0][candle.time]
                                m = var.val[0][candle.time-1] - var.val[0][candle.time]
                                size = -100
                            if var.indName == "trend": # for only trend replace the normal trend line and show another one instead
                                m = var.val[0][candle.time]
                                m *= self.gridconv[1] # convert to coordinates
                                m *= self.gridconv[0]
                                self.view.scene().removeItem(self.tangent)
                                self.tangent = QtCore.QLineF(candle.x-self.gridconv[0]*-100, candle.y-100*m, candle.x-self.gridconv[0]*100, candle.y+100*m)
                                self.tangent = QtWidgets.QGraphicsLineItem(self.tangent)
                                self.tangent.setPen(QtGui.QColor(cond["color"]))
                                self.view.scene().addItem(self.tangent)
                            else:
                                xs = [candle.time-abs(size), candle.time]
                                if size < 0: xs[1] -= size # size < 0 just means to also extend right
                                ys = [c-m*(candle.time-xs[0]), c+m*(xs[1]-candle.time)]
                                for i in range(2): # convert to coordinates
                                    xs[i] = coordinate("x", xs[i], self.gridconv, self.rangex, self.rangey, self.heivar)
                                    ys[i] = coordinate("y", ys[i], self.gridconv, self.rangex, self.rangey, self.heivar)
                                line = QtCore.QLineF(xs[0], ys[0], xs[1], ys[1])
                                self.tempInds[-1].append(QtWidgets.QGraphicsLineItem(line))
                                self.tempInds[-1][-1].setPen(QtGui.QColor(cond["color"]))
                                self.view.scene().addItem(self.tempInds[-1][-1])
        else: # remove all indicators
            if self.tabs.tabText(self.tabs.currentIndex()) not in ["Backtest", "Exit Percentages", "Benchmark Comparison"]: # if a normal tab is displayed
                for ind in self.tempInds:
                    for obj in ind:
                        self.view.scene().removeItem(obj)
            self.tempInds = []

    def resetWindows(self): # reset docker windows to original state
        for i in range(1, len(self.docks)): # all except first
            # Conditions/Indicators
            if i == 2 and self.mode.currentText() == "Conditions/Indicators":
                do = SubDock() # sub-sub-window
                do.setWindowTitle("Indicators")
                do.setFn(lambda: self.mode.setCurrentText("Base Graph"))

                wid = QtWidgets.QWidget() # main working area
                wid.setStyleSheet(widgetstring)
                alr = [] # already drawn indicators

                l = -1

                for ind in logic.indicators: # for all of the indicators
                    if not ("i", ind["ID"]) in alr: # if button has already been made
                        l = len(alr)
                        alr.append(("i", ind["ID"]))
                        btn = IndButton(wid, ind["ID"], "inds")
                        btn.setGeometry(5+(l%25)*60, 10+(l//25)*24, 50, 20)
                        btn.setAutoFillBackground(False)
                        btn.setStyleSheet("color:%s;" % ind["color"])
                        btn.setText(ind["name"])
                        btn.setDelFn(self.deleteButton)
                        btn.setToolTip(ind["name"])
                        btn.setClickFn(self.ctrlButton)
                        btn.setRenFn(self.renameButton)
                
                for cond in logic.conditions: 
                    if not ("c", cond["ID"]) in alr and len(cond["deps"]) == 0: # if button hasn't already been made or condition is complex
                        l = len(alr)
                        alr.append(("c", cond["ID"]))
                        btn = IndButton(wid, cond["ID"])
                        btn.typ = "conds"
                        btn.setGeometry(5+(l%25)*60, 10+(l//25)*24, 50, 20)
                        btn.setAutoFillBackground(False)
                        btn.setStyleSheet("color:%s;" % cond["color"])
                        btn.setText(cond["name"])
                        btn.setDelFn(self.deleteButton)
                        btn.setToolTip(cond["name"])
                        btn.setClickFn(self.ctrlButton)
                        btn.setRenFn(self.renameButton)

                l += 1

                btn = QtWidgets.QPushButton(wid)
                btn.setGeometry(5+(l%25)*60, 12+(l//25)*24, 15, 16) # + Button
                btn.setText("+")
                menu = QtWidgets.QMenu(self)
                act = menu.addAction("Indicator...")
                act.triggered.connect(self.indicatorDialog)
                act = menu.addAction("Condition...")
                act.triggered.connect(self.conditionCreator)
                btn.clicked.connect(lambda: menu.exec(btn.mapToGlobal(btn.rect().bottomLeft())))
                #btn.clicked.connect(self.conditionDialog)
                do.setWidget(wid)

                lay = QtWidgets.QVBoxLayout() # layout
                lay.addWidget(do)
                lay.setSpacing(0)
                lay.setContentsMargins(0, 0, 0, 0)
                w2 = QtWidgets.QWidget() # Only for layout
                w2.setLayout(lay)
                self.docks[2].setWidget(w2)
                break # break because we don't want to run other code

            elif i == 2 and self.mode.currentText() == "Strategies":
                do = SubDock() # sub-sub-window
                do.setWindowTitle("Strategies")
                do.setFn(lambda: self.mode.setCurrentText("Base Graph"))

                wid = QtWidgets.QWidget() # main working area
                wid.setStyleSheet(widgetstring)
                alr = [] # already added strategies

                l = -1

                for strat in logic.strategies: 
                    if not strat["ID"] in alr: # if button has already been made
                        l = len(alr)
                        alr.append(("s", strat["ID"]))
                        btn = IndButton(wid, strat["ID"], "strats")
                        btn.setGeometry(5+(l%25)*60, 10+(l//25)*24, 50, 20)
                        btn.setAutoFillBackground(False)
                        # btn.doPass = False # dont pass event to strategy dialog
                        # btn.setStyleSheet("color:%s;" % strat["color"])
                        btn.setText(strat["name"])
                        btn.setDelFn(self.deleteButton)
                        btn.setToolTip(strat["name"])
                        btn.setClickFn(self.ctrlButton)
                        btn.setRenFn(self.renameButton)
                        btn.setDebugFn(self.debugButton)
                        btn.setRunFn(self.calcStrategy)

                l += 1

                btn = QtWidgets.QPushButton(wid)
                btn.setGeometry(5+(l%25)*60, 12+(l//25)*24, 15, 16) # + Button
                btn.setText("+")
                btn.clicked.connect(self.strategyDialog)
                do.setWidget(wid)

                lay = QtWidgets.QVBoxLayout() # layout
                lay.addWidget(do)
                lay.setSpacing(0)
                lay.setContentsMargins(0, 0, 0, 0)
                w2 = QtWidgets.QWidget() # Only for layout
                w2.setLayout(lay)
                self.docks[2].setWidget(w2)
                break
            
            wid = QtWidgets.QWidget()
            wid.setStyleSheet(widgetstring)
            if i == 2: # conditions window
                lab = QtWidgets.QLabel(wid)
                lab.setStyleSheet("border: none;")
                if self.chartchecks[1].isChecked(): # if not candlestick view
                    lab.setText("Condition Check unavailable; Switch to Candlestick for Condition Check.")
                else:
                    lab.setText("Click on a Candle to see more info!")
                lab.move(2, 2)
            if i == 1 and self.sideStats.new: # if new stats were entered; dont reset window
                self.sideStats.new = False
            else: self.docks[i].setWidget(wid)

    def displaySelected(self): # change generals 1 to display selected spots for condition seeker
        wid = QtWidgets.QWidget()
        lab = QtWidgets.QLabel("Number of selected spots: " + str(len(self.spots)), wid)
        lab.move(2, 2)
        lab.setStyleSheet("border: none;")
        btn = QtWidgets.QPushButton("Seek for valid conditons", wid)
        btn.move(2, 30)
        btn.setStyleSheet(widgetstring)
        btn.clicked.connect(self.seekConditions)
        self.generals[1].setWidget(wid)

    def switchStats(self): # switch and display stats
        procManager.switch()
        self.displayStats()

    def displayStats(self): # change left window to show stats
        cur = procManager.current()
        if cur is not None:
            # things all have in common
            wid = QtWidgets.QWidget()
            wid.setStyleSheet(widgetstring)
            wid.setStyleSheet("border: none;")
            line = QtWidgets.QFrame(wid) # seperator line
            line.setGeometry(0, 1, 196, 3)
            line.setStyleSheet(widgetstring)
            btn = QtWidgets.QPushButton("Switch", wid)
            btn.move(125, 7)
            btn.setStyleSheet(widgetstring)
            btn.clicked.connect(self.switchStats)
            btn = QtWidgets.QPushButton("r", wid) # will display an x
            btn.setFont(QtGui.QFont("Marlett"))
            btn.setStyleSheet("background-color: #aa0000; color: #ffffff; border: 2px inset #a0a0a0;")
            btn.setGeometry(174, 7, 20, 20)
            btn.clicked.connect(self.sideRemove)
            if cur == "backthreads": # if backtests are calculated
                self.progs = [[]]
                self.progs[0].append(QtWidgets.QLabel("Success Rate: " + str(round(logic.stats.succ/logic.stats.processed, 3)), wid))
                self.progs[0][0].move(2, 28)
                self.progs[0][0].setStyleSheet("border: none;")
                if logic.stats.sf[1] == 0: sf = float("nan")
                else: sf = logic.stats.sf[0]/abs(logic.stats.sf[1])
                self.progs[0].append(QtWidgets.QLabel("Succ./Fail.: " + str(round(sf, 3)), wid))
                self.progs[0][1].move(105, 28)
                self.progs[0][1].setStyleSheet("border: none;")
                lab = QtWidgets.QLabel("Progress", wid)
                lab.move(2, 128)
                lab.setStyleSheet("border: none;")
                self.progs.append(QtWidgets.QProgressBar(wid))
                self.progs[1].setValue(int(logic.stats.progress))
                self.progs[1].setGeometry(2, 153, 192, 22)
                self.progs[1].setStyleSheet(widgetstring)
                if not self.debugvar[0]: # for backthreads
                    self.progs.append(StatGraph(wid))
                    self.progs[2].setGeometry(2, 68, 192, 60)
                    self.progs[2].setStyleSheet(widgetstring)
                    self.progs[2].newScene()
                    self.progs.append(QtWidgets.QComboBox(wid))
                    self.progs[3].setGeometry(2, 47, 50, 19)
                    self.progs[3].setStyleSheet(widgetstring + "background-color: #888888;")
                    self.progs[3].addItems(["Price"])
                btn = QtWidgets.QPushButton("Stop", wid)
                btn.move(2, 178)
                btn.clicked.connect(lambda: self.stopButton("backthreads"))
                btn.setStyleSheet(widgetstring)
                if self.debugvar[0]: # for debug
                    btn = QtWidgets.QPushButton("Next", wid)
                    btn.move(165, 178)
                    btn.setStyleSheet(widgetstring)
                    btn.clicked.connect(self.debugNext)
            elif cur == "condseeker":
                self.progs = []
                lab = QtWidgets.QLabel("Progress", wid)
                lab.move(2, 128)
                lab.setStyleSheet("border: none;")
                self.progs.append(QtWidgets.QProgressBar(wid))
                self.progs[0].setValue(100)#int(logic.stats.progress))
                self.progs[0].setGeometry(2, 153, 195, 22)
                self.progs[0].setStyleSheet(widgetstring)
            self.generals[2].setWidget(wid)
        else: self.generals[2].setWidget(QtWidgets.QWidget())

    def resetGeneral(self, indx):
        self.generals[indx].setWidget(QtWidgets.QWidget())
    
    def multiShow(self): # set generals[1] to display muiti mark
        wid = QtWidgets.QWidget()
        # display all fo the selected conditions
        lab = QtWidgets.QLabel("Selected Conditions", wid)
        lab.move(2, 2)
        lab.setStyleSheet("border: none;")
        i = 0
        for s in self.selected:
            ind = logic.find("c", s)
            btn = IndButton(wid, s) 
            btn.setAutoFillBackground(False)
            btn.setStyleSheet(widgetstring + "color:%s;" % logic.conditions[ind]["color"])
            btn.setText(logic.conditions[ind]["name"])
            btn.setGeometry(2+50*(i%3), 22*(1+i//3), 50, 20)
            btn.setClickFn(self.selectButton)
            btn.doDel = False
            i += 1
        btn = QtWidgets.QPushButton("To Strategy", wid)
        btn.move(2, 150)
        btn.setStyleSheet(widgetstring)
        btn.clicked.connect(self.strategyDialog)
        self.generals[1].setWidget(wid)
        # side display
        wid1 = QtWidgets.QWidget()
        wid1.setStyleSheet(widgetstring)
        self.sideStats.reset()
        self.sideStats.strings.append("No. Marked by all: " + str(self.marked.count("#8000ffff")))
        self.sideStats.display(wid1)
        self.docks[1].setWidget(wid1)

    def updateStats(self, ec=0): # update stats periodically until backthreads stop
        # if queue updated
        if not self.queue.empty():
            ec = 0
            acc = self.queue.get() # tuple (stats, ind)
            logic.stats = deepcopy(acc[0][0])
            if not logic.stats.finished:
                pass # get other variables and store them
            if procManager.current() == "backthreads": # if backthreads are currently shown
                if logic.stats.processed != 0: self.progs[0][0].setText("Success Rate: " + str(round(logic.stats.succ/logic.stats.processed, 3)))
                if logic.stats.sf[1] == 0: sf = float("nan")
                else: sf = logic.stats.sf[0]/abs(logic.stats.sf[1])
                self.progs[0][1].setText("Succ./Fail.: " + str(round(sf, 3)))
                self.progs[1].setValue(int(logic.stats.progress))
                key = self.progs[3].currentText().lower()
                if key != self.progs[2].current: # if different category selected
                    self.progs[2].dots = []
                    rangex = [100000, -100000]
                    for d in logic.stats.details: # get dots and new range
                        self.progs[2].dots.append([d[key], d["success"]])
                        if d[key] < rangex[0]: rangex[0] = d[key]
                        if d[key] > rangex[1]: rangex[1] = d[key]
                    if rangex[0] == rangex[1]: rangex[1] += 1
                    #print(rangex)
                    tot = rangex[1]-rangex[0]
                    nearest = 1/10000
                    while True: # get nearest fitting size
                        if str(nearest*10000)[0] == 1:
                            nearest *= 2.5
                        else: nearest *= 4
                        if nearest > tot: break
                    if str(nearest*10000)[0] == 1: nearest /= 10
                    else: nearest /= 5
                    rangex[0] = int(rangex[0]-rangex[0]%nearest) # get to nearest clean number
                    rangex[1] = int(rangex[1]+nearest-rangex[1]%nearest)
                    self.progs[2].rangex = rangex
                else: self.progs[2].dots.append([logic.stats.details[-1][key], logic.stats.details[-1]["success"]])
                self.progs[2].makeScene(key)
        elif ec == 2000 or self.stopbackgs: return # if ten seconds of nothing happen; cancel function
        else: ec += 1

        # queue another update in 5ms
        QtCore.QTimer.singleShot(5, lambda:self.updateStats(ec))

    def readstocks(self, which: str, what: str, how: str=""): # read in a stock and pass it to the candles
        global raw
        self.timeaxis = [] # reset date axis
        name = ""
        toload = ""
        ticker = ""
        if what == "quick" or what == "debug":
            if which.isdigit(): 
                if int(which) > len(stocks):
                    self.errormsg("The index of the ID is out of range.")
                    return
                else: toload = stocks[int(which)] # if an id was passed in
            else: 
                if which.upper() in stocks: toload = which.upper() # if a ticker was passed in
                else:
                    self.errormsg(which + " ticker is not in the dataset.")
                    return
            if how == "+":
                raw.append(read(toload))
            else: raw[logic.rawind] = read(toload)
            ticker = toload
            name = toload
            if what == "debug": name = "Debug " + name
        else:
            readtest = read(which, True)
            if len(readtest) == 0:
                self.errormsg(which.split("/")[-1] + " is not a valid file.")
                return
            if how == "+":
                raw.append(readtest)
            else: raw[logic.rawind] = readtest
            name = which.split("/")[-1]
        self.newScene(how, name, ticker)

    def reinitIndicators(self): # regather data for the indicators after e.g. the scene switched
        self.marked = [] # unmark all
        for ind in logic.indicators: # indicators
            t = len(raw[logic.rawind])-1
            out = indicator(logic.rawind, ind["indName"], ind["args"], t)
            if isinstance(out, tuple): # if multiple values were given
                temp = []
                for o in out:
                    temp.append(o)
                out = temp
            else: out = [out]
            ind["data"] = out
        for con in logic.conditions:
            if len(con["deps"]) != 0: # complex condition
                con["data"] = [] # unload data
            else:
                if len(con["data"]) != 0: # if condition has been loaded
                    con["data"] = [] # empty data
                    logic.getData(logic.find("c", con["ID"])) # get new data for condition

    def newScene(self, how="", tabName="", ticker=""): # reset scene and generate new scene using raw data
        self.loading = True # turn off scrolling while its loading
        self.candles = [] # empty candles
        if how == "+": logic.rawind = len(raw)-1 # uses last raw to do calculations
        self.rangex = (0, len(raw[logic.rawind]))
        self.marked = [] # reset marked spots
        if len(self.selected) != 0: # if something has been selected
            self.selected = []
            self.resetGeneral(1)
        elif len(self.spots) != 0:
            self.spots = []
            self.resetGeneral(1)
        self.reinitIndicators()
        for c in logic.conditions: # unload all conditions so they'll have to be calculated again
            c["data"] = []
        mi = 10000 # minimum value
        ma = 0 # maximum value
        avg = 0 # avg body size
        cans = [] # candle data for smaller system
        for t in range(len(raw[logic.rawind])): # get candles
            if raw[logic.rawind][t][1] > ma: ma = raw[logic.rawind][t][1]
            if raw[logic.rawind][t][2] < mi: mi = raw[logic.rawind][t][2]
            avg += abs(raw[logic.rawind][t][3] - raw[logic.rawind][t][0])
            l = [t] # [time, [o, h, l, c]]
            l.append([raw[logic.rawind][t][0], raw[logic.rawind][t][1], raw[logic.rawind][t][2], raw[logic.rawind][t][3]])
            cans.append([raw[logic.rawind][t][0], raw[logic.rawind][t][1], raw[logic.rawind][t][2], raw[logic.rawind][t][3], raw[logic.rawind][t][4]])
            self.candles.append(l)
        self.sview.candles = cans
        avg /= len(raw[logic.rawind])
        tenpows = [0.0005]
        while tenpows[-1] < avg: # fill up the list
            if str(1000/tenpows[-1])[0] == "4": # multiple of 2.5
                tenpows.append(tenpows[-1]*2)
            else: tenpows.append(tenpows[-1]*5)
        contenders = [abs(avg/tenpows[-2]-1), abs(avg/tenpows[-1]-1)]
        if contenders[0] < contenders[1]: tenpow = tenpows[-2]
        else: tenpow = tenpows[-1]
        tenpow *= 2 # because it looked for square size 
        self.rangey = (mi-mi%tenpow, ma+(tenpow-ma%tenpow)) # fill until next square
        self.gridconv = [40, 5, 40, tenpow]
        syst = System()
        syst.gridconv = deepcopy(self.gridconv)
        syst.rangex = deepcopy(self.rangex)
        syst.rangey = deepcopy(self.rangey)
        syst.candles = deepcopy(self.candles)
        syst.rawind = logic.rawind
        syst.timeaxis = deepcopy(self.timeaxis)
        if ticker.count(",") == 0: syst.live = [ticker] # no other data; take just the ticker
        else:
            sp = ticker.split(",")
            syst.live = sp
        if how == "+": 
            logic.systems.append(syst) # if a new tab is created
            self.resetBacktest()
            self.newTab(tabName)
        else: 
            logic.systems[self.tabs.currentIndex()] = syst # replace
            self.tabs.setTabText(self.tabs.currentIndex(), tabName)

        self.setScene()
    
    def closeEvent(self, event): # stop all threads when closing
        self.stopButton()
        event.accept()

app = QtWidgets.QApplication(sys.argv)

app.setStyle(QtWidgets.QStyleFactory.create(look))

if theme == "dark":
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(25, 25, 25))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(255, 0, 25))
    palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(0, 0, 0))
    app.setPalette(palette)

if __name__ == "__main__":

    window = GUI()

    window.show()

    #sys.exit(app.exec())
    app.exec()
