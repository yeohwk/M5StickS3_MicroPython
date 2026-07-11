import os, sys, io
import M5
from M5 import *

label0 = None
label1 = None

def setup():
    global label0, label1
    M5.begin()
    Widgets.setBrightness(150)		#Set LCD brightness to 150 (out of 255).
    Widgets.fillScreen(0x000000)	#Set LCD background color to 0x000000 (Black)
    Widgets.setRotation(1)			#Rotate LCD display by 90 degree.

    #Initialize text label0 and label1
    label0 = Widgets.Label("TEXT", 10, 40, 1.5, 0xFF0000, 0x000000, Widgets.FONTS.Montserrat18)
    label1 = Widgets.Label("TEXT", 10, 80, 1.0, 0x0000FF, 0x000000, Widgets.FONTS.Montserrat18)

def loop():
    M5.update()
  
    #Display texts at label0 ND and label1
    label0.setText(str('M5StickS3'))
    label1.setText(str('Nanyang Polytechnic'))
  
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
