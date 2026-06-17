CALL_BENCH_SRC = """
def add1(n):
    return n + 1

i = 0
total = 0
while i < 20000:
    total = add1(total)
    i = i + 1
"""


EXCEPTION_BENCH_SRC = """
def fail_if_zero(n):
    if n == 0:
        raise 1
    return n

def pass_through(n):
    return fail_if_zero(n)

i = 0
total = 0
while i < 5000:
    try:
        total = total + pass_through(0)
    except:
        total = total + 1
    i = i + 1
"""


TRY_NO_EXCEPTION_BENCH_SRC = """
def fail_if_zero(n):
    if n == 0:
        raise 1
    return n

def pass_through(n):
    return fail_if_zero(n)

i = 0
total = 0
while i < 5000:
    try:
        total = total + pass_through(1)
    except:
        total = total + 1
    i = i + 1
"""
