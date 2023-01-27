import subprocess
import os

TestPath = "/tmp/verioover/"
filedir = os.path.dirname(os.path.abspath(__file__))

clangpath = "clang"
kleepath = "klee"
ldpath = ""

def Runclang(filename, filepath):
    ctobc = subprocess.Popen([clangpath, "-I./include/",
                              "-emit-llvm",
                              "-c",
                              "-g",
                              "-O0",
                              "-Xclang",
                              "-disable-O0-optnone",
                              "-fsanitize=signed-integer-overflow",
                              filepath,
                              "-o",
                              TestPath + filename[:-2] + ".bc"])

    subprocess.Popen.wait(ctobc)


def RunKlee(filename):
    klee_ver = subprocess.Popen([
                                 kleepath,
                                 "-solver-backend=z3",
                                 "-max-time=5s",
                                 "-max-memory=7168",
                                 "-exit-on-error-type=Overflow",
                                 TestPath + filename[:-2] + ".bc"])

    subprocess.Popen.wait(klee_ver)

def DetectError():
    msgfile = open(TestPath + "/klee-last/messages.txt")
    msg = msgfile.read()

    if "overflow on" in msg:
        return "violation"
    elif "concretized symbolic size" in msg:
        return "unknown"
    elif "failed external call: __ubsan_handle_negate_overflow" in msg:
        return "violation"
    else:
        return "pass"