import yfinance as yf
import tensorflow as tf
import pandas as pd
import datetime as dt
from random import randint
from keras import layers
#from math import tanh, atanh
import numpy as np

# original name: AI Basic.py
# ai that takes stock data, evaluates it through a deep classifier and returns a predicted percentage value for the rise in 1 week
# my very first attempt at using tensorflow to predict something in the stock market
# last modified: 1/15/2023

#create the dataset
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

file_path = os.path.join(root_dir, "read", "Usable.xlsx")
stocklist = pd.read_excel(file_path)["Symbols"] # read only the ticker symbols

stocks = stocklist.sort_values().reset_index(drop=True) # sort the stocks alphabetically so ai doesn't only train on good ones
stock_evals = pd.Series([stocks.pop(i*20) for i in range(stocks.size//20)], name="Symbols") # take out 5% / 1/20 of the dataset to evaluate the ai on (// means floor division)

def stock_data(ticker, start, end): # get hourly stockdata
    dat = yf.Ticker(ticker).history(start=start, end=end, interval='1h')
    return dat

# def better_atanh(x):
#     if x == 1:
#         return 5
#     elif x == -1:
#         return -5
#     else:
#         return atanh(x)

all = [] # stotes every datapoint
data = []
y_data = []
siz = 70 # this will ONLY look for 15 days open last 3 weeks because 14 is too slow

#input()

def random_date(): # generate a random date between 1/6/2021 and 12/18/2022 and return an additional date before 3 weeks
    start = dt.datetime.now() - dt.timedelta(7*randint(3, 104)) # go back either 3 or 103 weeks
    end = start + dt.timedelta(21)
    return start, end

def inp_fn(x, al=False): # generates data to run on
    global data
    data = []
    global y_data
    y_data = []
    global siz
    n = 0
    yes = False
    global all
    if al: all = []
    print("Checking whether new dataset has same amount of days...")
    while not yes:
        st, en = random_date()
        for s in x.loc[:5].index:
            temp = stock_data(x[s], st, en)["Close"].reset_index(drop=True).to_list()
            if (len(temp)*2)//3 == siz: # if the date chosen has at least one of siz business days
                yes = True
    for s in x.loc[:74].index:
        temp = stock_data(x[s], st, en)["Close"].reset_index(drop=True).to_list()
        #print(temp)
        n += 1
        if len(temp) != 0 and len(temp) == siz*1.5: # all things have to be 105 or 98 big and not empty (105: 15 business days, 98: 14 business days)
            if al: all.append(temp) # save all of the data for visualisation
            last = temp[2*(len(temp)//3):] # remove last third
            temp = temp[:2*(len(temp)//3)]
            data.append(temp) # input is last 2 weeks
            chg = (last[-1]/temp[-1]-1)*100 # change in 1 week in percent
            y_data.append(chg) # output is expected rise in a week
        if n != 1: # clear the last lines
            print("\033[A                                                   \033[A")
            print("\033[A                                                   \033[A")
        print("Shuffling Dataset...")
        print(n, "/", 75, "\t\t\t")#x.size)
        # elif len(temp) == 0: # if printed error message remove last line
        #     print("\033[A\033[A")
    if len(data) == 0:
        print("UH OH")
    #data = np.array(data)


inp_fn(stocks)

siz = len(data[0]) # size of arrays within

model = tf.keras.Sequential((
    layers.InputLayer(input_shape=(siz)), 
    layers.Reshape((siz, 1)),
    layers.Conv1D(4, 7), 
    layers.MaxPooling1D(), 
    layers.Conv1D(1, 5), 
    layers.MaxPooling1D(),
    layers.Flatten(),
    layers.Dense(1, activation='linear')))

#model.summary()

# training
cont = True
left = 1

model.compile(optimizer='adam', loss=tf.keras.losses.MeanSquaredError())

history = []

while cont:
    history.append(model.fit(data, y_data, batch_size=5).history["loss"][0]) # make it so that history will contain all of the losses
    left -= 1
    print("Cycles left: ", left)
    if left == 0:
        if input("Continue training? (y/n)") == "y":
            left = int(input("How many cycles? \nEnter a number: "))
        else:
            cont = False
    if left > 0:
        inp_fn(stocks) # gather new data

#inp_fn(stock_evals)
#result = model.evaluate(data, y_data, batch_size=5)

print("Loss history: ", history) # avg min loss: 30% from truth

# visualize data
print("Getting Test output...")
inp_fn(stock_evals, al=True)
pred = model.predict(data)

#all = []

preds = []

for i in range(len(pred)):
    preds.append(pred[i][0]) # get percent values and divide it into the timestamps

fil1 = open("out1.txt", "w") # graph data
for i in range(105):
    for j in range(len(all)):
        fil1.write(str(all[j][i]) + ",") # write all of the first values in first row etc
    fil1.write("\n") # go to next row
fil1.close()

fil2 = open("out2.txt", "w")
for i in range(35):
    for j in range(len(y_data)):
        fil2.write(str((1+((preds[j])*i/35)/100)) + ",") # predicted rise (c+mx)-> c = first value, x = i, m = percent perdiction data[j][-1]*
    fil2.write("\n")
fil2.close()

# est = tf.estimator.DNNEstimator(head=tf.estimator.RegressionHead(), feature_columns=features, hidden_units=[30, 10], activation_fn=tf.keras.activations.tanh)
# est.train(lambda: inp_fn(stocks))

# result = est.evaluate(lambda: inp_fn(stock_evals, train=False))

#print(result)
