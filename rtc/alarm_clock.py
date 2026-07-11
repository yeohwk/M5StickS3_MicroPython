import os, sys, io
import M5
from M5 import *
from machine import RTC
import time

# -------------------------------------------------
# Hardcoded initial date and time
# -------------------------------------------------
INITIAL_YEAR = 2026
INITIAL_MONTH = 7
INITIAL_DAY = 2
INITIAL_WEEKDAY = 3       # 0 = Monday
INITIAL_HOUR = 14
INITIAL_MINUTE = 30
INITIAL_SECOND = 0

# -------------------------------------------------
# Hardcoded alarm time
# -------------------------------------------------
ALARM_HOUR = 14
ALARM_MINUTE = 31

# -------------------------------------------------
# Global variables
# -------------------------------------------------
rtc = RTC()

alarm_enabled = False
alarm_ringing = False

last_display_second = -1
last_beep_time = 0

label_time = None
label_date = None
label_alarm = None
label_status = None


# -------------------------------------------------
# Button A: Enable alarm
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global alarm_enabled, alarm_ringing

    alarm_enabled = True
    alarm_ringing = False

    label_status.setText("Alarm: ENABLED")
    label_status.setColor(0x00FF00, 0x000000)


# -------------------------------------------------
# Button B: Disable alarm
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global alarm_enabled, alarm_ringing

    alarm_enabled = False
    alarm_ringing = False

    Speaker.stop()

    label_status.setText("Alarm: DISABLED")
    label_status.setColor(0xFF0000, 0x000000)


# -------------------------------------------------
# Update clock display
# -------------------------------------------------
def update_clock_display(year, month, day, hour, minute, second):
    time_text = "{:02d}:{:02d}:{:02d}".format(
        hour,
        minute,
        second
    )

    date_text = "{:02d}/{:02d}/{:04d}".format(
        day,
        month,
        year
    )

    label_time.setText(time_text)
    label_date.setText(date_text)


# -------------------------------------------------
# Check alarm time
# -------------------------------------------------
def check_alarm(hour, minute, second):
    global alarm_ringing

    if not alarm_enabled:
        alarm_ringing = False
        return

    # Start alarm when hour and minute match
    if hour == ALARM_HOUR and minute == ALARM_MINUTE:
        alarm_ringing = True

    # Stop automatically after the alarm minute has passed
    else:
        alarm_ringing = False


# -------------------------------------------------
# Generate repeating alarm sound
# -------------------------------------------------
def sound_alarm():
    global last_beep_time

    if alarm_ringing:
        current_time = time.ticks_ms()

        # Produce one short beep every 500 milliseconds
        if time.ticks_diff(current_time, last_beep_time) >= 500:
            last_beep_time = current_time
            Speaker.tone(2500, 200)


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_time, label_date
    global label_alarm, label_status
    global last_beep_time

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    Speaker.begin()
    Speaker.setVolumePercentage(80)

    # Set initial RTC date and time
    rtc.datetime((
        INITIAL_YEAR,
        INITIAL_MONTH,
        INITIAL_DAY,
        INITIAL_WEEKDAY,
        INITIAL_HOUR,
        INITIAL_MINUTE,
        INITIAL_SECOND,
        0
    ))

    label_time = Widgets.Label(
        "00:00:00",
        32,
        20,
        1.8,
        0x00FFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_date = Widgets.Label(
        "00/00/0000",
        60,
        60,
        1.0,
        0xFFFFFF,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_alarm = Widgets.Label(
        "Alarm {:02d}:{:02d}".format(ALARM_HOUR, ALARM_MINUTE),
        55,
        85,
        1.0,
        0xFFFF00,
        0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_status = Widgets.Label(
        "Alarm: DISABLED",
        45,
        110,
        1.0,
        0xFF0000,
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

    current_datetime = rtc.datetime()

    year = current_datetime[0]
    month = current_datetime[1]
    day = current_datetime[2]
    hour = current_datetime[4]
    minute = current_datetime[5]
    second = current_datetime[6]

    # Update LCD only when the second changes
    if second != last_display_second:
        last_display_second = second

        update_clock_display(
            year,
            month,
            day,
            hour,
            minute,
            second
        )

        check_alarm(hour, minute, second)

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