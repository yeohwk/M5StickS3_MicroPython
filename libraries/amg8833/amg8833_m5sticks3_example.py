import M5
from M5 import *
from hardware import I2C, Pin
import time

from amg8833 import AMG8833, __version__


sensor = None
last_info = None


# -------------------------------------------------
# Update one small value field only
# -------------------------------------------------
def update_value(text, x, y, width=45, height=16):
    M5.Lcd.fillRect(
        x,
        y,
        width,
        height,
        0x0000
    )

    M5.Lcd.setTextColor(
        0xFFFF,
        0x0000
    )

    M5.Lcd.drawString(
        text,
        x,
        y
    )


# -------------------------------------------------
# Setup
# -------------------------------------------------
def setup():
    global sensor
    global last_info

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    # Quick colour check: blue, cyan, green, yellow, red.
    M5.Lcd.fillRect(0, 0, 48, 128, 0x0000FF)
    M5.Lcd.fillRect(48, 0, 48, 128, 0x00FFFF)
    M5.Lcd.fillRect(96, 0, 48, 128, 0x00FF00)
    M5.Lcd.fillRect(144, 0, 48, 128, 0xFFFF00)
    M5.Lcd.fillRect(192, 0, 48, 128, 0xFF0000)
    time.sleep_ms(1200)
    Widgets.fillScreen(0x000000)

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

    # Draw the right-side labels once only.
    M5.Lcd.setTextColor(
        0xFFFF,
        0x0000
    )

    M5.Lcd.drawString("MAX", 195, 4)
    M5.Lcd.drawString("MIN", 195, 43)
    M5.Lcd.drawString("AVG", 195, 82)

    print("AMG8833 library version:", __version__)

    last_info = None


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_info

    M5.update()

    # Rainbow scale: cold blue, then cyan, green, yellow, and hot red.
    # The thermal-image area is not cleared between frames.
    stats = sensor.draw_thermal_image(
        lcd=M5.Lcd,
        x=0,
        y=0,
        width=192,
        height=128,
        minimum=20.0,
        maximum=31.0,
        refresh=True,
        show_hotspot=True,
        clear_background=False,
        only_changed=True,
        color_steps=24
    )

    current_info = (
        round(stats["maximum"], 1),
        round(stats["minimum"], 1),
        round(stats["average"], 1)
    )

    # Redraw the numerical fields only when a displayed value changes.
    if current_info != last_info:
        update_value("{:.1f}".format(current_info[0]), 195, 20)
        update_value("{:.1f}".format(current_info[1]), 195, 59)
        update_value("{:.1f}".format(current_info[2]), 195, 98)
        last_info = current_info

    row, column = stats["maximum_location"]

    print(
        "Minimum: {:.2f} C | Maximum: {:.2f} C at row {}, column {} | Average: {:.2f} C"
        .format(
            stats["minimum"],
            stats["maximum"],
            row,
            column,
            stats["average"]
        )
    )

    time.sleep_ms(200)


# -------------------------------------------------
# Program entry point
# -------------------------------------------------
if __name__ == "__main__":
    setup()

    while True:
        loop()
