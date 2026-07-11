import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Global variables
# -------------------------------------------------
running = False
x_pos = 0

label_title = None
label_status = None

# -------------------------------------------------
# Audio settings
# -------------------------------------------------
SAMPLE_RATE = 8000
BUFFER_SIZE = 256

# LCD settings
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135

GRAPH_X = 0
GRAPH_Y = 35
GRAPH_WIDTH = 240
GRAPH_HEIGHT = 95

# Frequency bands to display
FREQ_BANDS = [250, 500, 750, 1000, 1500, 2000, 2500, 3000]
BAND_COUNT = len(FREQ_BANDS)
BAND_HEIGHT = GRAPH_HEIGHT // BAND_COUNT


# -------------------------------------------------
# Frequency energy calculation using Goertzel method
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
        # Convert 8-bit unsigned audio sample to signed value
        x = sample - 128

        q0 = coeff * q1 - q2 + x
        q2 = q1
        q1 = q0

    power = q1 * q1 + q2 * q2 - q1 * q2 * coeff
    return power


# -------------------------------------------------
# Convert sound energy to colour
# -------------------------------------------------
def power_to_colour(power):
    # Adjust this value if the display is too sensitive or not sensitive enough
    scale = 50000

    level = int(power / scale)

    if level < 1:
        return 0x000000      # black - very low
    elif level < 3:
        return 0x0000FF      # blue - low
    elif level < 6:
        return 0x00FF00      # green - medium
    elif level < 10:
        return 0xFFFF00      # yellow - high
    else:
        return 0xFF0000      # red - very high


# -------------------------------------------------
# Draw one vertical spectrogram column
# -------------------------------------------------
def draw_spectrogram_column(powers):
    global x_pos

    for i in range(BAND_COUNT):
        colour = power_to_colour(powers[i])

        # Lower frequency bands are displayed near the bottom
        y = GRAPH_Y + GRAPH_HEIGHT - ((i + 1) * BAND_HEIGHT)

        Widgets.Rectangle(x_pos, y, 2, BAND_HEIGHT, colour, colour)

    x_pos = x_pos + 2

    # When the graph reaches the right side, clear and restart from the left
    if x_pos >= GRAPH_WIDTH:
        x_pos = 0
        Widgets.fillScreen(0x000000)
        label_title.setText("Spectrogram")
        label_status.setText("Running...")


# -------------------------------------------------
# Button A: Start spectrogram meter
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global running, x_pos

    running = True
    x_pos = 0

    Widgets.fillScreen(0x000000)
    label_title.setText("Spectrogram")
    label_status.setText("Running...")


# -------------------------------------------------
# Button B: Stop spectrogram meter
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global running

    running = False

    label_status.setText("Stopped")


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_title, label_status

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(150)

    label_title = Widgets.Label("Spectrogram", 10, 8, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_status = Widgets.Label("Press A to Start", 10, 28, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)

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

        # Record a short sound sample
        Mic.record(audio_buffer, SAMPLE_RATE, True)

        powers = []

        for freq in FREQ_BANDS:
            power = goertzel(audio_buffer, freq, SAMPLE_RATE)
            powers.append(power)

        draw_spectrogram_column(powers)

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
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("please update to latest firmware")