import z3
from pycparser import CParser, c_ast, c_parser, c_generator
import signal

INT_MAX = 2147483647
INT_MIN = -2147483648

whilelist = []

context = {}
whileformul = []
optflag = False

s = z3.Solver()
s.set(timeout=5)
satlist = []

def getz3val(var, expr):
    left = expr.left
    right = expr.right

    x = z3.Int(var)

    op = expr.op

    if hasattr(left, "name") and hasattr(right, "name"):
        if left.name == var:
            return (x == INT_MIN)
        elif right.name == var:
            return (x == INT_MAX)

    elif hasattr(left, "name") and left.name == var and isinstance(right, c_ast.Constant):
        if op == "!=":
            return (x != int(right.value))
        elif op == "==":
            return (x == int(right.value))
        elif op == ">":
            return (x > int(right.value))
        elif op == ">=":
            return (x >= int(right.value))
        elif op == "<":
            return (x < int(right.value))
        elif op == "<=":
            return (x <= int(right.value))

    elif hasattr(right, "name") and right.name == var and isinstance(right, c_ast.Constant):
        if op == "!=":
            return (int(right.value) != x)
        elif op == "==":
            return (int(right.value) == x)
        elif op == ">":
            return (int(right.value) > x)
        elif op == ">=":
            return (int(right.value) >= x)
        elif op == "<":
            return (int(right.value) < x)
        elif op == "<=":
            return (int(right.value) <= x)


def exprtrend(expr):
    trend = {}
    constmap = {}
    opmap = {}
    if isinstance(expr, c_ast.Assignment):
        try:
            if isinstance(expr.rvalue, c_ast.BinaryOp):
                varname = expr.lvalue.name
                trend[varname] = None
                if expr.rvalue.left.name == varname and isinstance(expr.rvalue.right, c_ast.Constant):
                    rightop = expr.rvalue.op
                    opmap[varname] = rightop
                    constmap[varname] = int(expr.rvalue.right.value)

                    if (rightop == '-' and trend[varname] == "down") or (rightop == '-' and trend[varname] == None):
                        trend[varname] = "down"
                    elif (rightop == "+" and trend[varname] == "up") or (rightop == "+" and trend[varname] == None):
                        trend[varname] = "up"
                    else:
                        trend[varname] = "unknown"

                return trend, constmap, opmap
            else:
                return trend, constmap, opmap

        except:
            pass


def Optbinop(binop, log, whileflag):
    formula = None
    constr = {}

    if hasattr(binop, "op"):
        op = binop.op

    if isinstance(binop, c_ast.FuncCall):
        return constr

    if whileflag:
        if isinstance(binop, c_ast.ID):
            return constr

        if isinstance(binop.left, c_ast.BinaryOp):
            tmp_constr = Optbinop(binop.left, formula, whileflag)
            for i in tmp_constr.keys():
                if i not in constr.keys():
                    constr[i] = []
                constr[i] += tmp_constr[i]

        if isinstance(binop.right, c_ast.BinaryOp):
            tmp_constr = Optbinop(binop.right, formula, whileflag)
            for i in tmp_constr.keys():
                if i not in constr.keys():
                    constr[i] = []
                constr[i] += tmp_constr[i]

        left = binop.left
        right = binop.right

        if hasattr(left, "name"):
            name = left.name
            if name in context:
                if name not in constr.keys():
                    constr[name] = []
                constr[name].append(binop)

        elif hasattr(right, "name"):
            name = right.name
            if name in context:
                if name not in constr.keys():
                    constr[name] = []
                constr[name].append(binop)

        else:
            pass
        return constr


def OptWhile(whileexpr, log, whileflag):
    formula = []
    trend = {}
    constmap = {}
    opmap = {}

    whilecond = whileexpr.cond
    constr = Optbinop(whilecond, formula, True)
    global optflag

    for i in context:
        if i in constr.keys():
            optflag = True
            whileflag = True
            break

    if whileflag:
        if isinstance(whileexpr.stmt, c_ast.Compound):
            blockitem = whileexpr.stmt.block_items
            if blockitem == None:
                return trend, constmap, opmap, formula
            for i in range(len(blockitem)):
                if isinstance(blockitem[i], c_ast.Assignment):
                    tmp_trend, tmp_constmap, tmp_opmap = exprtrend(blockitem[i])
                    trend.update(tmp_trend)
                    constmap.update(tmp_constmap)
                    opmap.update(tmp_opmap)

                elif isinstance(blockitem[i], c_ast.If):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptIf(blockitem[i], formula, whileflag)
                    trend.update(tmp_trend)
                    constmap.update(tmp_constmap)
                    opmap.update(tmp_opmap)
                    formula += tmp_formula

                elif isinstance(blockitem[i], c_ast.While):

                    nextwhilecond = blockitem[i].cond
                    nextconstr = Optbinop(nextwhilecond, formula, True)
                    for i in context:
                        if i in nextconstr.keys():
                            tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptWhile(blockitem[i], c_ast.While, whileflag)
                            trend.update(tmp_trend)
                            constmap.update(tmp_constmap)
                            opmap.update(tmp_opmap)
                            formula += tmp_formula
                            break

                    return

    else:
        if isinstance(whileexpr.stmt, c_ast.Compound):
            blockitem = whileexpr.stmt.block_items
            if blockitem == None:
                return trend, constmap, opmap, formula

            for i in range(len(blockitem)):
                if isinstance(blockitem[i], c_ast.Assignment):
                    tmp_trend, tmp_constmap, tmp_opmap = exprtrend(blockitem[i])
                    trend.update(tmp_trend)
                    constmap.update(tmp_constmap)
                    opmap.update(tmp_opmap)

                elif isinstance(blockitem[i], c_ast.If):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptIf(blockitem[i], formula, whileflag)
                    trend.update(tmp_trend)
                    constmap.update(tmp_constmap)
                    opmap.update(tmp_opmap)
                    formula += tmp_formula

                elif isinstance(blockitem[i], c_ast.While):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptWhile(blockitem[i], c_ast.While, whileflag)
                    trend.update(tmp_trend)
                    constmap.update(tmp_constmap)
                    opmap.update(tmp_opmap)
                    formula += tmp_formula

    for c in constr.keys():
        if c in trend.keys():
            for i in constr[c]:
                f = getz3val(c, i)
                whileformul.append(f)
        else:
            for i in constr[c]:
                f = getz3val(c, i)
                whileformul.append(f)

    return trend, constmap, opmap, formula


def OptIf(ifexpr, log, whileflag):
    formula = []
    conexpr = ifexpr.cond

    trend = {}
    constmap = {}
    opmap = {}

    true_trend = {}
    true_constmap = {}
    true_opmap = {}

    false_trend = {}
    false_constmap = {}
    false_opmap = {}
    constr = None

    if whileflag:
        constr = Optbinop(conexpr, formula, whileflag)
        if isinstance(ifexpr.iftrue, c_ast.Compound):
            true_blockitem = ifexpr.iftrue.block_items
            for i in range(len(true_blockitem)):
                if isinstance(true_blockitem[i], c_ast.If):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptIf(true_blockitem[i], formula, whileflag)
                    true_trend.update(tmp_trend)
                    true_constmap.update(tmp_constmap)
                    true_opmap.update(tmp_opmap)
                    formula += tmp_formula

                if isinstance(true_blockitem[i], c_ast.Assignment):
                    tmp_trend, tmp_constmap, tmp_opmap = exprtrend(true_blockitem[i])
                    true_trend.update(tmp_trend)
                    true_constmap.update(tmp_constmap)
                    true_opmap.update(tmp_opmap)


                if isinstance(true_blockitem[i], c_ast.While):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptWhile(true_blockitem[i], formula, whileflag)
                    true_trend.update(tmp_trend)
                    true_constmap.update(tmp_constmap)
                    true_opmap.update(tmp_opmap)
                    formula += tmp_formula

        if isinstance(ifexpr.iffalse, c_ast.Compound):
            false_blockitem = ifexpr.iffalse.block_items
            for i in range(len(false_blockitem)):
                if isinstance(false_blockitem[i], c_ast.If):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptIf(false_blockitem[i], formula, False)
                    false_trend.update(tmp_trend)
                    false_constmap.update(tmp_constmap)
                    false_opmap.update(tmp_opmap)
                    formula += tmp_formula

                if isinstance(false_blockitem[i], c_ast.While):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptWhile(false_blockitem[i], formula, False)
                    false_trend.update(tmp_trend)
                    false_constmap.update(tmp_constmap)
                    false_opmap.update(tmp_opmap)
                    formula += tmp_formula


                if isinstance(false_blockitem[i], c_ast.Assignment):
                    tmp_trend, tmp_constmap, tmp_opmap = exprtrend(false_blockitem[i])
                    false_trend.update(tmp_trend)
                    false_constmap.update(tmp_constmap)
                    false_opmap.update(tmp_opmap)

        true_keys = true_trend.keys()
        false_keys = false_trend.keys()
        for i in true_keys:
            if i not in false_keys:
                trend[i] = true_trend[i]
                constmap[i] = true_constmap[i]
                opmap[i] = true_opmap[i]
            else:
                if true_trend[i] == "unknown":
                    if false_trend[i] == "unknown":
                        continue
                    else:
                        trend[i] = false_trend[i]
                        constmap[i] = false_constmap[i]
                        opmap[i] = false_opmap[i]
                else:
                    if false_trend[i] == "unknown":
                        trend[i] = true_trend[i]
                        constmap[i] = true_constmap[i]
                        opmap[i] = true_opmap[i]
                    else:
                        if i in true_constmap.keys() and i in false_constmap.keys():
                            if true_constmap[i] > false_constmap[i]:
                                trend[i] = true_trend[i]
                                constmap[i] = true_constmap[i]
                                opmap[i] = true_opmap[i]
                            else:
                                trend[i] = false_trend[i]
                                constmap[i] = false_constmap[i]
                                opmap[i] = false_opmap[i]

        for i in false_keys:
            if i not in true_keys:
                trend[i] = false_trend[i]
                constmap[i] = false_constmap[i]
                opmap[i] = false_opmap[i]

        for c in constr.keys():
            for l in constr[c]:
                f = getz3val(c, l)
                formula.append(f)
        return trend, constmap, opmap, formula

    else:
        if isinstance(ifexpr.iftrue, c_ast.Compound):
            true_blockitem = ifexpr.iftrue.block_items
            for i in range(len(true_blockitem)):
                if isinstance(true_blockitem[i], c_ast.If):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptIf(true_blockitem[i], formula, False)
                    true_trend.update(tmp_trend)
                    true_constmap.update(tmp_constmap)
                    true_opmap.update(tmp_opmap)
                    formula += tmp_formula


                if isinstance(true_blockitem[i], c_ast.While):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptWhile(true_blockitem[i], formula, False)
                    true_trend.update(tmp_trend)
                    true_constmap.update(tmp_constmap)
                    true_opmap.update(tmp_opmap)
                    formula += tmp_formula
                    constr = Optbinop(conexpr, formula, True)

        if isinstance(ifexpr.iffalse, c_ast.Compound):
            false_blockitem = ifexpr.iffalse.block_items
            for i in range(len(false_blockitem)):
                if isinstance(false_blockitem[i], c_ast.If):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptIf(false_blockitem[i], formula, False)
                    false_trend.update(tmp_trend)
                    false_constmap.update(tmp_constmap)
                    false_opmap.update(tmp_opmap)
                    formula += tmp_formula

                if isinstance(false_blockitem[i], c_ast.While):
                    tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptWhile(false_blockitem[i], formula, False)
                    false_trend.update(tmp_trend)
                    false_constmap.update(tmp_constmap)
                    false_opmap.update(tmp_opmap)
                    formula += tmp_formula
                    constr = Optbinop(conexpr, formula, True)


        if constr != None:
            for c in constr.keys():
                for l in constr[c]:
                    f = getz3val(c, l)
                    formula.append(f)

        true_keys = true_trend.keys()
        false_keys = false_trend.keys()

        for i in true_keys:
            if i not in false_keys and i in constmap.keys() and i in true_constmap.keys():
                trend[i] = true_trend[i]
                constmap[i] = true_constmap[i]
                opmap[i] = true_opmap[i]
            else:
                if true_trend[i] == "unknown":
                    if false_trend[i] == "unknown":
                        continue
                    else:
                        trend[i] = false_trend[i]
                        constmap[i] = false_constmap[i]
                        opmap[i] = false_opmap[i]
                else:
                    if i not in false_trend:
                        continue

                    if false_trend[i] == "unknown" :
                        trend[i] = true_trend[i]
                        constmap[i] = true_constmap[i]
                        opmap[i] = true_opmap[i]
                    else:
                        if i in true_constmap.keys() and i in false_constmap.keys():
                            if true_constmap[i] > false_constmap[i]:
                                trend[i] = true_trend[i]
                                constmap[i] = true_constmap[i]
                                opmap[i] = true_opmap[i]
                            else:
                                trend[i] = false_trend[i]
                                constmap[i] = false_constmap[i]
                                opmap[i] = false_opmap[i]

        for i in false_keys:
            if i not in true_keys:
                trend[i] = false_trend[i]
                constmap[i] = false_constmap[i]
                opmap[i] = false_opmap[i]

        return trend, constmap, opmap, formula


def OptBlockItem(blockitem, log, whileflag):
    formula = []
    trend = {}
    constmap = {}
    opmap = {}

    for i in range(len(blockitem)):

        if isinstance(blockitem[i], c_ast.While):
            tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptWhile(blockitem[i], formula, whileflag)
            trend.update(tmp_trend)
            constmap.update(tmp_constmap)
            opmap.update(tmp_opmap)
            formula += tmp_formula

        if isinstance(blockitem[i], c_ast.If):
            tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptIf(blockitem[i], formula, whileflag)
            trend.update(tmp_trend)
            constmap.update(tmp_constmap)
            opmap.update(tmp_opmap)
            formula += tmp_formula
        if isinstance(blockitem[i], c_ast.Decl):
            decl = blockitem[i]
            varname = decl.name
            if varname in context.keys():
                continue
            else:
                if decl.init == None:
                    context[decl.name] = 0
                else:
                    if isinstance(decl.init, c_ast.Constant):
                        context[decl.name] = int(decl.init.value)
        if isinstance(blockitem[i], c_ast.Assignment):
            ass = blockitem[i]
            if isinstance(ass.rvalue, c_ast.Constant) and isinstance(ass.lvalue, c_ast.ID):
                context[ass.lvalue.name] = int(ass.rvalue.value)


    return trend, constmap, opmap, formula


def OptFunc(func, log):
    formula = []
    trend = {}
    constmap = {}
    opmap = {}
    global satlist

    satflag = False
    body = func.body

    if isinstance(body, c_ast.Compound):
        block_items = body.block_items
        tmp_trend, tmp_constmap, tmp_opmap, tmp_formula = OptBlockItem(block_items, formula, False)
        trend.update(tmp_trend)
        constmap.update(tmp_constmap)
        opmap.update(tmp_opmap)
        formula += tmp_formula

    parlist = []
    symvar = None
    timebase = -1


    for i in whileformul:
        if i == None:
            continue
        nums = i.num_args()
        for j in range(nums):
            if isinstance(i.arg(j), z3.z3.IntNumRef):
                timebase = int(str(i.arg(j)))
            elif isinstance(i.arg(j), z3.z3.ArithRef):
                symvar = i.arg(j)

    parlist.append((symvar, timebase))

    t = 0

    for symvar,timebase in parlist:
        if symvar == None:
            return False


        if str(symvar) in trend:
            if trend[str(symvar)] == "up":
                t = abs(int(INT_MIN / (timebase - constmap[str(symvar)])))
                # formula.append(symvar == INT_MIN)
            elif trend[str(symvar)] == "down":
                t = abs(int(INT_MAX / (timebase - constmap[str(symvar)])))
                # formula.append(symvar == INT_MAX)
        else:
            t = INT_MAX + INT_MAX/2

    for k,v in context.items():
        if isinstance(v, int):
            cvar = z3.Int(k)
            formula.append(cvar == v)

    print("time:", t)

    formula += whileformul

    for x in trend.keys():
        sym = z3.Int(x)
        s.reset()
        if trend[x] == "up":
            formula.append((sym + constmap[x] * t) > INT_MAX)

            s.add(z3.And(formula))
            if s.check() == z3.sat:
                satflag = True
                satlist = s.model()

        elif trend[x] == "down":
            formula.append((sym - constmap[x] * t) < INT_MIN)
            s.add(z3.And(formula))

            if s.check() == z3.sat:
                satflag = True
                satlist = s.model()

    print(formula)
    return satflag

def set_timeout(num, callback):
    def wrap(func):
        def handle(sig, frame):
            raise RuntimeError

        def to_do(*args, **kwargs):
            try:
                signal.signal(signal.SIGALRM, handle)
                signal.alarm(num)
                r = func(*args, **kwargs)
                signal.alarm(0)
                return r
            except RuntimeError as e:
                callback()

        return to_do
    return wrap

def optaftertime():
    print("Opt timeout!")

@set_timeout(5, optaftertime)
def OptAll(ast, symtable):
    log_formula = None
    satflag = False
    global context


    for i in range(len(ast.ext)):
        if isinstance(ast.ext[i], c_ast.FuncDef):
            for k, v in symtable.items():
                symtable[k] = k
            context.update(symtable)
            satflag = OptFunc(ast.ext[i], log_formula)
            context = {}

    return satlist,satflag, optflag

