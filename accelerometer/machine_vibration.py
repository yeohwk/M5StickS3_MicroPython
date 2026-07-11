import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import AccelUnit
import time
import math

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None
pahub_3 = None
accel_0 = None

label_title = None
label_x = None
label_y = None
label_z = None
label_vibration = None
label_status = None

previous_x = 0
previous_y = 0
previous_z = 0

last_sample_time = 0
first_reading = True

# Vibration thresholds in m/s²
WARNING_THRESHOLD = 0.50
ALERT_THRESHOLD = 1.50


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pahub_3, accel_0
    global label_title, label_x, label_y, label_z
    global label_vibration, label_status
    global last_sample_time

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label("Machine Vibration", 35, 5, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_x = Widgets.Label("X: --.-- m/s2", 10, 30, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_y = Widgets.Label("Y: --.-- m/s2", 10, 50, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_z = Widgets.Label("Z: --.-- m/s2", 10, 70, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_vibration = Widgets.Label("Vibration: --.--", 10, 92, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_status = Widgets.Label("Status: Monitoring", 10, 113, 1.0, 0x00FF00, 0x000000, Widgets.FONTS.Montserrat14)

    # Configure GPIO 10 as SCL and GPIO 9 as SDA
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Select Port 3 of the PaHUB
    pahub_3 = PAHUBUnit(i2c=i2c0, channel=3)

    # Initialize the ADXL345 Unit connected to PaHUB Port 3
    accel_0 = AccelUnit(pahub_3, 0x53)
    last_sample_time = time.ticks_ms()


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global previous_x, previous_y, previous_z
    global last_sample_time, first_reading

    M5.update()

    current_time = time.ticks_ms()

    # Read the accelerometer every 50 milliseconds
    if time.ticks_diff(current_time, last_sample_time) >= 50:
        last_sample_time = current_time

        acceleration = accel_0.get_accel()

        x = acceleration[0]
        y = acceleration[1]
        z = acceleration[2]

        if first_reading:
            vibration = 0
            first_reading = False
        else:
            change_x = x - previous_x
            change_y = y - previous_y
            change_z = z - previous_z
            vibration = math.sqrt(change_x ** 2 + change_y ** 2 + change_z ** 2)

        previous_x = x
        previous_y = y
        previous_z = z

        label_x.setText("X: {:.2f} m/s2".format(x))
        label_y.setText("Y: {:.2f} m/s2".format(y))
        label_z.setText("Z: {:.2f} m/s2".format(z))
        label_vibration.setText("Vibration: {:.2f}".format(vibration))

        if vibration >= ALERT_THRESHOLD:
            label_status.setText("Status: High Vibration")
            label_status.setColor(0xFF0000, 0x000000)

        elif vibration >= WARNING_THRESHOLD:
            label_status.setText("Status: Warning")
            label_status.setColor(0xFFFF00, 0x000000)

        else:
            label_status.setText("Status: Normal")
            label_status.setColor(0x00FF00, 0x000000)

    time.sleep_ms(10)


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