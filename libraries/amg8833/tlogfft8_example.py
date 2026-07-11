import M5
from M5 import *
from hardware import I2C, Pin
import time

from amg8833 import AMG8833
from tlogfft8 import ThermalLogFFT8


sensor = None
logfft = None


def setup():
    global sensor
    global logfft

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    i2c0 = I2C(
        0,
        scl=Pin(10),
        sda=Pin(9),
        freq=400000
    )

    sensor = AMG8833(
        i2c0,
        address=0x69,
        emissivity=0.95,
        frame_rate=10
    )

    sensor.set_moving_average(True)

    logfft = ThermalLogFFT8(
        input_normalization=ThermalLogFFT8.NORMALIZE_MINMAX,
        output_normalization=ThermalLogFFT8.OUTPUT_MINMAX,
        remove_dc=True
    )

    M5.Lcd.setTextColor(
        0xFFFFFF,
        0x000000
    )

    M5.Lcd.drawString(
        "8x8 Thermal Log-FFT",
        8,
        4
    )


def loop():
    M5.update()

    # Read the 8 x 8 AMG8833 thermal frame as 64 flattened values.
    thermal_8x8 = sensor.get_flattened_data(
        refresh=True
    )

    # Convert the 8 x 8 thermal frame into a 64-value log-FFT vector.
    logfft_vector = logfft.transform(
        thermal_8x8,
        shift=True
    )

    # Convert to byte values if the vector is used by a byte-based AI model.
    logfft_bytes = logfft.transform_to_bytes(
        thermal_8x8,
        shift=True
    )

    print("Log-FFT vector length:", len(logfft_vector))
    print(
        "First 8 float values:",
        [
            round(value, 3)
            for value in logfft_vector[:8]
        ]
    )
    print(
        "64 byte values:",
        list(logfft_bytes[:64])
    )

    M5.Lcd.fillRect(
        8,
        30,
        220,
        80,
        0x000000
    )

    M5.Lcd.drawString(
        "Vector size: {}".format(
            len(logfft_vector)
        ),
        8,
        30
    )

    M5.Lcd.drawString(
        "Byte size: {}".format(
            len(logfft_bytes)
        ),
        8,
        50
    )

    M5.Lcd.drawString(
        "Max byte: {}".format(
            max(logfft_bytes)
        ),
        8,
        70
    )

    M5.Lcd.drawString(
        "Min byte: {}".format(
            min(logfft_bytes)
        ),
        8,
        90
    )

    time.sleep_ms(1000)


if __name__ == "__main__":
    setup()

    while True:
        loop()
