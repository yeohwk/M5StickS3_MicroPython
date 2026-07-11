import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Constants
# -------------------------------------------------
THRESHOLD_INCREMENT = 0.1
MIN_THRESHOLD = 0.1
MAX_THRESHOLD = 16.0

SAMPLE_INTERVAL_MS = 50
ALARM_FREQUENCY = 2500
ALARM_DURATION_MS = 200
ALARM_INTERVAL_MS = 500

# -------------------------------------------------
# Global variables
# -------------------------------------------------
vibration_threshold = MIN_THRESHOLD

measuring = False
alarm_ringing = False

previous_ax = 0.0
previous_ay = 0.0
previous_az = 0.0

last_sample_time = 0
last_beep_time = 0

label_title = None
label_threshold = None
label_vibration = None
label_status = None
label_instruction = None


# -------------------------------------------------
# Calculate vibration level
# -------------------------------------------------
def calculate_vibration(ax, ay, az):
    global previous_ax, previous_ay, previous_az

    # Calculate changes in acceleration on all three axes
    delta_x = ax - previous_ax
    delta_y = ay - previous_ay
    delta_z = az - previous_az

    # Combine the changes into one vibration value
    vibration = math.sqrt(
        (delta_x * delta_x) +
        (delta_y * delta_y) +
        (delta_z * delta_z)
    )

    # Save current readings for the next calculation
    previous_ax = ax
    previous_ay = ay
    previous_az = az

    return vibration


# -------------------------------------------------
# Button A: Increase vibration threshold
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global vibration_threshold

    # Do not change threshold while measuring or alarming
    if measuring or alarm_ringing:
        return

    # Reset to 0.1g after reaching 16.0g
    if vibration_threshold >= MAX_THRESHOLD:
        vibration_threshold = MIN_THRESHOLD
    else:
        vibration_threshold = vibration_threshold + THRESHOLD_INCREMENT

        # Avoid floating-point rounding errors
        vibration_threshold = round(vibration_threshold, 1)

        if vibration_threshold > MAX_THRESHOLD:
            vibration_threshold = MAX_THRESHOLD

    label_threshold.setText(
        "Threshold: {:.1f}g".format(vibration_threshold)
    )

    label_status.setText("Threshold Set")


# -------------------------------------------------
# Button B: Start, stop, or silence alarm
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global measuring, alarm_ringing
    global previous_ax, previous_ay, previous_az
    global last_sample_time

    # Stop alarm and measurement
    if alarm_ringing:
        alarm_ringing = False
        measuring = False

        Speaker.stop()

        label_status.setText("Alarm Stopped")
        label_instruction.setText("A: Set  B: Start")
        return

    # Stop vibration measurement
    if measuring:
        measuring = False

        label_status.setText("Measurement Stopped")
        label_instruction.setText("A: Set  B: Start")
        return

    # Start vibration measurement
    accel = Imu.getAccel()

    previous_ax = accel[0]
    previous_ay = accel[1]
    previous_az = accel[2]

    last_sample_time = time.ticks_ms()
    measuring = True

    label_vibration.setText("Vibration: 0.00g")
    label_status.setText("Measuring")
    label_instruction.setText("B: Stop")


# -------------------------------------------------
# Check vibration level
# -------------------------------------------------
def measure_vibration():
    global measuring, alarm_ringing

    accel = Imu.getAccel()

    ax = accel[0]
    ay = accel[1]
    az = accel[2]

    vibration = calculate_vibration(ax, ay, az)

    label_vibration.setText(
        "Vibration: {:.2f}g".format(vibration)
    )

    # Trigger alarm when vibration exceeds threshold
    if vibration >= vibration_threshold:
        measuring = False
        alarm_ringing = True

        label_status.setText("VIBRATION ALERT!")
        label_instruction.setText("Press B to Stop")


# -------------------------------------------------
# Produce repeating alarm sound
# -------------------------------------------------
def sound_alarm():
    global last_beep_time

    if alarm_ringing:
        current_time = time.ticks_ms()

        if time.ticks_diff(current_time, last_beep_time) >= ALARM_INTERVAL_MS:
            last_beep_time = current_time

            Speaker.tone(
                ALARM_FREQUENCY,
                ALARM_DURATION_MS
            )


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_title, label_threshold
    global label_vibration, label_status
    global label_instruction
    global last_sample_time, last_beep_time

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    Speaker.begin()
    Speaker.setVolumePercentage(80)

    label_title = Widgets.Label(
        "Vibration Sensor",
        35,
        5,
        1.0,
        0xFFFFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_threshold = Widgets.Label(
        "Threshold: 0.1g",
        40,
        30,
        1.0,
        0xFFFF00,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_vibration = Widgets.Label(
        "Vibration: 0.00g",
        35,
        58,
        1.0,
        0x00FFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_status = Widgets.Label(
        "Ready",
        85,
        85,
        1.0,
        0x00FF00,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_instruction = Widgets.Label(
        "A: +0.1g  B: Start",
        25,
        110,
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
    last_beep_time = time.ticks_ms()


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_sample_time

    M5.update()

    if measuring:
        current_time = time.ticks_ms()

        if time.ticks_diff(
            current_time,
            last_sample_time
        ) >= SAMPLE_INTERVAL_MS:

            last_sample_time = current_time
            measure_vibration()

    sound_alarm()

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
            Speaker.stop()

            from utility import print_error_msg
            print_error_msg(e)

        except ImportError:
            print("please update to latest firmware")