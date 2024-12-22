import pathlib
from math import isnan, ceil, exp, sqrt
import pandas as pd
from random import SystemRandom
from copy import deepcopy
from numpy import corrcoef

# 3/2/2023
version = "1.2.0" 

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
"bollingerwidth", "volume", "peak", "valley"]
comps = ["movavg", "expavg", "contested", "meanrise", "bollinger"] # meanrise not part of conditions just in here fro convenience
pres = [] # will store precalculated complex conditions | shape = (stock, comps, (either 1 or how many of one kind there are), (either len(stock) or similar))
preinds = [] # will store the f.e. windows of the moving averages so: preinds = [[100, 200]]; precalcs[0][0][preinds[0].index(200)]

def randint(low, high): # different random function to improve randomness
    high = int(high + 1)
    low = int(low)
    n = SystemRandom().random() # random seed
    for i in range(1, high-low):
        if (n <= i/(high-low)): return i - 1 + low # if max = 4 and min = 0: if 0.2143124 < 1/4: return 0
    return high - 1

def read(x): # get 2 year hourly data from 1/20/2023
    pat = os.path.join(root_dir, "read", f"{x}.txt")
    path = pathlib.Path(pat)
    if not path.exists(): 
        return [] # check if file exists in dataset else return empty list
    file = open("2Yh Data\\" + x + ".txt")
    op = []
    # hi = []
    # lo = []
    # cl = []
    # vo = []
    lines = file.read() # read the lines
    lins = lines.splitlines() # split lines when \n is present
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
    #together = [op, hi, lo, cl, vo] # list of lists that contains all the data for the stock
    return op

# if all are loaded ~ 4gb of ram
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
del got, runs, rn, stocks, read#stock_evals, read # delete unused variables

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
    # if len(stock)-1 > spot + 16:
    #     last = spot # set it to now
    #     for i in range(16):
    #         if stock[last][3] < stock[spot+i][3]: last = spot+i # look if it is larger than
    #     return stock[last][3] > stock[spot][3] # if a rise is present

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
                # rem = -1
                # i = 0
                # for cell in self.cells:
                #     if cell.spot == self.cells[ran].spot and i != ran:
                #         rem = self.cells.index(cell) # look if cell exists in spot already
                #     i += 1
                # if rem != -1:
                #     self.cells.pop(rem) # remove cell
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

def cellcomp(c1, c2): # compares if 2 cells are the same
    if c1.condition != c2.condition: return False # if conditions don't match
    if c1.spot != c2.spot: return False # if spot doesn't match
    if c1.condition in ["movavg", "expavg"] or "bollinger" in c1.condition: # ma check | only for ones that actually matter
        if c1.ma != c2.ma: return False
    return True


def same(pl1, pl2): # looks if 2 players are the same
    if len(pl1.cells) != len(pl2.cells): return False # different amount of cells
    for c in range(len(pl1.cells)):
        if not cellcomp(pl1.cells[c], pl2.cells[c]): return False # if cells don't match up
    if pl1.weight != pl2.weight: return False # if weights don't match up
    if pl1.bias != pl2.bias: return False # if biases don't match up
    if pl1.outws != pl2.outws: return False # if order weights don't match up
    return True

def remove_clones(players): # removes duplicate players and returns player list
    newp = players
    remlist = []
    cont = True
    while cont:
        for p in range(len(newp)):
            for pl in range(len(newp)):
                if p != pl and same(newp[p], newp[pl]): # checks if two players are the same
                    remlist.append(pl)
                if len(remlist) > 0: break
            if len(remlist) > 0: break
            if p == len(newp)-1: cont = False # if every player has been checked
        for r in remlist:
            newp.pop(r) # remove players
        remlist = []
    return newp

players = []
plnum = 750 # number of players
gens = 75 # number of generations
batchn = 0 # number of generations before stocks get reshuffled
temp = [-1, 0]
while temp[0] == -1:
    if gens <= 50*pow(2, temp[1]): # makes it so that only 10 batches are possible at once
        temp[0] = 0
    else:
        temp[1] += 1

batchn = 5*pow(2, temp[1])
del temp


for i in range(plnum):
    players.append(Player(is_rand=False, readstr="1+1+1+0+0+0+1.001+.996+.966+1.025+1.047+peak/0/247/1.2/%"))
usedstocks = [] # what stocks are used in a generation
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
                elif "trend" in c.condition: tc = 2 # calculate contested ateas if trendline is wanted in any way
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

def tradefactor(nTrades): # so that over/undertrading is punished
    CONST = 0.00000042292379259074
    return exp(-CONST*pow(nTrades-3000, 2))

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

hiscores = []
gains = []
succs = []
rs = []

# generation simulation
#fil = open("Scor.txt", "w")
prep_stocks()
print("Starting simulation...")
for g in range(gens):
    print("Preparing new generation...\n")
    precalculate(players)
    print("Generation " + str(g+1) + "\n")
    startmoney = 10000
    start = randint(0, 1000)
    timeframe = start + 1000
    scores = []
    print("Player 1 -- score:") # filler text that gets deleted afterwards
    print(0)
    for player in players:
        print("\033[A                                                   \033[A")
        print("\033[A                                                   \033[A")
        print("Player " + str(len(scores) + 1) + " -- score:")
        print(0)
        storr = [] # store r values
        for stock in usedstocks:
            quickmu = []
            player.confidences = []
            time = start
            money = startmoney
            player.lasttime = time
            am200 = int(ceil(200/raw[stock][0][3])) # get the amount for 200 dollars so that each buy costs about the same amnt of money
            player.outs[0] = am200 # set basic amount
            while time < timeframe: # timeframe for stock simulation
                timestep(stock, player)
            sell_all()
            player.average += money-startmoney # add balance change to average
            if max(player.confidences) == min(player.confidences): pass # can't make corrcoef if the whole graph is just 0 or 1
            else: player.r += corrcoef(player.confidences, quickmu)[0, 1]
            print("\033[A                                                   \033[A")
            print(player.r)#fraction[0]/(player.fraction[0]+player.fraction[1]+0.000000001)) # 0.0000000001 so won't divide by 0
            storr.append(abs(player.r))
        player.average /= numsts # get average change
        player.r = min(storr) # get min r
        player.lastscore = 0.25*player.lastscore + abs(player.r)#*player.average*tradefactor(player.fraction[0]+player.fraction[1]) | only r for now
        #fil.write("\n" + " "+ str(abs(player.r)) + " " + str(player.average) + " "+ str(player.fraction[0]+player.fraction[1]+0.000000001))
        if player.fraction[1] > 0: temp = player.fraction[0]/(player.fraction[0]+player.fraction[1]) # rate of success
        elif player.fraction[0] > 0: temp = 1 # if no failures are present and at least 1 success then 100% success
        else: temp = 0 # if neither are present then 0% success
        scores.append((players.index(player), player.r, player.score, player.average, temp, player.lastscore))
        #abs(player.r)*player.average/(player.fraction[0]+player.fraction[1]+0.000000001))) 
        # (index, r, score, gains in $, succ. rate)
    scores = sorted(scores, key=lambda x: x[5])
    scores.reverse()
    templist = []
    for i in range(len(scores)): # if score == 0
        if scores[len(scores)-1-i][1] == 0:
            templist.append(len(scores)-1-i)
    for i in templist:
        scores.pop(i)
    print("\nGains: " + str(round(scores[0][3], 2)) + "$ Success rate: " + str(scores[0][4]) + " Score: " + str(round(scores[0][2], 2)) + " r: " + 
    str(round(scores[0][1], 3)))
    #print(players[scores[0][0]].savestring())
    #\nMidscore: " + str(round(scores[len(players)//2][2], 2)) + " Success rate: " + str(scores[len(players)//2][1]) + " Gains: " + str(round(scores[len(players)//2][3], 2)) +"$")
    hiscores.append(scores[0][2])
    gains.append(scores[0][3])
    succs.append(scores[0][4])
    rs.append(scores[0][1])
    templist = []
    temp = len(players)
    if g < gens-1: # only mutate if there is a next generation
        print("Advancing to next generation...")
        p = 0
        while len(templist) < temp//2: # get top 50 % of players
            #if not (scores[p][2] > -5 and scores[p][2] < 5 and scores[p][3] < 10): # if not (-5 < hiscore < 5 and gains < 10); add
            #if not (scores[p][4] == 0 or (scores[p][4] == 1 and scores[p][2] < 5)): # if succ == 0% or succ = 100% and score < 50%; dont add
            templist.append(players[scores[p][0]])
            p += 1
            if p > len(players)-1 or p > len(scores)-1: break # if for some reason more then half are failures
        players = templist # set only top 50 % of players
        for p in players: # reset player scores
            p.reset()
        temlen = len(players) # length of players with failures removed
        if temlen == 0: players.append(Player())
        for i in range(temp-temlen):
            ranpl = randint(0, temlen-1) # random player to modify
            gen = randint(0, 3) # what to do with player
            if len(players[ranpl].cells) <= 1 and gen == 1: # if player has / would have no more cells left, add cell
                gen = 0
            players.append(deepcopy(players[ranpl])) # copy player and place in spot -1
            if gen == 2: # replace
                ranpl2 = randint(0, temlen-1) # player 2 to take from | also could happen that player mutates with self
                while ranpl2 != ranpl or len(players[ranpl2].cells) == 0:
                    ranpl2 = randint(0, temlen-1)
                rancell = randint(0, len(players[ranpl2].cells)-1) # pick random cell index
                players[-1].mutate(2, players[ranpl2].cells[rancell]) # replace cell with new one in new player
            else:
                players[-1].mutate(gen)
            players[-1].lastscore = 0
            players[-1].de_failure() # remove players that never activate
        players = remove_clones(players) # remove duplicate players
        for i in range(temp-len(players)): # if players were removed
            players.append(Player(cellnum=randint(1, 6))) # fill in new ones with at least 1 cell
        if True:#(g+1) % batchn == 0 and g != 0: # if n batches have happened
            print("Reshuffling stock data...")
            prep_stocks()
            # start = randint(0, 1000)
            # timeframe = start + 1000

#fil.close()

# for each in players:
#     print(each.savestring())

file = open("Algorithm Results\\" + version + "_" + str(gens) + "-" + str(plnum)+ "_r.txt", "w")
file.write("Gain,Score,Success,r\n")
for h in range(len(hiscores)):
    #file.write(str(gains[h]) + "," + str(hiscores[h]) + "," + str(succs[h]) + "," +str(rs[h]) + "\n")
    file.write(str(rs[h])+ "\n")
file.close()

file = open("Algorithm Results\\" + version + "_" + str(gens) + "-" + str(plnum)+ "_r.plr", "w")
for pl in players:
    file.write(pl.savestring() + "\n")
file.close()
