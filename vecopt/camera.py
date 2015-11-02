import os
import io
import fcntl
import struct
import mmap

# constant for linux portability
_IOC_NRBITS = 8
_IOC_TYPEBITS = 8

# architecture specific
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRMASK = (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK = (1 << _IOC_TYPEBITS) - 1
_IOC_SIZEMASK = (1 << _IOC_SIZEBITS) - 1
_IOC_DIRMASK = (1 << _IOC_DIRBITS) - 1

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2


def _IOC(dir, type, nr, size):
    if isinstance(size, str) or isinstance(size, unicode):
        size = struct.calcsize(size)
    return dir  << _IOC_DIRSHIFT  | \
           type << _IOC_TYPESHIFT | \
           nr   << _IOC_NRSHIFT   | \
           size << _IOC_SIZESHIFT

def _IO(type, nr): return _IOC(_IOC_NONE, type, nr, 0)
def _IOR(type, nr, size): return _IOC(_IOC_READ, type, nr, size)
def _IOW(type, nr, size): return _IOC(_IOC_WRITE, type, nr, size)
def _IOWR(type, nr, size): return _IOC(_IOC_READ | _IOC_WRITE, type, nr, size)

TIMECODE_LEN = (32+32+4*8+4*8) / 8
TIMEVAL_LEN = (64+64)/8
buffer_fmt = 'IIIII%dsIIIiIII' % (TIMECODE_LEN + TIMEVAL_LEN)
buffer_INDEX = 0
buffer_TYPE = 1
buffer_MEMORY = 7
buffer_FD = 8
buffer_default = [0] * (12)
buffer_default[5] = '\x00' * (TIMECODE_LEN + TIMEVAL_LEN)

class CameraL4V(object):
    def __init__(self):
        self.camfd = None

    def open(self, name):
        self.camfd = open(name, 'rw')
        assert self.camfd >= 0
        buffer = ' ' * 512
        cmd = _IOR(ord('V'),0,'16c32c32cIII3I')
        while True:
            val = fcntl.ioctl(self.camfd, cmd, buffer)
            if val == -1:
                continue
            break
        reqfmt = 'III2I'
        buffer = struct.pack(reqfmt, 2,1,1,0,0)
        cmd = _IOWR(ord('V'),8,reqfmt)
        val = fcntl.ioctl(self.camfd, cmd, buffer)
        if val == -1:
            print "oh no", val
        count, type, mem, a,b = struct.unpack(reqfmt, val)
        print count, type, mem

        self.buffers = [None] * count
        for i in range(count):
            self._mmap_buffer(i)

    def _mmap_buffer(self, index):
        buf = buffer_default[:]
        buf[buffer_TYPE] = 1
        buf[buffer_MEMORY] = 1
        buf[buffer_FD] = index
        cmd = _IOWR(ord('V'), 15, buffer_fmt)
        bytes = struct.pack(buffer_fmt, buf)
        val = fcntl.ioctl(self.camfd, cmd, bytes)
        output = struct.unpack(buffer_fmt, buf)


c = CameraL4V()
c.open("/dev/video0")
img = c.getimage()


