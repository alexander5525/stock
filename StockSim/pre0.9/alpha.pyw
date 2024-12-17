import pathlib
from math import isnan, ceil, exp, sqrt
import pandas as pd
from random import SystemRandom
import yfinance as yf
import datetime as dt
from copy import deepcopy
from numpy import corrcoef
import sys
from PyQt6 import QtWidgets, QtGui, QtCore
import winsound
import threading
import os

def playsound(which="Error"): # For the error sound
    if which == "Error": winsound.PlaySound("SystemHand", winsound.SND_ALIAS)

# based on sim version = "1.2.1" 
version = "alpha"

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
time = 0 # randint(0, 2000) # random time point
timeframe = 2000 # until when the time is counted (so that stocks with less data wont only appear at the start)
money = 10000 # in dollars
operations = [] # stores the active operations
usedstocks = [] # predefinition
minmu = 0 # minimum mu value to count as success
quickmu = [] # stores mu values to calculate r

# vars for random cells
avconds = ["up", "down", "movavg", "expavg", "35up", "35down", "engulfup", "engulfdown", "closeabove", "closebelow", "contested", "bollingerabove", "bollingerbelow",
"bollingerwidth", "volume", "peak", "valley", "lasttrendup", "lasttrenddown"]
comps = ["movavg", "expavg", "contested", "meanrise", "bollinger"] # meanrise not part of conditions just in here for convenience
pres = [] # will store precalculated complex conditions | shape = (stock, comps, (either 1 or how many of one kind there are), (either len(stock) or similar))
preinds = [] # will store the e.g. windows of the moving averages so: preinds = [[100, 200]]; precalcs[0][0][preinds[0].index(200)]

def randint(low, high): # different random function to improve randomness
    high = int(high + 1)
    low = int(low)
    n = SystemRandom().random() # random seed
    for i in range(1, high-low):
        if (n <= i/(high-low)): return i - 1 + low # if max = 4 and min = 0: if 0.2143124 < 1/4: return 0
    return high - 1

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
    # hi = []
    # lo = []
    # cl = []
    # vo = []
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
            # op.append(float(l[0])) # for shape (75, 5, 3000)
            # hi.append(float(l[1]))
            # lo.append(float(l[2]))
            # cl.append(float(l[3]))
            # vo.append(float(l[4]))
        file.close()
    except:
        return []
    #together = [op, hi, lo, cl, vo] # list of lists that contains all the data for the stock
    return op

# if all are loaded ~ 4gb of ram
if False:
    print("Loading stock data...")
    got = [] # so that one stock isnt loaded twice
    runs = 0
    while runs < 100:
        rn = randint(0, len(stocks)-1)
        while rn in got:
            rn = randint(0, len(stocks)-1)
        got.append(rn)
        raw.append(read(stocks[rn]))
        if len(raw[-1]) >= 2000: # has to be certain length of timeframes
            runs += 1
        else:
            raw.pop(-1)
    evals = [] # same as raw but just for evaluation purposes
    # for s in stock_evals:
    #     evals.append(read(s))
    del got, runs, rn, stocks, read #stock_evals, read # delete unused variables

def buyable(index, amnt): # returns whether a stock is able to be bought
    return money >= amnt*raw[index][time][3]

class Operation():
    def __init__(self, stock, number, stlo, tapr): # acts as buy function as well
        global money
        # if fractional shares are allowed: number = float, else number = int
        super().__init__()
        self.running = True
        self.ind = stock
        self.amnt = number
        self.stop = stlo
        self.take = tapr
        self.time = time # save for evaluation purposes
        money -= raw[stock][time][3]*number
    def sell(self): # sells for current market price
        global money
        money += raw[self.ind][time][3]*self.amnt
        self.running = False


def near(a, b, n): # rounds a and b to n digits and checks if they're the same
    return round(a, n) == round(b, n) # if a rounded = b rounded then they're really close

def get_cont_extrs(stock, split=False): # gets extremes of a graph to calculate contested areas
    top = stock[0][3] # keep track of top value and if it didn't change add to peaks
    bottom = stock[0][3] # also keep track of bottom
    lasttop = 0 # keeps track of when top was last changed
    lastbottom = 0
    timesuntilextreme = 100
    extremes = [] # spots with peaks or lows
    peaks = [] # if needed
    lows = [] # can also be output seperately
    for i in range(len(stock)):
        if stock[i][3] > top:
            top = stock[i][3]
            lasttop = i
        if stock[i][3] < bottom:
            bottom = stock[i][3]
            lastbottom = i
        if i == lastbottom + timesuntilextreme:
            if split: lows.append(lastbottom)
            extremes.append(lastbottom)
            lastbottom = i
            bottom = stock[i][3]
        elif i == lasttop + timesuntilextreme:
            if split: peaks.append(lasttop)
            extremes.append(lasttop)
            lasttop = i
            top = stock[i][3]
    if split: return peaks, lows # gives split outputs
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


def condition(index, shape, spot, ma=200, k=2, width=10):
    # 0 open | 1 high | 2 low | 3 close | 4 volume
    #if iseval: stock = evals[index] # evaluation
    stock = raw[index] # makes it simpler
    if shape == "up" or shape == "green": # close > open
        return stock[spot][3] > stock[spot][0]
    elif shape == "down" or shape == "red": # close < open
        return stock[spot][3] < stock[spot][0]
    elif shape == "movavg": # will always look for bigger so true means avg > close
        if spot <= ma: return False
        if ma in preinds[0]:# and not iseval: # if data was precalculated
            slope = pres[usedstocks.index(index)][0][preinds[0].index(ma)][spot]
        else:
            temp = pd.DataFrame(stock[spot-ma:spot])
            slope = temp.rolling(window=ma).mean()[3][ma-1]
        return slope > stock[spot][3]
    elif shape == "expavg":
        if spot <= ma: return False
        if ma in preinds[1]:# and not iseval: # if precalculated
            slope = pres[usedstocks.index(index)][1][preinds[1].index(ma)][spot]
        else:
            temp = pd.DataFrame(stock[spot-ma:spot])
            slope = temp.ewm(span=ma, adjust=False).mean()[3][ma-1]
        return slope > stock[spot][3]
    elif shape == "35up": # Fibonacci candle up # buying pressure
        # if stock[spot][3] < stock[spot][0]: # if close < open: end || color does not matter
        #     return False
        high = stock[spot][1]
        low = stock[spot][2]
        if stock[spot][3] > stock[spot][0]: body = stock[spot][0]
        else: body = stock[spot][3]
        fibonacci = high - (high - low) * 0.382
        return body > fibonacci
        # temp = stock[spot][1] + stock[spot][2]
        # if stock[spot][3] > stock[spot][0]: lower = stock[spot][0]
        # else: lower = stock[spot][3]
        # return lower >= (1-0.382) * temp # if body of candle in 38.2% of top
    elif shape == "35down": # Fibonacci candle down # selling pressure
        # if stock[spot][0] < stock[spot][3]: # if open < close: end || color does not matter
        #     return False
        #temp = (stock[spot][0]-stock[spot][2])/(stock[spot][1]-stock[spot][2]) # (open-low)/(high-low)
        high = stock[spot][1]
        low = stock[spot][2]
        if stock[spot][3] > stock[spot][0]: body = stock[spot][3]
        else: body = stock[spot][0]
        fibonacci = low + (high - low) * 0.382
        return body < fibonacci
        # temp = stock[spot][1] + stock[spot][2]
        # if stock[spot][3] < stock[spot][0]: upper = stock[spot][0]
        # else: upper = stock[spot][3]
        # print(upper, (1-0.382) * temp)
        # return upper <= 0.382 * temp # if body of candle in 38.2% of bottom
    elif shape == "engulfup": # candle engulfs last and color change # buying pressure
        if stock[spot][0] > stock[spot][3] or stock[spot-1][3] > stock[spot-1][0]: # if opennow > closenow or closelast > openlast: end
            return False
        if not near(stock[spot][0], stock[spot-1][3], 1): # if not open ~~ last close: end
            return False
        return stock[spot][3] > stock[spot-1][0] # close > last open
    elif shape == "engulfdown": # candle engulfs last and color change # selling pressure
        if stock[spot][3] > stock[spot][0] or stock[spot-1][0] > stock[spot-1][3]: # if closenow > opennow or openlast > closelast: end
            return False
        if not near(stock[spot][3], stock[spot-1][0], 1): # if not close ~~ last open: end
            return False
        return stock[spot][3] < stock[spot-1][0] # close < last open
    elif shape == "closeabove": # close is above last high # buying pressure
        return stock[spot][3] > stock[spot-1][1] # close > last high
    elif shape == "closebelow": # close is below last low # selling pressure
        return stock[spot][3] < stock[spot-1][2] # close > last low
    elif shape == "contested": # if many peaks were in same area # market change
        if index in preinds[2]:# and not iseval:
            extremes = pres[usedstocks.index(index)][2][0] # if precalculated
            for e in extremes:
                if e > spot-100: # if extreme exceeds spot -100 because it needs to have at least 100 values until its considered an extreme
                    exind = extremes.index(e)
                    if exind < 0: # if no extremes until point; give empty list
                        extremes = []
                    else:
                        extremes = extremes[:exind] # only get until last extreme
                    break
        else:
            extremes = get_cont_extrs(stock[:spot-101]) # get extremes until spot
        nbox = []
        contestability = 3 # if contestability values are in nbox then its contested
        for n in range(11): # 5 up 5 down + same
            nbox.append(round(stock[spot][3]-5+n, 0))
        c = 0
        for e in extremes:
            if round(stock[e][3]) in nbox:
                c += 1
        return c >= contestability # if 5 or more peaks/lows are in current area
    elif shape == "bollinger": # placeholder for new condition comments
        # risk ranking through this + price envelopes (looser)
        # bollingerabove (price above upper bollinger)
        # bollingerbelow (price below lower bollinger)
        # bollingerwidth (if width of band below certain percentage)
        # trendline (if price touches trendline)
        # peak (if tallest at spot)
        # valley (if lowest at spot)
        # line (if stock follows line)
        # trend lines (tangents) (trendline bounce)
        # triangle trend lines
        # resistance line
        # sks formation
        # m w lines
        # leverage banking
        return False
    elif shape == "bollingerabove": # price above upper bollinger band
        if spot < ma*2: return False # if no standard deviation can be calculated
        if ma in preinds[4]:
            slope = pres[usedstocks.index(index)][0][preinds[0].index(ma)][spot]
            sigma = pres[usedstocks.index(index)][4][preinds[4].index(ma)][spot]
            return stock[spot][3] >= slope + k*sigma
        else:
            temp = pd.DataFrame(stock[spot-ma*2:spot]) # get twice the ma because movavg is needed for ma values
            slope = temp.rolling(window=ma).mean()[3] # get moving averages
            sigma = 0 # gets how far the average is off from the current values | standard deviation
            for i in range(ma):
                sigma += pow(stock[spot-ma+i][3]-slope[ma+i], 2) # (cls-mov)^2 -> (cls-mov)^2/n = var
            sigma = sqrt(sigma/ma) # sqrt(var)
            return stock[spot][3] >= slope[ma*2-1] + k*sigma # close >= movavg + k * sigma (k = 2)
    elif shape == "bollingerbelow": # price below lower bollinger band
        if spot < ma*2: return False # if no standard deviation can be calculated
        if ma in preinds[4]:
            slope = pres[usedstocks.index(index)][0][preinds[0].index(ma)][spot]
            sigma = pres[usedstocks.index(index)][4][preinds[4].index(ma)][spot]
            return stock[spot][3] <= slope - k*sigma 
        else:
            temp = pd.DataFrame(stock[spot-ma*2:spot]) # get twice the ma because movavg is needed for ma values
            slope = temp.rolling(window=ma).mean()[3] # get moving averages
            sigma = 0 # gets how far the average is off from the current values | standard deviation
            for i in range(ma):
                sigma += pow(stock[spot-ma+i][3]-slope[ma+i], 2) # (cls-mov)^2 -> (cls-mov)^2/n = var
            sigma = sqrt(sigma/ma) # sqrt(var)
            return stock[spot][3] <= slope[ma*2-1] - k*sigma # close <= movavg + k * sigma (k = 2)
    elif shape == "bollingerwidth": # width of band below width variable
        if spot < ma*2: return False # if no standard deviation can be calculated
        if ma in preinds[4]:
            slope = pres[usedstocks.index(index)][0][preinds[0].index(ma)][spot]
            sigma = pres[usedstocks.index(index)][4][preinds[4].index(ma)][spot]
            return stock[spot][3]/k*sigma >= width
        else:
            temp = pd.DataFrame(stock[spot-ma*2:spot]) # get twice the ma because movavg is needed for ma values
            slope = temp.rolling(window=ma).mean()[3] # get moving averages
            sigma = 0 # gets how far the average is off from the current values | standard deviation
            for i in range(ma):
                sigma += pow(stock[spot-ma+i][3]-slope[ma+i], 2) # (cls-mov)^2 -> (cls-mov)^2/n = var
            sigma = sqrt(sigma/ma) # sqrt(var)
            return stock[spot][3]/k*sigma >= width # close / k * sigma >= width (k = 2) ">" because it's being divided by width so smaller = larger
    elif shape == "volume": # volume above threshold
        return stock[spot][4] > ma*1000 # ma in thousand | volume > ma*1000
    elif shape == "peak": # local peak at spot
        if spot < 3: return False # if less than 3 spots before
        if spot+3 > time: top = time # if less than 3 spots after
        else: top = spot + 3
        temp = stock[spot-3:top+1] # get nearby values
        maxx = spot - 3
        for i in range(len(temp)):
            if stock[spot-3+i][3] > stock[maxx][3]: maxx = spot-3+i # get largest in range
        return maxx == spot # if spot is max value in range
    elif shape == "valley":
        if spot < 3: return False # if less than 3 spots before
        if spot+3 > time: top = time # if less than 3 spots after
        else: top = spot + 3
        temp = stock[spot-3:top+1] # get nearby values
        maxx = spot - 3
        for i in range(len(temp)):
            if stock[spot-3+i][3] < stock[maxx][3]: maxx = spot-3+i # get smallest in range
        return maxx == spot # if spot is min value in range
    elif shape == "lasttrendup": # checks if rise last 100 timestamps is above 0
        if spot < 104: return False
        if 4 in preinds[0]: # always use 4 day moving average
            slope = (pres[usedstocks.index(index)][0][preinds[0].index(4)][spot-100], pres[usedstocks.index(index)][0][preinds[0].index(4)][spot])
        else:
            temp = pd.DataFrame(stock[spot-104:spot])
            slope = (temp.rolling(window=ma).mean()[3][ma-1], temp.rolling(window=ma).mean()[3][ma-101])
        return slope[0]-slope[1] >= 0
    elif shape == "lasttrenddown": # checks if rise last 100 timestamps is below 0
        if spot < 104: return False
        if 4 in preinds[0]: # always use 4 day moving average
            slope = (pres[usedstocks.index(index)][0][preinds[0].index(4)][spot-100], pres[usedstocks.index(index)][0][preinds[0].index(4)][spot])
        else:
            temp = pd.DataFrame(stock[spot-104:spot])
            slope = (temp.rolling(window=ma).mean()[3][ma-1], temp.rolling(window=ma).mean()[3][ma-101])
        return slope[0]-slope[1] <= 0
    else:
        print(shape + " is not a shape.\nCheck your writing!")
        return False

class Cell():
    def __init__(self, condit, timespot, spvar=200):
        super().__init__()
        self.condition = condit
        self.spot = timespot # usually negative or 0
        self.ma = spvar
        self.exarg = [0, 0] # extra arguments used for ex. bollinger k
        self.active = None
        self.weight = 1 # will only be used in player
        self.reverse = False
    def calculate(self, st):#, iseval=False):
        global time
        if time + self.spot < 0: # if spot requested is outside of range
            self.active = False
        else:
            # Will determine and evt. reverse activation (^ is XOR)
            self.active = condition(st, self.condition, time+self.spot, self.ma, k=self.exarg[0], width=self.exarg[1]) ^ self.reverse 

class Player(): # player that will do the buying
    def __init__(self, is_rand=True, cellnum= 1, readstr=""):
        super().__init__()
        self.cells = [] # cells that contain the conditions
        self.weight = 1 # weight for confidence calculation | basic values
        self.bias = 0
        self.confidence = 0 # same as activation | goal: confidence ~ amount, sl, tp
        self.confidences = [] # stores multiple confidence values to calculate r
        self.r = 0 # average corrcoef for confidence and mu
        self.minconf = 1 # minimum amount  of confidence for player to activate
        self.outs = [1, 0.966, 1.047] # amount, stop loss, take profit # 1.001+.966+.996+1.047+1.025+
        self.outws = [1.001, 0.996, 1.025] # weights for outs (calc ex: stop = outs[1]+outws[1]*confidence)
        self.lasttime = 0 # last time when a stock was bought
        self.exws = [0, 0] # weights for external values [last time bought, price]
        self.average = 0 # will keep track of average money gained using this method
        self.score = 0 # will keep track of µ of rises it has predicted
        self.lastscore = 0 # will keep track of whatever the player was rated good in last attempts
        self.fraction = [0, 0] # first is number of successes and second is number of failures
        if is_rand: # generate random cells
            for i in range(cellnum):
                inco = randint(0, len(avconds)-1) # index of choosen condition
                spt = -i # spot of condition (for first generation pick -i)
                m = randint(2, 300) # time range for averages
                if "bollinger" in avconds[inco]: # get normal bollinger range
                    m = 20
                self.cells.append(Cell(avconds[inco], spt, m))
                if m == 20: 
                    self.cells[-1].exarg[0] = randint(1, 2)
                    if avconds[inco] == "bollingerwidth":
                        self.cells[-1].exarg[1] = randint(100, 1000)
            #     self.cells[-1].weight = 1 + randint(-5, 5)/10
            # self.weight = randint(1, 20)/10
            # self.bias = randint(-10, 10)/10
            # self.exws[0] = randint(0, 100)/10
            # self.exws[1] = randint(0, 10)/10
            # self.de_failure()
        elif readstr != "": # read player from string
            split = readstr.split("+")
            ncells = int(split[0]) # get number of cells
            self.minconf = float(split[1])
            self.weight = float(split[2])
            self.bias = float(split[3])
            self.exws[0] = float(split[4])
            self.exws[1] = float(split[5])
            self.outws[0] = float(split[6])
            self.outws[1] = float(split[7])
            self.outs[1] = float(split[8])
            self.outws[2] = float(split[9])
            self.outs[2] = float(split[10])
            split = split[-1].split("%") # get rest of string and split cells
            for sp in split:
                if len(sp) > 0: # so no empty cells exist
                    tings = sp.split("/")
                    self.cells.append(Cell(tings[0], int(tings[1]), int(tings[2])))
                    self.cells[-1].weight = float(tings[-2])
                    if len(tings) > 5:
                        if len(tings[3]) >= 1: self.cells[-1].exarg[0] = float(tings[3])
                    if len(tings) > 6:
                        if len(tings[4]) >= 1: self.cells[-1].exarg[1] = float(tings[4])
                    if len(tings) > 7:
                        if len(tings[5]) >= 1: self.cells[-1].reverse = bool(int(float(tings[5])))
    def calc(self, index):#, iseval=False):
        global operations, money
        if len(self.cells) == 0: # if the Player has no cells, i.e. no conditions
            return None
        numerator = 0 # how many times true is seen
        denominator = len(self.cells) # how many conditions/cells there are
        for c in self.cells: # calculate cell activations
            #denominator += 1
            c.calculate(index)#, iseval=iseval)
            if c.active: numerator += 1 * c.weight
        numerator += self.exws[0]*(time-self.lasttime) + self.exws[1]/raw[index][time][3] # add last buy time and price to confidence value
        self.confidence = (numerator/denominator) * self.weight + self.bias
        self.confidences.append(self.confidence)
        if self.confidence >= self.minconf: # if confidence of 1 or more: buy
            nvec = []
            for i in range(3):
                if i == 0: nvec.append(self.outs[i]*self.outws[i]*self.confidence) # get order amount based on confidence
                else: nvec.append(self.outs[i]*self.outws[i]*self.confidence) # calculate buy order limits based on confidence
            nvec[0] = int(nvec[0]) # make amount an integer
            #if iseval: price = evals[index][time][3] # current price
            price = raw[index][time][3] # current price
            if (buyable(index, nvec[0])): 
                operations.append(Operation(index, nvec[0], price*nvec[1], price*nvec[2])) # if enough money is available; buy
                self.lasttime = time # sets last time bought to now
    def is_failure(self):
        if self.exws[0] > 0 and self.weight > 0: return False # if buy time weight > 0 then eventually confidence will grow to 1
        den = len(self.cells)
        num = 0
        for c in self.cells:
            num += c.weight
        return ((num/den) *self.weight + self.bias) <= self.minconf # look if confidence is never above 1, and return false if it isn't
    def de_failure(self):
        while self.is_failure(): # if player never activates
            for c in self.cells:
                c.weight = 1 + randint(-5, 5)/10 # regenerate values
            self.weight = randint(1, 20)/10
            self.bias = randint(-10, 10)/10
            self.exws[0] = randint(0, 100)/10
    def mutate(self, mode, cel=Cell("up", -31)):
        if mode == 0: # add / new
            rangee = 1
            for i in range(3): # makes range random so that changes in upper/lower parts are more unlikely
                rangee *= pow(2, randint(0, 1))
                if i == 2: rangee *= pow(2, randint(-1, 1)) # so that curve focuses more on lower numbers
            rangee = int(rangee) # if range = 2^-1 | range distribution: 1:5, 2:7, 4:7, 8:4, 16:1
            if randint(1, 50) == 1: # so that 32 is technically possible
                rangee *= 2
            spot = -randint(0, rangee)
            # rem = -1
            # for cell in self.cells:
            #     if cell.spot == spot:
            #         rem = self.cells.index(cell) # look if cell exists in spot already
            # if rem != -1:
            #     self.cells.pop(rem) # remove cell
            inco = randint(0, len(avconds)-1) # condition
            m = randint(1, 300) # time range for averages
            if "bollinger" in avconds[inco]: # get normal bollinger range
                m = 20
            self.cells.append(Cell(avconds[inco], spot, m))
            if m == 20: 
                self.cells[-1].exarg[0] = randint(1, 2)
                if avconds[inco] == "bollingerwidth":
                    self.cells[-1].exarg[1] = randint(100, 1000)
        elif mode == 1: # remove
            if len(self.cells) > 0:
                rem = randint(0, len(self.cells)-1) # pick random cell
                self.cells.pop(rem) # remove cell
        elif mode == 2: # add / replace with given cell
            rem = -1
            for cell in self.cells:
                if cell.spot == cel.spot: 
                    rem = self.cells.index(cell) # look if cell exists in spot already
            if rem != -1:
                self.cells.pop(rem) # remove cell
            self.cells.append(cel) # add replacement cell
        elif mode == 3: # small changes
            ran = randint(0, len(self.cells)-1)
            choose = randint(0, 2)
            if choose == 0: # spot / self change
                choose = randint(0, 1)
                if choose == 0:
                    self.cells[ran].spot += randint(-5, 5) 
                    if self.cells[ran].spot > 0: self.cells[ran].spot = 0
                else:
                    choose = randint(0, 2)
                    if choose == 0: self.outws[0] += randint(-5, 5)/20 # randomize order amnt weight
                    else: 
                        if randint(0, 1) == 0:
                            self.outws[choose] += randint(-50, 50)/1000 # randomize limit weights
                        else:
                            self.outs[choose] += randint(-5, 5)/1000 # randomize limits
            elif choose == 1: # cell value change
                ran = randint(0, len(self.cells)-1)
                choose = randint(0, 2)
                if choose == 0:
                    if not "bollinger" in self.cells[ran].condition: self.cells[ran].ma += randint(-50, 50) # prevents bollinger with n != 20
                    else: self.cells[ran].exarg[1] = randint(100, 1000)
                    if self.cells[ran].ma <= 1:
                        self.cells[ran].ma = 2
                elif choose == 1:
                    self.cells[ran].weight += randint(-20, 20)/20
                else:
                    self.cells[ran].reverse = bool(randint(0, 1))
            else: # player weight / bias change
                choose = randint(0, 3)
                if choose == 0: self.weight += randint(-5, 5)/20
                elif choose == 1: self.bias += randint(-5, 5)/20
                elif choose == 2:
                    choose = randint(0, 1)
                    if choose == 0: self.exws[0] += randint(-5, 5)/50
                    else: self.exws[1] += randint(-5, 5)/50
                else:
                    self.minconf += randint(-5, 5)/20
    def reset(self):
        self.average = 0
        self.score = 0
        self.fraction = [0, 0]
        self.confidences = []
        self.r = 0
    def savestring(self):
        save = "" # should be num cells, seperated by commas
        save += numtostr(len(self.cells)) + "+" # + is basic seperator
        save += numtostr(self.minconf) + "+"
        save += numtostr(self.weight) + "+"
        save += numtostr(self.bias) + "+"
        save += numtostr(self.exws[0]) + "+"
        save += numtostr(self.exws[1]) + "+"
        for i in range(3): 
            save += numtostr(self.outws[i]) + "+"
            if i != 0:
                save += numtostr(self.outs[i]) + "+"
        for i in range(len(self.cells)):
            save += self.cells[i].condition + "/" # / is seperator for values
            save += str(self.cells[i].spot) + "/"
            save += str(self.cells[i].ma) + "/" 
            if not (not self.cells[i].reverse and self.cells[i].exarg[0] == 0 and self.cells[i].exarg[1] == 0): # if some of those values were changed
                save += numtostr(self.cells[i].exarg[0]) + "/"
                save += numtostr(self.cells[i].exarg[1]) + "/"
                save += str(int(self.cells[i].reverse)) + "/"
            save += numtostr(self.cells[i].weight) + "/%" # % is seperator for cells
        return save

# def cellcomp(c1, c2): # compares if 2 cells are the same
#     if c1.condition != c2.condition: return False # if conditions don't match
#     if c1.spot != c2.spot: return False # if spot doesn't match
#     if c1.condition in ["movavg", "expavg"] or "bollinger" in c1.condition: # ma check | only for ones that actually matter
#         if c1.ma != c2.ma: return False
#     return True


# def same(pl1, pl2): # looks if 2 players are the same
#     if len(pl1.cells) != len(pl2.cells): return False # different amount of cells
#     for c in range(len(pl1.cells)):
#         if not cellcomp(pl1.cells[c], pl2.cells[c]): return False # if cells don't match up
#     if pl1.weight != pl2.weight: return False # if weights don't match up
#     if pl1.bias != pl2.bias: return False # if biases don't match up
#     if pl1.outws != pl2.outws: return False # if order weights don't match up
#     return True

# def remove_clones(players): # removes duplicate players and returns player list
#     newp = players
#     remlist = []
#     cont = True
#     while cont:
#         for p in range(len(newp)):
#             for pl in range(len(newp)):
#                 if p != pl and same(newp[p], newp[pl]): # checks if two players are the same
#                     remlist.append(pl)
#                 if len(remlist) > 0: break
#             if len(remlist) > 0: break
#             if p == len(newp)-1: cont = False # if every player has been checked
#         for r in remlist:
#             newp.pop(r) # remove players
#         remlist = []
#     return newp

players = []
#plnum = 750 # number of players
#gens = 75 # number of generations
#batchn = 0 # number of generations before stocks get reshuffled
# temp = [-1, 0]
# while temp[0] == -1:
#     if gens <= 50*pow(2, temp[1]): # makes it so that only 10 batches are possible at once
#         temp[0] = 0
#     else:
#         temp[1] += 1

# batchn = 5*pow(2, temp[1])
# del temp


# for i in range(plnum):
#     players.append(Player(is_rand=False, readstr="1+1+1+0+0+0+1.001+.996+.966+1.025+1.047+peak/0/247/1.2/%"))
# usedstocks = [] # what stocks are used in a generation
numsts = 10 # how many stocks

def prep_stocks(): # prepares/shuffles all stocks 
    global usedstocks, pres, preinds
    usedstocks = []
    pres = []
    preinds = []
    for i in range(numsts):
        rn = randint(0, len(raw)-1)
        while rn in usedstocks: # not to get same stock twice
            rn = randint(0, len(raw)-1)
        usedstocks.append(rn) # dependent on how many stocks are preloaded

    # make precalc pre lists
    for i in range(numsts): # for each used stock
        pres.append([])
        for j in range(len(comps)): # complex conditions: ["movavg", "expavg", "contested", "meanrise", "bollinger"]
            pres[-1].append([])
    for j in range(len(comps)):
        preinds.append([])

    # get mean rises for stocks
    for st in usedstocks:
        for pr in range(len(raw[st])):
            pres[usedstocks.index(st)][3].append(mean_rise(raw[st], pr)) # append mean rise for each spot in each stock for evaluation
        maxx = max(pres[usedstocks.index(st)][3]) # save max of rise graph to scale it
        for r in range(len(pres[usedstocks.index(st)][3])): # scale graph
            pres[usedstocks.index(st)][3][r] /= maxx

def precalculate(plrs): # precalculate complex functions such as moving averages and save them in memory
    global preinds, pres
    for p in plrs: # plrs is players
        for c in p.cells:
            if c.condition in comps or "bollinger" in c.condition: # if condition is a complex function
                if "bollinger" in c.condition: tc = comps.index("bollinger") # if it uses bollinger bands in any way
                elif "lasttrend" in c.condition: tc = 0
                elif "trendline" in c.condition: tc = 2 # calculate contested ateas if trendline is wanted in any way
                else: tc = comps.index(c.condition) # get index of condition
                if tc < 2: # lower indexes are averages so there are more of them
                    if not c.ma in preinds[tc]: # if moving average has not yet been calculated
                        preinds[tc].append(c.ma) # append to precalculated indexes
                        for st in usedstocks:
                            temp = pd.DataFrame(raw[st])
                            if tc == 0: avg = temp.rolling(window=c.ma).mean()[3].reset_index(drop=True).to_list() # get list of moving average
                            else: avg = temp.ewm(span=c.ma, adjust=False).mean()[3].reset_index(drop=True).to_list() # exp. mov. avg.
                            pres[usedstocks.index(st)][tc].append(avg) # add average to precalcs
                elif tc == 2: # contested areas
                    for st in usedstocks:
                        if not st in preinds[tc]:
                            preinds[tc].append(st)
                            #temp = get_cont_extrs(stock=raw[st], split=True) # return peaks and valleys seperately
                            #extrs = temp[0] + temp[1] # combine peaks and valleys for total extremes
                            #extrs.sort() # sort extremes so that they're in numerical order
                            pres[usedstocks.index(st)][tc].append(get_cont_extrs(stock=raw[st])) # calculate and append extremes to precalcs
                            #pres[usedstocks.index(st)][tc].append(temp[0]) # peaks
                            #pres[usedstocks.index(st)][tc].append(temp[1]) # valleys
                elif tc == 4: # bollinger deviation
                    if not c.ma in preinds[0]: # get moving average for calculation
                        preinds[0].append(c.ma) 
                        for st in usedstocks:
                            temp = pd.DataFrame(raw[st])
                            avg = temp.rolling(window=c.ma).mean()[3].reset_index(drop=True).to_list() # get list of moving average
                            pres[usedstocks.index(st)][0].append(avg) # add average to precalcs
                    if not c.ma in preinds[4]:
                        preinds[tc].append(c.ma)
                        for st in usedstocks:
                            pres[usedstocks.index(st)][tc].append([])
                            dist = [] # distances
                            for t in range(len(raw[st])):
                                if t < c.ma: dist.append(float("nan")) # if movavg has no value yet
                                else: dist.append(pow(raw[st][t][3] - pres[usedstocks.index(st)][0][preinds[0].index(c.ma)][t], 2))
                            for t in range(len(raw[st])):
                                if t < c.ma*2: pres[usedstocks.index(st)][tc][-1].append(float("nan")) # if movavg hasn't existed for ma values yet
                                else: 
                                    var = 0
                                    for i in range(c.ma):
                                        var += dist[t-c.ma+i] # make average of last c.ma values
                                    var /= c.ma
                                    pres[usedstocks.index(st)][tc][-1].append(sqrt(var)) # append sigma to pres

# def tradefactor(nTrades): # so that over/undertrading is punished
#     CONST = 0.00000042292379259074
#     return exp(-CONST*pow(nTrades-3000, 2))

def timestep(stock, player):#, iseval=False):
    global time, operations, players, quickmu
    time += 1
    poplist = [] # operations that have finished
    for op in operations:
        if raw[op.ind][time][3] <= op.stop: # if stop loss is reached
            op.sell()
            poplist.append(operations.index(op))
        elif raw[op.ind][time][3] >= op.take: # if take profit is reached
            op.sell()
            poplist.append(operations.index(op))
    poplist.reverse() # reverse list, so that later indexes are removed first
    quickmu.append(pres[usedstocks.index(stock)][3][time]) # append mu value every timestep to get mu graph for timeframe
    for p in poplist: # remove finished operations
        scr = pres[usedstocks.index(operations[p].ind)][3][operations[p].time]*operations[p].amnt # score (meanrise*orderamnt = score)
        if pres[usedstocks.index(operations[p].ind)][3][operations[p].time] > minmu: # success (mu > minmu)
            player.fraction[0] += 1
        else:
            player.fraction[1] += 1
        player.score += scr*(raw[stock][0][3]/200) # multiply by price/200 to eliminate smaller stocks being better
        operations.pop(p)
    # player maths
    player.calc(stock) # player execution

def sell_all():
    global operations
    for op in operations:
        op.sell()
    operations = []

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

        painter.setPen(QtCore.Qt.GlobalColor.gray)
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
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if self.up: painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 235, 0)))
        else: painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 0, 0)))
        #painter.drawEllipse(QtCore.QPointF(self.x, self.y), 10, 10)
        painter.drawLine(QtCore.QLineF(self.x+self.wid/2, self.top, self.x+self.wid/2, self.tip)) # wick
        rec = QtCore.QRectF(self.x, self.y, self.wid, self.hei) # body
        painter.drawRect(rec)
        painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.white))
        fm = QtGui.QFontMetrics(painter.font())
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

class View(QtWidgets.QGraphicsView): # Main Graphics window
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setScene(scene)
        self.mouseFunction = self.dummy # setup dummy function to be overidden later
    
    def dummy(self, event):
        x = event.pos().x()
        y = event.pos().y()
    
    def setMouseFn(self, function):
        self.mouseFunction = function
    
    def wheelEvent(self, event): # modify the scroll behavior of the scrolling so that shift scroll is horizontal scroll
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier:
            # Shift key pressed, scroll horizontally
            scroll = -int(event.angleDelta().y()*0.875)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + scroll)
        else:
            # No modifier key pressed, pass event to base class
            super().wheelEvent(event)
    
    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        #print(event.pos())
        self.mouseFunction(event)
        return super().mouseMoveEvent(event)

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

class GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Simulator")
        self.setMinimumSize(800, 600)
        self.loading = False
        self.candles = [] # [[time, [o, h, l, c]], ...]
        self.inputs = [None, None, None, None] # placeholder for dialog line edits
        self.timeaxis = [] # will store dates

        #self.setWindowIcon("")
        self.create_widgets()
    
    def create_widgets(self):
        main = self.menuBar()

        file = main.addMenu("File")
        act = file.addAction("Open...")
        act.triggered.connect(self.open)
        file.addAction(act)
        act = file.addAction("Quick open...")
        act.triggered.connect(self.quickopen)
        file.addAction(act)
        act = file.addAction("Download...")
        act.triggered.connect(self.download)
        file.addAction(act)
        file.addSeparator()
        act = file.addAction("Close")
        act.triggered.connect(self.close)

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

        help = main.addMenu("Help")
        act = help.addAction("About")
        act.triggered.connect(self.about)
        help.addAction(act)

        self.labely = QtWidgets.QLabel("", self)
        self.labely.move(0, 300)
        self.labelx = QtWidgets.QLabel("", self)
        self.labelx.move(400, 575)

        self.gridconv = [40, 5, 40, 1] # (dx, corresponds to dt timeframes, dy, corresponds to dp price difference) 
        self.rangex = (0, 0) # timeframe
        self.rangey = (0, 0) # price range

        self.heivar = 0 

        self.draw_scene()
        

        # splitter = QtWidgets.QSplitter()
        # splitter.addWidget(label)
    
    def open(self): # open file dialog
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open stock data file", "", "Text files (*.txt);;All files (*.*)")[0] # get filename
        if filename == "": return # if now file was selected
        self.readstocks(filename, "open")

    def quickopen(self): # quick open dialogue box
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Quickopen...")
        dbox.setFixedSize(150, 85)
        label1 = QtWidgets.QLabel(dbox)
        label1.setGeometry(10, 10, 85, 25)
        self.inputs[0] = QtWidgets.QLineEdit(dbox)
        self.inputs[0].setGeometry(75, 10, 50, 25)
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(40, 52)
        label1.setText("Ticker/ID")
        btn.pressed.connect(lambda: self.quickchange("quick", dbox))
        dbox.exec()

    def quickchange(self, what, parent): # Execute quickopen/open code
        if what == "quick": # when quickopen was run before
            self.readstocks(self.inputs[0].text(), "quick")
        else:
            pass
        parent.close()
    
    def download(self): # download dialog box
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
        btn.pressed.connect(lambda: self.downloadChange(dbox))
        dbox.exec()

    def downloadChange(self, parent): # download data and load scene
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
        raw = []
        self.timeaxis = dat
        raw.append(red)
        self.newScene()
        parent.close()

    def chartCheck(self, who): # will control the checkboxes of the chart in view menu
        if who == 0:
            if self.chartchecks[0].isChecked(): # means after clicking on the checkbox it was checked
                self.chartchecks[1].setChecked(False)
            else:
                self.chartchecks[1].setChecked(True)
        elif who == 1:
            if self.chartchecks[1].isChecked():
                self.chartchecks[0].setChecked(False)
            else:
                self.chartchecks[0].setChecked(True)
        self.setScene()
            

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
        self.loading = True
        if what == "x":
            self.gridconv[0] = float(self.inputs[0].text())
            self.gridconv[1] = float(self.inputs[1].text())
        elif what == "y":
            self.gridconv[2] = float(self.inputs[0].text())
            self.gridconv[3] = float(self.inputs[1].text())
        parent.close()
        self.setScene()

    def toCoord(self, what, value): # shortcut for coordinate conversion
        return coordinate(what=what, value=value, gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)

    def draw_scene(self): # draws the graphical component

        # main graphic window
        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = View(self.scene, self)
        self.setScene()
        self.view.setGeometry(25, 25, 725, 525)
        #self.view.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.BlankCursor))
        self.view.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.view.horizontalScrollBar().valueChanged.connect(self.whenchangedx)
        self.view.verticalScrollBar().valueChanged.connect(self.whenchangedy)

        # y axis that will show price
        yaxis = QtWidgets.QGraphicsScene(self)
        yaxis.setSceneRect(0, 0, 25, 525)
        #self.yaxis.addLine(12.5, 0, 12.5, 550, QtGui.QPen(QtCore.Qt.GlobalColor.gray))
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
        #xaxis.addLine(0, 12.5, 725, 12.5, QtGui.QPen(QtCore.Qt.GlobalColor.gray))
        self.xview = Axis(xaxis, self)
        self.xview.setGeometry(25, 550, 725, 25)
        self.xview.setFixedHeight(25)
        self.xview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.xview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.xview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.xview.setMouseFn(lambda: self.gridBox("x"))
        #self.xaxis.clear()
        #view.move(200, 0)

        # Add the axes widgets to a layout
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
        
        # Add the main graphics view and axes layout to the main window
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(axes_widget)
        main_layout.addWidget(y_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget = QtWidgets.QWidget(self)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def whenchangedx(self): # update x axis
        if not self.loading:
            self.view.scene().removeItem(self.crosshairx)
            self.view.scene().removeItem(self.crosshairy)
            # sender = self.view.sender() # hor. scrollbar
            # self.labelx.setText(str(sender.value()))
            self.xview.scene().clear()
            self.xview.scene().setSceneRect(0, 0, self.view.width(), 25)
            pen = None
            #self.xview.scene().addLine(0, 12.5, 725, 12.5, QtGui.QPen(QtCore.Qt.GlobalColor.gray)) # reset axis
            first = 0
            for x in range(int((self.view.width()+self.view.horizontalScrollBar().value()%self.gridconv[0])/self.gridconv[0])+1): # int((width+scroll%gridconv)/grid)
                offset = self.view.horizontalScrollBar().value()%self.gridconv[0]
                ind = self.view.horizontalScrollBar().value()-offset+x*self.gridconv[0] # values on the axis i.e. base-offset+x*grid
                val = int((ind/self.gridconv[0])*self.gridconv[1])+self.rangex[0] # convert from coordinate to time using (x/gridx)*gridt and add offset from range
                if x == 0: first = val

                if len(self.timeaxis) != 0: # when a time axis is present
                    shorts = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    dat = self.timeaxis[val].to_pydatetime() # get date from date list
                    lastdat = self.view.horizontalScrollBar().value()-offset+(x-1)*self.gridconv[0] # ind
                    lastdat = int((lastdat/self.gridconv[0])*self.gridconv[1])+self.rangex[0] # val
                    if lastdat < 0: # if index out of range
                        val = dat.year
                        pen = QtGui.QPen()
                        pen.setColor(QtCore.Qt.GlobalColor.black)
                    else:
                        lastdat = self.timeaxis[lastdat].to_pydatetime() # else get date of said index
                        if dat.year > lastdat.year: # year changed
                            val = dat.year
                            pen = QtGui.QPen()
                            pen.setColor(QtCore.Qt.GlobalColor.black)
                        elif dat.month > lastdat.month: # month changed
                            val = shorts[dat.month-1]
                            pen = QtGui.QPen()
                            pen.setColor(QtCore.Qt.GlobalColor.black)
                        elif dat.day > lastdat.day: # day changed
                            val = str(dat.day)
                            pen = QtGui.QPen()
                            pen.setColor(QtCore.Qt.GlobalColor.darkGray)
                            if int(val)%10 == 1 and val != "11": val += "st"
                            elif int(val)%10 == 2 and val != "12": val += "nd"
                            elif int(val)%10 == 3 and val != "13": val += "rd"
                            else: val += "th"
                        elif dat.hour > lastdat.hour: # hour changed
                            val = str(dat.hour) + "h"
                            pen = QtGui.QPen()
                            pen.setColor(QtCore.Qt.GlobalColor.lightGray)
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
                tex = QtWidgets.QGraphicsSimpleTextItem(str(val))

                if pen != None: tex.setPen(pen)
                tex.setPos(QtCore.QPointF(x*self.gridconv[0]-offset, 0)) # (x*gridconv-offset, 0)
                self.xview.scene().addItem(tex)
                pen = None
            self.view.scene().addItem(self.crosshairy)
            self.view.scene().addItem(self.crosshairx)
            #candind = int((first-self.candles[0][0])/(self.candles[1][0]-self.candles[0][0])) # x = (y-c)/m # ERROR
            # offset = self.view.verticalScrollBar().value()%self.gridconv[2] # look at whenchangey y for description
            # ind = self.view.verticalScrollBar().value()-offset
            # if self.candles[candind][1][1] > ((self.view.scene().height()-ind)/self.gridconv[2])*self.gridconv[3]+self.rangey[0]: # if high is above view
            #     pass
            # elif self.candles[candind][1][2] < ((self.view.scene().height()-ind)/self.gridconv[2])*self.gridconv[3]+self.rangey[0]: # if low is below view
            #     self.view.verticalScrollBar().setValue(550-(int(self.toCoord("y", self.candles[candind][1][2]))-550)) # set scrollbar to make low in view

    def whenchangedy(self): # update y axis
        if not self.loading:
            self.view.scene().removeItem(self.crosshairx)
            self.view.scene().removeItem(self.crosshairy)
            # sender = self.view.sender()
            # self.labely.setText(str(sender.value()))
            self.yview.scene().clear()
            self.yview.scene().setSceneRect(0, 0, 35, self.view.height())
            #self.yview.scene().addLine(12.5, 0, 12.5, 550, QtGui.QPen(QtCore.Qt.GlobalColor.gray)) # reset axis
            for y in range(int((self.view.width()+self.view.verticalScrollBar().value()%self.gridconv[2])/self.gridconv[2])+1): # int((height+scroll%gridconv)/grid)
                offset = self.view.verticalScrollBar().value()%self.gridconv[2]
                ind = self.view.verticalScrollBar().value()-offset+y*self.gridconv[2]
                val = int(self.view.scene().height()-ind) # first convert to normal coordinates (y up, screen up)
                val = (val/self.gridconv[2])*self.gridconv[3]+self.rangey[0]
                offset += 7.5
                offx = 0
                if val < 10: # for centering
                    offx += 9
                elif val < 100:
                    offx += 5
                elif val < 1000:
                    offx += 3
                tex = QtWidgets.QGraphicsSimpleTextItem(str(val))
                
                tex.setPos(QtCore.QPointF(offx, y*self.gridconv[2]-offset)) # (y*gridconv-offset, 0)
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
        # self.scene.addItem(Candle(self.toCoord("x", 100), self.toCoord("y", 120))) 
        # self.scene.addItem(Candle(self.toCoord("x", 300), self.toCoord("y", 100))) 
        if self.chartchecks[0].isChecked(): # if Candlesticks is checked
            for c in self.candles:
                can = Candle(c[0], c[1])
                if len(self.timeaxis) != 0: 
                    dat = self.timeaxis[c[0]-self.rangex[0]].to_pydatetime()
                    can.date = dat
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                self.view.scene().addItem(can)
        else: # graph depiction
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
                can.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.blue))
                self.view.scene().addItem(can)
        
        # crosshair
        pen = QtGui.QPen(QtCore.Qt.GlobalColor.black)
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

        self.loading = False
    
    def updateCrosshair(self, event): # update the crosshair when mouse moved, fn will pe passed on
        pointf = QtCore.QPointF(event.pos().x(), event.pos().y()) # preconvert because else it wont accept
        scene_pos = self.view.mapFromScene(pointf)

        dx = self.view.horizontalScrollBar().value()*2 # also add the change of the scrolling to the crosshair
        dy = self.view.verticalScrollBar().value()*2

        self.crosshairy.setLine(scene_pos.x()+dx, scene_pos.y()-1500+dy, scene_pos.x()+dx, scene_pos.y()+1500+dy)
        self.crosshairx.setLine(scene_pos.x()-2000+dx, scene_pos.y()+dy, scene_pos.x()+2000+dx, scene_pos.y()+dy)


    def readstocks(self, which: str, what: str): # read in a stock and pass it to the candles
        global raw
        self.timeaxis = [] # reset date axis
        #isError = False
        toload = ""
        if what == "quick":
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
            raw = []
            raw.append(read(toload))
        else:
            readtest = read(which, True)
            if len(readtest) == 0:
                self.errormsg(which.split("/")[-1] + " is not a valid file.")
                return
            raw = []
            raw.append(readtest)
        self.newScene()
        #print("done")
    
    def newScene(self):
        self.loading = True # turn off scrolling while its loading
        self.candles = [] # empty candles
        self.rangex = (0, len(raw[0]))
        mi = 10000 # minimum value
        ma = 0 # maximum value
        for t in range(len(raw[0])): 
            if raw[0][t][1] > ma: ma = raw[0][t][1]
            if raw[0][t][2] < mi: mi = raw[0][t][2]
            l = [t] # [time, [o, h, l, c]]
            l.append([raw[0][t][0], raw[0][t][1], raw[0][t][2], raw[0][t][3]])
            self.candles.append(l)
        totran = ma-mi # total range
        tenpow = -5
        #bits = int(100*totran/20)/100 # normal divisor
        while totran > 2*pow(10, tenpow): # get nearest power of 10 * 2
            tenpow += 1
        self.rangey = (int(mi), ma)
        self.gridconv = [40, 5, 40, ceil(pow(10, tenpow-2))]
        self.setScene()

    
        

app = QtWidgets.QApplication(sys.argv)

window = GUI()

window.show()

app.exec()


# hiscores = []
# gains = []
# succs = []
# rs = []

# generation simulation
#fil = open("Scor.txt", "w")
#prep_stocks()
# print("Starting simulation...")
# for g in range(gens):
#     print("Preparing new generation...\n")
#     precalculate(players)
#     print("Generation " + str(g+1) + "\n")
#     startmoney = 10000
#     start = randint(0, 1000)
#     timeframe = start + 1000
#     scores = []
#     print("Player 1 -- score:") # filler text that gets deleted afterwards
#     print(0)
#     for player in players:
#         print("\033[A                                                   \033[A")
#         print("\033[A                                                   \033[A")
#         print("Player " + str(len(scores) + 1) + " -- score:")
#         print(0)
#         storr = [] # store r values
#         for stock in usedstocks:
#             quickmu = []
#             player.confidences = []
#             time = start
#             money = startmoney
#             player.lasttime = time
#             am200 = int(ceil(200/raw[stock][0][3])) # get the amount for 200 dollars so that each buy costs about the same amnt of money
#             player.outs[0] = am200 # set basic amount
#             while time < timeframe: # timeframe for stock simulation
#                 timestep(stock, player)
#             sell_all()
#             player.average += money-startmoney # add balance change to average
#             if max(player.confidences) == min(player.confidences): pass # can't make corrcoef if the whole graph is just 0 or 1
#             else: player.r += corrcoef(player.confidences, quickmu)[0, 1]
#             print("\033[A                                                   \033[A")
#             print(player.r)#fraction[0]/(player.fraction[0]+player.fraction[1]+0.000000001)) # 0.0000000001 so won't divide by 0
#             storr.append(abs(player.r))
#         player.average /= numsts # get average change
#         player.r = min(storr) # get min r
#         player.lastscore = 0.25*player.lastscore + abs(player.r)#*player.average*tradefactor(player.fraction[0]+player.fraction[1]) | only r for now
#         #fil.write("\n" + " "+ str(abs(player.r)) + " " + str(player.average) + " "+ str(player.fraction[0]+player.fraction[1]+0.000000001))
#         if player.fraction[1] > 0: temp = player.fraction[0]/(player.fraction[0]+player.fraction[1]) # rate of success
#         elif player.fraction[0] > 0: temp = 1 # if no failures are present and at least 1 success then 100% success
#         else: temp = 0 # if neither are present then 0% success
#         scores.append((players.index(player), player.r, player.score, player.average, temp, player.lastscore))
#         #abs(player.r)*player.average/(player.fraction[0]+player.fraction[1]+0.000000001))) 
#         # (index, r, score, gains in $, succ. rate)
#     scores = sorted(scores, key=lambda x: x[5])
#     scores.reverse()
#     templist = []
#     for i in range(len(scores)): # if score == 0
#         if scores[len(scores)-1-i][1] == 0:
#             templist.append(len(scores)-1-i)
#     for i in templist:
#         scores.pop(i)
#     print("\nGains: " + str(round(scores[0][3], 2)) + "$ Success rate: " + str(scores[0][4]) + " Score: " + str(round(scores[0][2], 2)) + " r: " + 
#     str(round(scores[0][1], 3)))
#     #print(players[scores[0][0]].savestring())
#     #\nMidscore: " + str(round(scores[len(players)//2][2], 2)) + " Success rate: " + str(scores[len(players)//2][1]) + " Gains: " + str(round(scores[len(players)//2][3], 2)) +"$")
#     hiscores.append(scores[0][2])
#     gains.append(scores[0][3])
#     succs.append(scores[0][4])
#     rs.append(scores[0][1])
#     templist = []
#     temp = len(players)
#     if g < gens-1: # only mutate if there is a next generation
#         print("Advancing to next generation...")
#         p = 0
#         while len(templist) < temp//2: # get top 50 % of players
#             #if not (scores[p][2] > -5 and scores[p][2] < 5 and scores[p][3] < 10): # if not (-5 < hiscore < 5 and gains < 10); add
#             #if not (scores[p][4] == 0 or (scores[p][4] == 1 and scores[p][2] < 5)): # if succ == 0% or succ = 100% and score < 50%; dont add
#             templist.append(players[scores[p][0]])
#             p += 1
#             if p > len(players)-1 or p > len(scores)-1: break # if for some reason more then half are failures
#         players = templist # set only top 50 % of players
#         for p in players: # reset player scores
#             p.reset()
#         temlen = len(players) # length of players with failures removed
#         if temlen == 0: players.append(Player())
#         for i in range(temp-temlen):
#             ranpl = randint(0, temlen-1) # random player to modify
#             gen = randint(0, 3) # what to do with player
#             if len(players[ranpl].cells) <= 1 and gen == 1: # if player has / would have no more cells left, add cell
#                 gen = 0
#             players.append(deepcopy(players[ranpl])) # copy player and place in spot -1
#             if gen == 2: # replace
#                 ranpl2 = randint(0, temlen-1) # player 2 to take from | also could happen that player mutates with self
#                 while ranpl2 != ranpl or len(players[ranpl2].cells) == 0:
#                     ranpl2 = randint(0, temlen-1)
#                 rancell = randint(0, len(players[ranpl2].cells)-1) # pick random cell index
#                 players[-1].mutate(2, players[ranpl2].cells[rancell]) # replace cell with new one in new player
#             else:
#                 players[-1].mutate(gen)
#             players[-1].lastscore = 0
#             players[-1].de_failure() # remove players that never activate
#         players = remove_clones(players) # remove duplicate players
#         for i in range(temp-len(players)): # if players were removed
#             players.append(Player(cellnum=randint(1, 6))) # fill in new ones with at least 1 cell
#         if True:#(g+1) % batchn == 0 and g != 0: # if n batches have happened
#             print("Reshuffling stock data...")
#             prep_stocks()
#             # start = randint(0, 1000)
#             # timeframe = start + 1000

#fil.close()

# for each in players:
#     print(each.savestring())

# file = open("Algorithm Results\\" + version + "_" + str(gens) + "-" + str(plnum)+ "_r.txt", "w")
# file.write("Gain,Score,Success,r\n")
# for h in range(len(hiscores)):
#     #file.write(str(gains[h]) + "," + str(hiscores[h]) + "," + str(succs[h]) + "," +str(rs[h]) + "\n")
#     file.write(str(rs[h])+ "\n")
# file.close()

# file = open("Algorithm Results\\" + version + "_" + str(gens) + "-" + str(plnum)+ "_r.plr", "w")
# for pl in players:
#     file.write(pl.savestring() + "\n")
# file.close()
