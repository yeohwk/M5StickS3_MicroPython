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

LIGHT_PORT = 2

# Calibration values
DARK_RAW = 0
BRIGHT_RAW = 4095
MAX_LUX = 1000.0


# -------------------------------------------------
# Convert the analog reading into estimated lux
# -------------------------------------------------
def convert_to_lux(raw_value):
    # Limit the reading to the calibration range
    if raw_value < DARK_RAW:
        raw_value = DARK_RAW

    if raw_value > BRIGHT_RAW:
        raw_value = BRIGHT_RAW

    # Convert the analog reading into estimated lux
    lux = ((raw_value - DARK_RAW) / (BRIGHT_RAW - DARK_RAW)) * MAX_LUX
    return lux


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

    print("M5Stack Light Sensor Unit")
    print("Connected to PbHUB Port 2")
    print("Measuring environmental light intensity...")
    print("------------------------------------------")


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    # Read the Light Sensor Unit on PbHUB Port 2.
    # Sensor connection is inverted where Dark = 4095 and Bright = 0.
    # Use 4095 - raw sensor readout value to obtain the non-inverted value.
    # For acquiring analog value, the analog port is channel 0 of the LIGHT_PORT.
    raw_value = 4095 - pbhub_0.analog_read(LIGHT_PORT)

    # Convert the analog reading into estimated lux
    light_lux = convert_to_lux(raw_value)
    print("Raw: {} | Light Intensity: {:.1f} lux" .format(raw_value, light_lux))
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