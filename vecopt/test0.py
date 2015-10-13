import sys
sys.setcheckinterval(10000000)
def main():
    import _numpypy.multiarray as np
    a = np.array([1]*3420, dtype='int64')
    return (a + a).sum()
print main()
