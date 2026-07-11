import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import PBHUBUnit
from unit import Relay4Unit
import time

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None
pahub_5 = None
pbhub_0 = None
relay4_0 = None

label_title = None
label_status = None


# -------------------------------------------------
# Switch one relay on and off
# -------------------------------------------------
def operate_relay(channel):
    # Switch on the selected relay.
    # The corresponding LED follows the relay state.
    relay4_0.set_relay_state(channel, 1)

    label_status.setText("Relay {}: ON".format(channel))

    time.sleep(1)

    # Switch off the selected relay.
    relay4_0.set_relay_state(channel, 0)

    label_status.setText("Relay {}: OFF".format(channel))

    time.sleep(2)


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0, pahub_5, pbhub_0, relay4_0
    global label_title, label_status

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label("4 Relay Control", 45, 25, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_status = Widgets.Label("Initializing...", 55, 70, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat18)

    # Configure GPIO 10 as SCL and GPIO 9 as SDA.
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Select Port 5 of the PaHUB.
    pahub_5 = PAHUBUnit(i2c=i2c0, channel=5)

    # Initialize the PbHUB for the standard expansion template.
    pbhub_0 = PBHUBUnit(i2c0, 0x61)

    # Initialize the 4 Relay Unit connected to PaHUB Port 5.
    relay4_0 = Relay4Unit(pahub_5)

    # Set synchronous mode:
    # each LED follows its corresponding relay state.
    relay4_0.set_mode(Relay4Unit.SYNC_MODE)

    # Ensure all relays are switched off initially.
    relay4_0.set_relay_all(0)

    label_status.setText("Ready")
    time.sleep(1)


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    # Operate Relays 1 to 4 sequentially.
    for channel in range(1, 5):
        operate_relay(channel)


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
            # Switch off all relays when the program stops.
            if relay4_0 is not None:
                relay4_0.set_relay_all(0)

            from utility import print_error_msg
            print_error_msg(e)

        except ImportError:
            print("please update to latest firmware")