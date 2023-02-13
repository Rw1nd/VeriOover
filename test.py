import yaml
import os
import subprocess

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
TestDirPath = ROOT_PATH + "/test"
TestDir = os.listdir(TestDirPath)

RightNum = 0
UnknowNum = 0
Unknowlist = []
FalseNum = 0
Falselist = []
Sum = 0

logfile = open("./log.txt", "w")

for i in TestDir:
    if i == ".DS_Store":
        continue
    files = os.listdir(TestDirPath + "/" + i)
    for f in files:
        if f[-3:] == "yml":
            ymlfile = TestDirPath + "/" + i + "/" + f
            cfile = ymlfile[:-3] + 'c'
            yml = open(ymlfile)
            myml = yaml.load(yml.read(), Loader=yaml.Loader)
            TargetRes = myml["properties"][0]["expected_verdict"]
            print(cfile)
            work = subprocess.Popen(["/usr/bin/time","./VeriOover", "--file", cfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.Popen.wait(work)
            (VeriRes, timelog) = work.communicate()
            VeriRes = str(VeriRes, 'utf-8')
            timelog = str(timelog, 'utf-8')

            logfile.write(cfile+ ":\n" + timelog + "===\n")

            if "Undetectable!" in VeriRes:
                VeriRes = "Undetectable!"
            elif "No Integer Overflow!" in VeriRes:
                VeriRes = "No Integer Overflow!"
            else:
                VeriRes = "Overflow!"

            print(TargetRes)
            print(VeriRes)

            Sum += 1
            if VeriRes == "Undetectable!":
                UnknowNum += 1
                Unknowlist.append(cfile)
            elif VeriRes == "No Integer Overflow!" and TargetRes:
                RightNum += 1
            elif VeriRes == "Overflow!" and not TargetRes:
                RightNum += 1
            else:
                FalseNum += 1
                Falselist.append(cfile)

            print("Correct detection: ", str(RightNum) + "/" + str(Sum))
            print("Incorrect detection: ", str(FalseNum) + "/" + str(Sum))
            print("Unknow detection: ", str(UnknowNum) + "/" + str(Sum))
            print(Unknowlist)
            print(Falselist)


logfile.close()

file = open("log.txt")

text = file.read()

loglist = []

while len(text) > 0:
    start = text.find("===")
    loglist.append(text[:start+4])
    text = text[start+4:]

timemap = {}
for i in loglist:
    send = i.find(":")
    filepath = i[:send]
    systime = float(i[-14:-8])
    usertime = float(i[-35:-26])
    realtime = float(i[-50:-45])
    timemap[filepath] = usertime + systime


vlist = timemap.values()
print("max: ", max(vlist))
print("min: ", min(vlist))
print("adv: ", sum(timemap.values())/len(timemap))
print("sum: ", sum(vlist))

file.close()