import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C	#I2C Library 
from unit import PAHUBUnit	#PaHUB Library
from unit import PBHUBUnit	#PbHUB Library

i2c0 = None		#Added to support external peripherals connecting to I2C Bus
pahub_0 = None	#Added for PaHUB
pbhub_0 = None	#Added for PbHUB

def setup():
    global i2c0, pahub_0, pbhub_0

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)

    #I2C peripherals Initialization codes
    #Set M5StickS3 GPIO Pin 9 and 10 to be I2C Bus port with Bus clock of 100KHz 
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)
    pahub_0 = PAHUBUnit(i2c=i2c0, channel=0)	#PaHUB Initialization
    pbhub_0 = PBHUBUnit(i2c0, 0x61)				#PbHUB Initialization

def loop():
    global i2c0, pahub_0, pbhub_0
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
