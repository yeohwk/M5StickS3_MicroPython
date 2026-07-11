import os, sys, io
import M5
from M5 import *

def btnA_wasPressed_event(state):
    Widgets.fillScreen(0x00FF00)


def btnB_wasPressed_event(state):
    Widgets.fillScreen(0xFF0000)


def setup():
    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)

    BtnA.setCallback(type=BtnA.CB_TYPE.WAS_PRESSED, cb=btnA_wasPressed_event)
    BtnB.setCallback(type=BtnB.CB_TYPE.WAS_PRESSED, cb=btnB_wasPressed_event)

def loop():
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