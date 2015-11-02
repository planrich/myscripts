
import cffi
import imageio
import numpy

ffi = cffi.FFI()
ffi.cdef("""
void init_device(char * name, int w, int h);

void get_image(int * buffer);
""")
C = ffi.dlopen('./readimage.so')

video_device = ffi.new("char[]", "/dev/video0")
W = 848
H = 480
C.init_device(video_device, W, H)
img = numpy.zeros(W*H*3, dtype=numpy.int32).reshape(H,W,3)
outimg = numpy.zeros(W*H*3, dtype=numpy.uint8).reshape(H,W,3)
import sys, pygame
pygame.init()
#import pygame.surfarray

size = width, height = 800, 600
speed = [2, 2]
black = 0, 0, 0

screen = pygame.display.set_mode(size)

buffer = ffi.cast("char*", img.ctypes.data)

import time
t = 0
now = time.time()
frame = 0

pygame.font.init()
myfont = pygame.font.SysFont("monospace", 25)

import sobel

from pygame.surface import locked
from pygame._sdl import sdl

label = myfont.render("-", 0, (255,255,255))
surface = pygame.Surface((848,480),0,24,masks=(0xff000000,0x00ff0000,0x0000ff00,0x0))
with locked(surface._c_surface):
    surface._c_surface.pixels = ffi.cast("int*", outimg.ctypes.data)
last_ten_count = 20
last_ten = [0.0] * last_ten_count
lti = 0
while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

    n = time.time()
    t += (n - now)
    now = n
    frame += 1
    if t >= 1.0:
        t -= 1
        ms = sum(last_ten)/float(last_ten_count) * 1000.0
        label = myfont.render("fps: %d, ms: %.2f" % (frame,ms), 1, (255,255,255))
        frame = 0

    C.get_image(buffer)
    n = time.time()
    sobel.sobel(img, outimg)
    e = time.time()
    last_ten[lti] = (e-n)
    lti += 1
    if lti >= last_ten_count:
        lti = 0

    screen.fill(black)
    screen.blit(surface, (0,0))
    screen.blit(label, (50, 500))
    pygame.display.flip()
