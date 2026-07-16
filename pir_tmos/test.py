import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import TMOSUnit

i2c0 = None
tmos_0 = None

motion = None
motion_var = None
presence = None
presence_var = None
temperature = None

def tmos_0_presence_detect_event(arg):
    global i2c0, tmos_0
    print("Presence: {}, Motion: {}" .format(tmos_0.get_presence_state(), tmos_0.get_motion_state()))

def tmos_0_motion_detect_event(arg):
    global i2c0, tmos_0
    print("Presence: {}, Motion: {}" .format(tmos_0.get_presence_state(), tmos_0.get_motion_state()))
 
def tmos_0_presence_not_detected_event(arg):
    global i2c0, tmos_0
    print("Presence: {}" .format(tmos_0.get_presence_state())) 

def tmos_0_motion_not_detected_event(arg):
    global i2c0, tmos_0
    print("Motion: {}" .format(tmos_0.get_motion_state())) 

def setup():
    global i2c0, tmos_0, motion, motion_var, presence, presence_var, temperature

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)

    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)
    tmos_0 = TMOSUnit(i2c0, 0x5a)
    tmos_0.set_gain_mode(7)							#7
    tmos_0.set_tmos_sensitivity(1000)
    tmos_0.set_motion_threshold(200)
    tmos_0.set_motion_hysteresis(50)				#50
    tmos_0.set_presence_threshold(200)
    tmos_0.set_presence_hysteresis(50)				#50
    tmos_0.set_tambient_shock_threshold(10)
    tmos_0.set_tambient_shock_hysteresis(2)
  
    tmos_0.set_callback(tmos_0_presence_detect_event, tmos_0.PRESENCE_DETECT)
    tmos_0.set_callback(tmos_0_motion_detect_event, tmos_0.MOTION_DETECT)
    tmos_0.set_callback(tmos_0_presence_not_detected_event, tmos_0.PRESENCE_NOT_DETECTED)
    tmos_0.set_callback(tmos_0_motion_not_detected_event, tmos_0.MOTION_NOT_DETECTED)

def loop():
  global i2c0, tmos_0, motion, motion_var, presence, presence_var, temperature
  M5.update()
  tmos_0.tick_callback()
  
  if (tmos_0.get_data_ready() == 1):
      print("Presence: {}, Motion: {}, Temp: {}" .format(tmos_0.get_presence_state(), tmos_0.get_motion_state(), tmos_0.get_temperature_data()))  
  
#  motion = tmos_0.get_motion_state()
#  motion_var = tmos_0.get_motion_value()
#  presence = tmos_0.get_presence_state()
#  presence_var = tmos_0.get_presence_value()
#  temperature = tmos_0.get_temperature_data()


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
