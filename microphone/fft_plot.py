import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Global variables
# -------------------------------------------------
running = False

# -------------------------------------------------
# Audio settings
# -------------------------------------------------
SAMPLE_RATE = 8000
BUFFER_SIZE = 512

# -------------------------------------------------
# LCD settings
# -------------------------------------------------
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135

GRAPH_X = 0
GRAPH_Y = 0
GRAPH_WIDTH = 240
GRAPH_HEIGHT = 135

# -------------------------------------------------
# Frequency bands
# Focus on human voice and general sound range
# -------------------------------------------------
FREQ_BANDS = [
    100, 200, 300, 400, 500, 600,
    700, 800, 900, 1000, 1200, 1400,
    1600, 1800, 2000, 2200, 2400, 2600,
    2800, 3000, 3200, 3400, 3600, 3800
]

BAND_COUNT = len(FREQ_BANDS)
BAR_WIDTH = GRAPH_WIDTH // BAND_COUNT

# Smoothing memory
previous_levels = [0] * BAND_COUNT

# Sensitivity setting
SCALE_FACTOR = 3.2		#2.2
NOISE_THRESHOLD = 5.5   #5.5


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

    # Remove DC offset
    total = 0
    for sample in samples:
        total = total + sample

    average = total / n

    index = 0

    for sample in samples:
        x = sample - average

        # Simple triangular window to reduce sudden edge effects
        if index < n / 2:
            window = index / (n / 2)
        else:
            window = (n - index) / (n / 2)

        x = x * window

        q0 = coeff * q1 - q2 + x
        q2 = q1
        q1 = q0

        index = index + 1

    power = q1 * q1 + q2 * q2 - q1 * q2 * coeff

    if power < 0:
        power = 0

    return power


# -------------------------------------------------
# Convert frequency power to display level
# -------------------------------------------------
def power_to_level(power):
    if power <= 1:
        return 0

    log_power = math.log10(power)

    # Ignore weak background noise
    if log_power < NOISE_THRESHOLD:
        return 0

    level = int((log_power - NOISE_THRESHOLD) * SCALE_FACTOR * 10)

    if level < 0:
        level = 0

    if level > GRAPH_HEIGHT:
        level = GRAPH_HEIGHT

    return level


# -------------------------------------------------
# Convert level to colour
# -------------------------------------------------
def level_to_colour(level):
    if level <= 5:
        return 0x000000      # black
    elif level <= 20:
        return 0x0000FF      # blue
    elif level <= 40:
        return 0x00FFFF      # cyan
    elif level <= 65:
        return 0x00FF00      # green
    elif level <= 90:
        return 0xFFFF00      # yellow
    elif level <= 115:
        return 0xFF8000      # orange
    else:
        return 0xFF0000      # red


# -------------------------------------------------
# Draw frequency domain bar graph
# -------------------------------------------------
def draw_frequency_graph(levels):
    # Clear the screen for fresh frequency plot
    Widgets.fillScreen(0x000000)

    for i in range(BAND_COUNT):
        level = levels[i]
        colour = level_to_colour(level)

        x = GRAPH_X + (i * BAR_WIDTH)
        bar_height = level

        y = GRAPH_Y + GRAPH_HEIGHT - bar_height

        # Draw vertical bar
        Widgets.Rectangle(
            x,
            y,
            BAR_WIDTH - 1,
            bar_height,
            colour,
            colour
        )


# -------------------------------------------------
# Get frequency levels from microphone
# -------------------------------------------------
def get_frequency_levels():
    global previous_levels

    audio_buffer = bytearray(BUFFER_SIZE)

    # Record one short block of microphone data
    Mic.record(audio_buffer, SAMPLE_RATE, True)

    levels = []

    for i in range(BAND_COUNT):
        power = goertzel(audio_buffer, FREQ_BANDS[i], SAMPLE_RATE)
        level = power_to_level(power)

        # Smooth the display so the bars do not jump too much
        smooth_level = int((previous_levels[i] * 0.5) + (level * 0.5))
        previous_levels[i] = smooth_level

        levels.append(smooth_level)

    return levels


# -------------------------------------------------
# Button A: Start display
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global running, previous_levels

    running = True
    previous_levels = [0] * BAND_COUNT
    Widgets.fillScreen(0x000000)


# -------------------------------------------------
# Button B: Stop display
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global running

    running = False
    Widgets.fillScreen(0x000000)


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(180)

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
        levels = get_frequency_levels()
        draw_frequency_graph(levels)

    time.sleep_ms(1)


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