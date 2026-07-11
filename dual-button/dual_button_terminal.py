import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PBHUBUnit
import time

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None
pbhub_0 = None

BUTTON_PORT = 0
RED_BUTTON_PIN = 0
BLUE_BUTTON_PIN = 1

previous_red = 1
previous_blue = 1

# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pbhub_0

    M5.begin()

    # Configure the I2C bus
    i2c0 = I2C(
        0,
        scl=Pin(10),
        sda=Pin(9),
        freq=100000
    )

    # Initialize the PbHUB
    pbhub_0 = PBHUBUnit(i2c0, 0x61)

    print("M5Stack Dual-Button Unit")
    print("Connected to PbHUB Port 0")
    print("Waiting for button input...")
    print("----------------------------")

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global previous_red, previous_blue

    M5.update()

    # Read both buttons from PbHUB Port 0
    red_state = pbhub_0.digital_read(BUTTON_PORT, RED_BUTTON_PIN)
    blue_state = pbhub_0.digital_read(BUTTON_PORT, BLUE_BUTTON_PIN)

    # A pressed button returns 0
    if red_state == 0 and previous_red == 1:
        print("Red button pressed")

    if blue_state == 0 and previous_blue == 1:
        print("Blue button pressed")

    previous_red = red_state
    previous_blue = blue_state
    time.sleep_ms(50)

# -------------------------------------------------
# Do not modify
# -------------------------------------------------
if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()

    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
            
        except ImportError:
            print("Please update to the latest firmware")