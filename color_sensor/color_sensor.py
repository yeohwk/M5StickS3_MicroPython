import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import PBHUBUnit
from unit import ColorUnit
import time

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None
pahub_0 = None
pbhub_0 = None
color_0 = None

label_title = None
label_red = None
label_green = None
label_blue = None

last_update_time = 0

# -------------------------------------------------
# Convert RGB components into one LCD color value
# -------------------------------------------------
def create_rgb_color(red, green, blue):
    colour = (red << 16) | (green << 8) | blue
    return colour

# -------------------------------------------------
# Draw detected color on LCD
# -------------------------------------------------
def display_detected_color(red, green, blue):
    colour = create_rgb_color(red, green, blue)

    # Display colour in the lower part of the LCD
    Widgets.Rectangle(0, 62, 240, 73, colour, colour)

# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pahub_0, pbhub_0, color_0
    global label_title, label_red, label_green, label_blue
    global last_update_time

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    # -------------------------------------------------
    # Create LCD labels
    # -------------------------------------------------
    label_title = Widgets.Label("RGB Colour Sensor", 40, 2, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_red = Widgets.Label("R: 000", 10, 30, 1.0, 0xFF0000, 0x000000, Widgets.FONTS.Montserrat18)
    label_green = Widgets.Label("G: 000", 85, 30, 1.0, 0x00FF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_blue = Widgets.Label("B: 000", 165, 30, 1.0, 0x0000FF, 0x000000, Widgets.FONTS.Montserrat18)

    # -------------------------------------------------
    # I2C and hub initialization
    # GPIO 10 = SCL
    # GPIO 9  = SDA
    # -------------------------------------------------
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Initialize PaHUB on Channel 0
    pahub_0 = PAHUBUnit(i2c=i2c0, channel=0)

    # Initialize PbHUB
    pbhub_0 = PBHUBUnit(i2c0, 0x61)

    # Initialize Color Sensor connected to PaHUB Channel 0
    color_0 = ColorUnit(pahub_0)

    last_update_time = time.ticks_ms()

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_update_time

    M5.update()

    current_time = time.ticks_ms()

    # Update sensor reading five times per second
    if time.ticks_diff(current_time, last_update_time) >= 200:
        last_update_time = current_time

        # Read RGB components as values from 0 to 255
        rgb_values = color_0.get_color_rgb_bytes()

        red = rgb_values[0]
        green = rgb_values[1]
        blue = rgb_values[2]

        # Update numerical RGB values
        label_red.setText("R: {:03d}".format(red))
        label_green.setText("G: {:03d}".format(green))
        label_blue.setText("B: {:03d}".format(blue))

        # Recreate detected colour on LCD
        display_detected_color(red, green, blue)

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