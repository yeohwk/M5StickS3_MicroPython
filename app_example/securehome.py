import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import PBHUBUnit
from unit import RFIDUnit
from unit import Relay4Unit
import time

# -------------------------------------------------
# Global variables
# -------------------------------------------------
i2c0 = None

pahub_4 = None
pahub_5 = None
pbhub_0 = None

rfid_0 = None
relay4_0 = None

label_title = None
label_mode = None
label_status = None
label_timer = None
label_tags = None
label_alarm = None

# -------------------------------------------------
# Hardware connections
# -------------------------------------------------
DUAL_BUTTON_PORT = 0
RED_BUTTON_PIN = 0
BLUE_BUTTON_PIN = 1

PIR_PORT = 1
PIR_SIGNAL_PIN = 1

RFID_PAHUB_PORT = 4
RELAY_PAHUB_PORT = 5

# Relay 1 controls the external alarm
ALARM_RELAY = 1

# -------------------------------------------------
# System settings
# -------------------------------------------------
MAX_TAGS = 2
COUNTDOWN_TIME = 10000
BUZZER_FREQUENCY = 2000
BUZZER_INTERVAL = 600

# -------------------------------------------------
# System operating modes
# -------------------------------------------------
MODE_DISARMED = 0
MODE_ENROLMENT = 1
MODE_ARMED = 2
MODE_COUNTDOWN = 3
MODE_ALARM = 4

system_mode = MODE_DISARMED

authorised_uids = []

countdown_start_time = 0
last_countdown_second = -1

alarm_active = False
last_buzzer_time = 0

previous_red_state = 1
previous_blue_state = 1

card_latched = False

# -------------------------------------------------
# Convert an RFID UID into readable text
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
# Update the number of enrolled tags
# -------------------------------------------------
def update_tag_display():
    label_tags.setText("Tags enrolled: {}/{}" .format(len(authorised_uids), MAX_TAGS))

# -------------------------------------------------
# Activate the external alarm and buzzer
# -------------------------------------------------
def activate_alarm():
    global alarm_active
    global last_buzzer_time

    relay4_0.set_relay_state(ALARM_RELAY, 1)

    alarm_active = True
    last_buzzer_time = 0

    label_mode.setText("Mode: ALARM")
    label_mode.setColor(0xFF0000, 0x000000)

    label_status.setText("INTRUDER ALERT")
    label_status.setColor(0xFF0000, 0x000000)

    label_timer.setText("Present authorised tag")
    label_alarm.setText("Alarm: ON")
    label_alarm.setColor(0xFF0000, 0x000000)
    print("ALARM ACTIVATED")

# -------------------------------------------------
# Deactivate the external alarm and buzzer
# -------------------------------------------------
def deactivate_alarm():
    global alarm_active

    relay4_0.set_relay_state(ALARM_RELAY, 0)
    Speaker.stop()

    alarm_active = False

    label_alarm.setText("Alarm: OFF")
    label_alarm.setColor(0x00FF00, 0x000000)
    print("Alarm deactivated")

# -------------------------------------------------
# Return the system to disarmed mode
# -------------------------------------------------
def disarm_system():
    global system_mode
    global last_countdown_second

    deactivate_alarm()

    system_mode = MODE_DISARMED
    last_countdown_second = -1

    label_mode.setText("Mode: DISARMED")
    label_mode.setColor(0x00FF00, 0x000000)

    label_status.setText("Red: Arm  Blue: Enrol")
    label_status.setColor(0xFFFFFF, 0x000000)

    label_timer.setText("System ready")
    print("System disarmed")

# -------------------------------------------------
# Arm the security system
# -------------------------------------------------
def arm_system():
    global system_mode

    if len(authorised_uids) == 0:
        label_status.setText("Enrol RFID tag first")
        label_status.setColor(0xFFFF00, 0x000000)

        print("Cannot arm: no RFID tag enrolled")
        return

    deactivate_alarm()
    system_mode = MODE_ARMED
    
    label_mode.setText("Mode: ARMED")
    label_mode.setColor(0xFFFF00, 0x000000)
    label_status.setText("Monitoring for motion")
    label_status.setColor(0xFFFFFF, 0x000000)
    label_timer.setText("Present tag to disarm")
    print("System armed")

# -------------------------------------------------
# Enter RFID enrolment mode
# -------------------------------------------------
def start_enrolment():
    global system_mode
    global card_latched

    if system_mode != MODE_DISARMED:
        return

    if len(authorised_uids) >= MAX_TAGS:
        label_status.setText("Maximum 2 tags reached")
        label_status.setColor(0xFFFF00, 0x000000)
        print("Enrolment failed: tag limit reached")
        return

    system_mode = MODE_ENROLMENT
    card_latched = False

    label_mode.setText("Mode: ENROLMENT")
    label_mode.setColor(0x00FFFF, 0x000000)
    label_status.setText("Present RFID tag")
    label_status.setColor(0xFFFFFF, 0x000000)
    label_timer.setText("Waiting for tag...")
    print("RFID enrolment mode")

# -------------------------------------------------
# Begin the motion-entry countdown
# -------------------------------------------------
def start_countdown():
    global system_mode
    global countdown_start_time
    global last_countdown_second

    system_mode = MODE_COUNTDOWN
    countdown_start_time = time.ticks_ms()
    last_countdown_second = -1

    label_mode.setText("Mode: COUNTDOWN")
    label_mode.setColor(0xFF8000, 0x000000)
    label_status.setText("Motion detected")
    label_status.setColor(0xFF8000, 0x000000)
    print("Motion detected: countdown started")

# -------------------------------------------------
# Check whether an RFID tag is authorised
# -------------------------------------------------
def is_authorised(uid_text):
    return uid_text in authorised_uids

# -------------------------------------------------
# Process a detected RFID tag
# -------------------------------------------------
def process_rfid_tag():
    global system_mode
    global card_latched

    if card_latched:
        return

    if not rfid_0.is_new_card_present():
        return

    uid = rfid_0.read_card_uid()
    uid_text = uid_to_text(uid)

    if uid_text is None:
        return

    card_latched = True

    print("RFID UID:", uid_text)

    # Enrol a new RFID tag
    if system_mode == MODE_ENROLMENT:

        if uid_text in authorised_uids:
            label_status.setText("Tag already enrolled")
            label_status.setColor(0xFFFF00, 0x000000)
            print("Tag already enrolled")

        elif len(authorised_uids) < MAX_TAGS:
            authorised_uids.append(uid_text)

            label_status.setText("Tag enrolled")
            label_status.setColor(0x00FF00, 0x000000)
            label_timer.setText("UID: " + uid_text)
            update_tag_display()
            print("Tag enrolled successfully")

        time.sleep_ms(800)
        disarm_system()

    # An authorised tag disarms the system
    elif system_mode in (
        MODE_ARMED,
        MODE_COUNTDOWN,
        MODE_ALARM
    ):

        if is_authorised(uid_text):
            label_status.setText("Authorised tag")
            label_status.setColor(0x00FF00, 0x000000)
            print("Access authorised")
            disarm_system()

        else:
            label_status.setText("Invalid RFID tag")
            label_status.setColor(0xFF0000, 0x000000)
            print("Access denied")

    rfid_0.close()


# -------------------------------------------------
# Read the two buttons
# -------------------------------------------------
def process_buttons():
    global previous_red_state
    global previous_blue_state

    red_state = pbhub_0.digital_read(DUAL_BUTTON_PORT, RED_BUTTON_PIN)

    blue_state = pbhub_0.digital_read(DUAL_BUTTON_PORT, BLUE_BUTTON_PIN)

    # Red button: arm the system
    if red_state == 0 and previous_red_state == 1:
        if system_mode == MODE_DISARMED:
            arm_system()

    # Blue button: enrol one RFID tag
    if blue_state == 0 and previous_blue_state == 1:
        if system_mode == MODE_DISARMED:
            start_enrolment()

    previous_red_state = red_state
    previous_blue_state = blue_state


# -------------------------------------------------
# Read the PIR motion sensor
# -------------------------------------------------
def process_motion_sensor():
    motion_state = pbhub_0.digital_read(PIR_PORT, PIR_SIGNAL_PIN)

    if system_mode == MODE_ARMED and motion_state == 1:
        start_countdown()


# -------------------------------------------------
# Update the 10-second countdown
# -------------------------------------------------
def process_countdown():
    global system_mode
    global last_countdown_second

    if system_mode != MODE_COUNTDOWN:
        return

    elapsed = time.ticks_diff(time.ticks_ms(), countdown_start_time)
    remaining_ms = COUNTDOWN_TIME - elapsed
    remaining_seconds = (remaining_ms + 999) // 1000

    if remaining_seconds < 0:
        remaining_seconds = 0

    if remaining_seconds != last_countdown_second:
        last_countdown_second = remaining_seconds
        label_timer.setText("Alarm in: {} seconds" .format(remaining_seconds))
        print("Alarm countdown:", remaining_seconds, "seconds")

    if elapsed >= COUNTDOWN_TIME:
        system_mode = MODE_ALARM
        activate_alarm()


# -------------------------------------------------
# Produce a repeating alarm tone
# -------------------------------------------------
def process_buzzer():
    global last_buzzer_time

    if not alarm_active:
        return

    current_time = time.ticks_ms()

    if time.ticks_diff(current_time, last_buzzer_time) >= BUZZER_INTERVAL:
        last_buzzer_time = current_time
        Speaker.tone(BUZZER_FREQUENCY, 400)


# -------------------------------------------------
# Allow the RFID reader to detect another tag
# -------------------------------------------------
def reset_card_latch():
    global card_latched

    if not rfid_0.is_new_card_present():
        card_latched = False


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0
    global pahub_4, pahub_5, pbhub_0
    global rfid_0, relay4_0
    global label_title, label_mode
    global label_status, label_timer
    global label_tags, label_alarm

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label("SecureHome", 65, 3, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat18)
    label_mode = Widgets.Label("Mode: DISARMED", 8, 29, 1.0, 0x00FF00, 0x000000, Widgets.FONTS.Montserrat14)
    label_status = Widgets.Label("Red: Arm  Blue: Enrol", 8, 50, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_timer = Widgets.Label("System ready", 8, 71, 1.0, 0xFFFFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_tags = Widgets.Label("Tags enrolled: 0/2", 8, 92, 1.0, 0x00FFFF, 0x000000, Widgets.FONTS.Montserrat14)
    label_alarm = Widgets.Label("Alarm: OFF", 8, 113, 1.0, 0x00FF00, 0x000000, Widgets.FONTS.Montserrat14)

    # Configure the shared I2C bus
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=100000)

    # Initialize the PbHUB
    pbhub_0 = PBHUBUnit(i2c0, 0x61)

    # Select PaHUB Port 4 for the RFID 2 Unit
    pahub_4 = PAHUBUnit(i2c=i2c0, channel=RFID_PAHUB_PORT)

    # Select PaHUB Port 5 for the 4-Relay Unit
    pahub_5 = PAHUBUnit(i2c=i2c0, channel=RELAY_PAHUB_PORT)

    # Initialize the RFID 2 Unit
    rfid_0 = RFIDUnit(pahub_4)

    # Initialize the 4-Relay Unit
    relay4_0 = Relay4Unit(pahub_5)
    relay4_0.set_mode(Relay4Unit.SYNC_MODE)
    relay4_0.set_relay_all(0)

    # Initialize the embedded buzzer
    Speaker.begin()
    Speaker.setVolume(180)
    Speaker.stop()

    print("SecureHome RFID Motion Alarm System")
    print("-----------------------------------")
    print("Dual-Button Unit : PbHUB Port 0")
    print("  Red button     : Signal pin 0")
    print("  Blue button    : Signal pin 1")
    print("PIR Sensor Unit  : PbHUB Port 1, signal pin 1")
    print("RFID 2 Unit      : PaHUB Port 4")
    print("4-Relay Unit     : PaHUB Port 5")
    print("External alarm   : Relay 1")
    print("Local alarm      : M5StickS3 embedded buzzer")
    print("-----------------------------------")
    print("System disarmed")


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    process_buttons()
    process_motion_sensor()
    process_rfid_tag()
    process_countdown()
    process_buzzer()
    reset_card_latch()

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

            Speaker.stop()

            from utility import print_error_msg
            print_error_msg(e)

        except ImportError:
            print("Please update to the latest firmware")