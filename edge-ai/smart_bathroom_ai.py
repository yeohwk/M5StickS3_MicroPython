import os, sys, io
import M5
from M5 import *
from hardware import Pin
from hardware import I2C
from unit import PAHUBUnit
from unit import PBHUBUnit
from unit import ENVPROUnit
from unit import Relay4Unit
import time


# -------------------------------------------------
# Global device objects
# -------------------------------------------------
i2c0 = None

pahub_2 = None
pahub_5 = None
pbhub_0 = None

envpro_0 = None
relay4_0 = None


# -------------------------------------------------
# LCD labels
# -------------------------------------------------
label_title = None
label_occupancy = None
label_environment = None
label_light = None
label_air = None
label_outputs = None
label_ai = None


# -------------------------------------------------
# Hardware connections
# -------------------------------------------------
ENVPRO_PAHUB_PORT = 2
RELAY_PAHUB_PORT = 5

PIR_PORT = 1
PIR_SIGNAL_PIN = 1

LIGHT_SENSOR_PORT = 2

# Relay assignments
LIGHT_RELAY = 1
FAN_RELAY = 2


# -------------------------------------------------
# Light sensor settings
# -------------------------------------------------
ADC_MAX = 4095
MAX_LUX = 1000.0

LIGHT_ON_THRESHOLD_LUX = 250.0
LIGHT_OFF_THRESHOLD_LUX = 350.0


# -------------------------------------------------
# Environmental thresholds
# -------------------------------------------------
TEMPERATURE_HIGH = 30.0
TEMPERATURE_RECOVERY = 27.0

HUMIDITY_HIGH = 75.0
HUMIDITY_RECOVERY = 68.0


# -------------------------------------------------
# Air-quality settings
# -------------------------------------------------
GAS_BASELINE_SAMPLES = 20

GAS_ALERT_RATIO = 0.70
GAS_RECOVERY_RATIO = 0.80

BUZZER_FREQUENCY = 2000
BUZZER_INTERVAL = 5000


# -------------------------------------------------
# Timing settings
# -------------------------------------------------
SENSOR_UPDATE_INTERVAL = 1000
LIGHT_OFF_DELAY = 10000
OCCUPANCY_HOLD_TIME = 30000
ACTIVITY_WINDOW = 60000


# -------------------------------------------------
# Edge AI settings
# -------------------------------------------------
AI_UPDATE_INTERVAL = 2000

AI_VACANT_NORMAL = "VACANT_NORMAL"
AI_OCCUPIED_NORMAL = "OCCUPIED_NORMAL"
AI_STEAMY_HUMID = "STEAMY_HUMID"
AI_POOR_AIR = "POOR_AIR"
AI_CALIBRATING = "CALIBRATING"

ai_classification = AI_CALIBRATING
ai_confidence = 0.0
last_ai_update = 0


# -------------------------------------------------
# Edge AI class prototypes
#
# Feature order:
# 0: Temperature
# 1: Humidity
# 2: Gas response
# 3: Light intensity
# 4: Motion activity
# 5: Occupancy
# -------------------------------------------------
AI_PROTOTYPES = {
    AI_VACANT_NORMAL: [
        0.35,
        0.40,
        0.05,
        0.50,
        0.00,
        0.00
    ],

    AI_OCCUPIED_NORMAL: [
        0.45,
        0.50,
        0.10,
        0.45,
        0.35,
        1.00
    ],

    AI_STEAMY_HUMID: [
        0.65,
        0.85,
        0.20,
        0.35,
        0.55,
        1.00
    ],

    AI_POOR_AIR: [
        0.55,
        0.65,
        0.90,
        0.40,
        0.30,
        0.70
    ]
}


# -------------------------------------------------
# Sensor values
# -------------------------------------------------
temperature = 0.0
humidity = 0.0
pressure_hpa = 0.0
gas_resistance = 0.0
light_lux = 0.0


# -------------------------------------------------
# Occupancy and activity states
# -------------------------------------------------
occupied = False
previous_motion_state = 0
last_motion_time = 0

motion_event_count = 0
activity_window_start = 0
average_motion_activity = 0


# -------------------------------------------------
# Output states
# -------------------------------------------------
light_on = False
fan_on = False
gas_alert = False

light_off_countdown = False
light_off_start_time = 0


# -------------------------------------------------
# Timing variables
# -------------------------------------------------
last_sensor_update = 0
last_buzzer_time = 0


# -------------------------------------------------
# Gas baseline variables
# -------------------------------------------------
gas_baseline = 0.0
gas_baseline_total = 0.0
gas_baseline_count = 0


# -------------------------------------------------
# Limit a value to the range from 0.0 to 1.0
# -------------------------------------------------
def clamp01(value):
    if value < 0.0:
        return 0.0

    if value > 1.0:
        return 1.0

    return value


# -------------------------------------------------
# Convert Light Sensor reading into estimated lux
# -------------------------------------------------
def convert_to_lux(raw_value):
    if raw_value < 0:
        raw_value = 0

    if raw_value > ADC_MAX:
        raw_value = ADC_MAX

    return (raw_value / ADC_MAX) * MAX_LUX


# -------------------------------------------------
# Estimate relative VOC response
# -------------------------------------------------
def estimate_relative_voc():
    if gas_baseline <= 0 or gas_resistance <= 0:
        return 0.0

    ratio = gas_baseline / gas_resistance
    relative_voc = (ratio - 1.0) * 100.0

    if relative_voc < 0:
        relative_voc = 0.0

    if relative_voc > 999:
        relative_voc = 999.0

    return relative_voc


# -------------------------------------------------
# Control the bathroom light
# -------------------------------------------------
def set_light(state):
    global light_on

    if state and not light_on:
        relay4_0.set_relay_state(LIGHT_RELAY, 1)
        light_on = True
        print("Bathroom light: ON")

    elif not state and light_on:
        relay4_0.set_relay_state(LIGHT_RELAY, 0)
        light_on = False
        print("Bathroom light: OFF")


# -------------------------------------------------
# Control the exhaust fan
# -------------------------------------------------
def set_fan(state):
    global fan_on

    if state and not fan_on:
        relay4_0.set_relay_state(FAN_RELAY, 1)
        fan_on = True
        print("Exhaust fan: ON")

    elif not state and fan_on:
        relay4_0.set_relay_state(FAN_RELAY, 0)
        fan_on = False
        print("Exhaust fan: OFF")


# -------------------------------------------------
# Start the delayed light-off countdown
# -------------------------------------------------
def start_light_off_countdown():
    global light_off_countdown
    global light_off_start_time

    light_off_countdown = True
    light_off_start_time = time.ticks_ms()

    print("Light will switch off in 10 seconds")


# -------------------------------------------------
# Read and process the PIR sensor
# -------------------------------------------------
def process_occupancy():
    global occupied
    global previous_motion_state
    global last_motion_time
    global motion_event_count
    global light_off_countdown

    current_time = time.ticks_ms()

    motion_state = pbhub_0.digital_read(
        PIR_PORT,
        PIR_SIGNAL_PIN
    )

    if motion_state == 1:
        last_motion_time = current_time

        # Count only a new motion event
        if previous_motion_state == 0:
            motion_event_count += 1
            print("Human motion detected")

        # Change from vacant to occupied
        if not occupied:
            occupied = True
            print("Bathroom status: OCCUPIED")

        # Cancel the light-off countdown
        if light_off_countdown:
            light_off_countdown = False
            print("Light-off countdown cancelled")

    # Change from occupied to vacant after no motion
    if occupied:
        elapsed = time.ticks_diff(
            current_time,
            last_motion_time
        )

        if elapsed >= OCCUPANCY_HOLD_TIME:
            occupied = False
            print("Bathroom status: VACANT")

            if light_on:
                start_light_off_countdown()

    previous_motion_state = motion_state


# -------------------------------------------------
# Periodically evaluate the bathroom light
# -------------------------------------------------
def process_light_control():
    global light_off_countdown

    # Light control applies only while occupied
    if not occupied:
        return

    # Cancel any pending light-off countdown
    if light_off_countdown:
        light_off_countdown = False
        print("Light-off countdown cancelled")

    # Switch on when the room is too dark
    if not light_on:
        if light_lux < LIGHT_ON_THRESHOLD_LUX:
            set_light(True)

    # Switch off when sufficient natural light exists
    else:
        if light_lux >= LIGHT_OFF_THRESHOLD_LUX:
            set_light(False)


# -------------------------------------------------
# Process the delayed light-off operation
# -------------------------------------------------
def process_light_off_countdown():
    global light_off_countdown

    if not light_off_countdown:
        return

    if occupied:
        light_off_countdown = False
        print("Light-off countdown cancelled")
        return

    elapsed = time.ticks_diff(
        time.ticks_ms(),
        light_off_start_time
    )

    if elapsed >= LIGHT_OFF_DELAY:
        light_off_countdown = False
        set_light(False)


# -------------------------------------------------
# Update average human-motion activity
# -------------------------------------------------
def process_motion_activity():
    global activity_window_start
    global motion_event_count
    global average_motion_activity

    current_time = time.ticks_ms()

    if time.ticks_diff(
        current_time,
        activity_window_start
    ) >= ACTIVITY_WINDOW:

        average_motion_activity = motion_event_count

        print(
            "Motion activity:",
            average_motion_activity,
            "events per minute"
        )

        motion_event_count = 0
        activity_window_start = current_time


# -------------------------------------------------
# Establish the initial gas baseline
# -------------------------------------------------
def process_gas_baseline():
    global gas_baseline
    global gas_baseline_total
    global gas_baseline_count

    if gas_baseline_count >= GAS_BASELINE_SAMPLES:
        return

    if gas_resistance > 0:
        gas_baseline_total += gas_resistance
        gas_baseline_count += 1

    if gas_baseline_count == GAS_BASELINE_SAMPLES:
        gas_baseline = (
            gas_baseline_total /
            GAS_BASELINE_SAMPLES
        )

        print(
            "Gas baseline established:",
            gas_baseline,
            "ohms"
        )


# -------------------------------------------------
# Determine whether air quality is abnormal
# -------------------------------------------------
def process_air_quality():
    global gas_alert

    if gas_baseline <= 0 or gas_resistance <= 0:
        return

    gas_ratio = gas_resistance / gas_baseline

    if not gas_alert and gas_ratio <= GAS_ALERT_RATIO:
        gas_alert = True
        print("WARNING: Abnormal air quality detected")

    elif gas_alert and gas_ratio >= GAS_RECOVERY_RATIO:
        gas_alert = False
        Speaker.stop()
        print("Air quality returned to normal")


# -------------------------------------------------
# Convert sensor readings into AI input features
# -------------------------------------------------
def extract_ai_features():
    # Temperature range: 20 to 40 degrees Celsius
    temperature_feature = clamp01(
        (temperature - 20.0) / 20.0
    )

    # Humidity is already a percentage
    humidity_feature = clamp01(
        humidity / 100.0
    )

    # Gas response increases as gas resistance falls
    if gas_baseline > 0 and gas_resistance > 0:
        gas_feature = clamp01(
            1.0 - (
                gas_resistance /
                gas_baseline
            )
        )
    else:
        gas_feature = 0.0

    # Light range: 0 to 1000 lux
    light_feature = clamp01(
        light_lux / MAX_LUX
    )

    # 10 or more motion events per minute
    # represents high activity
    motion_feature = clamp01(
        average_motion_activity / 10.0
    )

    if occupied:
        occupancy_feature = 1.0
    else:
        occupancy_feature = 0.0

    return [
        temperature_feature,
        humidity_feature,
        gas_feature,
        light_feature,
        motion_feature,
        occupancy_feature
    ]


# -------------------------------------------------
# Calculate squared Euclidean distance
# -------------------------------------------------
def calculate_distance(features, prototype):
    total = 0.0

    for index in range(len(features)):
        difference = (
            features[index] -
            prototype[index]
        )

        total += difference * difference

    return total


# -------------------------------------------------
# Classify the bathroom condition
# -------------------------------------------------
def classify_bathroom_condition(features):
    best_class = None
    best_distance = 999999.0
    second_best_distance = 999999.0

    for class_name in AI_PROTOTYPES:
        prototype = AI_PROTOTYPES[class_name]

        distance = calculate_distance(
            features,
            prototype
        )

        if distance < best_distance:
            second_best_distance = best_distance
            best_distance = distance
            best_class = class_name

        elif distance < second_best_distance:
            second_best_distance = distance

    if second_best_distance <= 0:
        confidence = 1.0

    elif second_best_distance >= 999999.0:
        confidence = 0.0

    else:
        confidence = (
            second_best_distance -
            best_distance
        ) / second_best_distance

    confidence = clamp01(confidence)

    return best_class, confidence


# -------------------------------------------------
# Run the Edge AI model periodically
# -------------------------------------------------
def process_edge_ai():
    global ai_classification
    global ai_confidence
    global last_ai_update

    current_time = time.ticks_ms()

    if time.ticks_diff(
        current_time,
        last_ai_update
    ) < AI_UPDATE_INTERVAL:
        return

    last_ai_update = current_time

    # Wait until gas calibration is complete
    if gas_baseline_count < GAS_BASELINE_SAMPLES:
        ai_classification = AI_CALIBRATING
        ai_confidence = 0.0
        return

    features = extract_ai_features()

    result = classify_bathroom_condition(
        features
    )

    ai_classification = result[0]
    ai_confidence = result[1]

    print(
        "Edge AI:",
        ai_classification,
        "| Confidence: {:.0f}%"
        .format(ai_confidence * 100)
    )

    feature_text = []

    for value in features:
        feature_text.append(
            "{:.2f}".format(value)
        )

    print("AI features:", feature_text)


# -------------------------------------------------
# Control the exhaust fan
# -------------------------------------------------
def process_fan_control():
    # Direct air-quality safety override
    if gas_alert:
        set_fan(True)
        return

    # AI detects a poor-air pattern
    if ai_classification == AI_POOR_AIR:
        set_fan(True)
        return

    # AI detects steamy or humid conditions
    if (
        occupied and
        ai_classification == AI_STEAMY_HUMID
    ):
        set_fan(True)
        return

    # Conventional temperature and humidity control
    if occupied:
        if not fan_on:
            if (
                temperature >= TEMPERATURE_HIGH or
                humidity >= HUMIDITY_HIGH
            ):
                set_fan(True)

        else:
            if (
                temperature <= TEMPERATURE_RECOVERY and
                humidity <= HUMIDITY_RECOVERY and
                ai_classification != AI_STEAMY_HUMID
            ):
                set_fan(False)

    else:
        set_fan(False)


# -------------------------------------------------
# Produce the air-quality warning tone
# -------------------------------------------------
def process_buzzer():
    global last_buzzer_time

    if not gas_alert:
        return

    current_time = time.ticks_ms()

    if time.ticks_diff(
        current_time,
        last_buzzer_time
    ) >= BUZZER_INTERVAL:

        last_buzzer_time = current_time

        Speaker.tone(
            BUZZER_FREQUENCY,
            500
        )

        print("Air-quality warning buzzer")


# -------------------------------------------------
# Read all environmental sensors
# -------------------------------------------------
def read_sensors():
    global temperature
    global humidity
    global pressure_hpa
    global gas_resistance
    global light_lux
    global last_sensor_update

    current_time = time.ticks_ms()

    if time.ticks_diff(
        current_time,
        last_sensor_update
    ) < SENSOR_UPDATE_INTERVAL:
        return

    last_sensor_update = current_time

    temperature = envpro_0.get_temperature()
    humidity = envpro_0.get_humidity()
    pressure_hpa = envpro_0.get_pressure()
    gas_resistance = envpro_0.get_gas_resistance()

    # The Light Sensor signal is inverted
    light_raw = (
        ADC_MAX -
        pbhub_0.analog_read(
            LIGHT_SENSOR_PORT
        )
    )

    light_lux = convert_to_lux(
        light_raw
    )

    process_gas_baseline()
    process_air_quality()

    # Periodically evaluate lighting while occupied
    process_light_control()

    relative_voc = estimate_relative_voc()

    print(
        "Temp: {:.1f} C | "
        "Humidity: {:.1f}% | "
        "Pressure: {:.1f} hPa | "
        "Light: {:.1f} lux | "
        "Gas: {:.0f} ohm | "
        "Relative VOC: {:.1f}"
        .format(
            temperature,
            humidity,
            pressure_hpa,
            light_lux,
            gas_resistance,
            relative_voc
        )
    )


# -------------------------------------------------
# Update the LCD
# -------------------------------------------------
def update_display():
    if occupied:
        occupancy_text = "Occupied"
    else:
        occupancy_text = "Vacant"

    label_occupancy.setText(
        "Room: {} Act:{}/m"
        .format(
            occupancy_text,
            average_motion_activity
        )
    )

    label_environment.setText(
        "T:{:.1f}C RH:{:.1f}%"
        .format(
            temperature,
            humidity
        )
    )

    label_light.setText(
        "Light:{:.0f} lux"
        .format(light_lux)
    )

    if gas_baseline_count < GAS_BASELINE_SAMPLES:
        label_air.setText(
            "Air: Calibrating"
        )

        label_air.setColor(
            0xFFFFFF,
            0x000000
        )

    elif gas_alert:
        label_air.setText(
            "WARNING: Poor air"
        )

        label_air.setColor(
            0xFF0000,
            0x000000
        )

    else:
        label_air.setText(
            "Air: Normal"
        )

        label_air.setColor(
            0x00FF00,
            0x000000
        )

    label_outputs.setText(
        "Light:{} Fan:{}"
        .format(
            "ON" if light_on else "OFF",
            "ON" if fan_on else "OFF"
        )
    )

    if ai_classification == AI_POOR_AIR:
        label_ai.setText(
            "AI: POOR AIR {:.0f}%"
            .format(
                ai_confidence * 100
            )
        )

        label_ai.setColor(
            0xFF0000,
            0x000000
        )

    elif ai_classification == AI_STEAMY_HUMID:
        label_ai.setText(
            "AI: STEAMY {:.0f}%"
            .format(
                ai_confidence * 100
            )
        )

        label_ai.setColor(
            0xFF8000,
            0x000000
        )

    elif ai_classification == AI_OCCUPIED_NORMAL:
        label_ai.setText(
            "AI: OCCUPIED {:.0f}%"
            .format(
                ai_confidence * 100
            )
        )

        label_ai.setColor(
            0x00FFFF,
            0x000000
        )

    elif ai_classification == AI_VACANT_NORMAL:
        label_ai.setText(
            "AI: VACANT {:.0f}%"
            .format(
                ai_confidence * 100
            )
        )

        label_ai.setColor(
            0x00FF00,
            0x000000
        )

    else:
        label_ai.setText(
            "AI: Calibrating"
        )

        label_ai.setColor(
            0xFFFFFF,
            0x000000
        )


# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global i2c0
    global pahub_2
    global pahub_5
    global pbhub_0
    global envpro_0
    global relay4_0

    global label_title
    global label_occupancy
    global label_environment
    global label_light
    global label_air
    global label_outputs
    global label_ai

    global last_sensor_update
    global last_motion_time
    global activity_window_start
    global last_ai_update

    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)

    label_title = Widgets.Label(
        "Smart Bathroom AI",
        38, 2, 1.0,
        0xFFFFFF, 0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_occupancy = Widgets.Label(
        "Room: Vacant",
        5, 25, 1.0,
        0x00FFFF, 0x000000,
        Widgets.FONTS.Montserrat12
    )

    label_environment = Widgets.Label(
        "T:--.-C RH:--.-%",
        5, 43, 1.0,
        0xFFFFFF, 0x000000,
        Widgets.FONTS.Montserrat12
    )

    label_light = Widgets.Label(
        "Light:---- lux",
        5, 61, 1.0,
        0xFFFF00, 0x000000,
        Widgets.FONTS.Montserrat12
    )

    label_air = Widgets.Label(
        "Air: Calibrating",
        5, 79, 1.0,
        0xFFFFFF, 0x000000,
        Widgets.FONTS.Montserrat12
    )

    label_outputs = Widgets.Label(
        "Light:OFF Fan:OFF",
        5, 97, 1.0,
        0x00FF00, 0x000000,
        Widgets.FONTS.Montserrat12
    )

    label_ai = Widgets.Label(
        "AI: Calibrating",
        5, 115, 1.0,
        0x00FFFF, 0x000000,
        Widgets.FONTS.Montserrat12
    )

    # Configure the shared I2C bus
    i2c0 = I2C(
        0,
        scl=Pin(10),
        sda=Pin(9),
        freq=100000
    )

    # Initialize PbHUB
    pbhub_0 = PBHUBUnit(
        i2c0,
        0x61
    )

    # ENV-Pro Unit on PaHUB Port 2
    pahub_2 = PAHUBUnit(
        i2c=i2c0,
        channel=ENVPRO_PAHUB_PORT
    )

    envpro_0 = ENVPROUnit(
        pahub_2
    )

    # 4-Relay Unit on PaHUB Port 5
    pahub_5 = PAHUBUnit(
        i2c=i2c0,
        channel=RELAY_PAHUB_PORT
    )

    relay4_0 = Relay4Unit(
        pahub_5
    )

    relay4_0.set_mode(
        Relay4Unit.SYNC_MODE
    )

    relay4_0.set_relay_all(0)

    # Initialize embedded buzzer
    Speaker.begin()
    Speaker.setVolume(180)
    Speaker.stop()

    current_time = time.ticks_ms()

    last_sensor_update = current_time
    last_motion_time = current_time
    activity_window_start = current_time
    last_ai_update = current_time

    print(
        "Smart Bathroom Edge AI System"
    )

    print(
        "--------------------------------"
    )

    print(
        "ENV-Pro Unit      : PaHUB Port 2"
    )

    print(
        "4-Relay Unit      : PaHUB Port 5"
    )

    print(
        "  Relay 1         : Bathroom light"
    )

    print(
        "  Relay 2         : Exhaust fan"
    )

    print(
        "PIR Sensor        : PbHUB Port 1, pin 1"
    )

    print(
        "Light Sensor      : PbHUB Port 2"
    )

    print(
        "Warning output    : Embedded buzzer"
    )

    print(
        "AI classes        : Vacant, Occupied,"
    )

    print(
        "                    Steamy, Poor Air"
    )

    print(
        "--------------------------------"
    )

    print(
        "Gas calibration started"
    )


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()

    process_occupancy()
    process_motion_activity()

    read_sensors()

    process_edge_ai()
    process_fan_control()

    process_light_off_countdown()
    process_buzzer()
    update_display()

    time.sleep_ms(50)


# -------------------------------------------------
# Program entry point
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
            print(
                "Please update to the latest firmware"
            )