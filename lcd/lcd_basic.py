#Imports (Place library imports HERE!)
import os, sys, io
import M5
from M5 import *
import time

def setup():
    M5.begin()
    #Place initialization codes HERE!
    Widgets.setBrightness(150)		#Set LCD brightness (0 - 255)
    Widgets.fillScreen(0xffff00)	#Set LCD background colour: 0xRRGGBB
    Widgets.setRotation(0)    		#Set LCD screen rotation

def loop():
    M5.update()
    #Place application codes HERE!

#Do not modify.
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
