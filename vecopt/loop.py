
import array

def f():
    v = array.array('d', [1.0] * 10000)
    o = array.array('d', [2.0] * 10000)
    j = 0
    while j < 10000:
        i = 0
        s = 0.0
        while i < len(v):
            s += o[i]
            i += 1
        j += 1


f()
