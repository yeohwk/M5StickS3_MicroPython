import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import ENVPROUnit
import time

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None
pahub_2 = None
envpro_0 = None

label_title = None
label_temperature = None
label_humidity = None
label_pressure = None
label_air_quality = None

last_update_time = 0

gas_baseline = 0
baseline_total = 0
baseline_samples = 0
BASELINE_SAMPLE_COUNT = 10

# -------------------------------------------------
# Estimate relative VOC concentration
# -------------------------------------------------
def estimate_voc_ppm(gas_resistance):
    global gas_baseline

    if gas_baseline <= 0 or gas_resistance <= 0:
        return 0

    # Lower gas resistance generally indicates
    # a stronger response to volatile compounds.
    ratio = gas_baseline / gas_resistance
    voc_ppm = (ratio - 1.0) * 100.0

    if voc_ppm < 0:
        voc_ppm = 0

    if voc_ppm > 999:
        voc_ppm = 999

    return voc_ppm

# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pahub_2, envpro_0
    global label_title, label_temperature
    global label_humidity, label_pressure
    global label_air_quality, last_update_time

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label("ENV-Pro Monitor", 45, 5, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_temperature = Widgets.Label("Temperature: --.- C", 10, 32, 1.0, 0xFF8000, 0x000000, Widgets.FONTS.Montserrat18)
    label_humidity = Widgets.Label("Humidity: --.- %RH", 10, 57, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_pressure = Widgets.Label("Pressure: ----.- hPa", 10, 82, 1.0, 0xFFFF00, 0x000000, Widgets.FONTS.Montserrat18)
    label_air_quality = Widgets.Label("VOC: ----.- ppm", 10, 107, 1.0, 0x00FF00, 0x000000, Widgets.FONTS.Montserrat18)

    # Configure GPIO 10 as SCL and GPIO 9 as SDA
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Select Port 2 of the PaHUB
    pahub_2 = PAHUBUnit(i2c=i2c0, channel=2)

    # Initialize the ENV-Pro Unit connected to PaHUB Port 2
    envpro_0 = ENVPROUnit(pahub_2)
    last_update_time = time.ticks_ms()

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_update_time
    global gas_baseline, baseline_total, baseline_samples

    M5.update()

    current_time = time.ticks_ms()

    if time.ticks_diff(current_time, last_update_time) >= 1000:
        last_update_time = current_time

        temperature = envpro_0.get_temperature()
        humidity = envpro_0.get_humidity()

        # get_pressure() already provides pressure in hPa
        pressure_hpa = envpro_0.get_pressure()

        gas_ohm = envpro_0.get_gas_resistance()

        # Establish an initial clean-air reference
        if baseline_samples < BASELINE_SAMPLE_COUNT:
            if gas_ohm > 0:
                baseline_total = baseline_total + gas_ohm
                baseline_samples = baseline_samples + 1

            if baseline_samples == BASELINE_SAMPLE_COUNT:
                gas_baseline = baseline_total / BASELINE_SAMPLE_COUNT

            voc_ppm = 0
        else:
            voc_ppm = estimate_voc_ppm(gas_ohm)

        label_temperature.setText("Temperature: {:.1f} C".format(temperature))
        label_humidity.setText("Humidity: {:.1f} %RH".format(humidity))
        label_pressure.setText("Pressure: {:.1f} hPa".format(pressure_hpa))

        if baseline_samples < BASELINE_SAMPLE_COUNT:
            label_air_quality.setText("VOC: Calibrating...")
        else:
            label_air_quality.setText("Est. VOC: {:.1f} ppm".format(voc_ppm))

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