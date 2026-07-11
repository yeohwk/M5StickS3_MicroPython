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

# PbHUB port connected to the Angle Unit
ANGLE_PORT = 3

# Change to 1023 if using an older 10-bit PbHUB
ADC_MAX = 4095


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pbhub_0

    M5.begin()

    # Configure the I2C bus
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Initialize the PbHUB at I2C address 0x61
    pbhub_0 = PBHUBUnit(i2c0, 0x61)

    print("M5Stack Angle Unit")
    print("Connected to PbHUB Port 3")
    print("----------------------------")


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    # Read the Angle Unit on PbHUB Port 0
    raw_value = pbhub_0.analog_read(ANGLE_PORT)

    # Convert the reading into a percentage
    percentage = (raw_value / ADC_MAX) * 100

    # Estimate the knob position from 0 to 300 degrees
    angle = (raw_value / ADC_MAX) * 300

    print(
        "Raw: {} | Position: {:.1f}% | Angle: {:.1f} degrees"
        .format(raw_value, percentage, angle)
    )

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