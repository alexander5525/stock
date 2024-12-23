# Stock Sim Version 1.0
# Author: alexander5525
# Started: 11/25/2023
# Description: Stock strategy analyzer that allows external strategies to be tested, thoroughly analyzed and reviewed and be tested on s&p 500 live data
# Note: Please provide proper attribution if reusing any part of this code.
import pathlib
from math import isnan, ceil, exp, sqrt, sin, asin, cos, acos, tan, atan, pi, floor, log10
import typing
from PyQt6.QtWidgets import QWidget
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
from xml.etree import ElementTree as ET
from importlib import util
import stocklib
from functools import partial

def playsound(which="Error"): # For the error sound
    if which == "Error": winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
    elif which == "Asterisk": winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
    elif which == "Exclamation": winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)

# based on sim version = "1.2.1" 
version = "1.0"

theme = "dark"
look = "Windows"

if theme == "light": # for light theme
    dockstring = "QDockWidget::title { background-color: #A0A0A0; border: 2px solid #BEBEBE;}"
    widgetstring = "background-color: #ffffff; border: 2px inset #A0A0A0;"
else: # for dark theme
    dockstring = "QDockWidget::title { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0A246A, stop:1 #A6CAF0); border: 2px solid #BEBEBE;}"
    widgetstring = "background-color: #191919; border: 2px inset #666666;"

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

raw = [[]] # raw y2h stock data

# available indicators

visinds = ["Volume", "SMA", "EMA", "VWAP", "RSI", "MACD", "BollingerBands", "GaussianChannel", "ATR"]
objinds = {} # indicator objects

for v in visinds:
    objinds[v] = getattr(stocklib, v)() # make objects from each class

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
    date = [d.to_pydatetime().replace(tzinfo=None) for d in date] # convert from pandas to pydatetime
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
        file = open(path)
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
        self.type = stty # order type
        self.amnt = number
        self.stop = stlo
        self.take = tapr
        self.trai = perc
        self.time = time # save for evaluation purposes
        self.fees = fee
        self.reviewVals = {} # dictionary for variables

def near(a, b, n): # rounds a and b to n digits and checks if they're the same
    return round(a, n) == round(b, n) # if a rounded = b rounded then they're really close

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

def rateSurrounding(stock, spot, fn, n, threshold=0.55): # get the surrounding n values (spot-n/2<spot<spot+n/2) and rate how close the spot was to nearest peak/valley
    vals = []
    for s in range(n+1):
        sp = spot+s-n//2
        if sp < 0:
            vals.append(0)
        else:
            vals.append(fn(stock, sp, n))
    peakfilter = [] # all peaks filtered with true or false
    valfilter = [] 
    for i in range(len(vals)):
        if i == 0: ran = [float("nan")] + vals[:2]
        elif i == n: ran = vals[-2:] + [float("nan")]
        else: ran = vals[i-1:i+2]
        if ran.index(nanmax(ran)) == 1 and vals[i] > threshold:
            peakfilter.append(True)
        else: peakfilter.append(False)
        if ran.index(nanmin(ran)) == 1 and vals[i] < -threshold:
            valfilter.append(True)
        else: valfilter.append(False)
    if peakfilter[n//2]: peak = 0 # if peak is at spot
    else:
        half = peakfilter[:n//2]
        half.reverse()
        if True in half: peak = -half.index(True) # get index of the first true | negative because it's before the spot
        else: peak = float("nan")
        half = peakfilter[n//2+1:]
        if True in half: temp = half.index(True)
        else: temp = float("nan")
        if peak != peak or abs(peak) > temp: peak = temp # if peak in top half is closer; take that index

    if valfilter[n//2]: valley = 0 # if valley is at spot
    else:
        half = valfilter[:n//2]
        half.reverse()
        if True in half: valley = -half.index(True) # get index of the first true | negative because it's before the spot
        else: valley = float("nan")
        half = valfilter[n//2+1:]
        if True in half: temp = half.index(True)
        else: temp = float("nan")
        if valley != valley or abs(valley) > temp: valley = temp # if valley in top half is closer; take that index
    
    if peak != peak: peak = float("inf") # if peak is nan
    if valley != valley: valley = float("inf")

    return peak, valley

def numtostr(number, roundto=3): # for better readability in the plr files
    if type(number) == int: # if int return normal string
        return str(number)
    number = round(number, roundto) # round so it doesn't get too cluttered
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

def coordinate(what: str, value, gridc, rx, ry, height):
    if what == "x":
        coord = (gridc[0]*(value-rx[0]))/gridc[1]
        return coord
    elif what == "y":
        coord = height-(gridc[2]*(value-ry[0]))/gridc[3]
        return coord

class Group(): # group item for common stock groups
    def __init__(self, name, items, links):
        self.name = name
        self.items = items
        self.links = links

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

class Dot(QtWidgets.QGraphicsItem):
    def __init__(self, x, y, shape, color, parent=None):
        super().__init__(parent)
        self.text = "Default"
        # self.time = date
        self.x = x
        self.y = y
        # self.up = up
        self.shap = shape
        self.color = color
        self.wid = 10
        self.hei = 10
        self.points = {}
        self.tool = "" # tooltip
        self.setAcceptHoverEvents(True)
        
    def convCoords(self, gridc, rx, ry, height):
        self.x = coordinate("x", self.x, gridc, rx, ry, height)
        self.y = coordinate("y", self.y, gridc, rx, ry, height) #abs(self.ohlc[0]-self.ohlc[3])*(gridc[2]/gridc[3]) # dp*px per np/ p per npx
        if self.shap == "upTriangle": 
            self.points["Vertices"] = [QtCore.QPointF(self.x, self.y+self.hei), QtCore.QPointF(self.x+self.wid, self.y+self.hei), QtCore.QPointF(self.x+self.wid/2, self.y)]
        elif self.shap == "downTriangle": 
            self.points["Vertices"] = [QtCore.QPointF(self.x, self.y), QtCore.QPointF(self.x+self.wid, self.y), QtCore.QPointF(self.x+self.wid/2, self.y+self.hei)]

    def boundingRect(self): # important for boundaries
        return QtCore.QRectF(self.x, self.y, self.wid, self.hei) # rect
        
    def paint(self, painter, option, widget):
        painter.setPen(QtGui.QColor(self.color))
        painter.setBrush(QtGui.QColor(self.color))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        if "Triangle" in self.shap:
            tri = QtGui.QPolygonF(self.points["Vertices"]) # triangle made out of vertices
            painter.drawPolygon(tri)
        elif self.shap == "Circle":
            cir = QtCore.QRectF(self.x, self.y, self.wid, self.hei) # define rect as outer boundaries of circle
            painter.drawEllipse(cir)
        
    def hoverEnterEvent(self, event): # Tooltip
        self.setToolTip(self.tool)

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
        self.stockInfo = ["", "", ""] # [ticker, period, spot]
        self.spot = -1 # special spot to display (-1 for last)
        self.rects = [] # rects that will be displayed in the scene | [[x1, y1, x2, y2, color]]
        self.dates = [] # when filled, will assign dates to candles of the same spot
        self.isLive = False # whether to use live date (has no use here)
        self.visinds = [] # list of stockdata visuals that will be displayed
    
    def setMouseFn(self, function): # for Crosshair
        self.mouseFunction = function

    def setInfoFn(self, function):
        self.leftFn = function
    
    def makeScene(self): # same as setScene for gui
        if self.spot == -1: start = 229
        elif self.spot < 70: start = 0
        else: start = self.spot - 70
        end = start + 70
        if end > len(self.candles): end = len(self.candles)
        sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
        self.heivar = sizy
        self.scene().clear()
        self.scene().setSceneRect(0, 0, self.pxSize[0]-10, self.pxSize[1]-10)
        grid = Grid(QtCore.QRectF(-5, -5, self.pxSize[0], self.pxSize[1]))
        grid.density = self.density
        self.scene().addItem(grid)
        for rect in self.rects:
            conrect = []
            for i in range(4):
                if i%2 == 0: what = "x"
                else: what = "y"
                conrect.append(coordinate(what, rect[i], self.gridconv, self.rangex, self.rangey, self.heivar))
                # if conrect[-1] < 0: conrect[-1] = 0
                # if what == "y" and conrect[-1] > self.pxSize[1]: conrect[-1] = self.pxSize[1] - 1 
            if conrect[1] > conrect[3]:
                temp = conrect[1]
                conrect[1] = conrect[3]
                conrect[3] = temp
            recc = QtCore.QRectF(conrect[0], conrect[1], abs(conrect[0]-conrect[2]), abs(conrect[1]-conrect[3]))
            self.scene().addRect(recc, QtGui.QPen(QtCore.Qt.PenStyle.NoPen), QtGui.QColor(rect[4]))
        if self.dMode == 0: # if Candlesticks is checked 
            i = start
            for c in self.candles[start:end]: 
                can = Candle(i, c)
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                if len(self.dates) != 0:
                    can.date = self.dates[i]#.to_pydatetime()
                #print(can.x, can.y)
                self.scene().addItem(can)
                i += 1
            #print(can.y)
        elif self.dMode == 2: # heikin-ashi
            # first candle
            c = deepcopy(self.candles[start])
            last = Candle(0, c)
            last.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
            self.scene().addItem(last)
            i = start+1
            for c in self.candles[start+1:end+1]: # all except first one
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
                for i in range(start, end): # do same as graph
                    c = [self.candles[i], self.candles[i+1]] # for simplification
                    for e in range(2):
                        c[e] = Candle(i+e, c[e])
                        c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                    if i != end:
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
        # mi = float("inf") # minimum value
        # ma = float("-inf") # maximum value
        # if self.isVolume:
        #     # get max and min volume
        #     pass
        # else:
        #     for g in self.graphInds:
        #         gg = [x for x in g if not isnan(x)] # remove all nan values from list
        #         if min(gg) < mi: mi = min(gg)
        #         if max(gg) > ma: ma = max(gg)
        #     self.rangey = (mi, ma)
        self.rangey = self.visinds["rangey"]
        # 150 is height of smallview
        # grc3 = (totran*grc2)/npx
        self.gridconv[3] = ((self.rangey[1]-self.rangey[0])*self.gridconv[2])/150
                
        sizy = ((self.rangey[1]-self.rangey[0])/self.gridconv[3])*self.gridconv[2] # ((p-p0)/how many p per pixel)*npixels
        self.heivar = sizy
        self.scene().clear()
        self.scene().setSceneRect(0, 0, self.sizx, 150)
        self.scene().addItem(Grid(QtCore.QRectF(0, 0, self.sizx, 150), self.gridconv))
        
        for v in self.visinds:
            if v not in ["rangey", "gridconv"]: # show everything except viewer parameters
                ob = self.visinds[v]
                if ob.name == "line":
                    if type(ob.data) == str: # if a reference was given
                        data = self.graphInds[ob.data]
                    elif type(ob.data) in (int, float): data = len(self.candles)*[ob.data]
                    else: data = ob.data
                    for i in range(len(self.candles)-1): # do same as graph
                        if type(ob.color) == str: color = ob.color
                        else: color = ob.color[i]
                        c = [self.candles[i], self.candles[i+1]] # for simplification
                        for e in range(2):
                            c[e] = Candle(i+e, c[e])
                            c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                        if i != len(self.candles)-1:
                            close1 = coordinate("y", data[i], self.gridconv, self.rangex, self.rangey, self.heivar) # get positions
                            close2 = coordinate("y", data[i+1], self.gridconv, self.rangex, self.rangey, self.heivar)
                        if not (close1 != close1 or close2 != close2): # nan check
                            can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                            pen = QtGui.QPen(QtGui.QColor(color))
                            if ob.shape == "dashed": pen.setStyle(QtCore.Qt.PenStyle.DashLine)
                            elif ob.shape == "dotted": pen.setStyle(QtCore.Qt.PenStyle.DotLine)
                            elif ob.shape == "dashdot": pen.setStyle(QtCore.Qt.PenStyle.DashDotLine)
                            can.setPen(pen)
                            self.scene().addItem(can)
                elif ob.name == "rect":
                    if ob.shape in ["f2", "r2"]: # if rect between 2 graphs
                        if type(ob.data) == str:
                            data = (self.graphInds[ob.data.split(",")[0]], self.graphInds[ob.data.split(",")[1]])
                        else:
                            data = ob.data # ob.data has to be a tuple of 2 lists
                    data = list(data)
                    for i in range(2):
                        if type(data[i]) in (int, float): # make lists of only that number
                            data[i] = len(self.candles)*[data[i]]
                        elif type(data[i]) == str: # copy data from indicator
                            data[i] = self.graphInds[data[i]]
                    # elif type(ob.data) == str:
                    #     data = ind.data[ob.data]
                    # else: data = ob.data
                    # update this code if rect without 2 bounds
                    if "f" in ob.shape:
                        for i in range(len(self.candles)-1): # do same as graph
                            if type(ob.color) == str: color = ob.color
                            else: color = ob.color[i]
                            c = [self.candles[i], self.candles[i+1]] # for simplification
                            for e in range(2):
                                c[e] = Candle(i+e, c[e])
                                c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                            if i != len(self.candles)-1:
                                vertices = []
                                for j in range(2):
                                    if data[j][i] != data[j][i]: break # nan check
                                    y = coordinate("y", data[j][i], self.gridconv, self.rangex, self.rangey, self.heivar)
                                    vertices.append(QtCore.QPointF(c[0].x+c[0].wid/2, y)) # get positions
                                    y = coordinate("y", data[j][i+1], self.gridconv, self.rangex, self.rangey, self.heivar)
                                    vertices.append(QtCore.QPointF(c[1].x+c[1].wid/2, y))
                            if len(vertices) == 4:
                                # for cool effect remove
                                vertices.append(vertices.pop(2)) # change order
                                pol = QtWidgets.QGraphicsPolygonItem(QtGui.QPolygonF(vertices))
                                pol.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))#(QtGui.QColor(color))
                                pol.setBrush(QtGui.QColor(color))
                                self.scene().addItem(pol)
                    else:
                        for i in range(len(self.candles)):
                            if type(ob.color) == str: color = ob.color
                            else: color = ob.color[i]
                            c = self.candles[i] # for simplification
                            c = Candle(i, c)
                            c.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                            x = c.x
                            ys = [coordinate("y", data[0][i], self.gridconv, self.rangex, self.rangey, self.heivar), 
                                  coordinate("y", data[1][i], self.gridconv, self.rangex, self.rangey, self.heivar)]
                            wid = c.wid
                            hei = abs(ys[0] - ys[1])
                            ys.sort() # sort so that lowest is the first index
                            if not (hei != hei): # hei cant be nan
                                rect = QtWidgets.QGraphicsRectItem(x, ys[0], wid, hei)
                                rect.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))#(QtGui.QColor(color))
                                rect.setBrush(QtGui.QColor(color))
                                self.scene().addItem(rect)

        # # volume
        # if self.isVolume: # only display volume bars
        #     vols = []
        #     for c in self.candles:
        #         vols.append(c[4])
        #     mx = max(vols) # max volume
        #     mn = min(vols) # min volume
        #     for i in range(len(vols)):
        #         hei = vols[i] - mn 
        #         hei = 150*(hei/(mx-mn)) # map to 1 - 50
        #         can = Candle(i, self.candles[i])
        #         can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
        #         rect = QtCore.QRectF(can.x, self.scene().height()-hei, can.wid, hei)
        #         nopen = QtGui.QPen(QtCore.Qt.PenStyle.NoPen)
        #         self.scene().addRect(rect, nopen, self.colors[0])

        # # indicators
        # if len(self.graphInds) != 0: # if indicators are used
        #     j = 0
        #     for ind in self.graphInds: # for every graph indicator
        #         for i in range(len(self.candles)-1): # do same as graph
        #             c = [self.candles[i], self.candles[i+1]] # for simplification
        #             for e in range(2):
        #                 c[e] = Candle(i+e, c[e])
        #                 c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
        #             if i != len(self.candles)-1:
        #                 close1 = coordinate("y", ind[i], self.gridconv, self.rangex, self.rangey, self.heivar) # get positions
        #                 close2 = coordinate("y", ind[i+1], self.gridconv, self.rangex, self.rangey, self.heivar)
        #             can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
        #             can.setPen(self.colors[j])
        #             self.scene().addItem(can)
        #         j += 1

        # # text annotations
        # j = 0
        # for a in self.annotations:
        #     tex = SimpleText(a[0], self.colors[j], QtCore.QPointF(a[1], a[2]))
        #     self.scene().addItem(tex)
        #     j += 0

    def initScene(self): # same as newScene for gui
        self.marked = [] # reset marked spots
        if self.spot != -1: # focus on the spot and the 60 around the spot
            self.rangex = (self.spot-60, self.spot)

        mi = 10000 # minimum value
        ma = 0 # maximum value
        avg = 0 # avg body size
        processed = 0
        for t in range(60): # get last 60 candles
            if self.spot == -1: t = -t-1
            else: t = self.spot-t
            if self.spot == -1 or (self.spot != -1 and t >= 0): 
                avg += abs(self.candles[t][3] - self.candles[t][0])
                processed += 1
            if self.candles[t][1] > ma: ma = self.candles[t][1]
            if self.candles[t][2] < mi: mi = self.candles[t][2]
        avg /= processed
        tenpows = [0.0005]
        while tenpows[-1] < avg: # fill up the list
            if str(1000/tenpows[-1])[0] == "4": # multiple of 2.5
                tenpows.append(tenpows[-1]*2)
            else: tenpows.append(tenpows[-1]*5)
        contenders = [abs(avg/tenpows[-2]-1), abs(avg/tenpows[-1]-1)]
        if contenders[0] < contenders[1]: tenpow = tenpows[-2]
        else: tenpow = tenpows[-1]
        tenpow *= 2 # because it looked for square size 
        if self.spot == -1: 
            last = self.candles[-3][3] # last visible candle
            self.rangey = (last-last%tenpow-5*tenpow, last+(5*tenpow-last%tenpow)) # take last and go 10 squares in each direction
        else:
            self.rangey = (mi, ma)
        
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
        self.raw = [] # raw data for system
        self.timeaxis = [] # dates for system
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

class LabeledWidget(QWidget): # this is a widget (dont use this)
    def __init__(self, label_text, typ="lineedit", parent=None):
        super(LabeledWidget, self).__init__(parent)

        if type(label_text) == list: 
            temp = label_text[1:]
            label_text = label_text[0]

        self.label = QtWidgets.QLabel(label_text)
        self.label.setFixedWidth(100)
        # self.line_edit = 
        self.typ = typ
        if typ == "lineedit":
            self.widget = QtWidgets.QLineEdit()
        elif typ == "autocomplete":
            self.widget = AutoCompleteLineEdit(self, temp)
        elif typ == "combobox":
            self.widget = QtWidgets.QComboBox()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.widget)
    
    def getText(self):
        if self.typ in ["lineedit", "autocomplete"]: return self.widget.text()
        elif self.typ == "combobox": return self.widget.currentText()

    def setText(self, text):
        if self.typ in ["lineedit", "autocomplete"]: self.widget.setText(text)
        elif self.typ == "combobox": return self.widget.setCurrentText(text)

class LabeledLineEditItem(QtWidgets.QListWidgetItem): # use this
    def __init__(self, label_text, typ="lineedit", parent=None):
        super(LabeledLineEditItem, self).__init__(parent)

        self.labeledWidget = LabeledWidget(label_text, typ)
        self.setSizeHint(self.labeledWidget.sizeHint())

        self.list_widget_item = self.listWidget().setItemWidget(self, self.labeledWidget)

    def text(self):
        return self.labeledWidget.getText()

    def setText(self, text):
        self.labeledWidget.setText(text)

class AutoCompleteLineEdit(QtWidgets.QLineEdit): # lineedit with writing suggestions
    def __init__(self, parent, suggestions):
        super().__init__(parent=parent)

        self.links = [] # linked suggestions [(thing typed, thing transformed on enter)]
        self.suggestions = suggestions
        self.grey_part = ""
        self.blackPart = ""
        self.doubleCall = False # workaround for setting text without triggering the autocomplete
        if theme == "dark": self.textColor = "color: white;"
        else: self.textColor = "color: black;"

        # Connect signals
        self.textChanged.connect(self.show_inline_suggestion)
        self.installEventFilter(self)

    def setText(self, a0: str, external=True):
        if external: self.doubleCall = True # any external setText should only change the black text and not trigger autocomplete
        return super().setText(a0)

    def eventFilter(self, obj, event):
        if obj == self and event.type() == QtGui.QKeyEvent.Type.KeyPress:
            key = event.key()
            if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Tab):
                self.complete_text()
                return True
            elif key == QtCore.Qt.Key.Key_Backspace:
                if len(self.blackPart) > 1:
                    #self.blackPart = self.blackPart[:-1]
                    self.doubleCall = False
                    self.setText(self.blackPart[:-1], False)
                else: 
                    #self.blackPart = ""
                    self.doubleCall = False
                    self.setText("", False)
                # self.show_inline_suggestion()
                return True

        return super().eventFilter(obj, event)

    def show_inline_suggestion(self):
        if self.doubleCall: # to not edit the text twice
            self.doubleCall = False
            return
        text = self.text().upper()
        self.doubleCall = True
        self.setText(text) # change Text to upper without triggering autocomplete
        self.blackPart = text
        if text == "": return
        matched_text = self.find_closest_match(text)
        if matched_text:
            self.grey_part = matched_text[len(text):]
            self.doubleCall = True
            self.setText(matched_text, False)
            self.setStyleSheet(self.textColor)
            self.setSelection(len(text), len(matched_text))
        else:
            self.grey_part = ""
            self.setStyleSheet(self.textColor)

    def find_closest_match(self, partial_text):
        for suggestion in self.suggestions:
            if suggestion.startswith(partial_text):
                return suggestion
        return None

    def complete_text(self):
        text = self.text()
        self.blackPart = text
        matched_text = self.find_closest_match(text)
        if matched_text:
            for i in range(len(self.links)):
                if matched_text == self.links[i][0]:
                    matched_text = self.links[i][1] # switch the match with the link
                    self.blackPart = matched_text
            self.doubleCall = True
            self.setText(matched_text, False)
        self.grey_part = ""

    def focusOutEvent(self, event):
        self.grey_part = ""
        self.doubleCall = True
        self.setText(self.blackPart, False)
        self.setStyleSheet(self.textColor)
        super().focusOutEvent(event)

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
            if type(item) != ListItem or (type(item) == ListItem and item.typ == "cc"): # if its a listitem that is of type cc or if it's a regular item
                act = menu.addAction("Delete")
                act.triggered.connect(lambda: self.fn1(item))
            menu.exec(self.mapToGlobal(pos))
    
    def setFn(self, fn, fn1): # right click commands
        self.fn = fn
        self.fn1 = fn1

class RightClickList(QtWidgets.QListWidget): # list that has some right click actions
    def __init__(self, parent: QWidget | None = ...):
        super().__init__(parent)
        self.fns = {} # for right click | dict with key being what is displayed and value being the function
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, pos): # right click on item
        item = self.itemAt(pos)
        if item is None: return
        menu = QtWidgets.QMenu()
        for fn_name, func in self.fns.items():  # assuming self.fns is a dictionary
            act = menu.addAction(fn_name)
            fun = partial(func, item) # Use functools.partial to pass arguments to the lambda
            act.triggered.connect(fun)

        menu.exec(self.mapToGlobal(pos))

class ListItem(QtWidgets.QListWidgetItem):
    def __init__(self, text, idd, parent=None, typ="ci"):
        super().__init__(text, parent)
        self.idd = idd
        self.typ = typ
        self.conns = [] # connected coditions / complex conditions

class IDItem(QtWidgets.QListWidgetItem): # item with an id
    def __init__(self, text, idd, parent=None):
        super().__init__(text + " (" + str(idd) + ")", parent)
        self.id = idd

class LinkedItem(QtWidgets.QListWidgetItem): # for commons
    def __init__(self, text, link, parent=None):
        super().__init__(text, parent)
        self.actText = text
        self.link = link

class ExpandableItem(QtWidgets.QListWidgetItem):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.items = []
        self.links = []
        self.isExpanded = False
        self.actText = text # actual text
        self.setText("> " + text)
        # self.listWidget() # returns parent
        # self.listWidget().indexFromItem(self).row() # index in parent
    
    def toggleExpanded(self):
        if self.isExpanded:
            self.setText("> " + self.actText)
            self.isExpanded = False
        else:
            self.setText("V " + self.actText)
            self.isExpanded = True

class OperationList(QtWidgets.QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.operations = [] # list of operation dicts
        self.isSorted = False # whether to sort or not
        self.sortBy = "Newest" # this is the category that future new entries will be sorted by
        self.reversed = False # whether to reverse sorted list
        self.attrSort = [] # how the attributes are sorted i.e. ["Ticker", "Entry Time", "Exit Percentage"]
        self.showConditions = False # whether to display conditions in the tooltip
        self.sorts = [] # values that can be sorted by
    
    def makeList(self): # generate list with all items 
        self.clear()
        for o in self.operations:
            self.addItem(OperationListItem(o, displist=self.attrSort, showConds=self.showConditions))
    
    def sortedList(self, sortBy:list=[]): # sorts list by category and lists ones that dont use the category at the end
        self.isSorted = True
        if sortBy != []:
            self.sortBy = sortBy[0]
            self.reversed = sortBy[1]
        dictsorted = sorted(self.operations, key=lambda x: x.get(self.sortBy, float("inf")))
        if self.reversed: dictsorted.reverse()
        self.clear()
        for d in dictsorted:
            self.addItem(OperationListItem(d, displist=self.attrSort, showConds=self.showConditions))

class OperationListItem(QtWidgets.QListWidgetItem):
    def __init__(self, dicts, parent=None, displist=[], showConds=False):
        super().__init__(parent)
        self.dicct = dicts
        if "ID" in list(self.dicct.keys()): st = str(self.dicct["ID"]) + " "
        else: st = ""
        if displist == []:
            if "Entry Time" in list(self.dicct.keys()):
                self.setText(st + "Op. " + self.dicct["Ticker"] + " " + str(self.dicct["Entry Time"]) + " " + numtostr(self.dicct["Exit Percentage"]) + "%")
            else:
                self.setText(st + "Op. " + self.dicct["Ticker"] + " " + str(self.dicct["Entry Spot"]) + " " + numtostr(self.dicct["Exit Percentage"]) + "%")
        else:
            stt = st + "Op."
            for d in displist:
                if d in list(self.dicct.keys()):
                    if "Percentage" in d: stt += f" {self.dicct[d]/100:2.1%}"
                    elif type(self.dicct[d]) in [int, float]: stt += f" {self.dicct[d]:.2f}"
                    else: stt += " " + str(self.dicct[d])
            self.setText(stt)
        if self.dicct["Exit Percentage"] < 0: brush = QtGui.QBrush(QtGui.QColor(255, 0, 0))
        else: brush = QtGui.QBrush(QtGui.QColor(0, 255, 0))
        self.setForeground(brush)
        self.clickFn = None
        st = ""
        for k in self.dicct:
            if not showConds and str(k)[0].islower(): break # break at the first key in lowercase
            st += str(k) + ": " + str(self.dicct[k]) + ", "
        st = st[:-2]
        self.setToolTip(st)

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

class SmartStats(): # stats that generate themselves using the original values
    def __init__(self):
        # idea: dictionary for each strategy using the id if they need to be seperated
        # each element in entexs: [number positive, number negative, number processed, float sum positive percentages, float sum negative percentages]
        #                          ("n+"),          ("n-"),          ("n"),            ("s+p"),                       ("s-p")
        self.entexs = {} 
        self.succs = {} # success rates
        self.sfs = {} # s/fs
        self.names = [] # list of names with a 1:1 correspondence to the dictionaries
        self.processed = 0 # number of stocks processed in total
    
    def generate(self):
        self.processed = 0
        for key in self.entexs.keys():
            # success rate 
            if self.entexs[key]["n+"] + self.entexs[key]["n-"] == 0: self.succs[key] = float("nan")
            else: self.succs[key] = self.entexs[key]["n+"] / (self.entexs[key]["n+"] + self.entexs[key]["n-"]) # number of positives / number of operations
            # s/f
            if self.entexs[key]["s-p"] == 0: self.sfs[key] = float("nan")
            else: self.sfs[key] = abs(self.entexs[key]["s+p"] / self.entexs[key]["s-p"])
            self.processed += self.entexs[key]["n"]

class SceneOperations(): # special objects that should be shown in scene
    def __init__(self):
        self.pos = 0 # spot that scene should focus on
        self.update = False # whether setScene should move on next update
        self.right = True # whether the scene should show the spot on the left of the viewer or on the right
        self.visuals = [] # list of visual objects to display on scene

class TypeValues(): # when a value is requested from the user
    def __init__(self, name, default, typ, dataran=[]):
        self.name = name # name displayed
        self.default = default # default value
        self.val = default # current value
        self.test = None # test value that will be used in the error check
        self.typ = typ # datatype
        self.drange = dataran # range of data (i.e. [0, inf])
    
    def errorcheck(self):
        if self.typ in [int, float]:
            if self.typ == int and not isint(self.test): return "Type Error"
            if self.typ == float and not isfloat(self.test): return "Type Error"
            self.val = self.typ(self.test)
            if self.val < self.drange[0]: return "Range Error"
            if self.val > self.drange[1]: return "Range Error"

class BackProcess(): # just for any processes in the future
    def __init__(self, fn, process:str, args:tuple=()):
        self.fn = fn
        self.name = process # name of process associated
        self.args = args # arguments needed

    def start(self): # start the thread
        self.process = multiprocessing.Process(target=self.fn, args=self.args) 
        self.process.start()

class NamedThread(QtCore.QThread): # same as a qthread but with a name
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name

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

class Indicator(): # stock indicator
    # "ID":newidd, "name":name, "indName":current, "args":inps, "dMode":dMode, "data":out, "color":color, "show":self.inputs[2][0].isChecked()
    def __init__(self, idd, name, indName, args, dMode, dData, data, color, logic, show=True):
        self.name = name # display name
        self.indName = indName # name of indicator used
        self.args = args # arguments for indicator
        self.dMode = dMode # display mode for bottom screen indicators
        self.dData = dData # visuals that will be displayed
        self.data = data # indicator data
        self.color = color # rgb color as hex string
        self.show = show # whether to show indicator
        self.logic = logic # indicator object
        self.id = idd # identificator
    
    def getData(self, stock):
        self.logic.stock = stock
        self.logic.calculate()
        out = {}
        for d in self.logic.data:
            out[d] = self.logic.data[d]
        self.dData = self.logic.dData
        self.data = out

class Strategy(): # stock strategy
    # {"ID":idd, "name":name, "conds":conds, "data":data, "show":True, "calc":calc, "risk":risk, "prefs":prefs}
    def __init__(self, idd, name, fileName, args):
        self.name = name # display name
        self.filename = fileName # name of file used
        self.logic = None # logic class imported from a .py file
        self.args = args # arguments for strategy
        self.data = [] # strategy data
        self.id = idd # identificator

class BLProcess(): # bottom left process
    def __init__(self, idd, name, typ):
        self.idd = idd
        self.name = name
        self.typ = typ
        self.processes = [] # list of multiprocessing processes

class ProcessManager(): # will keep track of multiprocessing | does not store processes themselves
    def __init__(self):
        self.processes = [] # not active processes but running / ran processes | List of bl processes
        self.shown = None # currently shown process

    def register(self, process:str, typ="d"): # get id for process and save it in list
        # check if process is already registered
        for p in self.processes:
            if p.name == process: return
        idd = 0
        i = 0
        while i < len(self.processes): # check if id is already in use
            if self.processes[i].idd == idd:
                idd += 1
                i = -1 # if id in use go up and restart process
            i += 1

        if len(self.processes) == 0: # if no process has been loaded set current process to this one
            self.shown = idd
        
        self.processes.append(BLProcess(idd, process, typ)) # processes are saved as a bl process (id, processstring, type)
    
    def delist(self, process:str): # remove process of string
        pop = None
        for p in range(len(self.processes)):
            if self.processes[p].name == process: pop = p
        
        if pop is not None:
            for proc in self.processes[pop].processes:
                proc.process.join(timeout=0) # check whether process is finished by trying to join and finishing immediately
                if proc.process.is_alive(): # if process is still running
                    proc.process.terminate() # kill process
            self.processes[pop].processes = []
        
        if pop is not None: self.processes.pop(pop)

        if len(self.processes) == 0: self.shown = None # if no more processes exist, set current to none
    
    def current(self): # returns current process
        for p in self.processes:
            if p.idd == self.shown: return p.name
        return None
    
    def currentIndex(self): # returns index of current process
        for p in range(len(self.processes)):
            if self.processes[p].idd == self.shown: return p
        return None
    
    def indexOf(self, name): # return index of process with name
        for p in range(len(self.processes)):
            if self.processes[p].name == name: return p       
        return None

    def remCurrent(self): # removes current process
        for p in self.processes:
            if p.idd == self.shown: break
        
        for proc in p.processes:
            proc.process.join(timeout=0) # check whether process is finished by trying to join and finishing immediately
            if proc.process.is_alive(): # if process is still running
                proc.process.terminate() # kill process
        p.processes = []

        self.processes.remove(p) # remove current process

        # changes current process
        if len(self.processes) == 0: self.shown = None
        else: self.shown = self.processes[0].idd
    
    def switch(self): # switch current shown
        for ind in range(len(self.processes)):
            if self.processes[ind].idd == self.shown: break
        splits = split(self.processes, ind)

        if len(splits[1]) != 0: self.shown = splits[1][0][0] # set current shown to first in split list
        elif len(splits[0]) != 0: self.shown = splits[0][0][0] # else loop around
        # if both lists are empty; means no other processes exist
    
    def setCurrent(self, what): # set current to process with same name
        for p in self.processes:
            if p.name == what: break
        
        self.shown = p.idd

procManager = ProcessManager() # global process manager

class Logic(): # class for all of the logic things needed in the gui
    def __init__(self):
        self.indicators = [] # data for the indicators | list of indicators
        self.strategies = [] # list
        self.operations = [] # list of operations
        self.systems = [] # stores all systems
        self.entexs = [[], [], [], []] # predefinition
        self.currentSystem = 0 # stores current backtested system
        self.stratPath = "" # string for storing currently edited strategies
        self.manyStats = [] # for multiple stats
        self.stockConfigures = [TypeValues("Balance", 10000, float, [0, float("inf")]), TypeValues("Fees", 0, float, [0, float("inf")]), TypeValues("Used Stock(s)", "DEFAULT", str),
                                TypeValues("Period", "2y", str, ["1d", "5d", "2wk", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]),
                                TypeValues("Interval", "1d", str, ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"])]
        self.reviewData = {} # stores review data here when review window is closed

    def find(self, what, idd): # searches for index of object with id
        if what == "i": search = self.indicators
        elif what == "s": search = self.strategies

        for x in range(len(search)):
            if search[x].id == idd: return x

    def queueData(self, idd, tickers, queue, live): # runs the strategy on the stocks and puts the operations into the queue
        strat = self.strategies[self.find("s", idd)]
        # load class again and set logic to the strategy object of that class
        spec = util.spec_from_file_location("user_module", strat.filename)
        userModule = util.module_from_spec(spec)
        spec.loader.exec_module(userModule)
        stt = getattr(userModule, "Strategy")
        strat.logic = stt()
        for st in self.stockConfigures:
            strat.logic.stratVals[st.name] = st.val
        for ticker in tickers:
            strat.logic.stratVals["Ticker"] = ticker
            # strat.logic.reinit()
            if live:
                data, dates = stock_data(ticker, period=strat.logic.stratVals["Period"], interval=strat.logic.stratVals["Interval"])
            else:
                data = read(ticker)
                dates = []
            if len(data) <= 1:
                queue.put([])
                continue
            ops = strat.logic.data(data, dates)
            for o in ops: # set operation id to id of strategy
                o.diagnostics["ID"] = idd
            queue.put(ops)

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
        self.raw = [] # current shown raw data
        self.timeaxis = [] # will store dates
        self.moved = False # When the screen has been moved, dont activate mouse functions
        self.docks = [] # predefinition
        self.marked = [] # what spots are marked
        self.dialog = None # condition dialog window 
        self.tangent = None # tangent object
        self.prefs = {} # {"Name of setting":bool}
        self.queue = multiprocessing.Queue() # queue for backthreads
        self.progs = [] # list of objects used to display progress
        self.stopbackgs = False # whether to stop all background operations
        self.threads = [] # predefinition
        self.spots = [] # selected spots for condition seeker
        self.processes = [] # for all non backthread processes
        self.cornerBtn = WidgetContainer() # Button in bottom right corner of view to change scale
        self.tempInds = [] # list of temporaty indicators for peek | [[qgraphicsobjects]]
        self.specialObjects = {} # dict of pyqt objects that are used by several functions
        self.sceneOps = SceneOperations() # special scene operations and objects

        self.create_widgets()

        # debug setup
        self.readstocks("0", "quick", "+")
        # self.readstocks("debug.txt", "open", "+")
    
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
        act = file.addAction("Preferences...")
        act.triggered.connect(self.showPrefs)
        file.addSeparator()
        act = file.addAction("Close")
        act.triggered.connect(self.close)

        # preferences menu
        self.prefs = {}
        self.prefs["Calculate strategies on live data"] = True
        self.prefs["Show group items in suggestions"] = False
        self.commons = [] # common stocks (list of str) [[stock_ticker, switchcode=None], ...]
        self.backSettings = {"increment":1} # dictionary for backtest settings
        self.loadConfig()
        edit = main.addMenu("Edit")
        act = edit.addAction("Common Stocks...")
        act.triggered.connect(self.commonDialog)
        act = edit.addAction("Backtests...")
        act.triggered.connect(self.backtestSettings)
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
        view.addSeparator()
        act = view.addAction("Unmark All")
        act.triggered.connect(self.unmarkAll)
        act = view.addAction("Reset")
        act.triggered.connect(self.resetAll)

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
        y_widget.setFixedWidth(35) # axis may not be larger than 35 pixels wide
        
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
        self.docks.append(QtWidgets.QDockWidget("Strategies", self))
        self.docks[0].setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.docks[0].setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.docks[0].setStyleSheet(dockstring)
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        self.docks[0].setWidget(wid)

        side1 = QtWidgets.QMainWindow(self)
        side1.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.docks[0])
        side1.setFixedWidth(200)

        self.docks.append(QtWidgets.QDockWidget("Review", self))
        self.docks[1].setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.docks[1].setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.docks[1].setStyleSheet(dockstring)
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        self.docks[1].setWidget(wid)

        side3 = QtWidgets.QMainWindow(self)
        side3.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.docks[1])
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
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)
        self.resetWindows()
    
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
                # self.mode.setEnabled(True)
                self.gridconv = deepcopy(logic.systems[index].gridconv)
                self.rangex = deepcopy(logic.systems[index].rangex)
                self.rangey = deepcopy(logic.systems[index].rangey)
                self.candles = deepcopy(logic.systems[index].candles)
                self.raw = deepcopy(logic.systems[index].raw)
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
        backrem = self.tabs.tabText(index) in ["Backtest", "Exit Percentages", "Benchmark Comparison"] # whether it's a backtest being removed

        changeTo = None
        if index == self.tabs.currentIndex():
            self.tabs.setCurrentIndex(index-1) # if current index would be removed, change current index
            changeTo = index-1 # change to what index

        if backrem:
            self.stopButton() # stop all background threads if still running
            procManager.delist("backthreads")
            # self.mode.setEnabled(True)
            if self.tabs.tabText(self.tabs.currentIndex()) in ["Backtest", "Exit Percentages", "Benchmark Comparison"]: # if backtest was selected
                self.tabs.setCurrentIndex(logic.currentSystem)
                self.gridconv = deepcopy(logic.systems[logic.currentSystem].gridconv)
                self.rangex = deepcopy(logic.systems[logic.currentSystem].rangex)
                self.rangey = deepcopy(logic.systems[logic.currentSystem].rangey)
                self.candles = deepcopy(logic.systems[logic.currentSystem].candles)
                self.raw = deepcopy(logic.systems[logic.currentSystem].raw)
                self.timeaxis = deepcopy(logic.systems[logic.currentSystem].timeaxis)
                self.reinitIndicators()
                self.setScene()
            return
        self.tabs.removeTab(index) # remove tab

        logic.systems.pop(index) # remove system as well

        # if no more stocks are loaded
        if self.tabs.tabText(self.tabs.currentIndex()) == "+": 
            self.candles = [] # reset candles
            self.marked = []
            self.setScene() # load blank scene
        elif changeTo is not None: # if the current tab was deleted and a new one has to be loaded also if tab is not the + tab
            self.focus.placed = False
            self.moved = False
            # logic.currentSystem = changeTo
            self.marked = []
            # self.mode.setEnabled(True)
            self.gridconv = deepcopy(logic.systems[changeTo].gridconv)
            self.rangex = deepcopy(logic.systems[changeTo].rangex)
            self.rangey = deepcopy(logic.systems[changeTo].rangey)
            self.candles = deepcopy(logic.systems[changeTo].candles)
            self.raw = deepcopy(logic.systems[changeTo].raw)
            self.timeaxis = deepcopy(logic.systems[changeTo].timeaxis)
            self.reinitIndicators()
            self.setScene()

    def showPrefs(self): # show preferences
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Preferences")
        dbox.setFixedSize(500, 375)
        i = 0
        self.inputs[0] = []
        for pref in self.prefs:
            self.inputs[0].append(QtWidgets.QCheckBox(pref, dbox))
            self.inputs[0][-1].setChecked(self.prefs[pref])
            self.inputs[0][-1].setGeometry(10+(i%2)*240, 10+(i//2)*30, 230, 22)
            i += 1
        acc = QtWidgets.QPushButton("OK", dbox)
        acc.clicked.connect(lambda: self.prefProcess(dbox))
        acc.move(235, 345)
        dbox.exec()

    def prefProcess(self, parent=None): # save perferences
        for i in range(len(self.inputs[0])):
            key = list(self.prefs.keys())[i]
            self.prefs[key] = self.inputs[0][i].isChecked() # save inputs to prefs
        self.saveConfig()
        parent.close()
        
    def resetAll(self): # reset all strategies, conditions and indicators
        result = QtWidgets.QMessageBox.question(self, "Are you sure", "This action will reset the program to it's normal state.\nContinue?", 
        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
        if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
            return
        # delete all tabs, reset bottom window, mode, strategies, conditions, indicators, load basic stock...
        poplist = []
        for t in range(self.tabs.count()):
            if self.tabs.tabText(t) != "+": poplist.append(t)
        poplist.reverse()
        for p in poplist: self.tabs.removeTab(p)
        logic.systems = []
        logic.currentSystem = 0
        logic.indicators = []
        logic.strategies = []
        logic.reviewData = {}
        self.stopButton()
        procManager.processes = []
        procManager.shown = None
        self.readstocks("0", "quick", "+")
    
    def open(self, how=""): # open file dialog
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open stock data file", "", "Text files (*.txt);;All files (*.*)")[0] # get filename
        if filename == "": return # if no file was selected
        if self.tabs.count() -1 == 0: how = "+"
        self.readstocks(filename, "open", how)

    def quickopen(self, how=""): # quick open dialogue box
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Quick open...")
        dbox.setFixedSize(150, 85)
        label1 = QtWidgets.QLabel(dbox)
        label1.setGeometry(10, 10, 85, 25)
        suggs, links = self.generateSuggestions()
        self.inputs[0] = AutoCompleteLineEdit(dbox, suggs)
        self.inputs[0].links = links
        self.inputs[0].setGeometry(75, 10, 50, 25)
        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(40, 52)
        label1.setText("Ticker/ID")
        if self.tabs.count() -1 == 0: how = "+"
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
        if self.tabs.count() -1 == 0: how = "+"
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
        suggs, links = self.generateSuggestions()
        self.inputs[0] = AutoCompleteLineEdit(wid, suggs)
        self.inputs[0].links = links
        self.inputs[0].setText(tik)
        self.inputs[0].setGeometry(60, 10, 50, 25)
        label2 = QtWidgets.QLabel("Period", wid)
        label2.setGeometry(10, 40, 85, 25)
        self.inputs[1] = []
        self.inputs[1].append(QtWidgets.QComboBox(wid))
        if cur == "Fixed": avail = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"] # available intervals
        else: avail = ["1d", "5d", "2wk", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] # available periods
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

        def dateError(start, end): # error code for fixed dates
            if start > end: 
                self.errormsg("Start date is more recent than end date.")
                return
            if self.inputs[1][0].currentText() == "1m": # 1 Minute
                if start < dt.datetime.now() - dt.timedelta(days=30):
                    self.errormsg("Date range too big. (Maximum = 30d)")
                    return
                elif end-start > dt.timedelta(days=7):
                    self.errormsg("Only 7 consecutive days allowed.")
                    return
            elif self.inputs[1][0].currentText() == "15m": # 15 Minutes
                if start < dt.datetime.now() - dt.timedelta(days=60):
                    self.errormsg("Date range too big. (Maximum = 60d)")
                    return
            elif self.inputs[1][0].currentText() == "1h": # 1 hour
                if start < dt.datetime.now() - dt.timedelta(days=730):
                    self.errormsg("Date range too big. (Maximum = 730d)")
                    return

        groups = [x.name.upper() for x in self.commons if type(x) == Group]
        if self.inputs[0].text().upper() in groups: # if a group is entered
            for c in self.commons:
                if type(c) == Group:
                    if c.name.upper() == self.inputs[0].text().upper(): break
            tickers = deepcopy(c.items) # copy tickers
            for t in tickers: # open a new tab for each ticker in group
                st = t.upper() + ","
                if self.inputs[1][1].currentText() == "Fixed":
                    try:
                        start = dt.datetime(self.inputs[2][0].value(), self.inputs[2][1].value(), self.inputs[2][2].value())
                        end = dt.datetime(self.inputs[3][0].value(), self.inputs[3][1].value(), self.inputs[3][2].value())
                    except ValueError:
                        self.errormsg("Date is invalid.")
                        return
                    dateError(start, end)
                    for j in range(2):
                        for i in range(3):
                            st += str(self.inputs[2+j][i].value()) + ","
                    st += self.inputs[1][0].currentText()
                    red, dat = stock_data(t, start, end, self.inputs[1][0].currentText()) # get data and date
                else:
                    st += self.inputs[1][0].currentText() + "," + self.inputs[2].currentText()
                    red, dat = stock_data(t, period=self.inputs[1][0].currentText(), interval=self.inputs[2].currentText())
                if len(red) > 1:
                    self.newScene("+", "Live " + t.upper(), st, [red, dat])
            parent.close()
            return # end function here so that other code wont get executed
        
        st = self.inputs[0].text().upper() + ","
        if self.inputs[1][1].currentText() == "Fixed": # fixed date procedure
            try:
                start = dt.datetime(self.inputs[2][0].value(), self.inputs[2][1].value(), self.inputs[2][2].value())
                end = dt.datetime(self.inputs[3][0].value(), self.inputs[3][1].value(), self.inputs[3][2].value())
            except ValueError:
                self.errormsg("Date is invalid.")
                return
            dateError(start, end)
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
                elif self.inputs[1][0].currentText()[-1] == "k": # week period
                    pass
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
        self.newScene(how, "Live " + self.inputs[0].text().upper(), st, [red, dat])
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

    def loadConfig(self): # loads all config data and stores them in memory
        try:
            tree = ET.parse(os.path.join(os.path.dirname(__file__), "config.xml"))
        except:
            return # return if xml wasn't found
        root = tree.getroot()
        elements = [e for e in root.iter()]
        for e in elements:
            if e.tag == "settings" and e.attrib["name"] == "preferences": break # get the element of the preference settings
        for s in e.iter():
            if s.tag != "settings":
                self.prefs[s.attrib["name"]] = s.attrib["boolean"].lower() == "true"

        for e in elements:
            if e.tag == "settings" and e.attrib["name"] == "common stocks": break # get the element of the common stocks settings
        
        lis = e.find("list")
        elms = [e for e in lis.iter()][1:] # get every element except self
        final = []
        i = 0
        while i < len(elms):
            if elms[i].tag == "group": # for group remove all items in group from elms and save list of all group items
                glist = [[], []] # [[items], [links]]
                its = [g for g in elms[i].iter()][1:]
                for it in its:
                    if "switchcode" in it.attrib: st = it.attrib["switchcode"]
                    else: st = None
                    glist[0].append(it.text)
                    glist[1].append(st)
                final.append(Group(elms[i].attrib["name"], glist[0], glist[1]))
                for p in range(len(its)): # for each item in group
                    del elms[i+1] # delete as many next items from elements as there are items in group
            else:
                if "switchcode" in elms[i].attrib: st = elms[i].attrib["switchcode"]
                else: st = None
                final.append([elms[i].text, st])
            i += 1
        
        self.commons = final

        for e in elements:
            if e.tag == "settings" and e.attrib["name"] == "backtest": break # get backtest settings

        for s in e.iter():
            if s.tag != "settings":
                self.backSettings[s.attrib["name"]] = int(s.attrib["value"])

    def saveConfig(self): # take all memory variables and store them in config.xml
        root = ET.Element("config")
        child = ET.SubElement(root, "settings", {"name":"preferences"})
        for p in self.prefs:
            sub = ET.Element("setting", {"name":p, "boolean":str(self.prefs[p]).lower()})
            child.append(sub)
        
        child = ET.SubElement(root, "settings", {"name":"common stocks"})
        lis = ET.Element("list")
        for c in self.commons: 
            if type(c) == list:
                sub = ET.Element("item")
                sub.text = c[0]
                if c[1] is not None: sub.attrib["switchcode"] = c[1]
            elif type(c) == Group:
                sub = ET.Element("group")
                sub.attrib["name"] = c.name
                for i in range(len(c.items)):
                    item = ET.Element("item")
                    item.text = c.items[i]
                    if c.links[i] is not None: item.attrib["switchcode"] = c.links[i]
                    sub.append(item)
            lis.append(sub)
        child.append(lis)

        child = ET.SubElement(root, "settings", {"name":"backtest"})
        for k in self.backSettings:
            sub = ET.Element("setting", {"name":k, "value":str(self.backSettings[k])})
            child.append(sub)

        tree = ET.ElementTree(root)
        doctype = '<!DOCTYPE config SYSTEM "config.dtd">'

        # Write the XML file with DOCTYPE
        with open('config.xml', 'wb') as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n{doctype}\n'.encode())
            tree.write(f, encoding='utf-8')

    def commonDialog(self): # change common stocks
        dbox = QtWidgets.QDialog(self)
        dbox.setFixedSize(320, 185)
        dbox.setWindowTitle("Edit Common Stocks...")
        #lis = QtWidgets.QListWidget(dbox)
        lis = StratList(dbox)
        lis.setGeometry(10, 10, 200, 150)
        for c in self.commons:
            if type(c) == list:
                lis.addItem(LinkedItem(c[0], c[1]))
                # lis.coData.append(c[1])
            else: # group
                item = ExpandableItem(c.name)
                item.items = c.items
                item.links = c.links
                lis.addItem(item)
        
        def handle(han):
            item = lis.itemFromIndex(han)
            if type(item) == ExpandableItem:
                if item.isExpanded:
                    item.items = []
                    item.links = []
                    while True: # take out all items that still belong to group
                        tem = lis.item(lis.row(item) + 1)
                        if tem is None: break
                        if tem.text().startswith("    "):
                            tem = lis.takeItem(lis.row(item) + 1) # take item below expand item
                            item.items.append(tem.actText)
                            item.links.append(tem.link)
                        else: break
                    item.toggleExpanded()
                else:
                    for i in range(len(item.items)):
                        it = LinkedItem(item.items[i], item.links[i])
                        it.setText("    " + item.items[i])
                        lis.insertItem(lis.row(item)+1, it)
                    item.toggleExpanded()

        lis.clicked.connect(handle)
        # lis.coData = [None]*len(self.commons)
        line = QtWidgets.QLineEdit(dbox)
        line.setGeometry(225, 10, 75, 22)

        ok = False
        changes = False

        def add():
            if line.text() == "": return
            nonlocal changes
            changes = True
            lis.addItem(LinkedItem(line.text().upper(), None))
            # lis.coData.append(None)
            line.setText("") # reset text

        btn = QtWidgets.QPushButton("Add", dbox)
        btn.move(225, 35)
        btn.clicked.connect(add)

        def remove(item=None):
            if item is None or type(item) == bool: item = lis.currentItem()
            if type(item) == ExpandableItem:
                threading.Thread(target=lambda:playsound("Exclamation")).start()
                result = QtWidgets.QMessageBox.question(self, "Edit Common Stocks...", f"Do you want remove the entire group?", 
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                    return
            nonlocal changes
            changes = True
            if type(item) == ExpandableItem:
                while True: # take out all items that belong to group
                    tem = lis.item(lis.row(item) + 1)
                    if tem is None: break
                    if tem.text().startswith("    "):
                        lis.takeItem(lis.row(item) + 1) # take item below expand item
                        # item.items.append(tem.actText, tem.link)
                    else: break
            lis.takeItem(lis.row(item)) # take item out of list

        btn = QtWidgets.QPushButton("Remove Sel.", dbox)
        btn.move(225, 60)
        btn.clicked.connect(remove)

        def connect(item):
            nonlocal changes
            # row = lis.row(item)
            if type(item) == ExpandableItem:
                self.errormsg("Cannot link a group to a codeword.")
                return
            db = QtWidgets.QDialog(dbox)
            db.setWindowTitle("Setup A Connection...")
            db.setFixedSize(250, 110)
            QtWidgets.QLabel("Setup a codeword for this item \ne.g. Microsoft -> MSFT", db).move(10, 10)
            line = QtWidgets.QLineEdit(db)
            line.setGeometry(10, 45, 230, 22)
            if item.link is not None:
                line.setText(item.link)

            def ok():
                nonlocal changes
                changes = True
                item.link = line.text()
                db.close()

            btn = QtWidgets.QPushButton("OK", db)
            btn.move(90, 80)
            btn.clicked.connect(ok)
            db.exec()
        
        lis.setFn(connect, remove)

        def group():
            nonlocal changes
            db = QtWidgets.QDialog(dbox)
            db.setWindowTitle("Make A New Group...")
            db.setFixedSize(325, 200)
            
            QtWidgets.QLabel("All items", db).move(10, 10)
            alllist = QtWidgets.QListWidget(db)
            alllist.setGeometry(10, 35, 75, 150)
            for i in range(lis.count()):
                item = lis.item(i)
                if type(item) != ExpandableItem and not item.text().startswith("    "):
                    alllist.addItem(item.text())

            QtWidgets.QLabel("Group", db).move(150, 10)
            grouplist = QtWidgets.QListWidget(db)
            grouplist.setGeometry(150, 35, 75, 150)

            def moveCondition(direction): # move conditions between boxes
                if direction == "add":
                    item = alllist.currentItem()
                    alllist.takeItem(alllist.row(item))
                    grouplist.addItem(item)
                elif direction == "remove":
                    item = grouplist.currentItem()
                    grouplist.takeItem(grouplist.row(item))
                    alllist.addItem(item)

            btn = QtWidgets.QPushButton("←", db)
            btn.setGeometry(110, 125, 26, 26)
            btn.clicked.connect(lambda: moveCondition("remove"))
            btn2 = QtWidgets.QPushButton("→", db)
            btn2.setGeometry(110, 45, 26, 26)
            btn2.clicked.connect(lambda: moveCondition("add"))

            QtWidgets.QLabel("Group Name", db).move(235, 10)
            namel = QtWidgets.QLineEdit(db)
            namel.setGeometry(235, 35, 75, 25)

            def create():
                nonlocal changes
                forgroup = [grouplist.item(i).text() for i in range(grouplist.count())]
                if forgroup == []:
                    self.errormsg("No items in group.")
                    return
                if namel.text() == "":
                    self.errormsg("Group needs a name.")
                    return
                # remove all items that are in the group
                grupp = [[], []]
                i = 0
                while i < lis.count():
                    item = lis.item(i)
                    if item.text() in forgroup: # if item will not be put in group
                        grupp[0].append(item.actText)
                        grupp[1].append(item.link)
                        lis.takeItem(i)
                    else:
                        i += 1
                # add collapsed group
                g = ExpandableItem(namel.text())
                g.items = grupp[0]
                g.links = grupp[1]
                lis.addItem(g)
                changes = True
                db.close()

            btn = QtWidgets.QPushButton("Create", db)
            btn.move(235, 158)
            btn.clicked.connect(create)

            db.exec()

        btn = QtWidgets.QPushButton("Group...", dbox)
        btn.move(225, 85)
        btn.clicked.connect(group)

        def save():
            nonlocal ok
            ok = True
            self.commons = []
            count = lis.count()
            i = 0
            while i < count:
                item = lis.item(i)
                if type(item) == ExpandableItem:
                    if item.isExpanded: # collapse all open groups
                        item.items = []
                        item.links = []
                        while True: # take out all items that still belong to group
                            tem = lis.item(lis.row(item) + 1)
                            if tem is None: break
                            if tem.text().startswith("    "):
                                tem = lis.takeItem(lis.row(item) + 1) # take item below expand item
                                item.items.append(tem.actText)
                                item.links.append(tem.link)
                            else: break
                    item.toggleExpanded()
                    self.commons.append(Group(item.actText, item.items, item.links))
                else:
                    self.commons.append([item.actText, item.link])
                i += 1
            self.saveConfig()
            dbox.close()
        
        def uSure():
            if not ok and changes:
                threading.Thread(target=lambda:playsound("Exclamation")).start()
                result = QtWidgets.QMessageBox.question(self, "Edit Common Stocks...", f"Do you want to save changes?", 
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                    return
                save()

        btn = QtWidgets.QPushButton("Save", dbox)
        btn.move(225, 133)
        btn.clicked.connect(save)

        dbox.finished.connect(uSure)
        dbox.exec()

    def generateSuggestions(self): # generate suggestions with links for autocomplete tickers
        suggs = []
        links = [] # linked suggestions that will change when typed
        for c in self.commons:
            if type(c) == list:
                suggs.append(c[0])
                if c[1] is not None:
                    suggs.append(c[1]) # links should still appear as a suggestion
                    links.append((c[1], c[0])) # what is linked with/changes into what
            elif type(c) == Group: # group
                suggs.append(c.name)
                if self.prefs["Show group items in suggestions"]:
                    for i in range(len(c.items)):
                        if c.links[i] is not None:
                            suggs.append(c.links[i])
                            links.append((c.links[i], c.items[i]))
        return suggs, links

    def backtestSettings(self): # change e.g. increment of backtest
        dbox = QtWidgets.QDialog(self)
        dbox.setWindowTitle("Edit Backtest data...")
        dbox.setFixedSize(300, 75)
        QtWidgets.QLabel("Amount of backprocesses in backtest:", dbox).move(10, 10)
        line = QtWidgets.QLineEdit(dbox)
        line.setGeometry(235, 10, 50, 22)
        line.setText(str(self.backSettings["increment"]))
        ok = False

        def ok():
            nonlocal ok
            ok = True
            if not isint(line.text()): 
                self.errormsg(f"{line.text()} is not a valid integer.")
                return
            elif int(line.text()) <= 0:
                self.errormsg("Number has to be at least 0.")
                return
            self.backSettings["increment"] = int(line.text())
            self.saveConfig()
            dbox.close()

        btn = QtWidgets.QPushButton("OK", dbox)
        btn.move(115, 45)
        btn.clicked.connect(ok)
        dbox.exec()

    def indicatorDialog(self, idd=False): # Dialogbox for viewing conditions
        if self.tabs.tabText(self.tabs.currentIndex()) == "+": 
            self.errormsg("Please load a stock first.")
            return
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
            current = self.inputs[0].currentText()
        else: 
            if type(idd) == int: 
                ind = logic.find("i", idd)
                current = logic.indicators[ind].indName
            else: 
                current = visinds[0] # default is condition at spot 0
        wid = QtWidgets.QWidget()
        lab = QtWidgets.QLabel("Indicator", wid)
        lab.move(5, 5)
        self.inputs[0] = QtWidgets.QComboBox(wid)
        for n in visinds:
            self.inputs[0].addItem(n)
        self.inputs[0].setGeometry(60, 2, 120, 22)
        self.inputs[0].setCurrentText(current) # set current selected to last selected
        self.inputs[0].currentTextChanged.connect(lambda: self.indicatorLayout(idd)) # connect text change to self
        args = []
        inps = []
        for a in objinds[current].argTypes:
            args.append(objinds[current].argTypes[a]["argName"])
            inps.append(objinds[current].argTypes[a]["default"])
        
        if first and type(ind) == int:
            for i in range(len(logic.indicators[ind].args)):
                inps[i] = logic.indicators[ind].args[i]

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
            should = logic.indicators[ind].show
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

        if first and type(ind) == int: self.inputs[3].setStyleSheet("background-color: %s;" % logic.indicators[ind].color) # preset color

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
        if current == "Volume":
            view2.isVolume = True
            view2.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
            view.initScene()
        else:
            objinds[current].stock = cans
            objinds[current].calculate()
            temp = ["graph", "bottom graph", "volume"]
            dMode = temp.index(objinds[current].dMode) + 1
            if dMode == 1: # graph
                for key in objinds[current].data:
                    view.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
                    view.graphInds.append(objinds[current].data[key])
                view.initScene() # because there can only be one per
            elif dMode == 2: # bottom graph
                view.initScene()
                for key in objinds[current].data:
                    view2.colors.append(QtGui.QColor(self.inputs[3].styleSheet().split(" ")[1][:-1]))
                    view2.graphInds.append(objinds[current].data[key])
                ry = deepcopy(objinds[current].dData["rangey"])
                if ry[0] is None: # get min from data
                    mn = float("inf")
                    for d in objinds[current].data:
                        if min(objinds[current].data[d]) < mn: mn = min(objinds[current].data[d])
                    ry = (mn, ry[1]) # get lowest value and set yrange to value
                if ry[1] is None: # get max from data
                    mx = float("-inf")
                    for d in objinds[current].data:
                        if max(objinds[current].data[d]) > mx: mx = max(objinds[current].data[d])
                    ry = (ry[0], mx) # get highest value and set yrange to value
                view2.rangey = ry
                gc = deepcopy(objinds[current].dData["gridconv"])
                for i in range(4):
                    if gc[i] is None: gc[i] = view.gridconv[i] # if None, just take value from bigger viewer
                    elif type(gc[i]) == str: # if str then take int(str)*rangey[1]
                        gc[i] = float(gc[i])*ry[1]
                    else: gc[i] /= 2 # if a specific value is given; divide by 2 to fit it into the viewer
        view2.makeScene()

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
        # for key in visinds: # find key corresponding to combobox text
        #     if indargs[key]["name"] == self.inputs[0].currentText(): break
        current = self.inputs[0].currentText()

        def isType(thing, typ): # pass thing and check if it's the type
            if typ == str: return True
            elif typ == int: return isint(thing)
            elif typ == float: return isfloat(thing)

        # error code
        for i in range(len(objinds[current].argTypes.keys())):
            value = self.inputs[1][i].text()
            arg = objinds[current].argTypes[list(objinds[current].argTypes.keys())[i]]
            
            if not isType(value, arg["type"]): 
                self.errormsg(value + " is not of type " + str(arg["type"]).split("\'")[1] + ".")
                return
            
            if arg["lower"] != "-inf": # if it has a bottom limit
                if arg["type"](value) < arg["lower"]:
                    self.errormsg(value + " is out of range.")
                    return
            
            maxx = arg["upper"]
            if maxx == "nan": maxx = len(self.raw)-1 # nan means len(stock)
            if maxx != "inf":
                if arg["type"](value) > maxx:
                    self.errormsg(value + " is out of range.")
                    return

        # get inputs
        old = None
        if type(idd) == int: # if it modified an old indicator; replace in list
            old = logic.find("i", idd)

        inps = [] 

        for i in range(len(self.inputs[1])):
            if i < len(objinds[current].argTypes):
                arg = objinds[current].argTypes[list(objinds[current].argTypes.keys())[i]]
                inps.append(arg["type"](self.inputs[1][i].text())) # append input converted to correct type

        # t = len(self.raw)-1
        obj = getattr(stocklib, current)() # make empty indicator object
        obj.stock = self.raw
        obj.setArgs(inps) # get arguments
        obj.calculate() # get data
        dData = obj.dData
        out = {}
        for d in obj.data: # data is dict of many
            out[d] = obj.data[d]

        end = False
        dMode = ["", "graph", "bottom graph", "volume"].index(objinds[current].dMode)
        # dMode = 0
        # if current in ["SMA", "EMA", "VWAP", "BollingerBands", "GaussianChannel", "GCDW"]: dMode = 1 # graph
        # elif current in ["MACD", "RSI", "ATR"]: dMode = 2 # second view graph
        # elif current in ["Volume"]: dMode = 3 # volume display
            
        if old is None: # if a new id is needed
            # add to indicators
            newidd = 0

            i = 0
            while i < len(logic.indicators): # check if id is already in use
                if logic.indicators[i].id == newidd:
                    newidd += 1
                    i = -1 # if id in use go up and restart process
                i += 1
        
        else: newidd = idd # else keep old id
        color = self.inputs[3].styleSheet().split(" ")[1][:-1] # color in hex
        name = ""
        name += current
        for inp in inps:
            name += " " + str(inp)

        # indict = {"ID":newidd, "name":name, "indName":current, "args":inps, "dMode":dMode, "data":out, "color":color, "show":self.inputs[2][0].isChecked()}
        indic = Indicator(newidd, name, current, inps, dMode, dData, out, color, obj, self.inputs[2][0].isChecked())
        if old is None: 
            logic.indicators.append(indic) # new indicator
        else: # if old indicator/condition is changed
            logic.indicators[old] = indic # replace old indicator

        self.setStrategyDocker()
        self.setScene()
        parent.close()

    def createStrategyProcesses(self, which="all"): # create processes for some/all strategies and start them
        self.stopbackgs = False
        procManager.register("strategies")
        procind = procManager.indexOf("strategies")
        tickers = []
        for s in logic.stockConfigures:
            if s.name == "Used Stock(s)": break # get used stocks
        if self.prefs["Calculate strategies on live data"]: # check if an internet connection exists
            try:
                table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies') # get s&p 500 tickers
            except:
                result = QtWidgets.QMessageBox.question(self, "No Internet", "Live data could not be found.\nCalculate strategies on offline data?", 
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if result != QtWidgets.QMessageBox.StandardButton.Yes: # only continue if yes is pressed
                    return
                self.prefs["Calculate strategies on live data"] = False
        if s.val == "DEFAULT":
            if self.prefs["Calculate strategies on live data"]:
                df = table[0]
                tickers = df["Symbol"].to_list()
            else:
                tickers = stocks
        else:
            groups = [x.name.upper() for x in self.commons if type(x) == Group]
            if s.val.upper() in groups: # if a group was entered
                for c in self.commons:
                    if type(c) == Group:
                        if c.name.upper() == s.val.upper(): break
                tickers = deepcopy(c.items) # copy tickers
            else:
                if "," in s.val: tickers = s.val.split(",") # assume tickers are split by commas
                tickers = [s.val] # make list of ticker

        incticks = self.backSettings["increment"]*[[]]
        for i in range(len(tickers)):
            incticks[int(i%self.backSettings["increment"])].append(tickers[i]) # split up tickers in x smaller, but still sorted lists

        if which != "all": # if only one
            strats = [logic.strategies[logic.find("s", which)]]
        else: # if all
            strats = logic.strategies
        
        for st in strats: # start processes
            for i in range(self.backSettings["increment"]):
                proc = BackProcess(logic.queueData, st.name, (st.id, incticks[i], self.queue, self.prefs["Calculate strategies on live data"]))
                procManager.processes[procind].processes.append(proc)
                procManager.processes[procind].processes[-1].start()
        
        # start queue
        self.threads = []
        self.threads.append(NamedThread("Queue", self))
        self.threads[-1].started.connect(self.updateOperations)
        self.threads[-1].finished.connect(self.threads[-1].quit)
        self.threads[-1].finished.connect(self.threads[-1].deleteLater)
        self.threads[-1].start()
        self.specialObjects["stopBtn"].setEnabled(True)
        self.specialObjects["exBtn"].setEnabled(True)

    def unmarkAll(self, clearIndicators=False): # removes all of the markings
        self.marked = []
        self.spots = []
        if clearIndicators: logic.indicators = []
        self.sceneOps.visuals = []
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
    
    def stopButton(self, what="all"): # button to stop background tasks
        # stop all processes / check whether they've finished
        if what == "all":
            self.stopbackgs = True
            for p in procManager.processes:
                for b in p.processes:
                    b.process.join(timeout=0) # check whether process is finished by trying to join and finishing immediately
                    if b.process.is_alive(): # if process is still running
                        b.process.terminate() # kill process
                p.processes = []
        
            for t in self.threads:
                t.quit()
            self.threads = []
        elif what == "strategies":
            self.stopbackgs = True
            parproc = procManager.processes[procManager.indexOf("strategies")]
            for p in parproc.processes:
                p.process.join(timeout=0) # check whether process is finished by trying to join and finishing immediately
                if p.process.is_alive(): # if process is still running
                    p.process.terminate() # kill process
            parproc.processes = []

            for i in range(len(self.threads)):
                if self.threads[i].name == "Queue": break
            
            self.threads[i].quit()
            del self.threads[i]
            self.specialObjects["stopBtn"].setDisabled(True)

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
                    dat = self.timeaxis[val]#.to_pydatetime() # get date from date list
                    lastdat = self.view.horizontalScrollBar().value()-offset+(x-1)*self.gridconv[0] # ind
                    lastdat = int((lastdat/self.gridconv[0])*self.gridconv[1])+self.rangex[0] # val
                    if lastdat < 0: # if index out of range
                        val = dat.year
                        if theme == "dark": col = QtGui.QColor("#00bbff")
                        else: col = QtGui.QColor("#3366ff")
                    else:
                        lastdat = self.timeaxis[lastdat]#.to_pydatetime() # else get date of said index
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
    
    def setScene(self): # set the Scene (reset, remake grid and candles...)
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
                    dat = self.timeaxis[c[0]-self.rangex[0]]#.to_pydatetime()
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
                dat = self.timeaxis[c[0]-self.rangex[0]]#.to_pydatetime()
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
                    dat = self.timeaxis[c[0]-self.rangex[0]]#.to_pydatetime()
                    can.date = dat
                can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                last = can
                self.view.scene().addItem(can)
        
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
                if ind.show: # if should show graph
                    if ind.dMode == 1: # main view indicator
                        for v in ind.dData: # v is a key
                            if v not in ["rangey", "gridconv"]: # show everything except viewer parameters
                                ob = ind.dData[v]
                                if ob.name == "line":
                                    if type(ob.data) == str: # if a reference was given
                                        data = ind.data[ob.data]
                                    elif type(ob.data) in (int, float): data = len(self.candles)*[ob.data]
                                    else: data = ob.data
                                    for i in range(len(self.candles)-1): # do same as graph
                                        if type(ob.color) == str: color = ob.color
                                        else: color = ob.color[i]
                                        c = [self.candles[i], self.candles[i+1]] # for simplification
                                        for e in range(2):
                                            c[e] = Candle(c[e][0], c[e][1])
                                            c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                        if i != len(self.candles)-1:
                                            close1 = self.toCoord("y", data[i]) # get positions
                                            close2 = self.toCoord("y", data[i+1])
                                        if not (close1 != close1 or close2 != close2): # nan check
                                            can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                                            pen = QtGui.QPen(QtGui.QColor(color))
                                            if ob.shape == "dashed": pen.setStyle(QtCore.Qt.PenStyle.DashLine)
                                            elif ob.shape == "dotted": pen.setStyle(QtCore.Qt.PenStyle.DotLine)
                                            elif ob.shape == "dashdot": pen.setStyle(QtCore.Qt.PenStyle.DashDotLine)
                                            can.setPen(pen)
                                            self.view.scene().addItem(can)
                                elif ob.name == "rect":
                                    if ob.shape == "f2": # if rect between 2 graphs
                                        if type(ob.data) == str:
                                            data = (ind.data[ob.data.split(",")[0]], ind.data[ob.data.split(",")[1]])
                                        else:
                                            data = ob.data # ob.data has to be a tuple of 2 lists
                                    # elif type(ob.data) == str:
                                    #     data = ind.data[ob.data]
                                    # else: data = ob.data
                                    # update this code if rect without 2 bounds
                                    for i in range(len(self.candles)-1): # do same as graph
                                        if type(ob.color) == str: color = ob.color
                                        else: color = ob.color[i]
                                        c = [self.candles[i], self.candles[i+1]] # for simplification
                                        for e in range(2):
                                            c[e] = Candle(c[e][0], c[e][1])
                                            c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                        if i != len(self.candles)-1:
                                            vertices = []
                                            for j in range(2):
                                                if data[j][i] != data[j][i]: break # nan check
                                                vertices.append(QtCore.QPointF(c[0].x+c[0].wid/2, self.toCoord("y", data[j][i]))) # get positions
                                                vertices.append(QtCore.QPointF(c[1].x+c[1].wid/2, self.toCoord("y", data[j][i+1])))
                                        if len(vertices) == 4:
                                            # for cool effect remove
                                            vertices.append(vertices.pop(2)) # change order
                                            pol = QtWidgets.QGraphicsPolygonItem(QtGui.QPolygonF(vertices))
                                            pol.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))#(QtGui.QColor(color))
                                            pol.setBrush(QtGui.QColor(color))
                                            self.view.scene().addItem(pol)
                                elif ob.name == "dots":
                                    pass
                        continue
                    elif ind.dMode == 2: # bottom graph
                        self.sview.setVisible(True)
                        self.syview.setVisible(True)
                        self.sview.gridconv = deepcopy(self.gridconv)
                        self.sview.visinds = deepcopy(ind.dData)
                        self.sview.graphInds = deepcopy(ind.data)
                        self.sview.regularScene()
                        changey = True
                        continue
                    for obj in ind.data: # in case of bollinger e.g. show all graphs
                        if ind.dMode == 1: # if displayMode = Graph
                            for i in range(len(self.candles)-1): # do same as graph
                                c = [self.candles[i], self.candles[i+1]] # for simplification
                                for e in range(2):
                                    c[e] = Candle(c[e][0], c[e][1])
                                    c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                                if i != len(self.candles)-1:
                                    close1 = self.toCoord("y", obj[i]) # get positions
                                    close2 = self.toCoord("y", obj[i+1])
                                if not (close1 != close1 or close2 != close2): # nan check
                                    can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                                    can.setPen(QtGui.QColor(ind.color))
                                    self.view.scene().addItem(can)
                        elif ind.dMode == 2: # display graph on bottom view
                            self.sview.setVisible(True)
                            self.syview.setVisible(True)
                            if ind.data.index(obj) == 0: 
                                if ind.indName == "rsi":
                                    self.sview.colors.append(QtGui.QColor("#888888"))
                                    fifties = []
                                    for i in range(len(self.candles)):
                                        fifties.append(50)
                                    self.sview.graphInds.append(fifties)
                                elif ind.indName == "macd":
                                    self.sview.colors.append(QtGui.QColor("#888888"))
                                    zeroes = []
                                    for i in range(len(self.candles)):
                                        zeroes.append(0)
                                    self.sview.graphInds.append(zeroes)
                                elif ind.indName == "atr":
                                    pass

                                self.sview.colors.append(QtGui.QColor(ind.color))
                            else:
                                col = QtGui.QColor(ind.color)
                                col.setRed(255-col.red())
                                col.setGreen(255-col.green())
                                col.setBlue(255-col.blue())
                                self.sview.colors.append(col)
                            self.sview.graphInds.append(obj)
                            self.sview.gridconv = deepcopy(self.gridconv)
                            self.sview.regularScene()
                            changey = True
                        elif ind.dMode == 3: # volume
                            self.sview.colors.append(QtGui.QColor(ind.color))
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
        for s in self.spots: # show selected spots
            can = Candle(self.candles[s][0], self.candles[s][1])
            can.convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
            rect = QtCore.QRectF(can.x, can.top-50, can.wid, can.tip-can.top+100)
            self.view.scene().addRect(rect, QtGui.QColor("#ffff00"))

        # visual operation objects
        for ob in self.sceneOps.visuals:
            if ob.name == "dot":
                pos = list(ob.position)
                if pos[0] is None: # the x position of a dot is based on the position entered in sceneOps
                    pos[0] = self.sceneOps.pos
                if pos[1] is None: # y position of a dot is based on the y of x unless specified otherwise
                    pos[1] = self.raw[pos[0]][3]
                obj = Dot(pos[0], pos[1], ob.shape, ob.color)
                obj.convCoords(self.gridconv, self.rangex, self.rangey, self.heivar)
                self.view.scene().addItem(obj)
            elif ob.name == "line":
                pos = list(ob.position)
                if pos[0] is None: pos[0] = 0 # if none is entered, just assume it starts from the beginning
                # pos[1] doesn't matter here
                ind = pos[0]*[float("nan")] + ob.data # move data by position
                ind += (len(self.candles)-len(ind))*[float("nan")] # fill with filler after if len is too little
                for i in range(len(self.candles)-1): # do same as graph
                    c = [self.candles[i], self.candles[i+1]] # for simplification
                    for e in range(2):
                        c[e] = Candle(c[e][0], c[e][1])
                        c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
                    if i != len(self.candles)-1:
                        close1 = self.toCoord("y", ind[i]) # get positions
                        close2 = self.toCoord("y", ind[i+1])
                    if not (close1 != close1 or close2 != close2): # nan check
                        can = QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2)
                        pen = QtGui.QPen(QtGui.QColor(ob.color))
                        if ob.shape == "dashed": pen.setStyle(QtCore.Qt.PenStyle.DashLine)
                        elif ob.shape == "dotted": pen.setStyle(QtCore.Qt.PenStyle.DotLine)
                        elif ob.shape == "dashdot": pen.setStyle(QtCore.Qt.PenStyle.DashDotLine)
                        can.setPen(pen)
                        self.view.scene().addItem(can)

        # adjust scrollbar
        if len(self.candles) != 0:
            offset = self.view.horizontalScrollBar().value()%self.gridconv[0]
            if self.sceneOps.update: # if a spot should be highlighted
                self.sceneOps.update = False # only do that once
                ind = ((self.sceneOps.pos-self.rangex[0])*self.gridconv[0])/self.gridconv[1] # scroll from time
                if self.sceneOps.right: # if the spot should be highlighted on the right, move the scrollbar over to the left
                    ind -= int(self.view.width()*0.9) # move scene to the left
                    if ind < 0: ind = 0 # if moving would result in negatives, just show start position
                self.view.horizontalScrollBar().setValue(int(ind))
                yval = self.toCoord("y", self.candles[self.sceneOps.pos][1][3]) - self.view.height()/2
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

        self.loading = False

    def updateCrosshair(self, event): # update the crosshair when mouse moved, fn will be passed on
        pointf = QtCore.QPointF(event.pos().x(), event.pos().y()) # preconvert because else it wont accept
        scene_pos = self.view.mapFromScene(pointf)

        dx = self.view.horizontalScrollBar().value()*2 # also add the change of the scrolling to the crosshair
        dy = self.view.verticalScrollBar().value()*2 # why *2 dont ask me

        # crosshair placement
        self.crosshairy.setLine(scene_pos.x()+dx, scene_pos.y()-1500+dy, scene_pos.x()+dx, scene_pos.y()+1500+dy)
        self.crosshairx.setLine(scene_pos.x()-2000+dx, scene_pos.y()+dy, scene_pos.x()+2000+dx, scene_pos.y()+dy)
            

    def updateInfo(self, event): # updates Condition info about candle
        if not self.moved:# and self.mode.currentText() == "Base Graph": # no accidental drag clicking
            canclick = False # if candle has been clicked on
            # self.tempIndicator(False) # reset all temporary indicators 
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
                            self.setScene()
                        else:
                            self.peek(item)
                            canclick = True
            if not canclick and self.focus.placed:
                self.view.scene().removeItem(self.focus)
                self.view.scene().removeItem(self.tangent)
                self.tangent = None
                self.focus.placed = False
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
        if spot >= 1: 
            start = spot - 20 # so it wont wrap around
            if start <= 0: 
                start = 0
                x = list(range(spot+1))
                y = self.raw[start:spot+1]
            else: 
                x = list(range(20))
                y = self.raw[start+1:spot+1] # get last 100 price points
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

        if type(self.tangent) == QtWidgets.QGraphicsLineItem:
            self.view.scene().removeItem(self.tangent)
        self.tangent = QtCore.QLineF(candle.x-width*-100, candle.y-100*m, candle.x-width*100, candle.y+100*m)
        self.tangent = QtWidgets.QGraphicsLineItem(self.tangent)
        self.tangent.setPen(QtGui.QColor(50, 240, 240))
        self.view.scene().addItem(self.tangent)
        
        # self.tempIndicator(True, candle)
    
    # def tempIndicator(self, add, candle=None): # shows or removes temporary indicators
    #     dispInds = ["sma", "ema", "bollinger", "gaussian", "v", "ʌ", "w", "m", "shs", "trend", "support", "resistance", "line"] # indicators that will be displayed
    #     if add:
    #         for cond in logic.conditions:
    #             #cond = logic.conditions[logic.find("c", ind[0])]
    #             for var in cond["vars"]:
    #                 #if type(var) == IndicatorVariable and var.var == "" and var.id == ind[1]: break # break at correct indicator
    #                 if type(var) == IndicatorVariable and var.var == "" and var.indName in dispInds and var.val is not None:
    #                     self.tempInds.append([])
    #                     if var.indName in ["sma", "ema", "bollinger", "gaussian"]:
    #                         for obj in var.val: # in case of bollinger e.g. show all graphs
    #                             for i in range(len(self.candles)-1): # do same as graph
    #                                 c = [self.candles[i], self.candles[i+1]] # for simplification
    #                                 for e in range(2):
    #                                     c[e] = Candle(c[e][0], c[e][1])
    #                                     c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
    #                                 if i != len(self.candles)-1:
    #                                     close1 = self.toCoord("y", obj[i]) # get positions
    #                                     close2 = self.toCoord("y", obj[i+1])
    #                                 if not (close1 != close1 or close2 != close2): # nan check
    #                                     self.tempInds[-1].append(QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, close1, c[1].x+c[1].wid/2, close2))
    #                                     self.tempInds[-1][-1].setPen(QtGui.QColor(cond["color"]))
    #                                     self.view.scene().addItem(self.tempInds[-1][-1])
    #                     elif var.indName in ["v", "ʌ", "w", "m", "shs"]: # for shapes just draw the shape
    #                         points = var.val[:-1] # cut off the size
    #                         if var.indName == "shs": points.pop() # remove neckline
    #                         for p in range(len(points)-1):
    #                             c = [self.candles[points[p]], self.candles[points[p+1]]] # for simplification
    #                             for e in range(2):
    #                                 c[e] = Candle(c[e][0], c[e][1])
    #                                 c[e].convCoords(gridc=self.gridconv, rx=self.rangex, ry=self.rangey, height=self.heivar)
    #                             self.tempInds[-1].append(QtWidgets.QGraphicsLineItem(c[0].x+c[0].wid/2, c[0].y+c[0].hei/2, c[1].x+c[1].wid/2, c[1].y+c[1].hei/2))
    #                             self.tempInds[-1][-1].setPen(QtGui.QColor(cond["color"]))
    #                             self.view.scene().addItem(self.tempInds[-1][-1])
    #                     elif var.indName in ["trend", "support", "resistance", "line"]: # line indicators
    #                         if var.indName in ["support", "resistance"]:
    #                             c = var.val[0]
    #                             m = var.val[1]
    #                             size = var.val[2]
    #                         elif var.indName == "line":
    #                             c = var.val[0][candle.time]
    #                             m = var.val[0][candle.time-1] - var.val[0][candle.time]
    #                             size = -100
    #                         if var.indName == "trend": # for only trend replace the normal trend line and show another one instead
    #                             m = var.val[0][candle.time]
    #                             m *= self.gridconv[1] # convert to coordinates
    #                             m *= self.gridconv[0]
    #                             self.view.scene().removeItem(self.tangent)
    #                             self.tangent = QtCore.QLineF(candle.x-self.gridconv[0]*-100, candle.y-100*m, candle.x-self.gridconv[0]*100, candle.y+100*m)
    #                             self.tangent = QtWidgets.QGraphicsLineItem(self.tangent)
    #                             self.tangent.setPen(QtGui.QColor(cond["color"]))
    #                             self.view.scene().addItem(self.tangent)
    #                         else:
    #                             xs = [candle.time-abs(size), candle.time]
    #                             if size < 0: xs[1] -= size # size < 0 just means to also extend right
    #                             ys = [c-m*(candle.time-xs[0]), c+m*(xs[1]-candle.time)]
    #                             for i in range(2): # convert to coordinates
    #                                 xs[i] = coordinate("x", xs[i], self.gridconv, self.rangex, self.rangey, self.heivar)
    #                                 ys[i] = coordinate("y", ys[i], self.gridconv, self.rangex, self.rangey, self.heivar)
    #                             line = QtCore.QLineF(xs[0], ys[0], xs[1], ys[1])
    #                             self.tempInds[-1].append(QtWidgets.QGraphicsLineItem(line))
    #                             self.tempInds[-1][-1].setPen(QtGui.QColor(cond["color"]))
    #                             self.view.scene().addItem(self.tempInds[-1][-1])
    #     else: # remove all indicators
    #         if self.tabs.tabText(self.tabs.currentIndex()) not in ["Backtest", "Exit Percentages", "Benchmark Comparison"]: # if a normal tab is displayed
    #             for ind in self.tempInds:
    #                 for obj in ind:
    #                     self.view.scene().removeItem(obj)
    #         self.tempInds = []

    def resetWindows(self): # (re)set docker windows
        self.setStrategyDocker()
        self.setReviewDocker()

    def setStrategyDocker(self): # resets the left docker widget
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        lab = QtWidgets.QLabel("Indicators", wid)
        lab.setStyleSheet("border: none;")
        lab.move(6, 7)
        indlist = RightClickList(wid)
        indlist.setGeometry(6, 25, 134, 200)
        indlist.setStyleSheet("background-color: #000000; border: 2px inset #A0A0A0;")
        for ind in logic.indicators:
            item = IDItem(ind.name, ind.id)
            brush = QtGui.QBrush(QtGui.QColor(ind.color))
            item.setForeground(brush)
            indlist.addItem(item)
        btn = QtWidgets.QPushButton("Add...", wid)
        btn.setGeometry(145, 25, 50, 22)
        btn.clicked.connect(self.indicatorDialog)

        def changeIndicator(item : IDItem):
            self.indicatorDialog(item.id)
        
        indlist.itemDoubleClicked.connect(changeIndicator)

        def delete(item=None):
            if len(logic.indicators) == 0: return
            if item is None or type(item) == bool: item = indlist.currentItem()
            logic.indicators.pop(logic.find("i", item.id))
            indlist.takeItem(indlist.row(item)) # take item out of list
            self.setScene()

        indlist.fns["Delete"] = delete

        btn = QtWidgets.QPushButton("Delete", wid)
        btn.setGeometry(145, 50, 50, 22)
        btn.clicked.connect(delete)

        lab = QtWidgets.QLabel("Strategies", wid)
        lab.setStyleSheet("border: none;")
        lab.move(6, 232)
        strlist = RightClickList(wid)
        strlist.setGeometry(6, 250, 134, 200)
        strlist.setStyleSheet("background-color: #000000; border: 2px inset #A0A0A0;")
        for strat in logic.strategies:
            item = IDItem(strat.name, strat.id)
            # brush = QtGui.QBrush(QtGui.QColor(strat.color))
            # item.setForeground(brush)
            strlist.addItem(item)
        
        def addStrategy(): # shows a file select dialog for selecting a strategy
            filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open strategy file...", "", "Python File (*.py)")[0] # get filename
            if filename == "": return
            i = 0
            idd = 0
            while i < len(logic.strategies): # check if id is already in use
                if logic.strategies[i].id == idd:
                    idd += 1
                    i = -1 # if id in use go up and restart process
                i += 1
            # load class from file
            spec = util.spec_from_file_location("user_module", filename)
            userModule = util.module_from_spec(spec)
            spec.loader.exec_module(userModule)
            strat = getattr(userModule, "Strategy")
            obj = strat()
            logic.strategies.append(Strategy(idd, filename.split("/")[-1][:-3], filename, obj.args))
            # display dbox asking for arguments
            self.setStrategyDocker()

        def deleteStrategy(item): # removes strategy from logic and list
            idd = item.id
            del logic.strategies[logic.find("s", item.id)]
            strlist.takeItem(strlist.row(item))
            i = 0
            while i < len(logic.operations):
                if logic.operations[i].diagnostics["ID"] == idd: del logic.operations[i]
                else: i += 1
            self.specialObjects["oList"].operations = []
            self.specialObjects["oList"].sortedList()
        
        def markStrategy(item): # marks all entries of the strategy
            idd = item.id
            strat = logic.strategies[logic.find("s", idd)]
            spec = util.spec_from_file_location("user_module", strat.filename)
            userModule = util.module_from_spec(spec)
            spec.loader.exec_module(userModule)
            strat = getattr(userModule, "Strategy")
            obj = strat()
            data = []
            for i in range(len(self.raw)):
                data.append(obj.entry(self.raw, self.timeaxis, i))
            self.marked = []
            for d in data:
                if d: self.marked.append("#40ff7700")
                else: self.marked.append(None)
            self.setScene()
        
        strlist.fns["Mark Entries"] = markStrategy
        strlist.fns["Delete"] = deleteStrategy

        def run(item=None): # runs the selected strategy/ies
            if len(logic.strategies) == 0: return
            if item is None or type(item) == bool: item = strlist.currentItem()
            if item is None: return
            strat = logic.strategies[logic.find("s", item.id)]

            # reset all because continuing is too complex
            self.specialObjects["smart"] = SmartStats()
            self.specialObjects["smartList"].clear()
            self.specialObjects["oList"].operations = []
            logic.operations = []
            self.specialObjects["oList"].clear()

            self.specialObjects["smart"].names = [item.text()]
            self.createStrategyProcesses(strat.id)
        
        def runAll(): # runs all strategies in multiprocesses
            if len(logic.strategies) == 0: return

            # reset all because continuing is too complex
            self.specialObjects["smart"] = SmartStats()
            self.specialObjects["smartList"].clear()
            self.specialObjects["oList"].operations = []
            logic.operations = []
            self.specialObjects["oList"].clear()

            self.specialObjects["smart"].names = []
            for i in range(strlist.count()):
                item = strlist.item(i)
                self.specialObjects["smart"].names.append(item.text())
            self.createStrategyProcesses()
            
        btn = QtWidgets.QPushButton("Add...", wid)
        btn.setGeometry(145, 250, 50, 22)
        btn.clicked.connect(addStrategy)

        btn = QtWidgets.QPushButton("Run", wid)
        btn.setGeometry(145, 280, 50, 22)
        btn.clicked.connect(run)

        btn = QtWidgets.QPushButton("Run All", wid)
        btn.setGeometry(145, 310, 50, 22)
        btn.clicked.connect(runAll)

        def configure(): # configure settings for all strategies
            dbox = QtWidgets.QDialog(self)
            dbox.setWindowTitle("Configure Strategies...")
            dbox.setFixedSize(500, 300)
            # QtWidgets.QLabel("Balance", dbox).move(10, 10)
            # QtWidgets.QLineEdit()
            lis = QtWidgets.QListWidget(dbox)
            lis.setGeometry(10, 10, 300, 200)
            for itm in logic.stockConfigures:
                suggs, links = self.generateSuggestions()
                name = itm.name
                if itm.typ in [int, float]: typ = "lineedit"
                elif itm.typ == str: 
                    if itm.drange == []: # if no limits
                        typ = "autocomplete"
                        name = [name] + suggs
                    else:
                        typ = "combobox"
                it = LabeledLineEditItem(name, parent=lis, typ=typ)
                if typ == "combobox": it.labeledWidget.widget.addItems(itm.drange) # add items to cbox
                elif typ == "autocomplete": it.labeledWidget.widget.links = links
                it.setText(str(itm.val))
            
            def ok():
                for i in range(lis.count()):
                    logic.stockConfigures[i].test = lis.item(i).text()
                    check = logic.stockConfigures[i].errorcheck()
                    if check == "Type Error":
                        self.errormsg(f"{logic.stockConfigures[i].test} is an invalid {logic.stockConfigures[i].typ}.")
                        return
                    elif check == "Range Error":
                        self.errormsg(f"{logic.stockConfigures[i].test} is out of range.")
                        return
                    if logic.stockConfigures[i].name == "Period": period = logic.stockConfigures[i].test
                    elif logic.stockConfigures[i].name == "Interval": interval = logic.stockConfigures[i].test
                
                avail1 = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"] # available intervals
                if period == "ytd":
                    inv = interval
                    comps = avail1[:avail1.index("60m")] # make interval range
                    if inv in comps:
                        self.errormsg("Interval too small for period.")
                        return
                elif period == "max":
                    inv = interval
                    comps = avail1[:avail1.index("1d")] # make interval range
                    if inv in comps:
                        self.errormsg("Interval too small for period.")
                        return
                else:
                    if period[-1] == "d": # day range
                        if interval in avail1[avail1.index("1d"):]:
                            self.errormsg("Interval too big for period.")
                            return
                    elif period[-1] == "o": # month range
                        inv = interval
                        comps = avail1[:avail1.index("60m")] # make interval range
                        if inv in comps:
                            self.errormsg("Interval too small for period.")
                            return
                    elif period[-1] == "k": # week period
                        pass
                    else: # year range
                        if int(period[:-1]) <= 2: # max 2 years
                            if interval in avail1[:avail1.index("1h")]:
                                self.errormsg("Interval too small for period.")
                                return
                        else: # above 2 years
                            if interval in avail1[:avail1.index("1d")]:
                                self.errormsg("Interval too small for period.")
                                return
                dicc = {} # convert typevalues to dict
                for st in logic.stockConfigures: # if no errors happened; store test values in real values
                    st.val = st.typ(st.test)
                    dicc[st.name] = st.val
                dbox.close()

            btn = QtWidgets.QPushButton("OK", dbox)
            btn.move(215, 250)
            btn.clicked.connect(ok)

            dbox.exec()

        btn = QtWidgets.QPushButton("Configure...", wid)
        btn.setGeometry(6, 460, 75, 22)
        btn.clicked.connect(configure)

        self.specialObjects["smart"] = SmartStats() # list to display strategies smartly
        self.specialObjects["smartList"] = QtWidgets.QListWidget(wid)
        self.specialObjects["smartList"].setGeometry(6, 500, 189, 100)
        self.specialObjects["smartList"].setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.specialObjects["smartList"].setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.specialObjects["smartList"].setStyleSheet("background-color: #000000; border: 2px inset #A0A0A0; color: #ffffff;")

        self.docks[0].setWidget(wid)
    
    def setReviewDocker(self): # resets the bottom docker widget
        wid = QtWidgets.QWidget()
        wid.setStyleSheet(widgetstring)
        def dblClick(item : OperationListItem):
            for op in logic.operations:
                if op.diagnostics == item.dicct: break # get corresponding operation
            ticker = item.dicct["Ticker"]
            interval = item.dicct["Interval"]
            period = item.dicct["Period"]
            self.sceneOps.pos = item.dicct["Exit Spot"]
            self.sceneOps.update = True
            self.sceneOps.right = True
            self.sceneOps.visuals = []
            vis = stocklib.Visual("dot", "upTriangle", "#00ff00")
            vis.position = (item.dicct["Entry Spot"], None) # place at entry spot
            self.sceneOps.visuals.append(vis)
            vis = stocklib.Visual("dot", "downTriangle", "#ff0000")
            vis.position = (item.dicct["Exit Spot"], None) # place at entry spot
            self.sceneOps.visuals.append(vis)
            self.sceneOps.visuals += op.reviewVis
            if self.tabs.count() == 1: how = "+"
            else: how = ""
            if self.prefs["Calculate strategies on live data"]:
                data, dates = stock_data(ticker, period=period, interval=interval)
                self.newScene(how=how, tabName=f"Live {ticker}", ticker=f"{ticker},{period},{interval}", data=[data, dates])
            else:
                data = read(ticker)
                self.newScene(how, ticker, ticker, data=[data, []])
        
        defaultsorts = ["Newest", "ID", "Ticker", "Entry Time", "Period", "Interval", "Entry Spot", "Entry Price",
                        "Exit Time", "Exit Spot", "Exit Price", "Exit Percentage"]
        sorts = deepcopy(defaultsorts)

        lab = QtWidgets.QLabel("Operations", wid)
        lab.setStyleSheet("border: none;")
        lab.move(7, 2)
        self.specialObjects["oList"] = OperationList(wid)
        self.specialObjects["oList"].setGeometry(7, 17, 235, 150)
        self.specialObjects["oList"].itemDoubleClicked.connect(dblClick)
        self.specialObjects["oList"].sorts = sorts
        self.specialObjects["oList"].attrSort = ["Ticker", "Entry Time", "Exit Percentage"] # what should be displayed by each list item
        self.specialObjects["oList"].setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.specialObjects["oList"].setStyleSheet("background-color: #000000; border: 2px inset #A0A0A0; color:#ffffff;")
        for op in logic.operations:
            self.specialObjects["oList"].addItem(OperationListItem(op.diagnostics, displist=["Ticker", "Entry Time", "Exit Percentage"]))
        
        disabled_style = """
            QPushButton:disabled {
                background-color: #000000;
                color: #666666; 
            }"""

        self.specialObjects["stopBtn"] = QtWidgets.QPushButton("Stop", wid)
        self.specialObjects["stopBtn"].setStyleSheet(disabled_style)
        self.specialObjects["stopBtn"].setGeometry(250, 17, 50, 22)
        self.specialObjects["stopBtn"].setDisabled(True)
        self.specialObjects["stopBtn"].clicked.connect(lambda: self.stopButton("strategies"))

        def export():
            # takes the dictionaries from the oList and writes them to a .xlsx
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save Data...", "", "Excel 2007-365 (*.xlsx)")
            if file_path == "":
                return 
            dicts = []
            for o in range(self.specialObjects["oList"].count()):
                dicts.append(self.specialObjects["oList"].item(o).dicct)
            df = pd.DataFrame(dicts)
            df.to_excel(file_path, index=False)

        self.specialObjects["exBtn"] = QtWidgets.QPushButton("Export...", wid)
        self.specialObjects["exBtn"].setGeometry(250, 145, 50, 22)
        self.specialObjects["exBtn"].clicked.connect(export)
        self.specialObjects["exBtn"].setStyleSheet(disabled_style)
        self.specialObjects["exBtn"].setEnabled(False)

        def configure(): # dbox to configure
            db = QtWidgets.QDialog(self)
            db.setWindowTitle("Configure List...")
            db.setFixedSize(300, 225)
            QtWidgets.QLabel("Sort by", db).move(140, 10)
            sbox = QtWidgets.QComboBox(db)
            sbox.setGeometry(185, 10, 100, 21)
            sbox.addItems(self.specialObjects["oList"].sorts)
            sbox.setCurrentText(self.specialObjects["oList"].sortBy)
            revcheck = QtWidgets.QCheckBox("Reverse", db)
            revcheck.move(185, 35)
            revcheck.setChecked(self.specialObjects["oList"].reversed)
            hcheck = QtWidgets.QCheckBox("Show Hrz. Scrollbar", db)
            hcheck.move(10, 160)
            if self.specialObjects["oList"].horizontalScrollBarPolicy() != QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff: hcheck.setChecked(True)
            check = QtWidgets.QCheckBox("Show Condition Values", db)
            check.move(150, 160)
            check.setChecked(self.specialObjects["oList"].showConditions)
            QtWidgets.QLabel("Displayed Attributes", db).move(10, 10)
            slist = QtWidgets.QListWidget(db)
            slist.setGeometry(10, 30, 150, 125)
            for s in self.specialObjects["oList"].sorts[1:]:
                item = QtWidgets.QListWidgetItem(s)
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                if s in self.specialObjects["oList"].attrSort: item.setCheckState(QtCore.Qt.CheckState.Checked)
                else: item.setCheckState(QtCore.Qt.CheckState.Unchecked)
                slist.addItem(item)
            def ok():
                if hcheck.isChecked(): self.specialObjects["oList"].setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                else: self.specialObjects["oList"].setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.specialObjects["oList"].showConditions = check.isChecked()
                self.specialObjects["oList"].sortBy = sbox.currentText()
                self.specialObjects["oList"].reversed = revcheck.isChecked()
                self.specialObjects["oList"].attrSort = []
                for ind in range(slist.count()):
                    item = slist.item(ind)
                    if item.checkState() == QtCore.Qt.CheckState.Checked:
                        self.specialObjects["oList"].attrSort.append(item.text())
                self.specialObjects["oList"].sortedList()
                db.close()
            btn = QtWidgets.QPushButton("OK", db)
            btn.move(115, 190)
            btn.clicked.connect(ok)
            db.exec()
        
        btn = QtWidgets.QPushButton("Configure List...", wid)
        btn.setGeometry(250, 50, 100, 22)
        btn.clicked.connect(configure)

        def benchmark(): # runs benchmark on current operations from both strategies and compares them with a ticker
            if logic.operations == []:
                self.errormsg("Run a strategy first.")
                return
            dbox = QtWidgets.QDialog(self)
            dbox.setWindowTitle("Benchmark")
            dbox.setFixedSize(200, 100)
            QtWidgets.QLabel("Ticker", dbox).move(10, 10)
            sugg, links = self.generateSuggestions()
            ticker = AutoCompleteLineEdit(dbox, sugg)
            ticker.links = links
            ticker.move(10, 35)
            ok = False

            def close():
                nonlocal ok
                ok = True
                dbox.close()

            btn = QtWidgets.QPushButton("OK", dbox)
            btn.move(65, 60)
            btn.clicked.connect(close)
            dbox.exec()
            if not ok or ticker.text() == "": return
            ticker = ticker.text()
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save Data...", "", "Excel 2007-365 (*.xlsx)")
            if file_path == "": return 
            for org in self.specialObjects["oList"].operations:
                if org["Entry Time"] != org["Entry Time"]: # if time is nan
                    self.errormsg("This only works on live data.")
                    return
                if "ID" in list(org.keys()): 
                    if org["ID"] == 1:
                        break # get data from first strategy
                else: break
            alll = [] # all ids that have already run
            for o in logic.operations:
                if o.diagnostics["ID"] not in alll:
                    alll.append(o.diagnostics["ID"])
            groups = [x.name.upper() for x in self.commons if type(x) == Group]
            if ticker.upper() in groups: # if a group was entered
                for c in self.commons:
                    if type(c) == Group:
                        if c.name.upper() == ticker.upper(): break
                ticker = deepcopy(c.items) # copy tickers
            else:
                ticker = [ticker] # make list of ticker
            
            data = {}
            dates = {}

            for t in ticker: # download data for every stock in group
                da, dt = stock_data(t, period=org["Period"], interval=org["Interval"])
                #dt = [d.to_pydatetime().replace(tzinfo=None) for d in dt]
                if len(dt) > 1:# if one fails, just continue
                    data[t] = da
                    dates[t] = dt

            if len(data) == 0: # if all fail; break
                self.errormsg("No data for period.")
                return
            fkey = list(dates.keys())[0] # first key of dates dict

            # assume data and dates are formatted like: data = {"MSFT":[...]}, dates = {"MSFT":[...]}
            # sync dates for each stock in groups meaning trim all data to same size and time scale
            sync = [] # will be filled with tuples
            for key in dates:
                sync.append((key, dates[key][0])) # make tuples of keys and dates
            
            sync = sorted(sync, key=lambda x: x[1])
            if sync[0][1] != sync[-1][1]: # if the first dates dont match; sync by trimming everything before latest first date
                for key in dates:
                    while dates[key][0] < sync[-1][1]:
                        del dates[key][0]
                        del data[key][0]

            for st in logic.stockConfigures:
                if st.name == "Balance": break
            start = st.val
            bal = {}
            for idd in alll:
                bal[idd] = start
            ops = deepcopy(self.specialObjects["oList"].operations)
            ops = sorted(ops, key=lambda x: x.get("Entry Time", float("inf")))

            poplist = []
            for i in range(len(ops)): # remove all operations that happened before the first timespot of the benchmark
                if ops[i]["Entry Time"] < dates[fkey][0]:
                    poplist.append(i)
                else: break # because they're sorted, just break after first few
            poplist.reverse()
            for p in poplist:
                ops.pop(p)
            
            question = [] # operations that apply to current timestamp
            currunnin = [] # operations that are currently running
            kept = {} # dict of lists of kept operations that will be displayed in the benchmark
            for idd in alll:
                kept[idd] = []

            for d in dates[fkey]: # go through all of the dates
                question = [] # get operations that happened in timeframe
                while True:
                    if len(ops) == 0: break
                    if ops[0]["Entry Time"] <= d: # if operation happened between last time and now
                        question.append(ops[0])
                        del ops[0] # remove first entry
                    else: break # bcs they're sorted; break at first one after the current date
                
                poplist = [] # sell running operations
                for o in currunnin: # terminate operations if they have been running until current date
                    ke = o["ID"] 
                    if o["Exit Time"] <= d:
                        poplist.append(currunnin.index(o))
                        bal[ke] += o["Amount"]*o["Exit Price"]
                        kept[ke].append(o)
                poplist.reverse()
                for p in poplist:
                    currunnin.pop(p)
                
                for o in question: # buy new operations if possible
                    ke = o["ID"] 
                    if o["Entry Price"]*o["Amount"] <= bal[ke]:
                        bal[ke] -= o["Entry Price"]*o["Amount"]
                        currunnin.append(o)

            # sell all at their exit price (might be a little off)
            for o in currunnin:
                ke = o["ID"] 
                bal[ke] += o["Amount"]*o["Exit Price"]
                kept[ke].append(o)
            currunnin = []

            for idd in alll:
                bal[idd] = start

            liquid = {} # dict of lists of liquid money at each timestep
            for idd in alll:
                liquid[idd] = []
            stockdata = {} # dict of stocks in ohlc | {"MSFT":[[ohlc], [dates]]}
            for key in kept:
                for o in kept[key]:
                    if o["Ticker"] not in stockdata.keys(): 
                        stockdata[o["Ticker"]] = list(stock_data(o["Ticker"], period=o["Period"], interval=o["Interval"]))
                        #stockdata[o["Ticker"]][1] = [d.to_pydatetime().replace(tzinfo=None) for d in stockdata[o["Ticker"]][1]]

            benliq = {} # liquid for the benchmark stocks
            for key in data:
                benliq[key] = []
            s = -1
            for d in dates[fkey]:
                s += 1
                for key in benliq: # calculate liquid for all
                    benliq[key].append(data[key][s][3]/data[key][0][3])
                # question = []
                liqpart = {} # liquid part for each strategy
                for idd in alll:
                    liqpart[idd] = 0
                while True:
                    l = 0
                    for key in kept:
                        l += len(kept[key])
                    if l == 0: break
                    end = False
                    for key in kept:
                        if len(kept[key]) == 0: break
                        if kept[key][0]["Entry Time"] <= d:
                            bal[key] -= kept[key][0]["Amount"]*kept[key][0]["Entry Price"]
                            for i in range(len(stockdata[kept[key][0]["Ticker"]][1])): # get equal date part in ticker data
                                if stockdata[kept[key][0]["Ticker"]][1][i] <= d: break
                            kept[key][0]["Spot"] = i-1 # -1 because 1 is always added each timestamp
                            currunnin.append(kept[key][0])
                            del kept[key][0]
                        else: 
                            end = True
                            break
                    if end: break
                
                poplist = []
                for i in range(len(currunnin)):
                    currunnin[i]["Spot"] += 1
                    ke = currunnin[i]["ID"] 
                    if currunnin[i]["Exit Time"] <= d:
                        poplist.append(i)
                        bal[ke] += currunnin[i]["Amount"]*currunnin[i]["Exit Price"]
                    else: 
                        liqpart[ke] += currunnin[i]["Amount"]*stockdata[currunnin[i]["Ticker"]][0][currunnin[i]["Spot"]][3]
                
                poplist.reverse()
                for p in poplist: currunnin.pop(p)
                
                for key in liquid:
                    liquid[key].append((bal[key]+liqpart[key])/start)
            findict = {"Date":dates[fkey]}
            for key in liquid:
                coolkey = logic.strategies[logic.find("s", key)].name
                findict[coolkey] = liquid[key]
            for key in benliq:
                findict[key] = benliq[key] # copy dict
            # analysis["Benchmark"] = findict # save benchmark data in analysis variable
            df = pd.DataFrame(findict)
            df.to_excel(file_path, index=False)
        
        btn = QtWidgets.QPushButton("Benchmark", wid)
        btn.clicked.connect(benchmark)
        btn.setGeometry(250, 100, 100, 22)

        self.docks[1].setWidget(wid)

    def updateOperations(self, ec=0): # get operations from the queue and reset the bottom docker
        if not self.queue.empty():
            ec = 0
            ops = self.queue.get()
            logic.operations += ops
            self.specialObjects["oList"].operations = [o.diagnostics for o in logic.operations]
            self.specialObjects["oList"].sortedList()
            first = True
            for o in ops:
                v = o.diagnostics
                if "ID" not in list(self.specialObjects["smart"].entexs.keys()): self.specialObjects["smart"].entexs["ID"] = {"n+": 0, "n-": 0, "n": 0, "s+p": 0, "s-p": 0}
                if first:
                    first = False
                    self.specialObjects["smart"].entexs["ID"]["n"] += 1 # add one stock because one is always put out per queue update
                if v["Exit Percentage"] > 0: 
                    self.specialObjects["smart"].entexs["ID"]["n+"] += 1
                    self.specialObjects["smart"].entexs["ID"]["s+p"] += v["Exit Percentage"]
                else: 
                    self.specialObjects["smart"].entexs["ID"]["n-"] += 1
                    self.specialObjects["smart"].entexs["ID"]["s-p"] += v["Exit Percentage"]
            self.specialObjects["smart"].generate()
            self.specialObjects["smartList"].clear()
            for i in range(len(self.specialObjects["smart"].names)):
                if "ID" in list(self.specialObjects["smart"].entexs.keys()):
                    st = f"{self.specialObjects['smart'].names[i]}: Success: {self.specialObjects['smart'].succs['ID']:2.1%}, s/f: {self.specialObjects['smart'].sfs['ID']:.2f}"
                    it = QtWidgets.QListWidgetItem(st)
                    it.setToolTip(st)
                    self.specialObjects["smartList"].addItem(it)
                # i += 1
        elif ec == 2000 or self.stopbackgs: 
            self.specialObjects["stopBtn"].setEnabled(False)
            return # if ten seconds of nothing happen; cancel function
        else: ec += 1

        # queue another update in 5ms
        QtCore.QTimer.singleShot(5, lambda:self.updateOperations(ec))

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
                else: toload = stocks[int(which)] # if an index was passed in
            else: 
                if which.upper() in stocks: toload = which.upper() # if a ticker was passed in
                else:
                    self.errormsg(which + " ticker is not in the dataset.")
                    return
            red = read(toload)
            ticker = toload
            name = toload
            if what == "debug": name = "Debug " + name
        else:
            readtest = read(which, True)
            if len(readtest) == 0:
                self.errormsg(which.split("/")[-1] + " is not a valid file.")
                return
            red = readtest
            name = which.split("/")[-1]
        self.newScene(how, name, ticker, [red, []])

    def reinitIndicators(self): # regather data for the indicators after e.g. the scene switched
        self.marked = [] # unmark all
        for ind in logic.indicators: # indicators
            ind.getData(self.raw)

    def newScene(self, how="", tabName="", ticker="", data=[]): # reset scene and generate new scene using raw data
        # data is a list of 2 lists [0] is the data, [1] are the dates
        self.raw = data[0]
        self.timeaxis = data[1]
        self.loading = True # turn off scrolling while its loading
        self.candles = [] # empty candles
        self.rangex = (0, len(data[0]))
        self.marked = [] # reset marked spots
        self.reinitIndicators()
        mi = 10000 # minimum value
        ma = 0 # maximum value
        avg = 0 # avg body size
        cans = [] # candle data for smaller system
        for t in range(len(data[0])): # get candles
            if data[0][t][1] > ma: ma = data[0][t][1]
            if data[0][t][2] < mi: mi = data[0][t][2]
            avg += abs(data[0][t][3] - data[0][t][0])
            l = [t] # [time, [o, h, l, c]]
            l.append([data[0][t][0], data[0][t][1], data[0][t][2], data[0][t][3]])
            cans.append([data[0][t][0], data[0][t][1], data[0][t][2], data[0][t][3], data[0][t][4]])
            self.candles.append(l)
        self.sview.candles = cans
        avg /= len(data[0])
        tenpows = [0.0005]
        while tenpows[-1] < avg: # fill up the list
            if str(1000/tenpows[-1])[0] == "4": # multiple of 2.5
                tenpows.append(tenpows[-1]*2)
            else: tenpows.append(tenpows[-1]*5)
        if len(tenpows) > 1:
            contenders = [abs(avg/tenpows[-2]-1), abs(avg/tenpows[-1]-1)]
            if contenders[0] < contenders[1]: tenpow = tenpows[-2]
            else: tenpow = tenpows[-1]
        else: tenpow = 0.0005
        tenpow *= 2 # because it looked for square size 
        self.rangey = (mi-mi%tenpow, ma+(tenpow-ma%tenpow)) # fill until next square
        self.gridconv = [40, 5, 40, tenpow]
        syst = System()
        syst.gridconv = deepcopy(self.gridconv)
        syst.rangex = deepcopy(self.rangex)
        syst.rangey = deepcopy(self.rangey)
        syst.candles = deepcopy(self.candles)
        syst.raw = deepcopy(data[0])
        syst.timeaxis = deepcopy(data[1])
        if ticker.count(",") == 0: syst.live = [ticker] # no other data; take just the ticker
        else:
            sp = ticker.split(",")
            syst.live = sp
        if how == "+": 
            logic.systems.append(syst) # if a new tab is created
            # self.resetBacktest()
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
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(0, 0, 0))
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
