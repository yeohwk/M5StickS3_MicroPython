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

ANGLE_PORT = 3
SERVO_PORT = 5

# Adjust this value based on the maximum reading observed
ADC_MAX = 4095

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

    print("Angle Sensor and Servo Control")
    print("Angle Unit: PbHUB Port 3")
    print("Servo Motor: PbHUB Port 5")
    print("--------------------------------")

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    # Read the Angle Unit connected to PbHUB Port 3
    raw_value = pbhub_0.analog_read(ANGLE_PORT)

    # Limit the value to the expected ADC range
    if raw_value < 0:
        raw_value = 0

    if raw_value > ADC_MAX:
        raw_value = ADC_MAX

    # Convert the analog reading to a servo angle
    servo_angle = int((raw_value / ADC_MAX) * 180)

    # Control the servo connected to PbHUB Port 5
    pbhub_0.set_servo_angle(SERVO_PORT, 0, servo_angle)

    print(
        "Raw: {} | Servo Angle: {} degrees"
        .format(raw_value, servo_angle)
    )

    time.sleep_ms(100)

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
            # Stop the servo
            if pbhub_0 is not None:
                pbhub_0.set_servo_angle(SERVO_PORT, 0, 90)

            from utility import print_error_msg
            print_error_msg(e)

        except ImportError:
            print("Please update to the latest firmware")