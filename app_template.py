#Imports (Place library imports HERE!)
import os, sys, io
import M5
from M5 import *
import time

def setup():
    M5.begin()
    #Place initialization codes HERE!   

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
