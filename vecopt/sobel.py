import numpy
import sys

if False and sys.argv[-1] != 'python':
    import scipy
    from scipy import ndimage

def read_line(array, ibytes, index, axis, loffset, roffset, base, end):
    """ read a line along the axis starting from i """
    stride = array.strides[axis] // array.dtype.itemsize
    farray = array.flat
    cidx = index - stride
    if cidx < base:
        cidx = index
    ibytes[0] = farray[cidx]
    i = 0
    count = ibytes.size - (loffset+roffset)
    while i < count and cidx < array.size: 
        ibytes[i+1] = farray[cidx]
        cidx += stride
        i += 1
    ibytes[i+1] = farray[cidx - stride]

def write_line(array, obytes, index, axis, loffset, roffset, base, end):
    stride = array.strides[axis] // array.dtype.itemsize
    farray = array.flat
    i = 0
    cidx = index
    count = obytes.size
    while i < count and cidx < array.size:
        farray[cidx] = obytes[i]
        cidx += stride
        i += 1

def correlate1d_3weigths(input, weights, axis):
    output = input.copy()
    _a, _b, _c = weights
    count = input.shape[axis]
    ibytes = numpy.array([0]*(count+2), dtype='int32')
    obytes = numpy.array([0]*(count), dtype='int32')
    innerstride = reduce(lambda r,x: r*x, input.shape[axis+1:], 1)
    outercount = reduce(lambda r,x: r*x, input.shape[:axis], 1)
    outerstride = input.strides[axis]
    if axis > 0:
        outerstride = input.strides[axis-1]
    outerstride /= input.dtype.itemsize
    i = 0
    outer = 0
    while outer < outercount:
        base = outer * outerstride
        end = base + innerstride 
        i = base
        while i < end:
            read_line(input, ibytes, i, axis, 1, 1, base, end)
            j = 0
            while j < count:
                j1 = j+1
                j2 = j+2
                j3 = j+3
                x = ibytes[j]
                y = ibytes[j1]
                z = ibytes[j2]
                w = ibytes[j3]
                x1 = x * _a
                y1 = y * _b

                z1 = z * _c
                y2 = y * _a

                z2 = z * _b
                x2 = w * _c
                obytes[j] = x1+y1+z1
                obytes[j1] = x2+y2+z2
                j += 2
                del x,z,y,w,x1,y1,z1,x2,y2,z2
            write_line(output, obytes, i, axis, 1, 1, base, end)
            i += 1
        outer += 1

    return output

def sobel_py(im, axis):
    im = correlate1d_3weigths(im, [-1,0,1], axis)
    return im
    #for i in range(3):
    #    if i != axis:
    #        im = correlate1d_3weigths(im, [1,2,1], i)
    #return im
def sobel_scipy(im, axis):
    return ndimage.sobel(im, axis)
    import scipy
    from scipy import ndimage
    im = ndimage.correlate1d(im, [-1,0,1], axis)
    return im
    #for i in range(3):
    #    if i != axis:
    #        im = ndimage.correlate1d(im, [1,2,1], i)
    #return im

# numpy.hypot not impl in pypy
def hypot(dx, dy):
    numpy.multiply(dx, dx, out=dx)
    numpy.multiply(dy, dy, out=dy)
    dx = numpy.add(dx, dy, out=dx)
    numpy.sqrt(dx, out=dx)
    return dx

def equal(expected, actual):
    e = expected.flat
    a = actual.flat
    for i in range(expected.size):
        assert e[i] == a[i], "do not match at pos %d, %s != %s" % (i,e[i],a[i])

def sobel(im, out):
    #im = im.astype('int32')
    dx = sobel_py(im, 0)
    dy = sobel_py(im, 1)
    mag = hypot(dx, dy)  # magnitude
    numpy.multiply(mag, 255.0 / numpy.max(mag), out=out)  # normalize (Q&D)
    return out 

def sobel_python(im, out):
    dx = sobel_scipy(im, 0)
    dy = sobel_scipy(im, 1)
    mag = hypot(dx, dy)      # magnitude
    max = numpy.max(mag)
    numpy.multiply(mag, 255.0 / max, out=out)  # normalize (Q&D)

if __name__ == "__main__":
    import imageio
    filename = sys.argv[1]
    im = imageio.imread(filename)
    im = im.astype('int32')
    arg = sys.argv[-1]
    if arg == 'python':
        i = 0
        dx = sobel_py(im, 0)
        dy = sobel_py(im, 1)
        mag = hypot(dx, dy)  # magnitude
        mag *= 255.0 / numpy.max(mag)  # normalize (Q&D)
    else:
        import scipy
        sobel = sobel_scipy
        dx = sobel_scipy(im, 0)
        dy = sobel_scipy(im, 1)
        mag = hypot(dx, dy)      # magnitude
        mag *= 255.0 / numpy.max(mag)  # normalize (Q&D)

    imageio.imwrite('sobel-' + filename, mag)
