import json
import datetime
import pprint
import random
import sys
import os
from simpleGraph import *
import scc

pp = pprint.PrettyPrinter(indent=4)

# todo from which date do I take T to start? Implement when there is more data

def removeFilename(f):
    try:
        os.remove(f)
    except OSError:
        pass

def hms_to_seconds(t):
    t = t.split(",")
    hms_index = len(t) - 1
    if len(t) > 1:
        daysNo = int(t[0].split(" ")[0])
    else:
        daysNo = 0
    h, m, s = [int(i) for i in t[hms_index].split(':')]
    return 86400*daysNo + 3600*h + 60*m + s

# find the time difference between two timestamps as a fraction of a day:
def calculateDuration(stamp1, stamp2):
    duration = int(stamp2) - int(stamp1)
    duration = hms_to_seconds(str(datetime.timedelta(seconds=duration)))
    durationFrac = duration / hms_to_seconds("24:00:00")
    return round(durationFrac, 2)

def parseConfig(config):
    with open(config, "r") as f:
        for line in f:
            conf = json.loads(line)
            if conf[0] == "m":
                m = int(conf[1])
            elif conf[0] == "n":
                n = int(conf[1])
            elif conf[0] == "d":
                d = int(conf[1])
            elif conf[0] == "T":
                T = float(conf[1])
    return(m, n, d, T)

def constructAirports(connecting, dests, hpt):
    airports = []
    with open(instanceFile, "w") as f:
        astats = ["airports", n]
        json.dump(astats, f)
        f.write("\n")
        for a in connecting:
            a.append("connecting")
            airports.append(a)
            json.dump(a, f)
            f.write("\n")
        for a in dests:
            a.append("destination")
            airports.append(a)
            json.dump(a, f)
            f.write("\n")
        for a in hpt:
            a.append("home_point")
            airports.append(a)
            json.dump(a, f)
            f.write("\n")
        json.dump(["holiday", T], f)
        f.write("\n")
        json.dump(["flights", m], f)
        f.write("\n")
    return airports

def generateA():
    A = []
    connecting = []
    dests = []
    hpt = []
    with open(allairports, "r") as f:
        for line in f:
            airport = json.loads(line)
            A.append(airport)
    with open(propsFile, "w") as f1:
        f1.write("all " + str(n) + "\n")
        # choose n airports:
        while len(connecting) < n:
            i = random.randint(0, len(A) - 1)
            f1.write(str(i) + "\n")
            a = A.pop(i)
            if a[1] == "1":
                a[1] = "0.2" # if no conn time was calculated, put default
            connecting.append(a)
        f1.write("destinations " + str(d) + "\n")
        # choose d destinations from the airports:
        while len(dests) < d:
            i = random.randint(0, len(connecting) - 1)
            f1.write(str(i) + "\n")
            dests.append(connecting.pop(i))
        # choose a home point:
        f1.write("home\n")
        i = random.randint(0, len(connecting) - 1)
        f1.write(str(i) + "\n")
        f1.write("T " + str(T) + "\n")
        f1.write("flights " + str(m) + "\n")
        hpt.append(connecting.pop(i))
    airports = constructAirports(connecting, dests, hpt)
    return airports

def randomTimeWindow(earliestStart, latestEnd):
    earliestDate = datetime.datetime.fromtimestamp(earliestStart)
    try:
        latestDate = datetime.datetime.fromtimestamp(latestEnd) - datetime.timedelta(days=T)
        randomStart = random.randint(earliestStart, latestDate.timestamp())
    except ValueError:
        print("Time between earliestStart and latestEnd is less than T")
    return randomStart

def generateF(airports):
    global startStamp
    startStamp = randomTimeWindow(1480550400, 1483228800) # type here the earliest and latest flight date in flightsCorpus
    airport_codes = [item[0] for item in airports]
    with open(fcorpus, "r") as f:
        currentDate = 0
        earliestStamp = 0
        F = []
        for line in f:
            flight = json.loads(line)
            if flight[2] in airport_codes and flight[3] in airport_codes and flight[0] >= startStamp:
                if earliestStamp == 0:
                    earliestStamp = flight[0]
                currentDate = calculateDuration(earliestStamp, flight[0])
                if currentDate + flight[1] <= T:
                    # print(flight[0], currentDate)
                    flight[0] = currentDate
                    F.append(flight)
    return F

def writeToFile(filename, items):
    with open(filename, "a") as f:
        for item in items:
            json.dump(item, f)
            f.write("\n")

def takeFromFrandomM(F):
    counter = 0
    randomF = []
    indices = []
    while counter < m and len(F) > 0:
        i = random.randint(0, len(F) - 1)
        indices.append(i)
        f = F.pop(i)
        f.insert(0, counter + 1)
        randomF.append(f)
        counter += 1
    return (randomF, indices)

# python generator.py <flights data filename> <number of instances per config> <congif files>
fcorpus = "/Users/ivababukova/uni/bookingData/decFlights" #sys.argv[1]
instancesPerConfig = 1 #int(sys.argv[2])
configFiles = sys.argv[1:]
ids = 0
numbOfFlights = 0
areStronglyConnected = False
startStamp = 0
ccsFailCounter = 0 # records how many times the current set of airports with some set of flights weren't strongly connected
configFailCounter = 0
configFailTolerance = 1000
ccsFailTolerance = 15

for config in  configFiles:
    (m, n, d, T) = parseConfig(config)
    while (not areStronglyConnected or ids < instancesPerConfig) and configFailCounter < configFailTolerance:
        while (numbOfFlights < m or ccsFailCounter >= ccsFailTolerance) and configFailCounter < configFailTolerance:
            if ccsFailCounter >= ccsFailTolerance:
                ccsFailCounter = 0
                configFailCounter += 1
                print("Failed CCS test 10 times in a row")
                print(configFailCounter)
            elif ccsFailCounter < 10:
                print("Not enough number of flights")
            instanceFile = "instances/" + str(m) + "_" + str(n) + "_" + str(d) + "_" + str(int(T)) + "_" + str(ids)
            propsFile = "props/" + str(m) + "_" + str(n) + "_" + str(d) + "_" + str(int(T)) + "_" + str(ids) + "_props"
            allairports = "airports_out"
            airports = generateA()
            F = generateF(airports)
            numbOfFlights = len(F)
        (flights, indices) = takeFromFrandomM(F)
        areStronglyConnected = scc.tarjans(SimpleGraph(flights, airports))
        if not areStronglyConnected:
            ccsFailCounter += 1
        if areStronglyConnected:
            print("created instance ", instanceFile)
            ids +=1
            writeToFile(instanceFile, flights)
            with open(propsFile, "a") as f:
                f.write("startStamp: " + str(startStamp) + "\n")
            writeToFile(propsFile, indices)
            numbOfFlights = 0
    if configFailCounter >= configFailTolerance:
        print("Instance could not be created for this config file: ", config, m, n, d, T)
        configFailCounter = 0
        numbOfFlights = 0
        ccsFailCounter = 0
        removeFilename(instanceFile)
        removeFilename(propsFile)
