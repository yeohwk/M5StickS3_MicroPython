import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Global variables
# -------------------------------------------------
running = False

label_title = None
label_status = None
label_band0 = None
label_band1 = None
label_band2 = None
label_band3 = None
label_band4 = None

# -------------------------------------------------
# Audio settings
# -------------------------------------------------
SAMPLE_RATE = 8000
BUFFER_SIZE = 256

# Frequency bands to monitor
FREQ_BANDS = [250, 500, 1000, 2000, 3000]


# -------------------------------------------------
# Goertzel frequency energy calculation
# -------------------------------------------------
def goertzel(samples, target_freq, sample_rate):
    n = len(samples)

    k = int(0.5 + ((n * target_freq) / sample_rate))
    omega = (2.0 * math.pi * k) / n
    coeff = 2.0 * math.cos(omega)

    q0 = 0
    q1 = 0
    q2 = 0

    for sample in samples:
        # Convert unsigned 8-bit audio sample to signed value
        x = sample - 128

        q0 = coeff * q1 - q2 + x
        q2 = q1
        q1 = q0

    power = q1 * q1 + q2 * q2 - q1 * q2 * coeff
    return power


# -------------------------------------------------
# Convert power value into simple bar display
# -------------------------------------------------
def make_bar(power):
    # Adjust this scale value if the bars are too short or too long
    scale = 50000

    level = int(power / scale)

    if level > 12:
        level = 12

    if level < 0:
        level = 0

    return "#" * level


# -------------------------------------------------
# Button A: Start meter
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global running

    running = True
    Widgets.fillScreen(0x000000)

    label_title.setText("Spectrogram")
    label_status.setText("Running...")


# -------------------------------------------------
# Button B: Stop meter
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global running

    running = False
    Widgets.fillScreen(0x000000)

    label_title.setText("Spectrogram")
    label_status.setText("Stopped")
    label_band0.setText("250Hz :")
    label_band1.setText("500Hz :")
    label_band2.setText("1kHz  :")
    label_band3.setText("2kHz  :")
    label_band4.setText("3kHz  :")


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_title, label_status
    global label_band0, label_band1, label_band2, label_band3, label_band4

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(150)

    label_title = Widgets.Label("Spectrogram", 10, 10, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_status = Widgets.Label("Press A to Start", 10, 35, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)

    label_band0 = Widgets.Label("250Hz :", 10, 65, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_band1 = Widgets.Label("500Hz :", 10, 90, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_band2 = Widgets.Label("1kHz  :", 10, 115, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_band3 = Widgets.Label("2kHz  :", 10, 140, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_band4 = Widgets.Label("3kHz  :", 10, 165, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)

    BtnA.setCallback(type=BtnA.CB_TYPE.WAS_PRESSED, cb=btnA_wasPressed_event)
    BtnB.setCallback(type=BtnB.CB_TYPE.WAS_PRESSED, cb=btnB_wasPressed_event)

    Mic.begin()
    Mic.setSampleRate(SAMPLE_RATE)


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    if running:
        audio_buffer = bytearray(BUFFER_SIZE)

        # Record a short audio sample
        Mic.record(audio_buffer, SAMPLE_RATE, True)

        powers = []

        for freq in FREQ_BANDS:
            power = goertzel(audio_buffer, freq, SAMPLE_RATE)
            powers.append(power)

        label_band0.setText("250Hz : " + make_bar(powers[0]))
        label_band1.setText("500Hz : " + make_bar(powers[1]))
        label_band2.setText("1kHz  : " + make_bar(powers[2]))
        label_band3.setText("2kHz  : " + make_bar(powers[3]))
        label_band4.setText("3kHz  : " + make_bar(powers[4]))

    time.sleep_ms(100)


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