import os, sys, io
import M5
from M5 import *
import time

circle0 = None
circle1 = None
rect0 = None
triangle0 = None
label0 = None

#Initialization (Run once)
def setup():
    global circle0, circle1, rect0, triangle0, label0

    M5.begin()
    Widgets.setRotation(0)
    Widgets.fillScreen(0x000000)
    circle0 = Widgets.Circle(34, 56, 15, 0xffffff, 0xea1313)
    circle1 = Widgets.Circle(91, 57, 15, 0xffffff, 0xffffff)
    rect0 = Widgets.Rectangle(35, 143, 60, 15, 0x19e240, 0x19e240)
    triangle0 = Widgets.Triangle(64, 90, 55, 118, 76, 118, 0xffffff, 0xffffff)
    label0 = Widgets.Label("Good Day !", 19, 198, 1.0, 0xffffff, 0x222222, Widgets.FONTS.Montserrat18)

    Speaker.setVolumePercentage(100)

#Main Program (Run in a loop)
def loop():
    global circle0, circle1, rect0, triangle0, label0
    M5.update()
    Speaker.tone(4000, 200) 	#4KHz Tone, 200ms duration.
    time.sleep(1)				#Delay 1s.

#System Default (Do not modify)
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
