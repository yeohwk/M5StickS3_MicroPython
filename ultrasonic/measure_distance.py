import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import UltrasoundI2CUnit
import time

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None
pahub_1 = None
ultrasonic_0 = None

label_title = None
label_distance = None
label_status = None

last_update_time = 0

# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pahub_1, ultrasonic_0
    global label_title, label_distance, label_status
    global last_update_time

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label("Distance Sensor", 45, 15, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_distance = Widgets.Label("Dist: -- cm", 45, 55, 1.4, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_status = Widgets.Label("Measuring...", 45, 100, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)

    # Configure GPIO 10 as SCL and GPIO 9 as SDA
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Select Port 1 of the PaHUB
    pahub_1 = PAHUBUnit(i2c=i2c0, channel=1)

    # Initialize the I2C Ultrasonic Distance Unit
    # connected to PaHUB Port 1
    ultrasonic_0 = UltrasoundI2CUnit(pahub_1)
    last_update_time = time.ticks_ms()

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_update_time

    M5.update()
    current_time = time.ticks_ms()

    # Read the sensor five times per second
    if time.ticks_diff(current_time, last_update_time) >= 200:
        last_update_time = current_time
        distance = ultrasonic_0.get_target_distance()

        if distance > 0 and distance < 7958:
            label_distance.setText("Dist: {:.1f} cm" .format(distance))
            label_status.setText("Object Detected")
        else:
            label_distance.setText("Dist: -- cm")
            label_status.setText("Out of Range")

    time.sleep_ms(20)

# -------------------------------------------------
# Do not modify
# -------------------------------------------------
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