import os, sys, io
import M5
from M5 import *
import math
import time
import array

# Global variables
measuring = False
label_title = None
label_db = None
label_status = None

# Audio settings
SAMPLE_RATE = 8000
BUFFER_SIZE = 512

# Reference value for estimated dB calculation
# This is not a calibrated SPL reference.
REF_VALUE = 1000

def estimate_db(audio_buffer):
    total = 0
    count = len(audio_buffer)

    for sample in audio_buffer:
        total = total + (sample * sample)

    if count == 0:
        return 0

    rms = math.sqrt(total / count)

    if rms <= 0:
        return 0

    db = 20 * math.log10(rms / REF_VALUE) + 60
    return db

def btnA_wasPressed_event(state):
    global measuring

    measuring = True
    Widgets.fillScreen(0x000000)
    label_title.setText("SPL Meter")
    label_status.setText("Measuring...")
    label_db.setText("dB: --")

def btnB_wasPressed_event(state):
    global measuring

    measuring = False
    Widgets.fillScreen(0x000000)
    label_title.setText("SPL Meter")
    label_status.setText("Stopped")
    label_db.setText("dB: --")

def setup():
    global label_title, label_db, label_status

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(150)

    label_title = Widgets.Label("SPL Meter", 10, 20, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_db = Widgets.Label("dB: --", 10, 60, 1.5, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_status = Widgets.Label("Press A to Start", 10, 110, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)

    BtnA.setCallback(type=BtnA.CB_TYPE.WAS_PRESSED, cb=btnA_wasPressed_event)
    BtnB.setCallback(type=BtnB.CB_TYPE.WAS_PRESSED, cb=btnB_wasPressed_event)

    Mic.begin()
    Mic.setSampleRate(SAMPLE_RATE)

def loop():
    M5.update()

    if measuring:
        audio_data = array.array("h", [0] * BUFFER_SIZE)

        if Mic.record(audio_data, SAMPLE_RATE, False):
            db_value = estimate_db(audio_data)
            label_db.setText("dB: {:.1f}".format(db_value))

            if db_value < 60:
                label_status.setText("Sound: Low")
            elif db_value < 80:
                label_status.setText("Sound: Medium")
            else:
                label_status.setText("Sound: High")

        time.sleep(0.2)


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