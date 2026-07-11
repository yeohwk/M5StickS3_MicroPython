import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Global variables
# -------------------------------------------------
label_status = None
label_ax = None
label_ay = None
label_az = None
label_angle = None

last_time = 0

# -------------------------------------------------
# Determine tilt direction
# -------------------------------------------------
def get_tilt_direction(ax, ay):
    threshold = 0.35

    if ax > threshold:
        return "Tilt Right"
    elif ax < -threshold:
        return "Tilt Left"
    elif ay > threshold:
        return "Tilt Up"
    elif ay < -threshold:
        return "Tilt Down"
    else:
        return "Flat / Stable"

# -------------------------------------------------
# Estimate tilt angle
# -------------------------------------------------
def get_tilt_angle(ax, ay, az):
    # Estimate tilt angle from acceleration vector
    horizontal = math.sqrt((ax * ax) + (ay * ay))

    if az == 0:
        return 0

    angle = math.atan(horizontal / abs(az))
    angle = angle * 180 / math.pi

    return angle

# -------------------------------------------------
# Draw simple visual indicator
# -------------------------------------------------
def draw_tilt_indicator(ax, ay):
    # Draw background area
    Widgets.Rectangle(0, 80, 240, 55, 0x000000, 0x000000) #55

    center_x = 120
    center_y = 108

    # Convert tilt values to screen movement
    dot_x = int(center_x + (ax * 60))
    dot_y = int(center_y - (ay * 40))

    # Limit dot position within screen area
    if dot_x < 10:
        dot_x = 10
    if dot_x > 230:
        dot_x = 230

    if dot_y < 90:
        dot_y = 90
    if dot_y > 130:
        dot_y = 130

    # Draw centre reference and moving dot
    Widgets.Circle(center_x, center_y, 4, 0xFFFFFF, 0xFFFFFF)
    Widgets.Circle(dot_x, dot_y, 8, 0x00FF00, 0x00FF00)

# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_title, label_status, label_ax, label_ay, label_az, label_angle, last_time

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(150)

    label_status = Widgets.Label("Status: --", 10, 2, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_ax = Widgets.Label("Ax: --", 10, 22, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_ay = Widgets.Label("Ay: --", 90, 22, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_az = Widgets.Label("Az: --", 170, 22, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_angle = Widgets.Label("Angle: --", 10, 40, 1.0, 0xFF8000, 0x000000, Widgets.FONTS.Montserrat18)

    last_time = time.ticks_ms()

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_time

    M5.update()

    # Update about 10 times per second
    if time.ticks_diff(time.ticks_ms(), last_time) >= 100:
        last_time = time.ticks_ms()

        accel = Imu.getAccel()

        ax = accel[0]
        ay = accel[1]
        az = accel[2]

        tilt_direction = get_tilt_direction(ax, ay)
        tilt_angle = get_tilt_angle(ax, ay, az)

        label_status.setText("Status: " + tilt_direction)
        label_ax.setText("Ax: {:.2f}".format(ax))
        label_ay.setText("Ay: {:.2f}".format(ay))
        label_az.setText("Az: {:.2f}".format(az))
        label_angle.setText("Angle: {:.1f} deg".format(tilt_angle))

        draw_tilt_indicator(ax, ay)

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