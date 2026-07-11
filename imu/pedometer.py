import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Constants
# -------------------------------------------------
SAMPLE_INTERVAL_MS = 50

# Step-detection settings
STEP_THRESHOLD = 0.18
STEP_RESET_LEVEL = 0.08
MIN_STEP_INTERVAL_MS = 300

# Approximate calories burned per step
CALORIES_PER_STEP = 0.04

# -------------------------------------------------
# Global variables
# -------------------------------------------------
monitoring = False

step_count = 0
calories_burned = 0.0

previous_magnitude = 1.0
step_peak_detected = False

last_sample_time = 0
last_step_time = 0

label_title = None
label_steps = None
label_calories = None
label_status = None
label_instruction = None


# -------------------------------------------------
# Calculate acceleration magnitude
# -------------------------------------------------
def calculate_magnitude(ax, ay, az):
    return math.sqrt(
        (ax * ax) +
        (ay * ay) +
        (az * az)
    )


# -------------------------------------------------
# Detect a walking step
# -------------------------------------------------
def detect_step(ax, ay, az):
    global previous_magnitude
    global step_peak_detected
    global last_step_time

    magnitude = calculate_magnitude(ax, ay, az)

    # Remove the approximate 1g gravity component
    movement = abs(magnitude - 1.0)

    current_time = time.ticks_ms()

    # Detect the rising movement peak
    if movement >= STEP_THRESHOLD and not step_peak_detected:
        if time.ticks_diff(
            current_time,
            last_step_time
        ) >= MIN_STEP_INTERVAL_MS:

            step_peak_detected = True
            last_step_time = current_time
            previous_magnitude = magnitude

            return True

    # Allow the next step after movement falls below reset level
    if movement <= STEP_RESET_LEVEL:
        step_peak_detected = False

    previous_magnitude = magnitude

    return False


# -------------------------------------------------
# Update LCD values
# -------------------------------------------------
def update_display():
    label_steps.setText(
        "Steps: {}".format(step_count)
    )

    label_calories.setText(
        "Calories: {:.2f} kcal".format(calories_burned)
    )


# -------------------------------------------------
# Button A: Start or stop monitoring
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global monitoring
    global step_peak_detected
    global last_sample_time
    global last_step_time

    if not monitoring:
        monitoring = True
        step_peak_detected = False

        last_sample_time = time.ticks_ms()
        last_step_time = time.ticks_ms()

        label_status.setText("Monitoring")
        label_instruction.setText("A: Stop  B: Reset")

    else:
        monitoring = False
        step_peak_detected = False

        label_status.setText("Stopped")
        label_instruction.setText("A: Start  B: Reset")


# -------------------------------------------------
# Button B: Reset steps and calories
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global step_count
    global calories_burned
    global step_peak_detected

    step_count = 0
    calories_burned = 0.0
    step_peak_detected = False

    update_display()
    label_status.setText("Reset")


# -------------------------------------------------
# Read IMU and update step count
# -------------------------------------------------
def monitor_steps():
    global step_count
    global calories_burned

    accel = Imu.getAccel()

    ax = accel[0]
    ay = accel[1]
    az = accel[2]

    if detect_step(ax, ay, az):
        step_count = step_count + 1

        calories_burned = (
            step_count * CALORIES_PER_STEP
        )

        update_display()


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_title
    global label_steps
    global label_calories
    global label_status
    global label_instruction
    global last_sample_time
    global last_step_time

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label(
        "IMU Pedometer",
        45,
        8,
        1.0,
        0xFFFFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_steps = Widgets.Label(
        "Steps: 0",
        65,
        38,
        1.4,
        0x00FFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_calories = Widgets.Label(
        "Calories: 0.00 kcal",
        35,
        72,
        1.0,
        0xFFFF00,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_status = Widgets.Label(
        "Stopped",
        85,
        98,
        1.0,
        0x00FF00,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_instruction = Widgets.Label(
        "A: Start  B: Reset",
        35,
        118,
        1.0,
        0xFFFFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    BtnA.setCallback(
        type=BtnA.CB_TYPE.WAS_PRESSED,
        cb=btnA_wasPressed_event
    )

    BtnB.setCallback(
        type=BtnB.CB_TYPE.WAS_PRESSED,
        cb=btnB_wasPressed_event
    )

    last_sample_time = time.ticks_ms()
    last_step_time = time.ticks_ms()


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_sample_time

    M5.update()

    if monitoring:
        current_time = time.ticks_ms()

        if time.ticks_diff(
            current_time,
            last_sample_time
        ) >= SAMPLE_INTERVAL_MS:

            last_sample_time = current_time
            monitor_steps()

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