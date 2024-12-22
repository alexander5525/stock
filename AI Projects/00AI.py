import yfinance as yf
import tensorflow as tf
import pandas as pd
import datetime as dt
from random import randint
from keras import layers
import numpy as np
import pathlib
from math import isnan

# original name: AI.py
# ai that takes stock data, evaluates it through a deep classifier and returns a value between -1 and 1 to tell how the stock is going to go
# doesn't work though
# last modified: 1/29/2023

#create the dataset
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

file_path = os.path.join(root_dir, "read", "Usable.xlsx")
stocklist = pd.read_excel(file_path)["Symbols"] # read only the ticker symbols

stocks = stocklist.sort_values().reset_index(drop=True) # sort the stocks alphabetically so ai doesn't only train on good ones
stock_evals = pd.Series([stocks.pop(i*20) for i in range(stocks.size//20)], name="Symbols") # take out 5% / 1/20 of the dataset to evaluate the ai on (// means floor division)

def stock_data(ticker, start, end): # get hourly stockdata
    dat = yf.Ticker(ticker).history(start=start, end=end, interval='1h')
    return dat

raw = [] # raw stock data (ideally 2 years hourly)
all = [] # stotes every datapoint
data = []
y_data = []
siz = 1024 # number of input timestamps
pred_per = 2 # percentage of dataset to predict

def read(x): # get 2 year hourly data from 1/20/2023
    pat = os.path.join(root_dir, "read", f"{x}.txt")
    path = pathlib.Path(pat)
    if not path.exists(): 
        return 0 # check if file exists in dataset else return 0
    file = open(path)
    op = []
    hi = []
    lo = []
    cl = []
    vo = []
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

for s in stocks.loc[:499]: # for every stock ticker until 74
    raw.append(read(s)) # get raw data


def inp_fn(x, al=False): # generates data to run on # (x is a list of stock data lists, which contain numbers (shape=(75, 3000, 5)))
    global data # shape should be (75, siz, 5) # siz, 5 because time, features 
    data = []
    global y_data
    y_data = []
    global all
    if al: all = []
    for s in x: # stock in stock list
        if len(s) >= siz:  # all stock data needs to have at least siz datapoints
            date = randint(0, len(s)-siz-1) # get a random data range between begin and now-siz
            if al: # save all of the data for visualisation
                a = [[], [], [], [], []]
                for i in s[date:date+siz]:
                    for j in range(5): 
                        a[j].append(i[j]) # convert to shape=(75, 5, siz)
                all.append(a)
            sts = s[date:int(date+siz*(1-pred_per/100))] # get data from stock, from random date until 100 - pred_per % of siz is reached
            data.append(sts) # append shortened list to data
            sts = [] # tmp = [s[end][close], s[begin][close]]
            tmp = [s[date+siz][3], s[int(date+siz*(1-pred_per/100))-1][3]] # get close last 100 - pred_per % of stock
            sts.append((tmp[0]/tmp[1]-1)) # get rise in set timeframe in percent
            y_data.append(sts) # output is expected rise in a week
        # if n != 1: # clear the last lines
        #     print("\033[A                                                   \033[A")
        #     print("\033[A                                                   \033[A")
        # print("Shuffling Dataset...")
        # print(n, "/", 75, "\t\t\t")#x.size)

#inp_fn(raw)

# smaller samples:
# data = data[:1]
# y_data = y_data[:1]

#print(np.asarray(data).shape) # (71, 135, 5)

class LayerModel(tf.keras.Model):
    def __init__(self):
        super().__init__()
        self.l0 = layers.InputLayer(input_shape=(None, int(siz*(1-pred_per/100)), 5))
        self.l1 = layers.Conv1D(filters=128, kernel_size=25, activation="tanh")
        self.l2 = layers.MaxPooling1D()
        self.l3 = layers.Conv1D(filters=64, kernel_size=10, activation="tanh")
        self.l4 = layers.MaxPooling1D()
        self.l5 = layers.Flatten()
        self.l6 = layers.Dense(1, activation='linear')
    def call(self, inputs): # when model is made run this
        x = self.l0(inputs)
        x = self.l1(x)
        x = self.l2(x)
        x = self.l3(x)
        x = self.l4(x)
        x = self.l5(x)
        return self.l6(x)

class StockAlgorithm():
    def __init__(self):
        super().__init__()
        self.layers = LayerModel()
        self.lossfn = tf.keras.losses.MeanAbsoluteError()
        self.optimizer = tf.keras.optimizers.Adam()
        self.metric = tf.keras.metrics.Mean()
    
    def fit(self, epochs): # training function
        for e in range(epochs):
            print("============================================================\n" + "Start of epoch %d" % (e,))

            # generate data
            inp_fn(raw)
            tensor = tf.convert_to_tensor(data)
            # Iterate over the batches of the dataset
            for step, x_train in enumerate(tensor):
                with tf.GradientTape() as tape:
                    reconstructed = self.layers(x_train)
                    # Compute reconstruction loss
                    loss = self.lossfn(x_train, reconstructed)
                    loss += sum(self.layers.losses)  # Add KLD regularization loss

                grads = tape.gradient(loss, self.layers.trainable_weights)
                self.optimizer.apply_gradients(zip(grads, self.layers.trainable_weights))

                self.metric(loss)

                if step % 100 == 0:
                    print("step %d: mean loss = %.4f" % (step, self.metric.result()))


seqmod = tf.keras.Sequential((
    layers.InputLayer(input_shape=(int(siz*(1-pred_per/100)), 5)), 
    layers.Conv1D(filters=128, kernel_size=25, activation="tanh"), 
    layers.MaxPooling1D(), 
    layers.Conv1D(filters=64, kernel_size=10, activation="tanh"), 
    layers.MaxPooling1D(), 
    layers.Flatten(), 
    layers.Dense(1, activation='linear')))

model = StockAlgorithm()

model.fit(epochs=10)

#model.summary()

# training
cont = True
left = int(input("Train for how many cycles?\n"))

#seqmod.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mean_absolute_error") # rmsprop vs adam
# loss is nan

history = []

while cont:
    history.append(seqmod.fit(data, y_data, batch_size=128).history["loss"][0]) # make it so that history will contain all of the losses
    left -= 1
    print("Cycles left: ", left)
    if left == 0:
        if input("Continue training? (y/n)\n") == "y":
            left = int(input("How many cycles? \nEnter a number: "))
        else:
            cont = False
    if left > 0:
        inp_fn(raw) # gather new data
        #pass


print(history) # avg min loss: 35% from truth

# visualize data

rawevs = []

for s in stock_evals: # for every evaluation ticker
    rawevs.append(read(s)) # get raw data

inp_fn(rawevs, al=True)
pred = seqmod.predict(data)

preds = []

for i in range(len(pred)):
    preds.append(pred[i][0]) # get percent values and divide it into the timestamps

fil1 = open("out1.txt", "w") # graph data
for i in range(siz):
    for j in range(len(all)):
        for v in range(5): # values i.e. open, high...
            fil1.write(str(all[j][v][i]) + ",") # write all of the first values in first row etc
    fil1.write("\n") # go to next row
fil1.close()

fil2 = open("out2.txt", "w")
for j in range(len(y_data)):
    fil2.write(str(((1+preds[j])*100))) # predicted rise; output: percentage
    fil2.write("\n")
fil2.close()

