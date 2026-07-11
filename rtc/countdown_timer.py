import os, sys, io
import M5
from M5 import *
from machine import RTC
import time

# -------------------------------------------------
# Constants
# -------------------------------------------------
TIME_INCREMENT = 5
MAX_TIME = 180

# -------------------------------------------------
# Global variables
# -------------------------------------------------
rtc = RTC()

preset_seconds = 0
remaining_seconds = 0

counting = False
alarm_ringing = False

countdown_end_time = 0
last_display_second = -1
last_beep_time = 0

label_title = None
label_time = None
label_status = None
label_instruction = None


# -------------------------------------------------
# Convert seconds into MM:SS format
# -------------------------------------------------
def format_time(total_seconds):
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return "{:02d}:{:02d}".format(minutes, seconds)


# -------------------------------------------------
# Button A: Increase preset time by 5 seconds
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global preset_seconds, remaining_seconds
    global counting, alarm_ringing

    # Do not change the preset while counting or alarming
    if counting or alarm_ringing:
        return

    # Return to 0 after reaching 180 seconds
    if preset_seconds >= MAX_TIME:
        preset_seconds = 0
    else:
        preset_seconds = preset_seconds + TIME_INCREMENT

    remaining_seconds = preset_seconds

    label_time.setText(format_time(remaining_seconds))

    if preset_seconds == 0:
        label_status.setText("Set Timer")
    else:
        label_status.setText("Timer Preset")


# -------------------------------------------------
# Button B: Start, stop, or silence alarm
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global counting, alarm_ringing
    global countdown_end_time, remaining_seconds
    global last_display_second

    # Stop alarm and restore the original preset time
    if alarm_ringing:
        alarm_ringing = False
        Speaker.stop()

        remaining_seconds = preset_seconds
        last_display_second = remaining_seconds

        label_time.setText(format_time(remaining_seconds))
        label_status.setText("Timer Reset")
        label_instruction.setText("A: Set  B: Start")
        return

    # Stop countdown if currently running
    if counting:
        counting = False

        label_status.setText("Countdown Stopped")
        label_instruction.setText("A: Set  B: Start")
        return

    # Start countdown if a valid time has been preset
    if remaining_seconds > 0:
        countdown_end_time = time.time() + remaining_seconds

        counting = True
        last_display_second = -1

        label_status.setText("Counting Down")
        label_instruction.setText("B: Stop")
    else:
        label_status.setText("Set Timer First")

# -------------------------------------------------
# Update remaining time
# -------------------------------------------------
def update_countdown():
    global remaining_seconds, counting, alarm_ringing

    remaining_seconds = int(countdown_end_time - time.time())

    if remaining_seconds <= 0:
        remaining_seconds = 0
        counting = False
        alarm_ringing = True

        label_time.setText("00:00")
        label_status.setText("TIME UP!")
        label_instruction.setText("Press B to Stop")


# -------------------------------------------------
# Sound alarm repeatedly
# -------------------------------------------------
def sound_alarm():
    global last_beep_time

    if alarm_ringing:
        current_time = time.ticks_ms()

        if time.ticks_diff(current_time, last_beep_time) >= 500:
            last_beep_time = current_time
            Speaker.tone(2500, 200)


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_title, label_time
    global label_status, label_instruction
    global last_beep_time

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    Speaker.begin()
    Speaker.setVolumePercentage(80)

    rtc.datetime((
        2026,
        7,
        2,
        3,
        12,
        0,
        0,
        0
    ))

    label_title = Widgets.Label(
        "Countdown Timer",
        40,
        10,
        1.0,
        0xFFFFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_time = Widgets.Label(
        "00:00",
        65,
        40,
        2.0,
        0x00FFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_status = Widgets.Label(
        "Set Timer",
        70,
        85,
        1.0,
        0xFFFF00,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_instruction = Widgets.Label(
        "A: +5s  B: Start",
        40,
        110,
        1.0,
        0x00FF00,
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

    last_beep_time = time.ticks_ms()


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_display_second

    M5.update()

    if counting:
        update_countdown()

        if remaining_seconds != last_display_second:
            last_display_second = remaining_seconds
            label_time.setText(format_time(remaining_seconds))

    sound_alarm()

    time.sleep_ms(50)


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