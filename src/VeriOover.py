#!/usr/bin/env python3

import yaml
import os
import argparse

import Opt
from Parser import InsertConcent
from Veri import Runclang, RunKlee, DetectError

TestPath = "/tmp/verioover/"

cnt = 0
rightnum = 0
unknow = 0
falsenum = 0
exitnum = 0
summ = 0

def RunVeri(filepath):
    start = filepath.rfind("/") + 1
    filename = filepath[start:]
    coflag = True

    try:
        linenumber, varscope, ast = InsertConcent(filepath, filename)

    except:
        print("Undetectable!")
        return

    Runclang(filename, TestPath + filename)

    RunKlee(filename)

    flag = DetectError()

    if flag == "violation":
        print("Overflow!")
        return

    try:
        satlist, satflag, optflag = Opt.OptAll(ast, linenumber)
        idmap = []
        if satflag and flag == "pass":
            for i in satlist:
                name = str(i)
                if name in linenumber:
                    idmap.append((name, str(satlist[i].as_long())))

            print("Overflow!")
            return

        else:
            print("No Integer Overflow!")
            return
    except:
        pass

    print("Undetectable!")

    return

