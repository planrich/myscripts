import sys
sys.setcheckinterval(10000000)
def main():
    import _numpypy.multiarray as np
    a = np.array([1]*6757, dtype='int16')
    return a.all()
print main()
