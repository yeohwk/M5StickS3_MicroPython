import os, sys, io
import M5
from M5 import *
import time

recording = False
playing = False
recorded = False

rec_data = None

label_title = None
label_status = None
label_info = None

SAMPLE_RATE = 8000
MAX_RECORD_TIME = 10
BUFFER_SIZE = SAMPLE_RATE * MAX_RECORD_TIME

def btnA_wasPressed_event(state):
    global recording, playing, recorded, rec_data

    if recording:
        return

    if playing:
        return

    recorded = False
    recording = True

    Widgets.fillScreen(0x000000)
    label_title.setText("Sound Recorder")
    label_status.setText("Recording...")
    label_info.setText("Max: 10 seconds")

    # Each new recording overwrites the previous recording
    rec_data = bytearray(BUFFER_SIZE)

    Mic.begin()
    Mic.record(rec_data, SAMPLE_RATE, False)

def btnB_wasPressed_event(state):
    global playing, recording, recorded

    if recording:
        return

    if not recorded:
        label_status.setText("No recording")
        label_info.setText("Press A first")
        return

    if not playing:
        playing = True
        label_status.setText("Playing...")
        label_info.setText("Please wait")

        Speaker.begin()
        Speaker.setVolumePercentage(80)
        Speaker.playRaw(rec_data, SAMPLE_RATE)
    else:
        Speaker.stop()
        playing = False
        label_status.setText("Playback stopped")
        label_info.setText("Press B to replay")

def setup():
    global label_title, label_status, label_info, rec_data

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(150)

    label_title = Widgets.Label("Sound Recorder", 10, 20, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_status = Widgets.Label("Press A to record", 10, 65, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_info = Widgets.Label("Press B to play", 10, 105, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)

    rec_data = bytearray(BUFFER_SIZE)

    BtnA.setCallback(type=BtnA.CB_TYPE.WAS_PRESSED, cb=btnA_wasPressed_event)
    BtnB.setCallback(type=BtnB.CB_TYPE.WAS_PRESSED, cb=btnB_wasPressed_event)


def loop():
    global recording, playing, recorded

    M5.update()

    if recording:
        if not Mic.isRecording():
            recording = False
            recorded = True
            Mic.end()

            label_status.setText("Recording saved")
            label_info.setText("Press B to play")

    if playing:
        if not Speaker.isPlaying():
            playing = False
            Speaker.end()

            label_status.setText("Playback done")
            label_info.setText("Press B to replay")

    time.sleep_ms(100)


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