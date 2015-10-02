

def f():
    i = 0
    v = [1] * 10000
    o = [2] * 10000
    while i < len(v):
        o[i] = o[i] + 1
        i += 1

    assert sum(o) == 2 * 10000

f()
