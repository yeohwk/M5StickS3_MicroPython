import os, sys, io
import M5
from M5 import *

title0  = None
circle0 = None
circle1 = None
circle2 = None
circle3 = None

def setup():
    global title0, circle0, circle1, circle2, circle3

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x7F7F00)
    title0 = Widgets.Title("Crazy Face", 3, 0xFFFFFF, 0x0000FF, Widgets.FONTS.Montserrat18)
    circle0 = Widgets.Circle(62, 87, 33, 0xFFFFFF, 0xFFFFFF)
    circle1 = Widgets.Circle(173, 71, 33, 0xFFFFFF, 0xFFFFFF)
    circle2 = Widgets.Circle(54, 78, 15, 0xFFFFFF, 0x181717)
    circle3 = Widgets.Circle(186, 74, 15, 0xFFFFFF, 0x0D0C0C)

def loop():
    global title0, circle0, circle1, circle2, circle3
    M5.update()

if __name__ == '__main__':
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("please update to latest firmware")
