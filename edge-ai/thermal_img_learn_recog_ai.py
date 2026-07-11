import M5
from M5 import *
from hardware import I2C, Pin
import time

from amg8833 import AMG8833
from tlogfft8 import ThermalLogFFT8
from nmaicore import NMAICore, NORM_L1, CLASSIFIER_RBF

# -------------------------------------------------
# Global objects
# -------------------------------------------------
sensor = None
logfft = None
ai = None

# -------------------------------------------------
# Learning and recognition settings
# -------------------------------------------------
MAX_IMAGES = 10

next_category = 1
learned_count = 0

# Button-state latch for Button A and Button B
previous_button_a = False
previous_button_b = False

# Recognition timing
RECOGNITION_INTERVAL = 500
last_recognition_time = 0

# Thermal display timing
DISPLAY_INTERVAL = 200
last_display_time = 0

# Latest thermal frame cache
latest_thermal_pixels = None

# NeuroMem settings
NETWORK_SIZE = 32
VECTOR_SIZE = 64

# Influence field settings for 64-value byte vectors
MINIF = 2
MAXIF = 8192

# -------------------------------------------------
# LCD helper functions
# -------------------------------------------------
def clear_info_area():
    M5.Lcd.fillRect(130, 0, 110, 135,0x000000)

def draw_static_screen():
    Widgets.fillScreen(0x000000)
    M5.Lcd.setTextColor(0xFFFFFF, 0x000000)
    M5.Lcd.drawString("Thermal AI", 138, 2)
    M5.Lcd.drawString("A:Learn", 138, 18)
    M5.Lcd.drawString("B:Forget", 138, 34)
    M5.Lcd.drawString("Mode:", 138, 52)
#   M5.Lcd.drawString("Result:", 138, 90)
#   M5.Lcd.drawString("Images:", 138, 116)

def update_info_text(mode_text, result_text, count_text):
    # Clear only the dynamic text area on the right.
    M5.Lcd.fillRect(138, 64, 98, 14, 0x000000)
    M5.Lcd.fillRect(138, 102, 98, 14, 0x000000)
    M5.Lcd.fillRect(138, 128, 98, 7, 0x000000)
    M5.Lcd.setTextColor(0x00FFFF, 0x000000)
    M5.Lcd.drawString(mode_text, 138, 64)
    M5.Lcd.setTextColor(0xFFFF00, 0x000000)
    M5.Lcd.drawString(result_text, 138, 102)
    M5.Lcd.setTextColor(0x00FF00, 0x000000)
    M5.Lcd.drawString(count_text, 138, 120)

def update_count_display():
    M5.Lcd.fillRect(138, 120, 98, 15, 0x000000)
    M5.Lcd.setTextColor(0x00FF00, 0x000000)
    M5.Lcd.drawString("{}/{}" .format(learned_count, MAX_IMAGES), 138, 120)

def update_result_display(category, distance):
    M5.Lcd.fillRect(138, 64, 98, 40, 0x000000)
    M5.Lcd.setTextColor(0x00FFFF, 0x000000)
    M5.Lcd.drawString("Recognise", 138, 64)
    M5.Lcd.setTextColor(0xFFFF00, 0x000000)
    M5.Lcd.drawString("C:{}".format(category), 138, 102)
    M5.Lcd.drawString("D:{}".format(distance), 188, 102)

def update_learning_display(category):
    M5.Lcd.fillRect(138, 64, 98, 40, 0x000000)
    M5.Lcd.setTextColor(0x00FF00, 0x000000)
    M5.Lcd.drawString("Learned", 138, 64)
    M5.Lcd.drawString("C:{}".format(category), 138, 102)
    update_count_display()

def update_forget_display():
    M5.Lcd.fillRect(138, 64, 98, 40, 0x000000)
    M5.Lcd.setTextColor(0xFF8000, 0x000000)
    M5.Lcd.drawString("Cleared", 138, 64)
    M5.Lcd.setTextColor(0xFFFF00, 0x000000)
    M5.Lcd.drawString("No model", 138, 102)
    update_count_display()

# -------------------------------------------------
# Convert thermal image into Log-FFT byte vector
# -------------------------------------------------
def build_feature_vector(thermal_pixels=None):
    if thermal_pixels is None:
        thermal_pixels = sensor.get_flattened_data(refresh=True)

    feature_vector = logfft.transform_to_bytes(thermal_pixels, input_normalization=ThermalLogFFT8.NORMALIZE_MINMAX, shift=True)
    return feature_vector

# -------------------------------------------------
# Update the thermal image display
# -------------------------------------------------
def process_thermal_display():
    global last_display_time
    global latest_thermal_pixels

    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_display_time) < DISPLAY_INTERVAL:
        return

    last_display_time = current_time

    # Draw the thermal image on the left side of the LCD.
    # The draw function also reads a fresh AMG8833 frame.
    stats = sensor.draw_thermal_image(
        lcd=M5.Lcd,
        x=0,
        y=0,
        width=128,
        height=128,
        minimum=20.0,
        maximum=35.0,
        refresh=True,
        show_hotspot=True,
        clear_background=False,
        only_changed=True,
        color_steps=24
    )

    # Reuse the same frame for learning and recognition.
    latest_thermal_pixels = sensor.get_flattened_data(refresh=False)

    # Display a compact maximum temperature below the panel title area.
    M5.Lcd.fillRect(138, 84, 98, 12, 0x000000)
    M5.Lcd.setTextColor(0xFFFFFF, 0x000000)
    M5.Lcd.drawString("Max:{:.1f}".format(stats["maximum"]), 138, 84)

# -------------------------------------------------
# Learn one thermal image
# -------------------------------------------------
def learn_current_image():
    global next_category
    global learned_count
    global latest_thermal_pixels

    if learned_count >= MAX_IMAGES:
        print("Learning rejected: maximum 10 images reached")
        update_forget_display()
        M5.Lcd.setTextColor(0xFF0000, 0x000000)
        M5.Lcd.drawString("Max 10", 138, 64)
        return

    if latest_thermal_pixels is None:
        latest_thermal_pixels = sensor.get_flattened_data(refresh=True)

    feature_vector = build_feature_vector(latest_thermal_pixels)
    category = next_category
    ai.learn(feature_vector, category)
    learned_count += 1
    next_category += 1

    print("--------------------------------")
    print("LEARNED THERMAL IMAGE")
#    print("Image number:", learned_count)
#    print("Assigned category:", category)
#    print("Feature vector length:", len(feature_vector))

    print("Img No: {}, Cat: {}, Vector Len: {}, Committed Neurons: {}" .format(learned_count, category, len(feature_vector), ai.count_committed_neurons()))
    print("Features:\n", list(feature_vector[:64]))
#   print("Committed neurons:", ai.count_committed_neurons())
    print("--------------------------------")
    
    update_learning_display(category)

# -------------------------------------------------
# Forget all learned thermal images
# -------------------------------------------------
def forget_learned_images():
    global next_category
    global learned_count

    ai.forget()
    next_category = 1
    learned_count = 0

    print("--------------------------------")
    print("FORGET ALL LEARNED IMAGES")
    print("Learned image count reset to:", learned_count)
    print("Next category reset to:", next_category)
    print("Committed neurons:", ai.count_committed_neurons())
    print("--------------------------------")

    update_forget_display()

# -------------------------------------------------
# Recognise current thermal image
# -------------------------------------------------
def recognise_current_image():
    global latest_thermal_pixels

    if learned_count == 0:
        print("Recognition -> no learned image yet")

        M5.Lcd.fillRect(138, 64, 98, 40, 0x000000)
        M5.Lcd.setTextColor(0x00FFFF, 0x000000)
        M5.Lcd.drawString("Recognise", 138, 64)
        M5.Lcd.setTextColor(0xFFFF00, 0x000000)
        M5.Lcd.drawString("No model", 138, 102)
        return

    if latest_thermal_pixels is None:
        latest_thermal_pixels = sensor.get_flattened_data(refresh=True)

    feature_vector = build_feature_vector(latest_thermal_pixels)
    result = ai.classify(feature_vector)

    category = result["category"]
    distance = result["distance"]
    identified = result["identified"]
    uncertain = result["uncertain"]

#    print("--------------------------------")
#    print("RECOGNITION RESULT")
#    print("Category:", category)
#    print("Distance:", distance)
#    print("Identified:", identified)
#    print("Uncertain:", uncertain)
#    print("--------------------------------")
    
    print("Recognition -> Cat: {}, Dist: {}, Identified: {}, Uncertain: {}" .format(category, distance, identified, uncertain))
    update_result_display(category, distance)

# -------------------------------------------------
# Process M5StickS3 Button A and Button B
# -------------------------------------------------
def process_buttons():
    global previous_button_a
    global previous_button_b

    button_a_pressed = BtnA.isPressed()
    button_b_pressed = BtnB.isPressed()

    # Button A: learn the current thermal image
    if button_a_pressed and not previous_button_a:
        learn_current_image()

    # Button B: forget all learned images
    if button_b_pressed and not previous_button_b:
        forget_learned_images()

    previous_button_a = button_a_pressed
    previous_button_b = button_b_pressed


# -------------------------------------------------
# Process recognition periodically
# -------------------------------------------------
def process_recognition():
    global last_recognition_time

    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_recognition_time) < RECOGNITION_INTERVAL:
        return

    last_recognition_time = current_time
    recognise_current_image()

# -------------------------------------------------
# Setup
# -------------------------------------------------
def setup():
    global sensor
    global logfft
    global ai
    global last_recognition_time
    global last_display_time
    global latest_thermal_pixels
    M5.begin()

    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)
    draw_static_screen()

    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=400000)
    sensor = AMG8833(i2c0, address=0x69, emissivity=0.95, frame_rate=10)
    sensor.set_moving_average(True)

    logfft = ThermalLogFFT8(
        input_normalization=ThermalLogFFT8.NORMALIZE_MINMAX,
        output_normalization=ThermalLogFFT8.OUTPUT_BYTE,
        remove_dc=True
    )

    ai = NMAICore(network_size=NETWORK_SIZE, vector_size=VECTOR_SIZE)
    ai.set_context(context=1, norm=NORM_L1, minif=MINIF, maxif=MAXIF)
    ai.set_classifier_type(CLASSIFIER_RBF)
    current_time = time.ticks_ms()
    last_recognition_time = current_time
    last_display_time = current_time

    latest_thermal_pixels = sensor.get_flattened_data(refresh=True)
    update_info_text("Recognise", "No model", "0/10")

    print("AI Thermal Image Learning and Recognition")
    print("--------------------------------")
    print("AMG8833 thermal sensor: I2C address 0x69")
    print("Input image size      : 8 x 8")
    print("Flattened pixels      : 64")
    print("Feature extraction    : normalized log-FFT")
    print("Feature vector size   : 64")
    print("AI model              : NMAICore")
    print("Default mode          : recognition")
    print("Button A              : learn current image")
    print("Button B              : forget learned images")
    print("Maximum learned images:", MAX_IMAGES)
    print("Thermal image         : displayed on LCD")
    print("--------------------------------")

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()
    process_thermal_display()
    process_buttons()
    process_recognition()
    time.sleep_ms(1)

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
            from utility import print_error_msg
            print_error_msg(e)

        except ImportError:
            print(e)
