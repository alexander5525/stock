# Stock Sim Version 0.9
# Author: alexander5525
# Finished: 6/21/2023
# Description: Simple stock strategy analyzer that can test a simple strategy on one stock at a time and provide backtest data on all stocks in the read folder
# Note: Please provide proper attribution if reusing any part of this code.
import pathlib
from math import isnan, ceil, exp, sqrt, atan, pi, floor
import typing
from PyQt6.QtCore import QObject
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

def playsound(which="Error"): # For the error sound
    if which == "Error": winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
    elif which == "Asterisk": winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
    elif which == "Exclamation": winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)

# based on sim version = "1.2.1" 
version = "0.9"

theme = "dark"
look = "Windows"


if theme == "light": # for light theme
    dockstring = "QDockWidget::title { background-color: #A0A0A0; border: 2px solid #BEBEBE;}"
    widgetstring = "background-color: #ffffff; border: 2px inset #A0A0A0;"
else: # for dark theme
    dockstring = "QDockWidget::title { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0A246A, stop:1 #A6CAF0); border: 2px solid #BEBEBE;}"
    widgetstring = "background-color: #191919; border: 2px inset #A0A0A0;"

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

file_path = os.path.join(root_dir, "read", "Usable.xlsx")
stocklist = pd.read_excel(file_path)["Symbols"] # read only the ticker symbols
del file_path

stocks = stocklist.sort_values().reset_index(drop=True) # sort the stocks alphabetically so ai doesn't only train on good ones
# stock_evals = pd.Series([stocks.pop(i*20) for i in range(stocks.size//20)], name="Symbols") # take out 5% / 1/20 of the dataset to evaluate the ai on (// means floor division)
stocks = stocks.to_list()
# stock_evals = stock_evals.to_list()
del stocklist

raw = [] # raw y2h stock data
operations = [] # stores the active operations
usedstocks = [] # predefinition
minmu = 0 # minimum mu value to count as success
quickmu = [] # stores mu values to calculate r

# vars for random cells
avconds = ["up", "down", "movavg", "expavg", "35up", "35down", "engulfup", "engulfdown", "closeabove", "closebelow", "contested", "bollingerabove", "bollingerbelow",
"bollingerwidth", "volume", "peak", "valley", "lasttrendup", "lasttrenddown", "v", "ʌ", "m", "w", "shs", "resistouch", "supportouch", "vwap",
"ha-up", "ha-down", "ha-shadowup", "ha-shadowdown", "ha-doji", "macd-momentum", "macd-market", "rsi"]
precalc = {"movavg":[], "expavg":[], "contested":[], "bollinger":[], "vwap":[], "heikin-ashi":[], "macd":[]} # precalculated values for conditions 

# what arguments are displayed in add/change condition dialog | [(key, Display as, default)] e.g. ("ma", "Window", 200)
bol = ("ma", "Moving Avg.", 20), ("k", "σ-Multiplier", 2)
neededArgs = {"up": [], "down":[], "movavg":[("ma", "Window", 200)], "expavg":[("ma", "Window", 200)], "35up":[("ma", "Body Size", 0.382)], "35down":[("ma", "Body Size", 0.382)],
"engulfup":[], "engulfdown":[], "closeabove":[], "closebelow":[], "contested":[], "bollingerabove":[bol[0], bol[1]], 
"bollingerbelow":[bol[0], bol[1]], "bollingerwidth":[bol[0], bol[1], ("width", "Width", 10)], "volume":[], "peak":[], "valley":[], "lasttrendup":[("ma", "Last x times", 20)],
"lasttrenddown":[("ma", "Last x times", 20)], "v":[("ma", "Minimum", 5), ("k", "Maximum", 100)], "ʌ":[("ma", "Minimum", 5), ("k", "Maximum", 100)],
"m":[("ma", "Minimum", 5), ("k", "Maximum", 100)], "w":[("ma", "Minimum", 5), ("k", "Maximum", 100)], "shs":[("ma", "Minimum", 5), ("k", "Maximum", 100)],
"cup":[("ma", "Minimum", 5), ("k", "Maximum", 100)], "inrange":[("ma", "Minimum", 5), ("k", "Maximum", 100)], "resistouch":[], "supportouch":[], "vwap":[("ma", "Window", 60)],
"ha-up":[], "ha-down":[], "ha-shadowup":[], "ha-shadowdown":[], "ha-doji":[], "macd-momentum":[], "macd-market":[], "rsi":[("ma", "Period", 14), ("k", "Percentage", 50)]}
# ranges and data types for inputs | nan means unlimited / len(stock)
bol = ("ma", int, 0, "nan"), ("k", int, 1, 99)
argRanges = {"movavg":[("ma", int, 0, "nan")], "expavg":[("ma", int, 0, "nan")], "35up":[("ma", float, 0, 1)], "35down":[("ma", float, 0, 1)], 
"bollingerabove":[bol[0], bol[1]], "bollingerbelow":[bol[0], bol[1]], "bollingerwidth":[bol[0], bol[1], ("width", int, 0, 999)], "lasttrendup":[("ma", int, 2, "nan")],
"lasttrenddown":[("ma", int, 2, "nan")], "v":[("ma", int, 5, "nan"), ("k", int, 5, "nan")], "ʌ":[("ma", int, 5, "nan"), ("k", int, 5, "nan")],
"m":[("ma", int, 5, "nan"), ("k", int, 5, "nan")], "w":[("ma", int, 5, "nan"), ("k", int, 5, "nan")], "shs":[("ma", int, 5, "nan"), ("k", int, 5, "nan")],
"cup":[("ma", int, 5, "nan"), ("k", int, 5, "nan")], "inrange":[("ma", int, 5, "nan"), ("k", int, 5, "nan")], "vwap":[("ma", int, 0, "nan")], 
"rsi":[("ma", int, 2, "nan"), ("k", int, 0, 100)]}
del bol

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
        if (n <= i/(high-low)): return i - 1 + low # if max = 4 and min = 0: if 0.2143124 < 1/4: return 0
    return high - 1

def split(lis, indx): # split list into two at given index
    if len(lis) == 0: return ([], [])
    elif len(lis) == 1 and indx == 0: return([], []) 
    elif indx == len(lis)-1: return (lis[:-1], [])
    elif indx == 0: return ([], lis[1:])

    a = lis[indx + 1:]
    b = lis[:indx]
    return (a, b)

def stock_data(ticker, start, end, interval): # get stock data and convert it to a list
    try:
        tik = yf.Ticker(ticker)
        tim = tik._get_ticker_tz(None, 10)
        if tim == None:
            raise Exception("Delisted")
        dat = tik.history(start=start, end=end, interval=interval)
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
        if self.type == "stoplimit":
            return raw[self.ind][time][3]*self.amnt 
        else:
            return self.stopprice*self.amnt # trailing stop

def near(a, b, n): # rounds a and b to n digits and checks if they're the same
    return round(a, n) == round(b, n) # if a rounded = b rounded then they're really close

def get_cont_extrs(stock, split=False): # gets extremes of a graph to calculate contested areas
    # l is list of 100 point trends 
    l = [0] # start with 0, because first is skipped
    for i in range(1, len(stock)-1):
        start = i - 100 # so it wont wrap around
        if start <= 0: 
            start = 0
            x = list(range(i+1))
            y = stock[start:i+1]
        else: 
            x = list(range(100))
            y = stock[start+1:i+1] # get last 100 price points
        y.reverse() # so that the tangent will fixate on last price point
        coeffs = polyfit(x, y, 1)
        l.append(coeffs[0][3])
    
    switches = [0] # when the trend switches
    if len(l) > 1:
        firstTrendUp = l[1] < 0 # check for under 0 for up because y is reversed
    else: firstTrendUp = True # if list too short assume uptrend
    currentTrend = firstTrendUp
    i = 0
    for t in l:
        trend = t < 0 # true if up; false if down
        if currentTrend ^ trend: # xor to check whether they're different
            currentTrend = not currentTrend
            switches.append(i) # save when the trend switched
        i += 1
    
    rems = []

    # remove small trends and merge them with the surrounding ones
    for s in range(len(switches)-1): # all except last one
        span = switches[s+1] - switches[s] # get size of trend span
        if span <= 10: # if span too small
            if switches[s] not in rems: rems.append(switches[s]) # remove switches
            if switches[s+1] not in rems: rems.append(switches[s+1])
    
    for r in rems:
        switches.remove(r)

    # now get peaks and valleys in trend ranges
    extremes = []
    peaks = []
    valleys = []
    currentTrend = firstTrendUp
    for s in range(len(switches)-1):
        current = switches[s]
        for t in range(switches[s], switches[s+1]):
            if currentTrend and stock[t][3] > stock[current][3]: # if uptrend and spot is above current highest
                current = t
            elif not currentTrend and stock[t][3] < stock[current][3]: # if downtrend and below lowest
                current = t
        if currentTrend: peaks.append(current) # append to peaks
        else: valleys.append(current) # append to valleys
        extremes.append(current)
        currentTrend = not currentTrend # flip because next trend will be opposite
    
    if split: return peaks, valleys # gives split outputs
    return extremes

def exp_values(n): # get exponent weights in list
    exps = []
    for i in range(n):
        val = exp(-(4/pow(n, 2))*pow(i+1-(n/4), 2))
        exps.append(val)
    return exps

def mean_rise(stock, spot): # get mean exponential rise from spot
    mu = 0
    if len(stock)-1 >= spot + 16: # make sure there are at least 16 more samples
        weights = exp_values(16)
        for s in range(16):
            perc = (stock[spot+s][3]/stock[spot][3]-1)*100 # get percentage
            mu += perc*weights[s] # add weighted values
        mu /= 16 # get mean
    return mu

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

def replaceOp(statement: str, operator: str): # make customizable eval statements
    if operator == "": return statement # return given statement when no operator is present
    ops = ["<=", ">=", ">", "<", "==", "near"]
    if operator == "=" : operator = "=="
    elif operator == "≈": operator = "near"

    for o in ops: # turn statement into ["a", "b"]
        if o in statement:
            if o == "near":
                statement = statement.split("near")[1] # cut off near so it looks like "(a, b, n)""
                statement = statement[1:-1] # cut off parenthesis | "a, b, n"
                statement = statement.split(",") # ["a", "b", "n"]
                statement = statement[:-1] # ["a", "b"]
            statement = statement.split(o) # cut out the operator used
            break
    
    if operator == "near":
        statement[0] = "near(" + statement[0] + "," # ["near(a,", "b"]
        statement.append(", 2)") # ["near(a,", "b", ", 2)"]
        return statement[0] + statement[1] + statement[2]
    else:
        return statement[0] + operator + statement[1] # return new valid statement

def condition(index, shape, spot, ma=200, k=2, width=10, operator="", doReturn=False, time=-1):
    # 0 open | 1 high | 2 low | 3 close | 4 volume
    # doReturn is for displaying indicators
    stock = raw[index] # makes it simpler
    if time == -1:
        time = len(stock)-1
    if shape == "up" or shape == "green": # close > open
        if doReturn: # return list of all ups
            statement = replaceOp("stock[i][3] > stock[i][0]", operator)
            l = []
            for i in range(spot):
                l.append(eval(statement))
            return l

        statement = replaceOp("stock[spot][3] > stock[spot][0]", operator)
        return eval(statement)
    elif shape == "down" or shape == "red": # close < open
        if doReturn: # return list of all downs
            statement = replaceOp("stock[i][3] < stock[i][0]", operator)
            l = []
            for i in range(spot):
                l.append(eval(statement))
            return l
        
        statement = replaceOp("stock[spot][3] < stock[spot][0]", operator)
        return eval(statement)
    elif shape == "35up": # Fibonacci candle up # buying pressure
        statement = replaceOp("body > fibonacci", operator)
        if doReturn: # return list of all 35ups
            l = []
            for i in range(spot):
                high = stock[i][1]
                low = stock[i][2]
                if stock[i][3] > stock[i][0]: body = stock[i][0]
                else: body = stock[i][3]
                fibonacci = high - (high - low) * ma
                l.append(eval(statement))
            return l
        
        high = stock[spot][1]
        low = stock[spot][2]
        if stock[spot][3] > stock[spot][0]: body = stock[spot][0]
        else: body = stock[spot][3]
        fibonacci = high - (high - low) * ma
        return eval(statement)
    elif shape == "35down": # Fibonacci candle down # selling pressure
        statement = replaceOp("body < fibonacci", operator)
        if doReturn: # return list of all 35downs
            l = []
            for i in range(spot):
                high = stock[i][1]
                low = stock[i][2]
                if stock[i][3] > stock[i][0]: body = stock[i][3]
                else: body = stock[i][0]
                fibonacci = low + (high - low) * ma
                l.append(eval(statement))
            return l
        
        high = stock[spot][1]
        low = stock[spot][2]
        if stock[spot][3] > stock[spot][0]: body = stock[spot][3]
        else: body = stock[spot][0]
        fibonacci = low + (high - low) * ma
        return eval(statement)
    elif shape == "engulfup": # candle engulfs last and color change # buying pressure
        if doReturn: # return list of all engulfups
            statement = replaceOp("stock[i][3] > stock[i-1][0]", operator)
            l = []
            for i in range(spot):
                c1 = not (stock[i][0] > stock[i][3] or stock[i-1][3] > stock[i-1][0])
                c2 = near(stock[i][0], stock[i-1][3], 1)
                c3 = eval(statement)
                l.append(c1 and c2 and c3) # all have to be true
            return l
        
        statement = replaceOp("stock[spot][3] > stock[spot-1][0]", operator)
        if stock[spot][0] > stock[spot][3] or stock[spot-1][3] > stock[spot-1][0]: # if opennow > closenow or closelast > openlast: end
            return False
        if not near(stock[spot][0], stock[spot-1][3], 1): # if not open ~~ last close: end
            return False
        return eval(statement) # close > last open
    elif shape == "engulfdown": # candle engulfs last and color change # selling pressure
        if doReturn: # return list of all engulfdowns
            statement = replaceOp("stock[i][3] < stock[i-1][0]", operator)
            l = []
            for i in range(spot):
                c1 = not (stock[i][3] > stock[i][0] or stock[i-1][0] > stock[i-1][3])
                c2 = near(stock[i][3], stock[i-1][0], 1)
                c3 = eval(statement)
                l.append(c1 and c2 and c3) # all have to be true
            return l
        
        statement = replaceOp("stock[spot][3] < stock[spot-1][0]", operator)
        if stock[spot][3] > stock[spot][0] or stock[spot-1][0] > stock[spot-1][3]: # if closenow > opennow or openlast > closelast: end
            return False
        if not near(stock[spot][3], stock[spot-1][0], 1): # if not close ~~ last open: end
            return False
        return eval(statement) # close < last open
    elif shape == "closeabove": # close is above last high # buying pressure
        if doReturn:
            statement = replaceOp("stock[i][3] > stock[i-1][1]", operator)
            l = []
            for i in range(spot):
                l.append(eval(statement))
            return l
        
        statement = replaceOp("stock[spot][3] > stock[spot-1][1]", operator)
        return eval(statement) # close > last high
    elif shape == "closebelow": # close is below last low # selling pressure
        if doReturn:
            statement = replaceOp("stock[i][3] < stock[i-1][2]", operator)
            l = []
            for i in range(spot):
                l.append(eval(statement))
            return l
        
        statement = replaceOp("stock[spot][3] < stock[spot-1][2]", operator)
        return eval(statement) # close > last low
    elif shape == "movavg": # will always look for bigger so true means avg > close
        if spot <= ma: return False
        if len(precalc["movavg"]) != 0: # if data was precalculated
            slope = precalc["movavg"][spot]
        else:
            temp = pd.DataFrame(stock)
            precalc["movavg"] = temp.rolling(window=ma).mean()[3].reset_index(drop=True).to_list() # precalc entire ma
            slope = precalc["movavg"][spot]
        if doReturn: 
            temp = pd.DataFrame(stock[:spot])
            return temp.rolling(window=ma).mean()[3].reset_index(drop=True).to_list() # return entire moving average if wanted

        statement = replaceOp("slope > stock[spot][3]", operator)
        return eval(statement)
    elif shape == "expavg":
        if spot <= ma: return False
        if len(precalc["expavg"]) != 0: # if precalculated
            slope = precalc["expavg"][spot]
        else:
            temp = pd.DataFrame(stock)
            precalc["expavg"] = temp.ewm(span=ma, adjust=False).mean()[3].reset_index(drop=True).to_list()
            slope = precalc["expavg"][spot]
        if doReturn: 
            temp = pd.DataFrame(stock[:spot])
            return temp.ewm(span=ma, adjust=False).mean()[3].reset_index(drop=True).to_list() # return entire exponential average if wanted

        statement = replaceOp("slope > stock[spot][3]", operator)
        return eval(statement)
    elif shape == "contested": # if many peaks were in same area # market change
        if doReturn:
            end = spot-101 # so it wont wrap around
            if end <= 0: extremes = []
            else: 
                extremes = get_cont_extrs(stock[:spot], True) # return peaks and valleys split
                extremes = [extremes[0], extremes[1]] # convert tuple to list
            return extremes
        
        if len(precalc["contested"]) == 0:
            precalc["contested"] = get_cont_extrs(stock)

        extremes = precalc["contested"] # if precalculated
        for e in extremes:
            if e > spot: 
                exind = extremes.index(e)
                if exind < 0: # if no extremes until point; give empty list
                    extremes = []
                else:
                    extremes = extremes[:exind] # only get until last extreme
                break
        nbox = []
        contestability = 3 # if contestability values are in nbox then its contested
        for n in range(3): # 1 up 1 down + same
            nbox.append(round(stock[spot][3]-1+n, 0))
        c = 0
        for e in extremes:
            if round(stock[e][3]) in nbox:
                c += 1
        
        statement = replaceOp("c >= contestability", operator)
        return eval(statement) # if 5 or more peaks/lows are in current area
    elif shape == "bollinger": # placeholder for new condition comments
        # risk ranking through this + price envelopes (looser)
        # bollingerabove (price above upper bollinger)
        # bollingerbelow (price below lower bollinger)
        # bollingerwidth (if width of band below certain percentage)
        # trendline (if price touches trendline)
        # peak (if tallest at spot)
        # valley (if lowest at spot)
        # line (if stock follows line)
        # trends (tangents) 
        # triangle trend lines
        # resistance line -> breakout up
        # support line -> breakout down
        # in range (between support and resistance)
        # shs formation
        # m w lines
        # leverage banking
        return False
    elif shape == "bollingerabove": # price above upper bollinger band
        if doReturn:
            temp = bollinger(stock[:spot], ma, k)
            return [temp[0], temp[1], temp[2]] # lower, middle, upper
        if spot < ma*2: return False # if no standard deviation can be calculated
        if len(precalc["bollinger"]) != 0:
            slope = precalc["bollinger"][2][spot] # upper band at spot
            statement = replaceOp("stock[spot][3] >= slope", operator)
            return eval(statement) 
        else:
            # precalc
            temp = bollinger(stock, ma, k)
            precalc["bollinger"] =  [temp[0], temp[1], temp[2]]
            temp = pd.DataFrame(stock[spot-ma*2:spot]) # get twice the ma because movavg is needed for ma values
            slope = temp.rolling(window=ma).mean()[3] # get moving averages
            sigma = 0 # gets how far the average is off from the current values | standard deviation
            for i in range(ma):
                sigma += pow(stock[spot-ma+i][3]-slope[ma+i], 2) # (cls-mov)^2 -> (cls-mov)^2/n = var
            sigma = sqrt(sigma/ma) # sqrt(var)
            statement = replaceOp("stock[spot][3] >= slope[ma*2-1] + k*sigma", operator)
            return eval(statement) # close >= movavg + k * sigma (k = 2)
    elif shape == "bollingerbelow": # price below lower bollinger band
        if doReturn:
            temp = bollinger(stock[:spot], ma, k)
            return [temp[0], temp[1], temp[2]]
        if spot < ma*2: return False # if no standard deviation can be calculated
        if len(precalc["bollinger"]) != 0:
            slope = precalc["bollinger"][0][spot] # lower band at spot
            statement = replaceOp("stock[spot][3] <= slope", operator)
            return eval(statement) 
        else:
            # precalc
            temp = bollinger(stock, ma, k)
            precalc["bollinger"] =  [temp[0], temp[1], temp[2]]
            temp = pd.DataFrame(stock[spot-ma*2:spot]) # get twice the ma because movavg is needed for ma values
            slope = temp.rolling(window=ma).mean()[3] # get moving averages
            sigma = 0 # gets how far the average is off from the current values | standard deviation
            for i in range(ma):
                sigma += pow(stock[spot-ma+i][3]-slope[ma+i], 2) # (cls-mov)^2 -> (cls-mov)^2/n = var
            sigma = sqrt(sigma/ma) # sqrt(var)
            statement = replaceOp("stock[spot][3] <= slope[ma*2-1] - k*sigma", operator)
            return eval(statement) # close <= movavg + k * sigma (k = 2)
    elif shape == "bollingerwidth": # width of band below width variable
        if doReturn:
            temp = bollinger(stock[:spot], ma, k)
            return [temp[0], temp[1], temp[2]]
        if spot < ma*2: return False # if no standard deviation can be calculated
        if len(precalc["bollinger"]) != 0:
            sigma = precalc["bollinger"][2][spot] - precalc["bollinger"][1][spot] # upper band - middle band
            statement = replaceOp("stock[spot][3]/k*sigma >= width", operator)
            return eval(statement)
        else:
            # precalc
            temp = bollinger(stock, ma, k)
            precalc["bollinger"] =  [temp[0], temp[1], temp[2]]
            temp = pd.DataFrame(stock[spot-ma*2:spot]) # get twice the ma because movavg is needed for ma values
            slope = temp.rolling(window=ma).mean()[3] # get moving averages
            sigma = 0 # gets how far the average is off from the current values | standard deviation
            for i in range(ma):
                sigma += pow(stock[spot-ma+i][3]-slope[ma+i], 2) # (cls-mov)^2 -> (cls-mov)^2/n = var
            sigma = sqrt(sigma/ma) # sqrt(var)
            statement = replaceOp("stock[spot][3]/k*sigma >= width", operator)
            return eval(statement) # close / k * sigma >= width (k = 2) ">" because it's being divided by width so smaller = larger
    elif shape == "volume": # volume above threshold
        if doReturn:
            l = []
            for i in range(spot):
                l.append(stock[i][4])
            return l
        
        statement = replaceOp("stock[spot][4] > ma*1000", operator)
        return eval(statement) # ma in thousand | volume > ma*1000
    elif shape == "peak": # local peak at spot
        if doReturn:
            l = []
            statement = replaceOp("maxx == i", operator)
            for i in range(spot):
                temp = stock[i-3:i+1] # get nearby values
                maxx = i - 3
                for j in range(len(temp)):
                    if stock[i-3+j][3] > stock[maxx][3]: maxx = i-3+j # get largest in range
                if i < 3: l.append(False) # if less than 3 spots before
                else: l.append(eval(statement))
            return l
        
        if spot < 3: return False # if less than 3 spots before
        if spot+3 > time: top = time # if less than 3 spots after
        else: top = spot + 3
        temp = stock[spot-3:top+1] # get nearby values
        maxx = spot - 3
        for i in range(len(temp)):
            if stock[spot-3+i][3] > stock[maxx][3]: maxx = spot-3+i # get largest in range
        statement = replaceOp("maxx == spot", operator)
        return eval(statement) # if spot is max value in range
    elif shape == "valley":
        if doReturn:
            l = []
            statement = replaceOp("minn == i", operator)
            for i in range(spot):
                temp = stock[i-3:i+1] # get nearby values
                minn = i - 3
                for j in range(len(temp)):
                    if stock[i-3+j][3] < stock[minn][3]: minn = i-3+j # get largest in range
                if i < 3: l.append(False) # if less than 3 spots before
                else: l.append(eval(statement))
            return l
        
        if spot < 3: return False # if less than 3 spots before
        if spot+3 > time: top = time # if less than 3 spots after
        else: top = spot + 3
        temp = stock[spot-3:top+1] # get nearby values
        minn = spot - 3
        for i in range(len(temp)):
            if stock[spot-3+i][3] < stock[minn][3]: minn = spot-3+i # get smallest in range
        statement = replaceOp("minn == spot", operator)
        return eval(statement) # if spot is min value in range
    elif shape == "lasttrendup": # checks if rise last up to 100 timestamps is above 0
        if doReturn: 
            l = [0] # start with 0, because first is skipped
            for i in range(1, spot):
                start = i - ma # so it wont wrap around
                if start <= 0: 
                    start = 0
                    x = list(range(i+1))
                    y = stock[start:i+1]
                else: 
                    x = list(range(ma))
                    y = stock[start+1:i+1] # get last 100 price points
                y.reverse() # so that the tangent will fixate on last price point
                coeffs = polyfit(x, y, 1)
                l.append(coeffs[0][3])
            return l

        if spot < 1: return False
        start = spot - ma # so it wont wrap around
        if start <= 0: 
            start = 0
            x = list(range(spot+1))
            y = stock[start:spot+1]
        else: 
            x = list(range(ma))
            y = stock[start+1:spot+1] # get last 100 price points
        y.reverse() # so that the tangent will fixate on last price point
        coeffs = polyfit(x, y, 1) # if y = mx + b then coeffs[0][3] = m, coeffs[1][3] = b
        if k == -1: return coeffs[0][3] # get slope instead of condition
        statement = replaceOp("coeffs[0][3] <= 0", operator)
        return eval(statement) # because it's reversed
    elif shape == "lasttrenddown": # checks if rise last up to 100 timestamps is below 0
        if doReturn: 
            l = [0] # start with 0, because first is skipped
            for i in range(1, spot):
                start = i - ma # so it wont wrap around
                if start <= 0: 
                    start = 0
                    x = list(range(i+1))
                    y = stock[start:i+1]
                else: 
                    x = list(range(ma))
                    y = stock[start+1:i+1] # get last 100 price points
                y.reverse() # so that the tangent will fixate on last price point
                coeffs = polyfit(x, y, 1)
                l.append(coeffs[0][3])
            return l
        
        if spot < 1: return False
        start = spot - ma # so it wont wrap around
        if start <= 0:
            start = 0
            x = list(range(spot+1))
            y = stock[start:spot+1]
        else: 
            x = list(range(ma))
            y = stock[start+1:spot+1] # get last 100 price points
        y.reverse() 
        coeffs = polyfit(x, y, 1) # if y = mx + b then coeffs[0][3] = m, coeffs[1][3] = b
        statement = replaceOp("coeffs[0][3] >= 0", operator)
        return eval(statement)
    elif shape == "v":
        if doReturn: return []

        avg = getAvgBody(stock, spot)

        # ma is width
        if spot < ma-1: return False

        while spot-ma >= 0 and ma <= k: # k is maximum width

            for x in [0]: # to allow breaking
                # neckline
                if stock[spot][3]-stock[spot-ma][3] > avg: break # have to be at the same height

                # get tallest in middle of v
                mid = stock[spot-ma+1:spot]
                peak = 0
                for m in range(len(mid)):
                    if mid[m][3] > mid[peak][3]: peak = m

                if mid[peak][3]-stock[spot][3] > avg/2: break # if something in the v is above neckline

                # check for valley in middle
                pit = stock[spot-ma:spot+1]
                val = 0
                for p in range(len(pit)):
                    if pit[p][3] < pit[val][3]:
                        val = p
                
                if val == len(pit)-1 or abs(val/(len(pit)-val-1)-1) > 0.2: break # if valley too far off middle

                # check whether they follow the shape of a v
                c = stock[spot][3] + (stock[spot][3] - pit[val][3])/3 # spot + (spot-v)/3 | start of v
                m = (stock[spot][3] - pit[val][3])/(val+1) # rise over run

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

                return True
            
            ma += 1
        # default return false
        return False
    elif shape == "ʌ": # upturned v
        if doReturn: return []

        avg = getAvgBody(stock, spot)

        # ma is width
        if spot < ma-1: return False

        while spot-ma >= 0 and ma <= k: # k is maximum width

            for x in [0]: # to allow breaking
                # neckline
                if stock[spot][3]-stock[spot-ma][3] > avg: break # have to be at the same height

                # get lowest in middle of ʌ
                mid = stock[spot-ma+1:spot]
                val = 0
                for m in range(len(mid)):
                    if mid[m][3] < mid[val][3]: val = m

                if stock[spot][3]-mid[val][3] > avg/2: break # if something in the ʌ is below neckline

                # check for peak in middle
                pit = stock[spot-ma:spot+1]
                peak = 0
                for p in range(len(pit)):
                    if pit[p][3] > pit[peak][3]:
                        peak = p
                
                if peak == len(pit)-1 or abs(peak/(len(pit)-peak-1)-1) > 0.2: break # if peak too far off middle

                # check whether they follow the shape of a ʌ
                c = stock[spot][3] - (pit[peak][3] - stock[spot][3])/3 # spot - (ʌ-spot)/3 | start of ʌ
                m = (pit[peak][3] - stock[spot][3])/(peak+1) # rise over run

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

                return True
            
            ma += 1
        # default return false
        return False
    elif shape == "m":
        if doReturn:
            return []

        # ma is minimum width
        if spot < ma-1: return False

        while spot-ma >= 0 and ma <= k: # to get any size of m

            for x in [0]: # simple loop to allow breaking
                # get middle valley
                mid = stock[spot-int(ma*3/4):spot-int(ma/4)+1] # middle area from w*3/4 to w/4
                val = 0
                for m in range(len(mid)):
                    if mid[m][3] < mid[val][3]:
                        val = m
                
                if val == len(mid)-1 or abs(val/(len(mid)-val-1)-1) > 0.33: break # if valley too far off middle

                # outer valleys
                side = stock[spot-ma:spot-int(ma*3/4)+1] # outer left valley
                val = 0
                for s in range(len(side)):
                    if side[s][3] < side[val][3]:
                        val = s
                if val != 0: break # if valley is not at very left; cant be an m

                # do same for other side
                side = stock[spot-int(ma/4):spot+1] # outer right valley
                side.reverse() # reverse so valley is at 0
                val = 0
                for s in range(len(side)):
                    if side[s][3] < side[val][3]:
                        val = s
                if val != 0: break # if valley is not at very right; cant be an m

                # check for peaks in between
                bigs = stock[spot-ma//2: spot+1]
                peak = 0
                for b in range(len(bigs)):
                    if bigs[b][3] > bigs[peak][3]: peak = b
                
                if peak == len(bigs)-1 or abs(peak/(len(bigs)-peak-1)-1) > 0.33: break # if peak too far off middle
                
                bigs = stock[spot-ma:spot-ma//2+1]
                peak = 0
                for b in range(len(bigs)):
                    if bigs[b][3] > bigs[peak][3]: peak = b
                
                if peak == len(bigs)-1 or abs(peak/(len(bigs)-peak-1)-1) > 0.33: break # if peak too far off middle

                return True
            ma += 1

        return False
    elif shape == "w":
        if doReturn:
            return []

        # ma is minimum width
        if spot < ma-1: return False

        while spot-ma >= 0 and ma <= k: # to get any size of w
            
            for x in [0]: # simple loop to allow breaking
                # get middle peak
                mid = stock[spot-int(ma*3/4):spot-int(ma/4)+1] # middle area from w*3/4 to w/4
                peak = 0
                for m in range(len(mid)):
                    if mid[m][3] > mid[peak][3]:
                        peak = m
                
                if peak == len(mid)-1 or abs(peak/(len(mid)-peak-1)-1) > 0.33: break # if peak too far off middle

                # outer peaks
                side = stock[spot-ma:spot-int(ma*3/4)+1] # outer left peak
                peak = 0
                for s in range(len(side)):
                    if side[s][3] > side[peak][3]:
                        peak = s
                if peak != 0: break # if peak is not at very left; cant be a w

                # do same for other side
                side = stock[spot-int(ma/4):spot+1] # outer right peak
                side.reverse() # reverse so peak is at 0
                peak = 0
                for s in range(len(side)):
                    if side[s][3] > side[peak][3]:
                        peak = s
                if peak != 0: break # if peak is not at very right; cant be a w
                
                # check for valleys in between
                bigs = stock[spot-ma//2: spot+1]
                val = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val][3]: val = b
                
                if val == len(bigs)-1 or abs(val/(len(bigs)-val-1)-1) > 0.33: break # if valley too far off middle

                
                bigs = stock[spot-ma:spot-ma//2+1]
                val = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val][3]: val = b
                
                if val == len(bigs)-1 or abs(val/(len(bigs)-val-1)-1) > 0.33: break # if valley too far off middle

                return True
            ma += 1
        
        # if ma > spot; no w has been found
        return False
    elif shape == "shs":
        if doReturn: return []

        avg = getAvgBody(stock, spot)
        # ma is minimum width
        if spot < ma-1: return False

        while spot-ma >= 0 and ma <= k: # to get any size of shs
            
            for x in [0]: # simple loop to allow breaking
                # get middle peak
                mid = stock[spot-int(ma*2/3):spot-int(ma/3)+1] # middle area from w*2/3 to w/3
                mpeak = 0
                for m in range(len(mid)):
                    if mid[m][3] > mid[mpeak][3]:
                        mpeak = m
                
                if mpeak == len(mid)-1 or abs(mpeak/(len(mid)-mpeak-1)-1) > 0.33: break # if peak too far off middle

                # lesser peaks
                side = stock[spot-ma:spot-int(ma*2/3)+1] # left peak
                peak = 0
                for s in range(len(side)):
                    if side[s][3] > side[peak][3]:
                        peak = s

                if peak == len(side)-1 or abs(peak/(len(side)-peak-1)-1) > 0.33: break # if peak too far off middle

                # do same for other side
                side2 = stock[spot-int(ma/3):spot+1] # right peak
                peak2 = 0
                for s in range(len(side2)):
                    if side2[s][3] > side2[peak2][3]:
                        peak2 = s
                if peak2 == len(side2)-1 or abs(peak2/(len(side2)-peak2-1)-1) > 0.33: break # if peak too far off middle
                
                if side[peak][3] > mid[mpeak][3] or side2[peak2][3] > mid[mpeak][3]: break # outer peaks have to be lower than middle peak

                # check for valleys in between
                valvals = [stock[spot][3]] # valley values
                bigs = stock[spot-ma//2: spot-ma//6+1]
                val = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val][3]: val = b
                
                valvals.append(bigs[val][3])
                
                bigs = stock[spot-5*ma//6:spot-ma//2+1]
                val = 0
                for b in range(len(bigs)):
                    if bigs[b][3] < bigs[val][3]: val = b
                
                valvals.append(bigs[val][3])
                valvals.append(stock[spot-ma][3])

                # valvals now holds all of the points on the neckline
                m = (valvals[0]-valvals[1])/(ma/3) # rise over run
                cancel = False
                for v in range(len(valvals)):
                    if abs(valvals[v]-(stock[spot][3] + m*v)) > avg*2: # if actual neckline is too far away from theoretical neckline
                        cancel = True
                if cancel: break
                return True
            ma += 1
        
        # if ma > spot; no w has been found
        return False
    elif shape == "cup": # cup shape
        if doReturn:
            return []

        # ma is minimum width
        if spot < ma-1: return False

        while spot-ma >= 0 and ma <= k: # to get any size of cup
            
            for x in [0]: # simple loop to allow breaking
                # neckline
                if round(stock[spot][3]-stock[spot-ma][3]) != 0: break # have to be at the same height

                # get tallest in middle of cup
                mid = stock[spot-ma+1:spot]
                peak = 0
                for m in range(len(mid)):
                    if mid[m][3] > mid[peak][3]: peak = m

                if round(mid[peak][3]-stock[spot][3]) > 0: break # if something in the cup is above neckline
                
                return True
            ma += 1
        
        # if ma > spot; no w has been found
        return False
    elif shape == "inrange": # if stock price is between a resistance and support line
        if doReturn: return []
        
        closes = []
        # k is maximum length | ma is minimum length
        x = spot-k-4
        if x < 0: x = 0
        # for s in stock[x:spot+1]:
        #     closes.append(s[3]) # get list of closes
        
        # get first derivative with help of slight smoothing
        derivative = []
        temp = pd.DataFrame(stock[x:spot+1])
        avg = temp.rolling(window=4).mean()[3].reset_index(drop=True).to_list() # get moving average of 4

        for a in range(4, len(avg)):
            derivative.append(avg[a]-avg[a-1])

        # check if average of boolean values is 0.5; this means the trend is indecisive
        add = 0
        for i in range(len(derivative)):
            add += int(derivative[i] > 0)
            if i >= ma: # so doesn't immediately assume trend 
                if abs((add / (i+1)) - 0.5) < 0.05: return True # if values near 0.5; trend is indecisive

        return False
    elif shape == "resistouch": # if price touches resistance
        if doReturn: return []

        avg = getAvgBody(stock, spot)

        if spot < 20: return False # some spots need to be present
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
        
        if len(touches) != 3: return False # if no three touches; cant be a resistance line
        x = spot-touches[-1] # range of resistance
        for j in range(2):
            if touches[j]-touches[j+1] < x/3: return False # minimum distance
        
        add = 0
        for j in range(x):
            if stock[spot-j][3] < stock[i][3]: add += 1 # if below line
        
        statement = replaceOp("add/x >= 0.90", operator) # most need to be below line
        return eval(statement) 
    elif shape == "supportouch": # if price touches support
        if doReturn: return []

        avg = getAvgBody(stock, spot)

        if spot < 20: return False # some spots need to be present
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
        
        if len(touches) != 3: return False # if no three touches; cant be a resistance line
        x = spot-touches[-1] # range of resistance
        for j in range(2):
            if touches[j]-touches[j+1] < x/3: return False # minimum distance
        
        add = 0
        for j in range(x):
            if stock[spot-j][3] > stock[i][3]: add += 1 # if above line
        
        statement = replaceOp("add/x >= 0.90", operator) # most need to be above line
        return eval(statement) 
    elif shape == "vwap": # volume weighted average price
        if doReturn:
            temp = []
            prods = [] # price * volume of all
            for i in range(spot+1): # equal to len(stock)
                prods.append(stock[i][3] * stock[i][4])
            for i in range(ma): temp.append(float("nan")) # no value for first few values
            for i in range(ma, spot+1):
                cumsum = 0
                vols = 0 # all volumes
                for m in range(ma): # for every window
                    cumsum += prods[i-m]
                    vols += stock[i-m][4]
                temp.append(cumsum/vols)
            return temp
        if len(precalc["vwap"]) == 0:
            temp = []
            prods = [] # price * volume of all
            for i in range(len(stock)): # equal to len(stock)
                prods.append(stock[i][3] * stock[i][4])
            for i in range(ma): temp.append(float("nan")) # no value for first few values
            for i in range(ma, len(stock)):
                cumsum = 0
                vols = 0 # all volumes
                for m in range(ma): # for every window
                    cumsum += prods[i-m]
                    vols += stock[i-m][4]
                temp.append(cumsum/vols)
            precalc["vwap"] = temp
        statement = replaceOp("stock[spot][3] < precalc[\"vwap\"][spot]", operator)
        return eval(statement)
    elif shape == "ha-up": # heikin-ashi up
        if doReturn: return []
        if len(precalc["heikin-ashi"]) == 0:
            precalc["heikin-ashi"] = getHeikinAshi(stock)
        if spot == 0: ohlc = stock[0]
        else: # get heikin ashi candle
            ohlc = precalc["heikin-ashi"][spot]
        statement = replaceOp("ohlc[3] > ohlc[0]", operator)
        return eval(statement)
    elif shape == "ha-down": # heikin-ashi down
        if doReturn: return []
        if len(precalc["heikin-ashi"]) == 0:
            precalc["heikin-ashi"] = getHeikinAshi(stock)
        if spot == 0: ohlc = stock[0]
        else: # get heikin ashi candle
            ohlc = precalc["heikin-ashi"][spot]
        statement = replaceOp("ohlc[3] < ohlc[0]", operator)
        return eval(statement)
    elif shape == "ha-shadowup": # heikin-ashi up shadow (high way above body)
        if doReturn: return []
        if len(precalc["heikin-ashi"]) == 0:
            precalc["heikin-ashi"] = getHeikinAshi(stock)
        if spot == 0: ohlc = stock[0]
        else: # get heikin ashi candle
            ohlc = precalc["heikin-ashi"][spot]
        if ohlc[0] - ohlc[2] > 0.2: return False # open and low have to be close together
        parts = []
        parts.append(abs(ohlc[3]-ohlc[0])) # close-open (body size)
        parts.append(ohlc[1]-ohlc[2]) # high - low (total size)
        statement = replaceOp("parts[0]/parts[1] <= 0.66", operator)
        return eval(statement)
    elif shape == "ha-shadowdown": # heikin-ashi down shadow (low way below body)
        if doReturn: return []
        if len(precalc["heikin-ashi"]) == 0:
            precalc["heikin-ashi"] = getHeikinAshi(stock)
        if spot == 0: ohlc = stock[0]
        else: # get heikin ashi candle
            ohlc = precalc["heikin-ashi"][spot]
        if ohlc[1] - ohlc[0] > 0.2: return False # high and open have to be close together
        parts = []
        parts.append(abs(ohlc[3]-ohlc[0])) # close-open (body size)
        parts.append(ohlc[1]-ohlc[2]) # high - low (total size)
        statement = replaceOp("parts[0]/parts[1] <= 0.66", operator)
        return eval(statement)
    elif shape == "ha-doji": # heikin-ashi doji (price not going anywhere)
        if doReturn: return []
        if len(precalc["heikin-ashi"]) == 0:
            precalc["heikin-ashi"] = getHeikinAshi(stock)
        if spot == 0: ohlc = stock[0]
        else: # get heikin ashi candle
            ohlc = precalc["heikin-ashi"][spot]
        up = ohlc[3] > ohlc[0]
        if up:
            top = ohlc[3]
            bot = ohlc[0]
        else:
            top = ohlc[0]
            bot = ohlc[3]
        parts = []
        parts.append(ohlc[1]-top) # top wick
        parts.append(bot-ohlc[2]) # bottom wick
        if parts[1] == 0: return False # can't divide by 0
        if ((top-bot)/parts[1]-1) >= 0.33: return False # body cant be bigger than the wick
        statement = replaceOp("abs(parts[0]/parts[1]-1) <= 0.25", operator)
        return eval(statement)
    elif shape == "macd-momentum": # moving average convergence/divergence | if bullish (up) momentum
        if doReturn:
            return []
        if len(precalc["macd"]) == 0:
            temp = pd.DataFrame(stock)
            ema12 = temp.ewm(span=12, adjust=False).mean()[3].reset_index(drop=True).to_list()
            ema26 = temp.ewm(span=26, adjust=False).mean()[3].reset_index(drop=True).to_list()
            macd = []
            for e in range(len(ema12)):
                macd.append(ema12[e]-ema26[e])
            temp = pd.DataFrame(macd)
            signal = temp.ewm(span=9, adjust=False).mean()[0].reset_index(drop=True).to_list()
            precalc["macd"] = [macd, signal]
        slope = [precalc["macd"][0][spot], precalc["macd"][1][spot]]
        statement = replaceOp("slope[0] >= slope[1]", operator)
        return eval(statement)
    elif shape == "macd-market": # moving average convergence/divergence | if bullish (up) market
        if doReturn:
            return []
        if len(precalc["macd"]) == 0:
            temp = pd.DataFrame(stock)
            ema12 = temp.ewm(span=12, adjust=False).mean()[3].reset_index(drop=True).to_list()
            ema26 = temp.ewm(span=26, adjust=False).mean()[3].reset_index(drop=True).to_list()
            macd = []
            for e in range(len(ema12)):
                macd.append(ema12[e]-ema26[e])
            temp = pd.DataFrame(macd)
            signal = temp.ewm(span=9, adjust=False).mean()[0].reset_index(drop=True).to_list()
            precalc["macd"] = [macd, signal]
        slope = precalc["macd"][0][spot]
        statement = replaceOp("slope > 0", operator)
        return eval(statement)
    elif shape == "rsi": # relative strength index
        if doReturn: return []
        closes = []
        x = spot - ma
        if x < 0: x = 0
        for st in stock[x:spot+1]:
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
        statement = replaceOp("rsi >= k", operator)
        return eval(statement)
    elif shape == "elliott": # elliott probability distribution
        pass
    else:
        print(shape + " is not a shape.\nCheck your writing!")
        return False

def resetPrecalc(): # resets all precalc lists
    for cond in precalc:
        precalc[cond] = []

def coordinate(what: str, value, gridc, rx, ry, height):
    if what == "x":
        coord = (gridc[0]*(value-rx[0]))/gridc[1]
        return coord
    elif what == "y":
        coord = height-(gridc[2]*(value-ry[0]))/gridc[3]
        return coord

class Grid(QtWidgets.QGraphicsItem):
    def __init__(self, rect, grid_information):
        super().__init__()
        self.rect = rect
        self.conversion = grid_information # (dx, corr dt, dy, corr dp)
        
    def boundingRect(self):
        return self.rect
    
    def paint(self, painter, option, widget):
        # draw grid

        density = (20, 20) # (x, y)

        if theme == "light": painter.setPen(QtCore.Qt.GlobalColor.gray)
        else: painter.setPen(QtGui.QColor(56, 56, 56))
        for x in range(int(self.rect.left()), int(self.rect.right()), density[0]):
            painter.drawLine(x, int(self.rect.top()), x, int(self.rect.bottom()))
        for y in range(int(self.rect.top()), int(self.rect.bottom()), density[1]):
            painter.drawLine(int(self.rect.left()), y, int(self.rect.right()), y)

class Candle(QtWidgets.QGraphicsItem):
    def __init__(self, time, ohlc, date=None):
        super().__init__()
        self.text = "Default"
        self.time = time
        self.ohlc = ohlc
        self.date = date
        #self.setFlag(QGraphicsItem.)
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
        painter.setBrush(QtGui.QBrush(self.color))
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
    def __init__(self, parent=None, idd=0):
        super().__init__(parent)
        self.delFn = lambda: type(None)
        self.idd = idd
        self.clickFn = lambda: type(None)
        self.ind = 0
        self.typ = "conds"
        self.doPass = True # whether to also pass event
        self.doDel = True # whether to show delete

    def setDelFn(self, fn, idd): # right click delete
        self.idd = idd
        self.delFn = fn
    
    def setClickFn(self, fn, ind): # left click
        self.clickFn = fn
        self.ind = ind
    
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.doPass: self.clickFn(e, self.ind)
            else: self.clickFn(self.ind)
        return super().mouseReleaseEvent(e)

    def contextMenuEvent(self, event):
        if not self.doDel: return
        menu = QtWidgets.QMenu(self)
        act = menu.addAction("Delete")
        act.triggered.connect(lambda: self.delFn(self.idd, self.typ))
        menu.setStyleSheet("color: white;")
        menu.exec(event.globalPos())

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

    def getCondition(self, shap: str = "", inputs=[], indid=None, stock=-1): # get indicator data and run condition on top
        inps = inputs
        shape = shap
        if stock == -1: stock = self.rawind # incase no stock is given, assume the base stock is used
        
        if indid is not None: # if id is given
            # conds = [self.inputs[0].currentText(), inps[4], inps[0], inps[1], inps[2], inps[3]] | try to recreate this
            indx = self.find("i", indid)
            shape = self.indicators[indx]["condVars"][0] 
            inps = [] # convert condVars into inps
            for i in range(2, 6): inps.append(self.indicators[indx]["condVars"][i])
            inps.append(self.indicators[indx]["condVars"][1]) # inps[4]
            inps.append(self.conditions[self.find("ci", indid)]["trigger"]) # inps[5]
        indout = [] 
        for i in range(inps[4]): indout.append(False)
        time = inps[4] # fast forward time
        resetPrecalc() # reset precalc
        for t in range(inps[4], len(raw[stock])): # only from spot offset onwards | base indicator
            indout.append(condition(stock, shape, t-inps[4], inps[0], inps[1], inps[2], inps[3], time=time))
            time += 1
        if inps[5] == "true": return indout # if all true return base list
        elif inps[5] == "first true":
            new = [indout[0]] # exported list # start with same as indout
            current = indout[0]
            for i in indout[1:]:
                if i == current: new.append(False)
                elif not current: # if not same and current was false; true
                    new.append(True)
                    current = True
                else: # if true switches to false
                    new.append(False)
                    current = False
            return new
        elif inps[5] == "last true":
            if inps[4] == 0: # same spot | all true is true
                return indout
            new = [] # exported list
            current = indout[0]
            for i in indout[1:]:
                if i == current: new.append(False)
                elif not current: # if not same and current was false; false
                    new.append(False)
                    current = True
                else: # if true switches to false
                    new.append(True)
                    current = False
            new.append(indout[-1]) # if last one is true always return true
            return new
        elif inps[5] == "near": # check two surrounding as well and return true if any of the three is true
            new = []
            current = False
            for i in range(len(indout)):
                current = False
                if i == 0 or i == len(indout)-1: # checks behind/ infront and itself
                    if i == 0: mult = -1
                    else: mult = 1
                    for j in range(2):
                        if indout[i-j*mult]: current = True
                else: # check surrounding two and itself
                    for j in range(3):
                        if indout[i-1+j]: current = True
                new.append(current)
            return new

    def getData(self, ind): # calculate data for conditions
        if self.conditions[ind]["indID"] != -1: # if indicator condition
            if len(self.conditions[ind]["data"]) == 0: # check if data has not been calculated
                dat = self.getCondition(indid=self.conditions[ind]["indID"])
                self.conditions[ind]["data"] = dat
        else: # complex condition (does not check for whether underlying conditions have been calculated)
            if len(self.conditions[ind]["data"]) == 0:
                if self.conditions[ind]["deps"][1] == "not": # not only needs one condition
                    dat = []
                    indx = self.find("c", self.conditions[ind]["deps"][0][1])
                    for d in self.conditions[indx]["data"]:
                        dat.append(not d) # invert true to false and false to true
                    self.conditions[ind]["data"] = dat
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
                    self.conditions[ind]["data"] = dat

    def delUnusedConditions(self): # self explanatory
        keep = [] # whether to keep condition
        for c in self.conditions:
            if c["indID"] == -1:
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

    def seekConditions(self, spots, stock): # return conditions given the spots and the stock
        if __name__ != "__main__":
            global raw
            inds = self.indicators
            conds = self.conditions
            raw = [stock]
            return # return because function hasn't been tested yet
        inds = [] # list of indicator dictionaries
        conds = [] # list of condition dictionaries
        graphs = ["movavg", "expavg", "bollinger", "vwap"] # indicators based on graphs
        spotscs = ["contested"] # indicators based on special spots
        i = 0
        for a in avconds: # get one of every condition
            args = [200, 2, 10]
            if len(neededArgs[a]) != 0:
                for n in neededArgs[a]:
                    args[["ma", "k", "width"].index(n[0])] = n[2] # get args
            dMode = 0
            for g in graphs: # get dMode
                if g in self.inputs[0].currentText(): dMode = 1
            if self.inputs[0].currentText() in spotscs: dMode = 2
            elif self.inputs[0].currentText() == "volume": dMode = 3
            inds.append({"ID:":i, "condVars":[a, 0, args[0], args[1], args[2], ""], "dMode":dMode, "color":"#ffffff", "show":False})
            conds.append({"ID":i, "indID":i, "act":0, "trigger":"true", "data":[], "deps":[]})
            i += 1
        
        coverage = [] # will contain percentage of selected important spots vs marked spots
        success = [] # percentage of spots in spots marked
        for c in conds: # calculate data for all default conditions
            self.getData(conds.index(c))
            add = 0
            for s in spots:
                if c["data"][s]: add += 1 # how many of the spots were marked
            add /= len(spots)
            success.append(add)
            trues = 0
            for d in c["data"]:
                if d: trues += 1
            if trues == 0: coverage.append(0)
            else: coverage.append(add/trues)
        
        keep = [] # conditions to keep from this check
        for i in range(len(conds)):
            if success[i] == 1: # if all spots were marked
                keep.append(i)
        
        needed = []
        currargs = [0]
        types = [int]
        mins = []
        maxes = [10]
        def step(which=0): # so that all are shuffled through
            if types[which] == int: increment = 1
            else: increment = 0.1
            currargs[which] += increment
            if currargs[which] > maxes[which]:
                currargs[which] = mins[which]
                if which != len(needed): step(which+1)
                else: return "finished"

        finals = []
        for k in keep:
            args = [] # arguments that will change: [before, ma, k, width]
            needed = [] # keys
            currargs = [0]
            types = [int]
            maxes = [10]
            mins = [0]
            conds[k]["trigger"] = "true"
            for n in neededArgs[inds[k]["condVars"][0]]:
                needed.append(n[0]) # key
                currargs.append(n[2]) # starting value
                mins.append(n[2]) # minimum
                types.append(n[1]) # type
                if n[3] == "nan": maxes.append(len(stock))
                else: maxes.append(n[3]) # maximum
            
            result = None
            while result != "finished":
                if currargs[0] == 0: # if one of the side args changed / just got started
                    for ne in range(len(needed)): # set arguments of indicator
                        ind = [0, 0, "ma", "k", "width"].index(needed[ne])
                        inds[k]["condVars"][ind] = currargs[ne+1]
                    conds[k]["data"] = []
                    self.getData(k) # get new data
                else: conds[k]["data"] = [0] + conds[k]["data"] # shift all one to the right to check before
                appendlist = []
                add = 0
                for s in spots:
                    if conds[k]["data"][s]: add += 1 # how many of the spots were marked
                add /= len(spots)
                appendlist.append(add)
                trues = 0
                for d in conds[k]["data"]:
                    if d: trues += 1
                if trues == 0: appendlist.append(0)
                else: appendlist.append(add/trues)
                for c in currargs: appendlist.append(c)
                args.append(appendlist)
                result = step() # run until all different possibilities have been tried
            
            firsts = []
            lasts = []
            for a in range(len(args)):
                if args[a][0] == 1: # if success is 1
                    if a != 0 and a != len(args)-1: # if a has surrounding spots
                        if args[a][2] != mins[0] and args[a-1][0] == 0: # if not spot 0 and last spot was 100% false
                            firsts.append(args) # first true should apply
                        elif args[a][2] != maxes[0] and args[a+1][0] == 0:
                            lasts.append(args) # last true should apply
            
            conds[k]["trigger"] = "first"
            for f in firsts:
                inds[k]["condVars"][1] = f[2]
                for ne in range(len(needed)): # set arguments of indicator
                    ind = [0, 0, "ma", "k", "width"].index(needed[ne])
                    inds[k]["condVars"][ind] = f[ne+3]
                conds[k]["data"] = []
                self.getData(k) # get new data
                appendlist = []
                add = 0
                for s in spots:
                    if conds[k]["data"][s]: add += 1 # how many of the spots were marked
                add /= len(spots)
                appendlist.append(add)
                trues = 0
                for d in conds[k]["data"]:
                    if d: trues += 1
                if trues == 0: appendlist.append(0)
                else: appendlist.append(add/trues)
                for c in f: appendlist.append(c)
                appendlist.append("first")
                args.append(appendlist)
            
            conds[k]["trigger"] = "last"
            for l in lasts:
                inds[k]["condVars"][1] = l[2]
                for ne in range(len(needed)): # set arguments of indicator
                    ind = [0, 0, "ma", "k", "width"].index(needed[ne])
                    inds[k]["condVars"][ind] = l[ne+3]
                conds[k]["data"] = []
                self.getData(k) # get new data
                appendlist = []
                add = 0
                for s in spots:
                    if conds[k]["data"][s]: add += 1 # how many of the spots were marked
                add /= len(spots)
                appendlist.append(add)
                trues = 0
                for d in conds[k]["data"]:
                    if d: trues += 1
                if trues == 0: appendlist.append(0)
                else: appendlist.append(add/trues)
                for c in l: appendlist.append(c)
                appendlist.append("last")
                args.append(appendlist)
            
            # sort by success
            args = sorted(args, key=lambda x: x[0])
            args.reverse() # so sorted descending

            finalists = []
            for a in range(len(args)):
                if args[a][0] == 1: # if success is 100%
                    finalists.append(args[a]) # keep
                else: break # if not 100%; cancel
            
            finalists = sorted(finalists, key=lambda x: x[1]) # sort by coverage
            finalists.reverse()
            if finalists[0][1] == 1: # if 100% coverage and 100% success
                idd = len(finals)
                trigger = finalists[0][-1]
                if type(trigger) != str: trigger = "true"
                finals.append(({"ID:":idd, "condVars":[a, 0, args[0], args[1], args[2], ""], "dMode":dMode, "color":"#ffffff", "show":False},
                               {"ID":idd, "indID":idd, "act":0, "trigger":trigger, "data":[], "deps":[]}))
                return # end search as perfect condition is found
            elif finalists[0][1] > 0.5: # above 50% coverage 
                trigger = finalists[0][-1]
                if type(trigger) != str: trigger = "true"
                finals.append(({"ID:":idd, "condVars":[a, 0, args[0], args[1], args[2], ""], "dMode":dMode, "color":"#ffffff", "show":False},
                               {"ID":idd, "indID":idd, "act":0, "trigger":trigger, "data":[], "deps":[]}))

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

    def backtest(self, ind): # backtest strategy of id
        time = 0
        stock = self.systems[self.currentSystem].rawind # current viewed stock
        startmoney = 10000
        amnt = int(ceil(200/raw[stock][0][3])) # how many stocks will be bought per purchase
        trailperc = 0.01
        fees = 0
        if len(self.strategies[ind]["risk"]) != 0: # if risk management has been set
            startmoney = self.strategies[ind]["risk"][0] # balance
            amnt = int(ceil(self.strategies[ind]["risk"][3]/raw[stock][0][3])) # how many stocks will be bought per purchase
            trailperc = self.strategies[ind]["risk"][2] # percentage of trail behind
            fees = self.strategies[ind]["risk"][4] # fees in % per trade
        operations = []
        money = startmoney
        timeframe = len(raw[stock])-1
        self.entexs = [[], [], [], []] # [ent, ext, extpercs, liqmoney] | entries, exits, exitpercentages and liquid money
        while time < timeframe: # timeframe for stock simulation
            poplist = [] # operations that have finished
            for op in operations:
                if op.type == "stoplimit":
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
                if operations[p].type != "stoplimit":
                    self.entexs[2].append((time, 100*(operations[p].stopprice/((1+fees)*operations[p].buyprice)-1))) # append exitprc using trailing stop, time and buy price
                sold = True # if operation is removed; something is sold
                operations.pop(p)
            
            bought = False
            if self.strategies[ind]["data"][time]: # if strategy here is true
                if money >= (1+fees)*amnt*raw[stock][time][3]: 
                    bought = True
                    money -= (1+fees)*amnt*raw[stock][time][3] # subtract money
                    operations.append(Operation(stock, "trailing", amnt, time, perc=trailperc, fee=fees)) # append 1% trailing stop operation
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
        succ = 0 # positive exits, num exits
        for e in self.entexs[2]: # get number of positive exits
            if e[1] > 0: succ += 1
        if len(self.entexs[2]) != 0: succ /= len(self.entexs[2]) # get percentage of positive exits
        else: succ = 0
        # set starting values
        self.stats.succ = succ
        self.stats.progress = 100/len(stocks) # set progress to 100%
        self.stats.processed = 1 

    def backthread(self, ind, queue): # function run by each backthread
        global raw
        back = self.backthreads[ind] # shortcut for convenience
        #elapsed = now() # get time when function is called
        back.condata = []
        for c in back.conds:
            back.condata.append([]) # make empty list for condition data

        # for multiprocessing
        if "__name__" != "__main__":
            raw = [[]]
            back.rawind = 0

        def getData(ind): # redefine getdata to deglobalize variables
            # ind is index of condition in back.conds
            cind = self.find("c", back.conds[ind][1])
            if self.conditions[cind]["indID"] != -1: # if indicator condition
                if len(back.condata[ind]) == 0: # check if data has not been calculated
                    dat = self.getCondition(indid=self.conditions[cind]["indID"], stock=back.rawind) # change what stock is used
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

        while back.rawpoint < len(stocks) -1:
            # get raw data
            priceavg = 0
            raw[back.rawind] = read(stocks[back.rawpoint])
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
            
                #global time, money, operations
                time = 0
                stock = back.rawind # current viewed stock
                startmoney = 10000
                amnt = int(ceil(200/raw[stock][0][3])) # how many stocks will be bought per purchase
                trailperc = 0.01
                fees = 0
                if len(back.risk) != 0: # if risk management has been set
                    startmoney = back.risk[0] # balance
                    amnt = int(ceil(back.risk[3]/raw[stock][0][3])) # how many stocks will be bought per purchase
                    trailperc = back.risk[2] # percentage of trail behind
                    fees = back.risk[4] # fees in % per trade
                money = startmoney
                timeframe = len(back.data)
                back.entexs = [[], [], [], []] # [ent, ext, extpercs, liqmoney] | entries, exits, exitpercentages and liquid money
                while time < timeframe: # timeframe for stock simulation
                    # timestep function
                    poplist = []
                    for op in back.operations:
                        if op.type == "stoplimit":
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
                        if back.operations[p].type != "stoplimit": # append exitprc using trailing stop, time and buy price
                            back.entexs[2].append((time, 100*(back.operations[p].stopprice/((1+fees)*back.operations[p].buyprice)-1))) 
                        sold = True # if operation is removed; something is sold
                        back.operations.pop(p)
                    
                    bought = False
                    if back.data[time]: # if strategy here is true
                        if money >= (1+fees)*amnt*raw[stock][time][3]: # if buyable
                            bought = True
                            money -= (1+fees)*amnt*raw[stock][time][3] # subract money
                            back.operations.append(Operation(stock, "trailing", amnt, time, perc=trailperc, fee=fees)) # append 1% trailing stop operation
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
                self.stats.succ += succ
                self.stats.progress += 100/len(stocks)
                if len(back.entexs[2]) != 0: self.stats.processed += 1 # if nothing was traded then dont add to denominator
            else: # if nothing was loaded then just add normal progress
                succ = 0 # positive exits, num exits
                self.stats.succ += succ
                self.stats.progress += 100/len(stocks)
                #self.stats.processed += 1
            outs = [self.stats] # if further things need to be passed in
            self.stats.details.append({"success": succ, "rawind":back.rawpoint, "price":priceavg})
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
                if cc["indID"] == -1: # if it's a complex condition
                    if cc["deps"][0][1] == idd: poplist.append(self.conditions.index(cc)) # if the condition uses deleted condition, add to poplist
                    elif cc["deps"][1] != "not": # if not not also check other condition
                        if cc["deps"][2][1] == idd: poplist.append(self.conditions.index(cc))
            poplist.reverse()
            for p in poplist:
                self.updateStrategies(self.conditions[p]["ID"]) # say that this condition will get deleted and check other dependencies
                self.conditions.pop(p)

    def saveStrategy(self, what=""): # saves a strategy
        if self.stratPath == "" or what == "as": # if no path for the saved file has yet been selected or save as has been selected
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save As", "", "Text Files (*.txt)")
            if file_path == "":
                return 
            self.stratPath = file_path
        string = ""
        for s in self.strategies:
            string += "{"
            string += str(s["ID"]) # save id at beginning
            string += "("
            for r in s["risk"]:
                string += str(r) + ","
            string += ")"
            for c in s["conds"]:
                string += "(" + c[0] + "," # condition type
                string += str(c[1]) + "," # save ids that are used in memory
                cind = self.find("c", c[1])
                if c[0] == "ci": # indicator conditon
                    cind = self.find("i", self.conditions[cind]["indID"]) # get index of dependent indicator
                    string += str(self.indicators[cind]["ID"]) + ","
                    for v in self.indicators[cind]["condVars"]: # save all of the indicator data
                        string += str(v) + ","
                    string += self.indicators[cind]["color"] + "|" # add seperator to seperate indicator from condition
                    cind = self.find("c", c[1]) # reset cind
                else: # complex condition
                    for d in self.conditions[cind]["deps"]: # for all dependencies
                        if type(d) == tuple: # if tuple
                            string += "["
                            for i in d:
                                string += str(i) + ","
                            string += "]"
                        else: string += d + ","
                    string += "|"
                string += self.conditions[cind]["trigger"] + ")" # add trigger at the end
            string += "}\n"
        # save string to file
        file = open(self.stratPath, "w")
        file.write(string)
        file.close()

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
        self.selected = [] # list of indexes of selected conditions 
        self.generals = [None, None, None] # widgets from the general dock
        self.spots = [] # selected spots for condition seeker
        self.processes = [] # for all non backthread processes
        #self.pricerects = [None, None] # rects on x and y axis that display where exactly crosshair is pointing to
        self.debugvar = [False, -1, -1, False] # [whether debug is enabled, current rawind, stategy ind, whether to adjust to first marked]

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
        act = view.addAction("Conditions...")
        act.triggered.connect(self.conditionDialog)
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
        layout1.addWidget(self.xview)
        layout1.setSpacing(0)
        layout1.setContentsMargins(0, 0, 0, 0)
        axes_widget = QtWidgets.QWidget(self)
        axes_widget.setLayout(layout1)

        # for y axis spacing in lower right corner
        y_layout = QtWidgets.QVBoxLayout()
        y_layout.addWidget(self.yview)
        y_layout.addSpacing(25)
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
        if filename == "": return # if now file was selected
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
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Download...")
        dbox.setFixedSize(300, 200)
        label1 = QtWidgets.QLabel(dbox)
        label1.setGeometry(10, 10, 85, 25)
        self.inputs[0] = QtWidgets.QLineEdit(dbox)
        self.inputs[0].setGeometry(60, 10, 50, 25)
        label2 = QtWidgets.QLabel(dbox)
        label2.setGeometry(10, 40, 85, 25)
        self.inputs[1] = QtWidgets.QComboBox(dbox)
        avail = ["1m", "15m", "1h", "1d", "1wk", "1mo", "3mo"] # available intervals
        for a in avail: self.inputs[1].addItem(a)
        self.inputs[1].setGeometry(60, 40, 75, 23)
        label3 = QtWidgets.QLabel(dbox)
        label3.setGeometry(10, 75, 85, 25)
        avail = [2022, 1, 27] # example date
        rans = [(2000, 3000), (1, 12), (1, 31)] # ranges for the different spinboxes
        for j in range(2):
            self.inputs[2+j] = []
            for i in range(3):
                self.inputs[2+j].append(QtWidgets.QSpinBox(dbox))
                self.inputs[2+j][-1].setGeometry(60+55*i, 75+j*40, 50, 25)
                self.inputs[2+j][-1].setRange(rans[i][0], rans[i][1])
                self.inputs[2+j][-1].setValue(avail[i]+j)
        label4 = QtWidgets.QLabel(dbox)
        label4.setGeometry(10, 115, 85, 25)
        input5 = QtWidgets.QComboBox(dbox) # Placeholder for future
        input5.addItem("Interval")
        input5.addItem("Period")
        input5.move(175, 10)
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(110, 160)
        label1.setText("Ticker")
        label2.setText("Interval")
        label3.setText("Start")
        label4.setText("End")
        btn.pressed.connect(lambda: self.downloadChange(dbox, how))
        dbox.exec()

    def downloadChange(self, parent, how=""): # download data and load scene
        global raw
        try:
            start = dt.datetime(self.inputs[2][0].value(), self.inputs[2][1].value(), self.inputs[2][2].value())
            end = dt.datetime(self.inputs[3][0].value(), self.inputs[3][1].value(), self.inputs[3][2].value())
        except ValueError:
            self.errormsg("Date is invalid.")
            return
        if start > end: 
            self.errormsg("Start date is more recent than end date.")
            return
        if self.inputs[1].currentText() == "1m": # 1 Minute
            if start < dt.datetime.now() - dt.timedelta(days=30):
                self.errormsg("Date range too big. (Maximum = 30)")
                return
            elif end-start > dt.timedelta(days=7):
                self.errormsg("Only 7 consecutive days allowed.")
                return
        elif self.inputs[1].currentText() == "15m": # 15 Minutes
            if start < dt.datetime.now() - dt.timedelta(days=60):
                self.errormsg("Date range too big. (Maximum = 60)")
                return
        elif self.inputs[1].currentText() == "1h": # 1 hour
            if start < dt.datetime.now() - dt.timedelta(days=730):
                self.errormsg("Date range too big. (Maximum = 730)")
                return
        red, dat = stock_data(self.inputs[0].text(), start, end, self.inputs[1].currentText()) # get data and date
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
        self.newScene(how, "Live " + self.inputs[0].text().upper())
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
    
    def pickColor(self): # color dialog
        sender = self.sender()
        # Open the color picker dialog and get the selected color
        color = QtWidgets.QColorDialog.getColor()

        # If the user selected a color, update the button's background color
        if color.isValid():
            sender.setStyleSheet("background-color: %s;" % color.name())

    def ctrlButton(self, event, ind=0): # pass method to check whether ctrl is pressed before
        if self.tabs.tabText(self.tabs.currentIndex()) == "+":
            self.errormsg("Please load a stock first.")
            return
        if event.modifiers().name == "ControlModifier": # execute multi marking
            if len(logic.conditions[ind]["data"]) == 0: # if data hasn't yet been loaded
                logic.getData(ind) # dont check for complex because it can only be indicator
            if ind not in self.selected: # if the button wasn't already selected
                self.selected.append(ind)
            else: # if button has already been selected; remove from list
                self.selected.remove(ind)
            self.multiMark()
            if len(self.selected) == 0: self.resetGeneral(1) # if nothing is selected anymore; reset
            else: self.multiShow() # update side window
            self.setScene()
        else: # default condition dialog
            self.conditionDialog(ind) 

    def selectButton(self, event, ind=0): # pass method to check whether ctrl is pressed before
        if event.modifiers().name == "ControlModifier": # reverse activation of marking
            pass # maybe add reverse activation here
        else: # remove selected indicator from list
            self.selected.remove(ind) # remove index from selected list
            self.multiMark() # change what is marked
            if len(self.selected) == 0: self.resetGeneral(1) # if nothing is selected anymore; reset
            else: self.multiShow() # update side window
            self.setScene()

    def conditionDialog(self, ind=False): # Dialogbox for viewing conditions
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
        self.dialog.setFixedSize(400, 300)
        self.dialog.setWindowTitle("Add a Condition/Indicator...")
        if type(ind) == int: # if an indicator is being changed
            self.dialog.setWindowTitle("Change Condition/Indicator...")
        self.dialog.setLayout(QtWidgets.QVBoxLayout())
        self.conditionLayout(ind, True) # set layout to custom function so it changes with whatever is selected
        self.dialog.exec()

    def conditionLayout(self, ind=False, first=False): # to change the appearing inputs with whatever is selected
        if not first: # If the layout is not being defined for the first time
            current = self.inputs[0].currentText()
        else: 
            if type(ind) == int: current = logic.indicators[ind]["condVars"][0]
            else: current = avconds[0] # default is condition at spot 0
        wid = QtWidgets.QWidget()
        lab = QtWidgets.QLabel("Indicator", wid)
        lab.move(5, 5)
        self.inputs[0] = QtWidgets.QComboBox(wid)
        for c in avconds:
            self.inputs[0].addItem(c)
        self.inputs[0].setGeometry(60, 2, 120, 22)
        if first: 
            if type(ind) == int: self.inputs[0].setCurrentText(current)
        else:
            self.inputs[0].setCurrentText(current) # set current selected to last selected
        self.inputs[0].currentTextChanged.connect(lambda: self.conditionLayout(ind)) # connect text change to self
        args = ["ma", "k", "width"] # args available 
        found = [False, False, False]
        text = ["ma", "k", "width"] # text shown
        inps = [200, 2, 10, "", "0", ""] # default args
        for item in neededArgs[current]:
            if args.index(item[0]) != -1: # if an argument was found
                found[args.index(item[0])] = True
                text[text.index(item[0])] = item[1] # Label
                inps[args.index(item[0])] = item[2] # Default Value
        
        if first and type(ind) == int: # copy operator
            inps[3] = logic.indicators[ind]["condVars"][5]
            if inps[3] != "":
                inps[3] = "Use " + inps[3] # add use if operator was used

        if first and type(ind) == int: # copy spot
            inps[4] = str(logic.indicators[ind]["condVars"][1])
        elif not first:
            inps[4] = self.inputs[1][4].text() # copy current spot

        if first and type(ind) == int: # copy spot
            inps[5] = "Trigger when " + str(logic.conditions[ind]["trigger"])

        dummy = QtWidgets.QWidget()
        self.inputs[1] = []

        if found[0]: 
            use = wid # if it was found, add to main widget
        else: 
            use = dummy # else add to dummy, so it doesn't appear on main
        lab2 = QtWidgets.QLabel(text[0], use)
        self.inputs[1].append(QtWidgets.QLineEdit(use))

        if found[1]: use = wid
        else: use = dummy
        lab3 = QtWidgets.QLabel(text[1], use)
        self.inputs[1].append(QtWidgets.QLineEdit(use))

        if found[2]: use = wid
        else: use = dummy
        lab4 = QtWidgets.QLabel(text[2], use)
        self.inputs[1].append(QtWidgets.QLineEdit(use))

        lab2.move(5, 70)
        self.inputs[1][0].setText(str(inps[0])) # ma
        self.inputs[1][0].setGeometry(5, 85, 35, 22)
        lab3.move(5, 110)
        self.inputs[1][1].setText(str(inps[1])) # k
        self.inputs[1][1].setGeometry(5, 125, 35, 22)
        lab4.move(5, 150)
        self.inputs[1][2].setText(str(inps[2])) # width
        self.inputs[1][2].setGeometry(5, 165, 35, 22)

        self.inputs[1].append(QtWidgets.QComboBox(wid)) # Operators
        items = ["Don't use different operator", "Use =", "Use ≈", "Use <", "Use <=", "Use >", "Use >="]
        self.inputs[1][3].addItems(items)
        self.inputs[1][3].move(180, 2)
        if inps[3] != "":
            self.inputs[1][3].setCurrentText(inps[3])
        
        lab5 = QtWidgets.QLabel("Look x behind", wid) # spot
        lab5.move(5, 30)
        self.inputs[1].append(QtWidgets.QLineEdit(inps[4], wid))
        self.inputs[1][4].setGeometry(5, 45, 35, 22)

        self.inputs[1].append(QtWidgets.QComboBox(wid))
        items = ["Trigger when true", "Trigger when first true", "Trigger when last true", "Trigger when near"]
        self.inputs[1][5].addItems(items)
        self.inputs[1][5].move(5, 250)
        if inps[5] != "": self.inputs[1][5].setCurrentText(inps[5])

        if first and type(ind) == int: # adapt text to what the variables were set to
            for i in range(3): self.inputs[1][i].setText(str(logic.indicators[ind]["condVars"][2+i]))

        for i in range(3): # if input is unused, set none
            if not found[i]: self.inputs[1][i] = None

        should = [False, True] # checkbox states
        if first and type(ind) == int:
            should[1] = logic.indicators[ind]["show"]
        elif not first:
            should[0] = self.inputs[2][0].isChecked()
            should[1] = self.inputs[2][1].isChecked()

        self.inputs[2] = []
        self.inputs[2].append(QtWidgets.QCheckBox("Mark True Spots", wid))
        self.inputs[2][0].move(185, 250)
        self.inputs[2][0].setChecked(should[0])
        self.inputs[2].append(QtWidgets.QCheckBox("Show Indicator", wid))
        self.inputs[2][1].move(295, 250)
        self.inputs[2][1].setChecked(should[1])

        if first: color = "background-color: %s;" % QtGui.QColor(randint(0, 255), randint(0, 255), randint(0, 255)).name() # rng color
        else: color = self.inputs[3].styleSheet() # dont always regenerate color
        self.inputs[3] = QtWidgets.QPushButton(wid)
        self.inputs[3].setGeometry(380, 5, 20, 20)
        self.inputs[3].setStyleSheet(color)

        if first and type(ind) == int: self.inputs[3].setStyleSheet("background-color: %s;" % logic.indicators[ind]["color"]) # preset color

        self.inputs[3].clicked.connect(self.pickColor)

        view = QtWidgets.QGraphicsView(wid)
        view.setGeometry(90, 35, 280, 200)

        btn = QtWidgets.QPushButton()
        btn.setText("OK")
        btn.setFocus()
        btn.clicked.connect(lambda: self.conditionExecute(self.dialog, ind))
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

    def conditionExecute(self, parent, ind=False): # mark spots that the condition is true for
        graphs = ["movavg", "expavg", "bollinger", "vwap"] # indicators based on graphs
        spots = ["contested"] # indicators based on special spots

        def isType(thing, typ): # pass thing and check if it's the type
            if typ == str: return True
            elif typ == int: return isint(thing)
            elif typ == float: return isfloat(thing)

        # Error prevention
        if len(neededArgs[self.inputs[0].currentText()]) != 0: # if arguments can be given
            for c in argRanges[self.inputs[0].currentText()]: # c = (key, type, min, max)
                # switch key
                if c[0] == "ma": key = self.inputs[1][0].text()
                elif c[0] == "k": key = self.inputs[1][1].text()
                elif c[0] == "width": key = self.inputs[1][2].text()

                if not isType(key, c[1]): 
                    self.errormsg(key + " is not of type " + str(c[1]).split("\'")[1] + ".")
                    return
                
                if c[1](key) < c[2]:
                    self.errormsg(key + " is out of range.")
                    return
                
                maxx = c[3]
                if maxx == "nan": maxx = len(raw[logic.rawind])-1 # nan means len(stock)
                if c[1](key) > maxx:
                    self.errormsg(key + " is out of range.")
                    return

        if not isint(self.inputs[1][4].text()):
            self.errormsg(self.inputs[1][4].text() + " is not a valid number.")
            return
        elif int(self.inputs[1][4].text()) < 0:
            self.errormsg("Future error; " + self.inputs[1][4].text() + " can't be computed.")
            return

        time = 0

        # get inputs
        old = None
        cold = None
        if type(ind) == int: # if it modified an old indicator; replace in list
            idd = logic.indicators[ind]["ID"]
            old = []
            for i in range(len(logic.indicators)): # find out how many and where
                if logic.indicators[i]["ID"] == idd: old.append(i)
            old.reverse()
            for o in range(len(old)-1): # pop all but one
                logic.indicators.pop(o)
            old = old[0] # from one length list to int

            # same for condition
            cold = []
            for i in range(len(logic.conditions)): # find out how many and where
                if logic.conditions[i]["indID"] == idd: # find condition based on indicator
                    cold.append(i)
            cold.reverse()
            for o in range(len(cold)-1): # pop all but one
                logic.conditions.pop(o)
            cold = cold[0] # from one length list to int
            cidd = logic.conditions[cold]["ID"] # get condition id

        inps = [200, 2, 10, "", 0, ""] # defaults

        if "35" in self.inputs[0].currentText(): # accept float for 35
            for i in range(len(self.inputs[1])):
                if self.inputs[1][i] is not None: 
                    if i == 4: inps[i] = int(self.inputs[1][4].text()) # use int for index
                    elif i == 3: 
                        if "Use" in self.inputs[1][3].currentText():
                            inps[3] = self.inputs[1][3].currentText().split(" ")[1]
                    elif i == 5:
                        if "Trigger when " in self.inputs[1][5].currentText():
                            inps[5] = self.inputs[1][5].currentText().split("Trigger when ")[1]
                    else: inps[i] = float(self.inputs[1][i].text()) # if input exists, get text
                    
        else: # else only use int
            for i in range(len(self.inputs[1])):
                if self.inputs[1][i] is not None: 
                    if i < 3 or i == 4: inps[i] = int(self.inputs[1][i].text()) # if input exists, get text
                    elif i == 5:
                        if "Trigger when " in self.inputs[1][5].currentText():
                            inps[5] = self.inputs[1][5].currentText().split("Trigger when ")[1]
                    else: 
                        if "Use" in self.inputs[1][3].currentText():
                            inps[3] = self.inputs[1][3].currentText().split(" ")[1]

        # Marking and gathering data
        data = []
        if self.inputs[2][0].isChecked(): # if it should mark spots
            self.marked = []
            data = logic.getCondition(self.inputs[0].currentText(), inps)
            for d in data:
                if d: self.marked.append("#40ff7700")
                else: self.marked.append(None)

        t = len(raw[logic.rawind])-1
        time = 0
        pre = []
        for i in range(inps[4]):
            pre.append(float("nan"))
        ind = condition(logic.rawind, self.inputs[0].currentText(), t-inps[4], inps[0], inps[1], inps[2], inps[3], doReturn=True, time=time)

        nested = any(isinstance(i, list) for i in ind)

        self.mode.setCurrentText("Conditions/Indicators")

        end = False
        dMode = 0
        if ind is not None:
            for g in graphs: # check which one of the graphs it is
                if g in self.inputs[0].currentText(): dMode = 1
            if not end: # check for spots
                if self.inputs[0].currentText() in spots: dMode = 2
                elif self.inputs[0].currentText() == "volume": dMode = 3
            
            if old is None: # if a new id is needed
                # add to indicators
                idd = 0
                cidd = 0

                i = 0
                while i < len(logic.indicators): # check if id is already in use
                    if logic.indicators[i]["ID"] == idd:
                        idd += 1
                        i = -1 # if id in use go up and restart process
                    i += 1
                i = 0

                while i < len(logic.conditions): # check if id is already in use
                    if logic.conditions[i]["ID"] == cidd:
                        cidd += 1
                        i = -1 # if id in use go up and restart process
                    i += 1
            
            if not nested:
                ind = [ind] # make nested list in case of simple list
            else: # reform all tuples etc to nested list
                l = []
                for i in ind:
                    l.append(i)
                ind = l
            if dMode == 1:
                for i in range(len(ind)):
                    ind[i] = pre + ind[i] # append pre to itself if a prvious spot is looked at
            conds = [self.inputs[0].currentText(), inps[4], inps[0], inps[1], inps[2], inps[3]]
            color = self.inputs[3].styleSheet().split(" ")[1][:-1] # color in hex
            indict = {"ID":idd, "condVars":conds, "dMode":dMode, "data":ind, "color":color, "show":self.inputs[2][1].isChecked()}
            condict = {"ID":cidd, "indID":idd, "act":0, "trigger":inps[5], "data":data, "deps":[]}
            if old is None: 
                logic.indicators.append(indict) # all of the info necessary for an indicator
                logic.conditions.append(condict)
            else: # if old indicator/condition is changed
                logic.indicators[old] = indict # replace old indicator
                logic.conditions[cold] = condict

                for s in logic.strategies: # check if changed condition is in a strategy
                    for c in s["conds"]:
                        if c[1] == cidd: # if condition in strategy
                            for cond in s["conds"]:
                                logic.conditions[logic.find("c", cond[1])]["data"] = [] # empty all data for strategy
                            break

            # if it should update strategies and not mark
            if self.prefs[self.findPref("Recalculate strategies after editing conditions")][1] and not self.inputs[2][0].isChecked():
                for s in logic.strategies:
                    edit = False
                    for c in s["conds"]:
                        if c[1] == cidd: edit = True
                    if edit: # if a strategy was indirectly edited
                        self.calcStrategy(s["ID"])

        self.setScene()
        parent.close()

    def seekConditions(self): # look for contitions that apply to selected spots only 
        self.processes.append(BackProcess(logic.seekConditions, "condseeker"))
        self.processes[-1].args = (deepcopy(self.spots), deepcopy(raw[logic.rawind]))
        self.processes[-1].start()
        procManager.register("condseeker")
        procManager.setCurrent("condseeker")
        self.displayStats()

    def strategyDialog(self, ind=False): # dialog box for running strategies
        if self.tabs.tabText(self.tabs.currentIndex()) == "+": 
            self.errormsg("Please load a stock first.")
            return
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Add a Strategy...")
        dbox.setFixedSize(280, 300)
        lab1 = QtWidgets.QLabel("Conditions", dbox)
        lab1.move(170, 5)
        lab1 = QtWidgets.QLabel("Strategy", dbox)
        lab1.move(25, 5)

        self.inputs[3] = [] # set 3 to blank to prevent errors

        self.inputs[0] = StratList(dbox)
        self.inputs[0].setFn(self.connectDialog, self.delCondition) # connect, delete
        self.inputs[0].setGeometry(25, 25, 75, 155)

        self.inputs[1] = QtWidgets.QListWidget(dbox)
        self.inputs[1].setGeometry(170, 25, 75, 155)

        used = [] # used indicator conditions
        # l is text for list objects
        if type(ind) == int: # if previous strategy is edited
            for c in logic.strategies[ind]["conds"]:
                if logic.find("c", c[1]) is None: # if a condition doesn't exist anymore
                    self.errormsg("Strategy can't be loaded; Condition is missing.")
                    return
                if c[0] == "ci": used.append(c[1]) # if an indiactor condition is used; 
                if logic.conditions[logic.find("c", c[1])]["indID"] == -1: # for complex condition
                    l = str(logic.conditions[logic.find("c", c[1])]["ID"]) + " " + logic.conditions[logic.find("c", c[1])]["deps"][1] # ID + operator for cc
                    self.inputs[0].addItem(ListItem(l, c[1], typ="cc"))
                else: # indicator condition
                    l = str(logic.conditions[logic.find("c", c[1])]["ID"]) + " "
                    l += logic.indicators[logic.find("i", logic.conditions[logic.find("c", c[1])]["indID"])]["condVars"][0] # append indicator condition to strategy list
                    self.inputs[0].addItem(ListItem(l, c[1]))
            for i in logic.indicators:
                temp = logic.conditions[logic.find("ci", i["ID"])]["ID"] # id of condition that uses indicator
                if not temp in used:
                    l = str(temp) + " " + i["condVars"][0] # append condition with indicator to available list
                    self.inputs[1].addItem(ListItem(l, temp))
            if len(logic.strategies[ind]["risk"]) != 0: # if risk has been changed
                for i in range(len(logic.strategies[ind]["risk"])):
                    if i != 1: # not combobox
                        if i == 2 or i == 4: # trail perc or fees
                            self.inputs[3].append(QtWidgets.QLineEdit(str(int(100*logic.strategies[ind]["risk"][i]))))
                        else:
                            self.inputs[3].append(QtWidgets.QLineEdit(str(int(logic.strategies[ind]["risk"][i]))))
                    else: 
                        outs = ["Trailing Stop"] # what the user sees
                        ins = ["trailing"] # what the program uses
                        self.inputs[3].append(QtWidgets.QComboBox())
                        self.inputs[3][i].addItem(outs[ins.index(logic.strategies[ind]["risk"][i])]) # add converted stop type to combobox
        else: # new strategy
            if len(self.selected) != 0: # if conditions have already been selected
                temp = []
                for s in self.selected: # add all selected conditons to left list
                    l = str(logic.conditions[s]["ID"]) + " "
                    indx = logic.find("i", logic.conditions[s]["indID"])
                    temp.append(logic.indicators[indx]["ID"]) # save id
                    l += str(logic.indicators[indx]["condVars"][0])
                    self.inputs[0].addItem(ListItem(l, logic.conditions[s]["ID"]))
                for i in logic.indicators:
                    if i["ID"] not in temp: # if id has not been used yet
                        l = str(logic.conditions[logic.find("ci", i["ID"])]["ID"]) + " " + i["condVars"][0] # append condition with indicator to list
                        self.inputs[1].addItem(ListItem(l, logic.conditions[logic.find("ci", i["ID"])]["ID"]))
            else:
                for i in logic.indicators:
                    l = str(logic.conditions[logic.find("ci", i["ID"])]["ID"]) + " " + i["condVars"][0] # append condition with indicator to list
                    self.inputs[1].addItem(ListItem(l, logic.conditions[logic.find("ci", i["ID"])]["ID"]))
        # self.inputs[1].addItems(l)

        self.inputs[2] = []
        self.inputs[2].append(QtWidgets.QCheckBox("Mark True Spots", dbox))
        self.inputs[2][0].move(145, 188)
        self.inputs[2][0].setChecked(True)
        self.inputs[2].append(QtWidgets.QCheckBox("Debug Mode", dbox))
        self.inputs[2][1].move(145, 217)
        self.inputs[2][1].setChecked(False)
        btn = QtWidgets.QPushButton("←", dbox)
        btn.setGeometry(122, 45, 26, 26)
        btn.clicked.connect(lambda: self.moveCondition("add"))
        btn2 = QtWidgets.QPushButton("→", dbox)
        btn2.setGeometry(122, 125, 26, 26)
        btn2.clicked.connect(lambda: self.moveCondition("remove"))
        btn3 = QtWidgets.QPushButton("OK", dbox)
        btn3.move(100, 265)
        btn3.clicked.connect(lambda: self.strategyExecute(dbox, ind))
        btn4 = QtWidgets.QPushButton("Tree View", dbox)
        btn4.move(25, 185)
        btn4.clicked.connect(lambda: self.treeView(dbox))
        btn5 = QtWidgets.QPushButton("Risk Mgmt.", dbox)
        btn5.move(25, 214)
        btn5.clicked.connect(lambda: self.riskDialog(dbox))
        dbox.exec()

    def treeView(self, parent=None): # view strategy as tree in seperate dbox
        dbox = QtWidgets.QDialog(parent)
        dbox.setWindowTitle("Strategy Tree View")
        dbox.setFixedSize(300, 250)
        tree = QtWidgets.QTreeWidget(dbox)
        tree.setGeometry(10, 10, 280, 230)

        # add tree containing all of the conditions and how they're linked
        items = self.inputs[0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
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
            if logic.conditions[indx]["indID"] == -1: # change how text is gotten based on condition
                l = str(logic.conditions[indx]["ID"]) + " " + logic.conditions[indx]["deps"][1]
            else:
                l = str(logic.conditions[indx]["ID"]) + " " + logic.indicators[logic.find("i", logic.conditions[indx]["indID"])]["condVars"][0]
            a = QtWidgets.QTreeWidgetItem(parent, [l]) # make entry on parent branch and save new branch point as a
            if twig[0][0] == "cc":
                # add new branch for cc
                if logic.conditions[indx]["deps"][1] == "not":
                    # only use deps[0]
                    indx = logic.find("c", logic.conditions[indx]["deps"][0][1]) # change indx just for checking
                    if indx is None: # no id was found
                        self.errormsg("Condition " + str(twig[0][1]) + " can't be processed because of missing subcondition.")
                        return
                    if logic.conditions[indx]["indID"] == -1: typ = "cc"
                    else: typ = "ci"
                    twig[1].append([(typ, logic.conditions[indx]["ID"]), []]) # add new to treelist
                    branch(twig[1][-1], a) # continue branch from here
                else:
                    indx = [logic.find("c", logic.conditions[indx]["deps"][0][1]), logic.find("c", logic.conditions[indx]["deps"][2][1])]
                    for j in range(2):
                        if indx[j] is None:
                            self.errormsg("Condition " + str(twig[0][1]) + " can't be processed because of missing subcondition.")
                            return
                        if logic.conditions[indx[j]]["indID"] == -1: typ = "cc"
                        else: typ = "ci"
                        twig[1].append([(typ, logic.conditions[indx[j]]["ID"]), []]) # add new to treelist
                        branch(twig[1][-1], a) # continue branch from here

        for t in treelist: branch(t, tree) # make fully filled treelist

        dbox.exec()

    def riskDialog(self, parent): # dialog for risk management
        dbox = QtWidgets.QDialog(parent)
        dbox.setFixedSize(300, 200)
        dbox.setWindowTitle("Risk Management")
        # use 3 because all others are already in use
        risk = None
        if len(self.inputs[3]) != 0: # if risk management has already been changed
            risk = []
            for i in range(len(self.inputs[3])): 
                if i != 1: risk.append(self.inputs[3][i].text())
                else: risk.append(self.inputs[3][i].currentText()) # current text for combobox
        self.inputs[3] = []
        lab = QtWidgets.QLabel("Balance in $", dbox)
        lab.move(10, 10)
        self.inputs[3].append(QtWidgets.QLineEdit("10000", dbox))
        self.inputs[3][0].setGeometry(125, 10, 50, 22)
        lab = QtWidgets.QLabel("Order Type", dbox)
        lab.move(10, 35)
        self.inputs[3].append(QtWidgets.QComboBox(dbox))
        self.inputs[3][1].addItems(["Trailing Stop"])
        self.inputs[3][1].setGeometry(125, 35, 85, 22)
        lab = QtWidgets.QLabel("Trailing Perc. in %", dbox)
        lab.move(10, 60)
        self.inputs[3].append(QtWidgets.QLineEdit("1", dbox))
        self.inputs[3][2].setGeometry(125, 60, 50, 22)
        lab = QtWidgets.QLabel("$ per Order", dbox)
        lab.move(10, 85)
        self.inputs[3].append(QtWidgets.QLineEdit("200", dbox))
        self.inputs[3][3].setGeometry(125, 85, 50, 22)
        lab = QtWidgets.QLabel("Fees per Trade in %", dbox)
        lab.move(10, 110)
        self.inputs[3].append(QtWidgets.QLineEdit("0", dbox))
        self.inputs[3][4].setGeometry(125, 110, 50, 22)

        if risk is not None:
            for i in range(len(risk)): 
                if i != 1: self.inputs[3][i].setText(risk[i])
                else: self.inputs[3][i].setCurrentText(risk[i]) # current text for combobox

        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(110, 170)
        btn.clicked.connect(dbox.close)
        dbox.show()

    def moveCondition(self, direction): # move conditions between boxes
        if direction == "add":
            item = self.inputs[1].currentItem()
            self.inputs[1].takeItem(self.inputs[1].row(item))
            self.inputs[0].addItem(item)
        elif direction == "remove":
            item = self.inputs[0].currentItem()
            self.inputs[0].takeItem(self.inputs[0].row(item))
            self.inputs[1].addItem(item)

    def strategyExecute(self, parent, indx=False): # ok button | adds strategy to list
        self.mode.setCurrentText("Strategies")

        # error code
        errd = False
        if len(self.inputs[3]) != 0: # risk management has been loaded
            for i in range(len(self.inputs[3])):
                if i != 1: # not combobox which has to be string
                    if i == 2 or i == 4:
                        if not isfloat(self.inputs[3][i].text()): errd = True
                    else: # check whether correct numbers were passed through
                        if not isint(self.inputs[3][i].text()): errd = True
            if errd:
                self.errormsg("Invalid risk management number type.")
                return
            
            # balance
            bal = int(self.inputs[3][0].text())
            if bal < 0:
                self.errormsg("Balance must be at least 0.")
                return
            
            # trail perc
            num = float(self.inputs[3][2].text())
            if num < 0 or num > 100: 
                self.errormsg("Trailing percentage must be within the range of [0;100]")
                return
            
            # $ per order
            num = int(self.inputs[3][3].text())
            if num < 0 or num > bal:
                self.errormsg("Money per order is out of range.")
                return
            
            # fees
            num = float(self.inputs[3][4].text())
            if num < 0 or num > 100:
                self.errormsg("Fees must be within the range of [0; 100]")
                return

        self.stopButton() # stop all threads to prepare for new strategy

        conds = [] # what determines the activation of the strategy
        items = self.inputs[0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
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
        
        risk = []
        if len(self.inputs[3]) == 3 and type(self.inputs[3][0]) == QtWidgets.QComboBox: self.inputs[3] = [] # reset if connect box was used last
        if len(self.inputs[3]) != 0: # if risk management has been edited
            for i in range(len(self.inputs[3])): 
                if i != 1: risk.append(int(self.inputs[3][i].text())) # all entered things are integers
                else: risk.append(self.inputs[3][i].currentText()) # current text for combobox

            # percent to absolute number
            risk[2] /= 100 # trail percentage
            risk[4] /= 100 # fees

            ins = ["Trailing Stop"] # what the user sees
            outs = ["trailing"] # what the program uses
            risk[1] = outs[ins.index(risk[1])] # convert from ins to outs

        idd = 0
        if type(indx) == int: idd = logic.strategies[indx]["ID"] # to replace older strategy
        else:
            i = 0
            while i < len(logic.strategies): # check if id is already in use
                if logic.strategies[i]["ID"] == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1

        strict = {"ID":idd, "conds":conds, "data":data, "show":True, "calc":calc, "risk":risk}
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
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open strategy file", "", "Text files (*.txt)")[0] # get filename
        if filename == "": return # if now file was selected
        lines = open(filename).readlines() # get lines of file
        if lines[0][0] != "{": # if file doesn't start with "{"
            self.errormsg("Invalid or empty file.")
            return
        self.mode.setCurrentText("Strategies")
        # dictionaries
        indict = {}
        condict = {}
        strict = {}
        # lists
        tups = []
        ins = []
        cons = []
        strats = []
        currcons = []
        # bools
        count = -1 # counts the number of commas to set variables
        string = "" # sting that stores read data
        riskread = False
        for line in lines:
            for char in line: # for each character
                if char == '{':
                    string = "" # clear any \n that might occur
                    currcons = []
                    strict = {"ID":-1, "conds":[], "data":[], "show":True, "calc":[], "risk":[]}
                elif char == ',':
                    if riskread:
                        if count == 0:
                            if string == "cc": condict["indID"] = -1 # set condict to complex condition
                        elif count == 1: condict["ID"] = int(string)
                        elif condict["indID"] == -1: # if complex condition
                            # 2 type, 3 id, 4 logic, 5 type, 6 id
                            if count != 4: # not the logic operator
                                if count % 3 == 0: # if id is currently handled
                                    tups.append(int(string))
                                else: tups.append(string) # type
                            else: condict["deps"].append(string) # append logic directly to deps
                        elif count == 2: # from here on no more complex condition
                            condict["indID"] = int(string) # indicator id
                            indict["ID"] = int(string)
                            tups = [] # reuse tups list for condVars
                        else:
                            # 3 indicator, 4 spot, 5 ma, 6 k, 7 width, 8 operator
                            if count in [3, 8]: tups.append(string) # if string not a number
                            else:
                                if isint(string): tups.append(int(string))
                                else: tups.append(float(string)) # also support float
                    else:
                        if count != 1: tups.append(float(string)) # everything else
                        else: tups.append(string) # stop type
                    string = ""
                    count += 1
                elif char == '|':
                    if condict["indID"] != -1: # indicator condition
                        indict["color"] = string # save color
                        indict["condVars"] = deepcopy(tups)
                        string = ""
                elif char == '(':
                    if count == -1: # if first parenthesis
                        strict["ID"] = int(string) # get strategy id
                        string = ""
                    count = 0
                    if riskread:
                        indict = {"ID":-1, "condVars":[], "dMode":-1, "data":[], "color":"", "show":False}
                        condict = {"ID":-1, "indID":-2, "act":0, "trigger":"", "data":[], "deps":[]}
                elif char == ')':
                    if riskread:
                        condict["trigger"] = string # at the end trigger will be in string
                        string = ""
                        cons.append(condict) # append condition to cons
                        currcons.append(condict) # get conditions
                        if condict["indID"] != -1: ins.append(indict) # if given append indicator to ins
                    else: 
                        riskread = True # after risk has been read go to other code
                        strict["risk"] = deepcopy(tups)
                        tups = []
                elif char == '[':
                    tups = []
                elif char == ']':
                    condict["deps"].append((tups[0], tups[1])) # append list converted to tuple to deps
                elif char == '}':
                    tups = []
                    for c in currcons: # for each read condition in strategy
                        if c["indID"] == -1: string = "cc"
                        else: string = "ci"
                        tups.append((string, c["ID"])) # get list of dependent conditions
                    strict["conds"] = deepcopy(tups)
                    strats.append(strict)
                else: string += char
        # processing the now loaded data
        linked = [] # every condition with it's indicator (if it exists)
        poplist = []
        for c in cons: # for every condition in every strategy
            if c["indID"] == -1: # complex condition
                tup = [c["ID"]]
            else: tup = [c["ID"], c["indID"]] # indicator condition
            if tup in linked: # if condition appears twice
                poplist.append(cons.index(c))
            else: linked.append(deepcopy(tup))

        # remove multiple appearíng conditions/indicators
        for p in poplist:
            ind = -1
            if cons[p]["indID"] != -1:
                for i in ins:
                    if i["ID"] == cons[p]["indID"]: ind = ins.index(i) # get index of corresponding indicator with same id
                ins.pop(ind) # remove indicator
            cons.pop(p) # remove condition
        
        # get new ids
        # indicator ids
        ids = []
        for i in logic.indicators:
            ids.append(i["ID"]) # add all loaded ids to list
        for l in linked:
            if len(l) == 2: # if ci
                old = l[1] # keep old id
                while l[1] in ids: # get new id
                    l[1] += 1
                ids.append(l[1]) # save new id to register
                # change id to copies of l to prevent having all ids shift
                for ind in ins:
                    if ind["ID"] == old: ind["ID"] = deepcopy(l) # change id of indicator
                for c in cons:
                    if c["indID"] == old: c["indID"] = deepcopy(l) # change id of indicator of complex condition
        
        # replace placeholder lists with integers
        for i in ins:
            if type(i["ID"]) == list: i["ID"] = i["ID"][1]
        for c in cons:
            if type(c["indID"]) == list: c["indID"] = c["indID"][1]
        
        # condition ids
        ids = []
        for c in logic.conditions:
            ids.append(c["ID"])
        for l in linked:
            old = l[0]
            while l[0] in ids: # get new id
                l[0] += 1
            ids.append(l[0])
            for c in cons:
                if c["ID"] == old: c["ID"] = deepcopy(l) # condition id
                elif c["indID"] == -1: # if cc
                    for d in range(len(c["deps"])):
                        if d != 1: # not logic operator
                            if c["deps"][d][1] == old: c["deps"][d] = (c["deps"][d][0], deepcopy(l)) # dependency id
            for s in strats:
                for c in range(len(s["conds"])):
                    if s["conds"][c][1] == old: s["conds"][c] = (s["conds"][c][0], deepcopy(l)) # strategy condition id
        
        # replace placeholders
        for c in cons:
            if type(c["ID"]) == list: c["ID"] = c["ID"][0]
            if c["indID"] == -1: # cc
                for d in range(len(c["deps"])):
                    if d != 1: # not operator
                        if type(c["deps"][d][1]) == list: 
                            c["deps"][d] = (c["deps"][d][0], c["deps"][d][1][0]) # because tuples can't be overwritten
        for s in strats:
            for c in range(len(s["conds"])):
                if type(s["conds"][c][1]) == list:
                    s["conds"][c] = (s["conds"][c][0], s["conds"][c][1][0])
        
        # strategy ids
        ids = []
        for s in logic.strategies:
            ids.append(s["ID"])
        for s in strats:
            old = s["ID"]
            while s["ID"] in ids:
                s["ID"] += 1
            ids.append(s["ID"])
        # no replacement needed because strats are only looked through once

        # add all dictionaries to variables
        for i in ins:
            logic.indicators.append(i)
        for c in cons:
            logic.conditions.append(c)
        for s in strats:
            logic.strategies.append(s)
        
        self.setScene()

    def delCondition(self, item): # delete unbound complex condition given the item
        self.inputs[0].takeItem(self.inputs[0].row(item)) # take item out of list
        logic.conditions.pop(logic.find("c", item.idd)) # pop item out of conditions

    def connectDialog(self, item): # dialog for connecting / editing conditions
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Connect...")
        dbox.setFixedSize(150, 125)

        lab1 = QtWidgets.QLabel("Connect", dbox)
        lab1.move(8, 10)
        lab2 = QtWidgets.QLabel("To", dbox)
        lab2.move(8, 60)

        conds = [] 
        items = self.inputs[0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
        for i in items:
            conds.append(i.text()) # if condition ("c", condID)

        self.inputs[3] = []
        for i in range(2):
            self.inputs[3].append(QtWidgets.QComboBox(dbox))
            self.inputs[3][i].setGeometry(65, 7+50*i, 75, 22)
            self.inputs[3][i].addItems(conds)
        self.inputs[3][0].setCurrentText(item.text())

        self.inputs[3].append(QtWidgets.QComboBox(dbox))
        self.inputs[3][2].setGeometry(65, 32, 75, 22)
        self.inputs[3][2].addItems(["Not", "And", "Or", "Xor"])

        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(37, 90)
        btn.clicked.connect(lambda: self.connectExec(dbox))

        dbox.exec()

    def connectExec(self, parent):
        # hide original conditions from calculation and only calc new connected one
        conds = [] 
        items = self.inputs[0].findItems("", QtCore.Qt.MatchFlag.MatchContains)
        for i in items:
            conds.append(i.text()) # if condition ("c", condID)
        indx = [conds.index(self.inputs[3][0].currentText())] # get indexes of selected items
        indx.append(conds.index(self.inputs[3][1].currentText()))

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
        if logic.conditions[logic.find("c", idd)]["indID"] == -1: deps.append(("cc", idd)) # if condition is dependent; append cc (complex condition)
        else: deps.append(("ci", idd)) # else append ci (condition indicator)
        deps.append(self.inputs[3][2].currentText().lower())

        if self.inputs[3][2].currentText() != "Not": # if not only exclude the first one and add new condition
            logic.conditions[logic.find("c", items[indx[1]].idd)]["calc"] = False # else also disable second one
            if logic.conditions[logic.find("c", items[indx[1]].idd)]["indID"] == -1: deps.append(("cc", items[indx[1]].idd)) # if condition is dependent; append cc (complex condition)
            else: deps.append(("ci", items[indx[1]].idd)) # else append ci (condition indicator)
        condict = {"ID":cidd, "indID":-1, "act":0, "trigger":"true", "data":[], "deps":deps}
        logic.conditions.append(condict)
        self.inputs[0].addItem(ListItem(str(cidd) + " " + self.inputs[3][2].currentText().lower(), cidd, typ="cc")) # add item to strategy condition list
        self.inputs[3] = [] # empty input list
        parent.close()

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
            color = logic.indicators[logic.find("i", logic.conditions[s]["indID"])]["color"]
            data = logic.conditions[s]["data"]
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

    def deleteButton(self, idd, typ="conds"): # deletes the button
        poplist = []
        if typ == "conds":
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

            for i in range(len(logic.indicators)):
                if logic.indicators[i]["ID"] == idd: # if indicator has said id
                    poplist.append(i)
            
            poplist.reverse() # pop in reverse
            for p in poplist:
                logic.indicators.pop(p)
            
            poplist = []

            for i in range(len(logic.conditions)):
                if logic.conditions[i]["indID"] == idd: # if indicator has said id
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
        
        if self.debugvar[1] + 1 >= len(stocks): return # if every stock has been read
        self.debugvar[1] += 1
        self.debugvar[3] = True
        self.readstocks(str(self.debugvar[1]), "debug") # load new data

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

        wid = QtWidgets.QWidget() # stats
        wid.setStyleSheet(widgetstring)
        self.sideStats.reset()
        self.sideStats.strings.append("Money: " + str(round(logic.stats.money, 2)) + "$")
        self.sideStats.strings.append("Number Marked: " + str(n))
        self.sideStats.display(wid)
        self.docks[1].setWidget(wid)

        self.backtest(self.debugvar[2])
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
        self.setScene()
        self.view.setGeometry(25, 25, 725, 525)
        #self.view.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.BlankCursor))
        self.view.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.view.horizontalScrollBar().valueChanged.connect(self.whenchangedx)
        self.view.verticalScrollBar().valueChanged.connect(self.whenchangedy)

        # y axis that will show price
        yaxis = QtWidgets.QGraphicsScene(self)
        yaxis.setSceneRect(0, 0, 25, 525)
        self.yview = Axis(yaxis, self)
        self.yview.setGeometry(750, 25, 25, 525)
        self.yview.setFixedWidth(35)
        self.yview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.yview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.yview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding)
        self.yview.setMouseFn(lambda: self.gridBox("y"))

        # x axis that will show time
        xaxis = QtWidgets.QGraphicsScene(self)
        xaxis.setSceneRect(0, 0, 725, 25)
        self.xview = Axis(xaxis, self)
        self.xview.setGeometry(25, 550, 725, 25)
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
                        col = QtGui.QColor(QtCore.Qt.GlobalColor.black)
                    else:
                        lastdat = self.timeaxis[lastdat].to_pydatetime() # else get date of said index
                        if dat.year > lastdat.year: # year changed
                            val = dat.year
                            col = QtGui.QColor(QtCore.Qt.GlobalColor.black)
                        elif dat.month > lastdat.month: # month changed
                            val = shorts[dat.month-1]
                            col = QtGui.QColor(QtCore.Qt.GlobalColor.black)
                        elif dat.day > lastdat.day: # day changed
                            val = str(dat.day)
                            col = QtGui.QColor(QtCore.Qt.GlobalColor.darkGray)
                            if int(val)%10 == 1 and val != "11": val += "st"
                            elif int(val)%10 == 2 and val != "12": val += "nd"
                            elif int(val)%10 == 3 and val != "13": val += "rd"
                            else: val += "th"
                        elif dat.hour > lastdat.hour: # hour changed
                            val = str(dat.hour) + "h"
                            col = QtGui.QColor(QtCore.Qt.GlobalColor.lightGray)
                        elif dat.minute > lastdat.minute: # minute changed
                            val = str(dat.minute) + "min"
                        elif dat.second > lastdat.second: # second changed
                            val = str(dat.second) + "s"
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
        self.heivar = sizy
        self.view.scene().clear()
        self.view.scene().setSceneRect(0, 0, sizx, sizy)
        self.view.scene().addItem(Grid(self.view.scene().sceneRect(), self.gridconv))
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
        
        if self.mode.currentText() == "Conditions/Indicators" or self.mode.currentText() == "Strategies":
            # indicators
            if len(logic.indicators) != 0: # if indicators are used
                for ind in logic.indicators: # for every indicator
                    if ind["show"]: # if should show graph
                        for obj in ind["data"]: # in case of bollinger e.g. show all graphs
                            if ind["dMode"] == 1: # if displayMode = Graph
                                for i in range(len(self.candles)-1): # do same as graph
                                    c = [self.candles[i], self.candles[i+1]] # for simplification
                                    for e in range(2):
                                        c[e] = Candle(c[e][0], c[e][1])
                                        c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                    if i != len(self.candles)-2:
                                        close1 = self.toCoord("y", obj[i]) # get positions
                                        close2 = self.toCoord("y", obj[i+1])
                                    can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                                    can.setPen(QtGui.QColor(ind["color"]))
                                    #if theme == "light": can.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.red))
                                    #else: can.setPen(QtGui.QPen(QtGui.QColor(240, 50, 240)))
                                    self.view.scene().addItem(can)
                            elif ind["dMode"] == 2: # mark important spots
                                for i in range(len(obj)):
                                    can = Candle(self.candles[obj[i]][0], self.candles[obj[i]][1])
                                    can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                    rect = QtCore.QRectF(can.x+1, 2, can.wid-1, self.view.scene().height()-2)
                                    self.view.scene().addRect(rect, QtGui.QColor(ind["color"]), QtGui.QColor(ind["color"]))
                            elif ind["dMode"] == 3: # volume
                                mx = max(obj) # max volume
                                mn = min(obj) # min volume
                                for i in range(len(obj)):
                                    hei = obj[i] - mn 
                                    hei = 100*(hei/(mx-mn)) # map to 1 - 100
                                    can = Candle(self.candles[i][0], self.candles[i][1])
                                    can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                    rect = QtCore.QRectF(can.x, self.view.scene().height()-hei, can.wid, hei)
                                    nopen = QtGui.QPen(QtCore.Qt.PenStyle.NoPen)
                                    self.view.scene().addRect(rect, nopen, QtGui.QColor(ind["color"]))
            # marked
            for m in range(len(self.marked)):
                if self.marked[m] is not None: # if spot is marked
                    can = Candle(self.candles[m][0], self.candles[m][1])
                    can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                    rect = QtCore.QRectF(can.x+1, 2, can.wid-1, self.view.scene().height()-2)
                    self.view.scene().addRect(rect, QtGui.QColor(self.marked[m]), QtGui.QColor(self.marked[m]))
        else: # base graph
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

        # selection rectangle for showing what candle is selected
        self.focus = Focus()
        self.tangent = None # Line that shows current trend

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
        
        # alpha
        m = -1*condition(logic.rawind, "lasttrendup", candle.time, k=-1, ma=20) # reverse m because y was reversed in condition
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
        # i.e. check whether condition is working in spot
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        labs = []
        resetPrecalc() 
        for i in range(len(avconds)):
            # print(avconds[i])
            # tim = now()
            labs.append(QtWidgets.QLabel(avconds[i], wid))
            labs[-1].setStyleSheet("border: none;")
            inps = [200, 2, 10] # get condition specific defaults
            names = ["ma", "k", "width"]
            for n in neededArgs[avconds[i]]:
                inps[names.index(n[0])] = n[2]# ignore contested because one run takes 370 ms
            if avconds[i] == "contested" or not condition(logic.rawind, avconds[i], candle.time, inps[0], inps[1], inps[2]):
                labs[-1].setStyleSheet(labs[-1].styleSheet() + " color: #404040;")
            labs[-1].move(2+125*(i%12), 2+20*(i//12))
            #print(now()-tim)
        self.docks[2].setWidget(wid)

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

                for ind in logic.indicators: # for all of the conditions
                    if not ind["ID"] in alr: # if button has already been made
                        l = len(alr)
                        alr.append(ind["ID"])
                        btn = IndButton(wid)
                        btn.typ = "conds"
                        btn.setGeometry(5+(l%25)*60, 10+(l//25)*24, 50, 20)
                        btn.setAutoFillBackground(False)
                        btn.setStyleSheet("color:%s;" % ind["color"])
                        btn.setText(ind["condVars"][0])
                        btn.setDelFn(self.deleteButton, ind["ID"])
                        btn.setToolTip(ind["condVars"][0])
                        btn.setClickFn(self.ctrlButton, logic.indicators.index(ind))

                l += 1

                btn = QtWidgets.QPushButton(wid)
                btn.setGeometry(5+(l%25)*60, 12+(l//25)*24, 15, 16) # + Button
                btn.setText("+")
                btn.clicked.connect(self.conditionDialog)
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
                        alr.append(strat["ID"])
                        btn = IndButton(wid)
                        btn.typ = "strats"
                        btn.setGeometry(5+(l%25)*60, 10+(l//25)*24, 50, 20)
                        btn.setAutoFillBackground(False)
                        btn.doPass = False # dont pass event to strategy dialog
                        # btn.setStyleSheet("color:%s;" % strat["color"])
                        btn.setText(str(strat["ID"]))
                        btn.setDelFn(self.deleteButton, strat["ID"])
                        btn.setToolTip(str(strat["ID"]))
                        btn.setClickFn(self.strategyDialog, logic.strategies.index(strat))

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
                    lab.setText("Click a Candle to see more info!")
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
                self.progs = []
                self.progs.append(QtWidgets.QLabel("Success Rate: " + str(logic.stats.succ/logic.stats.processed), wid))
                self.progs[0].move(2, 28)
                self.progs[0].setStyleSheet("border: none;")
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
            ind = logic.find("i", logic.conditions[s]["indID"]) # id of indicator
            btn = IndButton(wid)
            btn.setAutoFillBackground(False)
            btn.setStyleSheet(widgetstring + "color:%s;" % logic.indicators[ind]["color"])
            btn.setText(logic.indicators[ind]["condVars"][0])
            btn.setGeometry(2+50*(i%3), 22*(1+i//3), 50, 20)
            btn.setClickFn(self.selectButton, s)
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
                self.progs[0].setText("Success Rate: " + str(logic.stats.succ/logic.stats.processed))
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
        self.newScene(how, name)

    def reinitIndicators(self): # regather data for the indicators after e.g. the scene switched
        self.marked = [] # unmark all
        for ind in logic.indicators: # indicators
            graphs = ["movavg", "expavg", "bollingerabove", "bollingerbelow", "bollingerwidth"]
            end = False
            if ind["condVars"][0] in graphs: # if it's a graph
                if ind["condVars"][2] >= len(raw[logic.rawind]): # if window is bigger than new graph
                    ind["data"] = [] # return empty list
                    end = True
            if not end:
                resetPrecalc()
                l = condition(logic.rawind, ind["condVars"][0], len(raw[logic.rawind])-1-ind["condVars"][1], ind["condVars"][2], ind["condVars"][3],
                ind["condVars"][4], ind["condVars"][5], doReturn=True)
                nested = any(isinstance(i, list) for i in l)
                if not nested: l = [l]
                # buffer
                pre = []
                for i in range(ind["condVars"][1]):
                    pre.append(float("nan"))
                # add buffer to list
                for i in range(len(l)):
                    l[i] = pre + l[i]
                ind["data"] = l
        for con in logic.conditions:
            if con["indID"] == -1: # complex condition
                con["data"] = [] # unload data
            else:
                if len(con["data"]) != 0: # if condition has been loaded
                    con["data"] = [] # empty data
                    logic.getData(logic.find("c", con["ID"])) # get new data for condition

    def newScene(self, how="", tabName=""): # reset scene and generate new scene using raw data
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
        for t in range(len(raw[logic.rawind])): # get candles
            if raw[logic.rawind][t][1] > ma: ma = raw[logic.rawind][t][1]
            if raw[logic.rawind][t][2] < mi: mi = raw[logic.rawind][t][2]
            avg += abs(raw[logic.rawind][t][3] - raw[logic.rawind][t][0])
            l = [t] # [time, [o, h, l, c]]
            l.append([raw[logic.rawind][t][0], raw[logic.rawind][t][1], raw[logic.rawind][t][2], raw[logic.rawind][t][3]])
            self.candles.append(l)
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

    app.exec()
