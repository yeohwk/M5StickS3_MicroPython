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

PIR_PORT = 1
PIR_SIGNAL_PIN = 1


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pbhub_0

    M5.begin()

    # Configure the I2C bus
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)
    # Initialize the PbHUB
    pbhub_0 = PBHUBUnit(i2c0, 0x61)

    print("M5Stack PIR Motion Sensor")
    print("Connected to PbHUB Port 1")
    print("Waiting for human motion...")
    print("----------------------------")

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    # Read the PIR sensor connected to PbHUB Port 1
    motion_state = pbhub_0.digital_read(PIR_PORT, PIR_SIGNAL_PIN)

    if motion_state == 1:
        print("Motion detected")
    else:
        print("No motion detected")

    time.sleep_ms(500)

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