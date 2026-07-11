import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Global variables
# -------------------------------------------------
running = False
spectrogram_history = []

# Button B cycles sensitivity
sensitivity_index = 1

# Lower threshold = more sensitive
# Higher threshold = less sensitive
#NOISE_THRESHOLDS = [5.8, 6.2, 6.6, 7.0]
NOISE_THRESHOLDS = [5.5, 5.5, 5.5, 5.5]

#SCALING_FACTORS = [2.8, 3.2, 3.6, 4.0]
SCALING_FACTORS = [4, 4, 4, 4]

# -------------------------------------------------
# Audio settings
# -------------------------------------------------
SAMPLE_RATE = 8000
BUFFER_SIZE = 512

# -------------------------------------------------
# Full LCD settings
# -------------------------------------------------
GRAPH_X = 0
GRAPH_Y = 0
GRAPH_WIDTH = 240
GRAPH_HEIGHT = 135

COLUMN_WIDTH = 2
MAX_COLUMNS = GRAPH_WIDTH // COLUMN_WIDTH

# Focus on human speech range
FREQ_BANDS = [
    300, 400, 500, 600, 700, 800,
    900, 1000, 1100, 1200, 1300, 1400,
    1500, 1600, 1800, 2000, 2200, 2400,
    2600, 2800, 3000, 3200, 3400
]

BAND_COUNT = len(FREQ_BANDS)

previous_levels = [0] * BAND_COUNT


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

    total = 0
    for sample in samples:
        total = total + sample

    average = total / n

    index = 0

    for sample in samples:
        x = sample - average

        # Triangular window
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
# Convert power to colour level
# -------------------------------------------------
def power_to_level(power):
    threshold = NOISE_THRESHOLDS[sensitivity_index]
    scale = SCALING_FACTORS[sensitivity_index]

    if power <= 1:
        return 0

    log_power = math.log10(power)

    # Ignore weak background noise
    if log_power < threshold:
        return 0

    # Convert remaining signal into visible colour level
    level = int((log_power - threshold) * scale * 4)

    if level < 0:
        level = 0

    if level > 15:
        level = 15

    return level


# -------------------------------------------------
# Convert level to LCD colour
# -------------------------------------------------
def level_to_colour(level):
    if level <= 0:
        return 0x000000      # black
    elif level <= 2:
        return 0x000033      # very dark blue
    elif level <= 4:
        return 0x0000AA      # blue
    elif level <= 6:
        return 0x00AAAA      # cyan
    elif level <= 8:
        return 0x00AA00      # green
    elif level <= 10:
        return 0xAAAA00      # dark yellow
    elif level <= 12:
        return 0xFF8000      # orange
    else:
        return 0xFF0000      # red


# -------------------------------------------------
# Get one spectrogram column
# -------------------------------------------------
def get_spectrogram_column():
    global previous_levels

    audio_buffer = bytearray(BUFFER_SIZE)

    Mic.record(audio_buffer, SAMPLE_RATE, True)

    levels = []

    for i in range(BAND_COUNT):
        power = goertzel(audio_buffer, FREQ_BANDS[i], SAMPLE_RATE)
        level = power_to_level(power)

        # Less smoothing so speech appears faster
        smooth_level = int((previous_levels[i] * 0.45) + (level * 0.55))

        if smooth_level <= 1:
            smooth_level = 0

        previous_levels[i] = smooth_level
        levels.append(smooth_level)

    return levels


# -------------------------------------------------
# Update spectrogram history
# -------------------------------------------------
def update_history(levels):
    global spectrogram_history

    spectrogram_history.append(levels)

    if len(spectrogram_history) > MAX_COLUMNS:
        spectrogram_history.pop(0)


# -------------------------------------------------
# Draw spectrogram
# -------------------------------------------------
def draw_spectrogram():
    column_count = len(spectrogram_history)
    blank_columns = MAX_COLUMNS - column_count

    for col in range(MAX_COLUMNS):
        x = GRAPH_X + (col * COLUMN_WIDTH)

        if col < blank_columns:
            levels = None
        else:
            history_index = col - blank_columns
            levels = spectrogram_history[history_index]

        for band in range(BAND_COUNT):
            y1 = int(GRAPH_Y + GRAPH_HEIGHT - ((band + 1) * GRAPH_HEIGHT / BAND_COUNT))
            y2 = int(GRAPH_Y + GRAPH_HEIGHT - (band * GRAPH_HEIGHT / BAND_COUNT))
            band_height = y2 - y1

            if band_height < 1:
                band_height = 1

            if levels is None:
                colour = 0x000000
            else:
                colour = level_to_colour(levels[band])

            Widgets.Rectangle(
                x,
                y1,
                COLUMN_WIDTH,
                band_height,
                colour,
                colour
            )


# -------------------------------------------------
# Button A: Start or stop spectrogram
# -------------------------------------------------
def btnA_wasPressed_event(state):
    global running, spectrogram_history, previous_levels

    if not running:
        running = True
        spectrogram_history = []
        previous_levels = [0] * BAND_COUNT
        Widgets.fillScreen(0x000000)
    else:
        running = False


# -------------------------------------------------
# Button B: Change sensitivity
# -------------------------------------------------
def btnB_wasPressed_event(state):
    global sensitivity_index, spectrogram_history, previous_levels

    sensitivity_index = sensitivity_index + 1

    if sensitivity_index >= len(NOISE_THRESHOLDS):
        sensitivity_index = 0

    spectrogram_history = []
    previous_levels = [0] * BAND_COUNT
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
        levels = get_spectrogram_column()
        update_history(levels)
        draw_spectrogram()

    time.sleep_ms(5)


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