import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import RFIDUnit
from unit import Relay4Unit
import time

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None

pahub_4 = None
pahub_5 = None

rfid_0 = None
relay4_0 = None

label_title = None
label_mode = None
label_status = None
label_uid = None
label_relay = None

enrolment_mode = False
authorised_uid = None

relay_active = False
relay_start_time = 0

card_latched = False

# RELAY_UNLOCK is 4-Relay channel 1 in the program
RELAY_UNLOCK = 1
RELAY_ON_TIME = 5000

# -------------------------------------------------
# Convert the RFID UID into readable text
# -------------------------------------------------
def uid_to_text(uid):
    if uid is None:
        return None

    if isinstance(uid, int):
        return "{:X}".format(uid)

    if isinstance(uid, str):
        return uid

    try:
        return "".join("{:02X}".format(value) for value in uid)
    except Exception:
        return str(uid)

# -------------------------------------------------
# Turn Relay 1 on
# -------------------------------------------------
def activate_relay():
    global relay_active, relay_start_time

    relay4_0.set_relay_state(RELAY_UNLOCK, 1)

    relay_active = True
    relay_start_time = time.ticks_ms()

    label_relay.setText("Lock Actuator: OFF")
    label_relay.setColor(0x00FF00, 0x000000)

# -------------------------------------------------
# Turn Relay 1 off
# -------------------------------------------------
def deactivate_relay():
    global relay_active

    relay4_0.set_relay_state(RELAY_UNLOCK, 0)

    relay_active = False

    label_relay.setText("Lock Actuator: ON")
    label_relay.setColor(0xFFFFFF, 0x000000)

# -------------------------------------------------
# Change between security and enrolment modes
# -------------------------------------------------
def change_mode():
    global enrolment_mode, card_latched

    enrolment_mode = not enrolment_mode
    card_latched = False

    deactivate_relay()

    if enrolment_mode:
        label_mode.setText("Mode: ENROLMENT")
        label_mode.setColor(0xFFFF00, 0x000000)

        label_status.setText("Present RFID tag")
        label_uid.setText("UID: Waiting...")

    else:
        label_mode.setText("Mode: SECURITY")
        label_mode.setColor(0x00FFFF, 0x000000)

        label_status.setText("Present authorised tag")

        if authorised_uid is None:
            label_uid.setText("No tag enrolled")
        else:
            label_uid.setText("Ready")

# -------------------------------------------------
# Process a detected RFID tag
# -------------------------------------------------
def process_rfid_tag():
    global authorised_uid, card_latched

    if card_latched:
        return

    if not rfid_0.is_new_card_present():
        return

    uid = rfid_0.read_card_uid()
    uid_text = uid_to_text(uid)

    if uid_text is None:
        return

    card_latched = True
    label_uid.setText("UID: " + uid_text)

    if enrolment_mode:
        authorised_uid = uid_text

        label_status.setText("Tag enrolled")
        label_status.setColor(0x00FF00, 0x000000)

    else:
        if authorised_uid is None:
            label_status.setText("No enrolled tag")
            label_status.setColor(0xFFFF00, 0x000000)

        elif uid_text == authorised_uid:
            label_status.setText("Access granted")
            label_status.setColor(0x00FF00, 0x000000)

            activate_relay()

        else:
            label_status.setText("Access denied")
            label_status.setColor(0xFF0000, 0x000000)

    # End communication with the current RFID tag
    rfid_0.close()

# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0
    global pahub_4, pahub_5
    global rfid_0, relay4_0
    global label_title, label_mode
    global label_status, label_uid, label_relay

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label("RFID Security Access", 10, 5, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_mode = Widgets.Label("Mode: SECURITY", 10, 35, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_status = Widgets.Label("Press A to enrol", 10, 58, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_uid = Widgets.Label("No tag enrolled", 10, 81, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_relay = Widgets.Label("Lock Actuator: ON", 10, 105, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)

    # Configure the I2C bus
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Select PaHUB Port 4 for the RFID 2 Unit
    pahub_4 = PAHUBUnit(i2c=i2c0, channel=4)

    # Select PaHUB Port 5 for the 4-Relay Unit
    pahub_5 = PAHUBUnit(i2c=i2c0, channel=5)

    # Initialize the RFID 2 Unit
    rfid_0 = RFIDUnit(pahub_4)

    # Initialize the 4-Relay Unit
    relay4_0 = Relay4Unit(pahub_5)
    relay4_0.set_mode(Relay4Unit.SYNC_MODE)
    relay4_0.set_relay_all(0)

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global relay_active, card_latched

    M5.update()

    # Button A switches between the two modes
    if BtnA.wasClicked():
        change_mode()
        time.sleep_ms(200)

    # Read and process an RFID tag
    process_rfid_tag()

    # Allow another reading after the tag is removed
    if not rfid_0.is_new_card_present():
        card_latched = False

    # Turn Relay 1 off after five seconds
    if relay_active:
        if time.ticks_diff(time.ticks_ms(), relay_start_time) >= RELAY_ON_TIME:
            deactivate_relay()
            label_status.setText("Present authorised tag")
            label_status.setColor(0xFFFFFF, 0x000000)

    time.sleep_ms(50)

# -------------------------------------------------
# Do not modify
# -------------------------------------------------
if __name__ == "__main__":
    try:
        setup()

        while True:
            loop()

    except (Exception, KeyboardInterrupt) as e:
        try:
            if relay4_0 is not None:
                relay4_0.set_relay_all(0)

            from utility import print_error_msg
            print_error_msg(e)

        except ImportError:
            print("please update to latest firmware")