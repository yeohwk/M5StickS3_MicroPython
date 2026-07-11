import M5
from M5 import *
from hardware import I2C, Pin
import time
import math

from nmaicore import NMAICore, NORM_L1, CLASSIFIER_RBF

# =================================================
# M5StickS3 NMAI Vibration Monitoring System
#
# Hardware:
#   - M5StickS3
#   - M5Stack 3-Axis Digital Accelerometer Unit
#     based on ADXL345, I2C address 0x53
#   - Built-in speaker
#
# LCD Layout:
#   - Left side  : live time-domain vibration waveform
#   - Right side : instructions, AI result, learned count
#
# Operation:
#   - Default mode is monitoring / recognition.
#   - Button A learns the current vibration vector.
#   - Button B forgets all learned vibration vectors.
#   - Each learned vector is assigned a category starting
#     from 1 and auto-increments.
# =================================================

# -------------------------------------------------
# ADXL345 register definitions
# -------------------------------------------------
ADXL345_ADDRESS = 0x53
ADXL345_REG_DEVID = 0x00
ADXL345_REG_BW_RATE = 0x2C
ADXL345_REG_POWER_CTL = 0x2D
ADXL345_REG_DATA_FORMAT = 0x31
ADXL345_REG_DATAX0 = 0x32
ADXL345_DEVID = 0xE5

# -------------------------------------------------
# Sampling and vector settings
# -------------------------------------------------
VECTOR_SIZE = 256
SAMPLE_INTERVAL_MS = 5
MONITORING_INTERVAL_MS = 1000

# Stationary accelerometers still contain small ADC and mechanical noise.
# These settings make the displayed time-domain signal more stable.
NOISE_DEADBAND_G = 0.015          # Ignore very small vibration changes
WAVE_DISPLAY_RANGE_G = 0.20       # Fixed LCD waveform range: +/-0.20 g

# For ADXL345 full-resolution mode:
# approximately 3.9 mg per LSB.
ADXL345_SCALE_G = 0.0039

# -------------------------------------------------
# NMAI settings
# -------------------------------------------------
MAX_PROTOTYPES = 32
NETWORK_SIZE = 32
MINIF = 2
MAXIF = 8192

# -------------------------------------------------
# Speaker settings
# -------------------------------------------------
BEEP_FREQUENCY_LEARN = 1800
BEEP_FREQUENCY_FORGET = 800
BEEP_FREQUENCY_MATCH = 1200
BEEP_DURATION_MS = 120

# -------------------------------------------------
# LCD layout settings
# -------------------------------------------------
WAVE_X = 0
WAVE_Y = 0
WAVE_W = 128
WAVE_H = 128

INFO_X = 134
INFO_Y = 0
INFO_W = 106
INFO_H = 135

# -------------------------------------------------
# Global objects and states
# -------------------------------------------------
i2c0 = None
accelerometer = None
ai = None

previous_button_a = False
previous_button_b = False

learned_count = 0
next_category = 1

last_monitoring_time = 0

latest_samples = None
latest_vector = None
latest_peak = 0.0
latest_average = 0.0

# -------------------------------------------------
# ADXL345 Accelerometer Driver
# -------------------------------------------------
class ADXL345:
    def __init__(self, i2c, address=ADXL345_ADDRESS):
        self.i2c = i2c
        self.address = address
        self.scale_g = ADXL345_SCALE_G
        self.begin()

    def _write_u8(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes([value & 0xFF]))

    def _read_u8(self, register):
        data = self.i2c.readfrom_mem(self.address, register, 1)
        return data[0]

    def _read_bytes(self, register, length):
        return self.i2c.readfrom_mem(self.address, register, length)

    def begin(self):
        device_id = self._read_u8(ADXL345_REG_DEVID)

        if device_id != ADXL345_DEVID:
            print("Warning: ADXL345 device ID expected 0xE5, got:", hex(device_id))

        # BW_RATE = 0x0A gives 100 Hz output data rate.
        self._write_u8(ADXL345_REG_BW_RATE, 0x0A)

        # DATA_FORMAT:
        # bit 3 FULL_RES = 1
        # range bits = 11 for +/-16g
        self._write_u8(ADXL345_REG_DATA_FORMAT, 0x0B)

        # POWER_CTL:
        # bit 3 MEASURE = 1
        self._write_u8(ADXL345_REG_POWER_CTL, 0x08)

    def _to_int16(self, low_byte, high_byte):
        value = (low_byte | (high_byte << 8))

        if value & 0x8000:
            value -= 65536

        return value

    def read_raw(self):
        data = self._read_bytes(ADXL345_REG_DATAX0, 6)
        raw_x = self._to_int16(data[0], data[1])
        raw_y = self._to_int16(data[2], data[3])
        raw_z = self._to_int16(data[4], data[5])
        return raw_x, raw_y, raw_z

    def read_g(self):
        raw_x, raw_y, raw_z = self.read_raw()
        x_g = raw_x * self.scale_g
        y_g = raw_y * self.scale_g
        z_g = raw_z * self.scale_g
        return x_g, y_g, z_g

    def read_magnitude(self):
        x_g, y_g, z_g = self.read_g()
        magnitude = math.sqrt(x_g * x_g + y_g * y_g + z_g * z_g)
        return magnitude

# -------------------------------------------------
# LCD helper functions
# -------------------------------------------------
def draw_static_screen():
    Widgets.fillScreen(0x000000)

    # Left waveform frame
    M5.Lcd.drawRect(WAVE_X, WAVE_Y, WAVE_W, WAVE_H, 0x404040)
    M5.Lcd.setTextColor(0xFFFFFF, 0x000000)
    M5.Lcd.drawString("Vibration", 4, 4)

    # Right information area
    M5.Lcd.drawString("AI Vib Mon", INFO_X, 2)
    M5.Lcd.drawString("A:Train", INFO_X, 18)
    M5.Lcd.drawString("B:Forget", INFO_X, 32)
    M5.Lcd.drawString("Mode:", INFO_X, 50)
#   M5.Lcd.drawString("Result:", INFO_X, 84)
    M5.Lcd.drawString("Learned:", INFO_X, 100)

def clear_dynamic_info():
    M5.Lcd.fillRect(INFO_X, 64, INFO_W, 58, 0x000000)

def update_status_display(mode_text, result_text):
    M5.Lcd.fillRect(INFO_X, 64, INFO_W, 38, 0x000000)
    M5.Lcd.setTextColor(0x00FFFF, 0x000000)
    M5.Lcd.drawString(mode_text, INFO_X, 64)
    M5.Lcd.setTextColor(0xFFFF00, 0x000000)
    M5.Lcd.drawString(result_text, INFO_X, 82)

def update_learned_count_display():
    M5.Lcd.fillRect(INFO_X, 124, INFO_W, 12, 0x000000)
    M5.Lcd.setTextColor(0x00FF00, 0x000000)
    M5.Lcd.drawString("{}/{}".format(learned_count, MAX_PROTOTYPES), INFO_X, 114)

def draw_waveform(samples):
    if samples is None or len(samples) == 0:
        return

    # Clear the waveform plot area only.
    M5.Lcd.fillRect(WAVE_X + 1, WAVE_Y + 15, WAVE_W - 2, WAVE_H - 16, 0x000000)
    centre_y = WAVE_Y + 72

    # Draw centre reference line. This represents 0 g vibration change.
    M5.Lcd.drawLine(WAVE_X + 2, centre_y, WAVE_X + WAVE_W - 3, centre_y, 0x303030)

    previous_x = WAVE_X + 2
    previous_y = centre_y
    plot_width = WAVE_W - 4
    half_height = (WAVE_H - 30) // 2

    # Use a fixed display range instead of auto-scaling.
    # This prevents tiny stationary noise from filling the whole screen.
    for x_offset in range(plot_width):
        source_index = int((x_offset * len(samples)) / plot_width)
        value = samples[source_index]

        if value > WAVE_DISPLAY_RANGE_G:
            value = WAVE_DISPLAY_RANGE_G

        if value < -WAVE_DISPLAY_RANGE_G:
            value = -WAVE_DISPLAY_RANGE_G

        y = int(centre_y - (value / WAVE_DISPLAY_RANGE_G) * half_height)
        x = WAVE_X + 2 + x_offset

        if x_offset > 0:
            M5.Lcd.drawLine(previous_x, previous_y, x, y, 0x00FF00)

        previous_x = x
        previous_y = y

    M5.Lcd.fillRect(4, 108, 120, 17, 0x000000)
    M5.Lcd.setTextColor(0xFFFFFF, 0x000000)
    M5.Lcd.drawString("P:{:.3f}g".format(latest_peak), 4, 108)
    M5.Lcd.drawString("A:{:.3f}g".format(latest_average), 64, 108)

# -------------------------------------------------
# General helper functions
# -------------------------------------------------
def clamp_byte(value):
    value = int(value)

    if value < 0:
        return 0

    if value > 255:
        return 255

    return value

def normalize_to_byte_vector(values):
    minimum = min(values)
    maximum = max(values)
    span = maximum - minimum

    if span <= 0:
        return bytearray(VECTOR_SIZE)

    output = bytearray(VECTOR_SIZE)

    for index in range(VECTOR_SIZE):
        normalized = ((values[index] - minimum) / span)
        output[index] = clamp_byte(round(normalized * 255))

    return output

# -------------------------------------------------
# 256-point FFT processing
# -------------------------------------------------
def fft_1d(real, imag):
    n = len(real)

    # Bit-reversal permutation
    j = 0

    for i in range(1, n):
        bit = n >> 1

        while j & bit:
            j ^= bit
            bit >>= 1

        j ^= bit

        if i < j:
            real[i], real[j] = real[j], real[i]
            imag[i], imag[j] = imag[j], imag[i]

    # Cooley-Tukey FFT
    length = 2

    while length <= n:
        half = length // 2
        angle_step = -2.0 * math.pi / length

        for start in range(0, n, length):
            for offset in range(half):
                angle = angle_step * offset
                wr = math.cos(angle)
                wi = math.sin(angle)

                even_index = start + offset
                odd_index = even_index + half
                odd_real = real[odd_index]
                odd_imag = imag[odd_index]
                temp_real = (wr * odd_real - wi * odd_imag)
                temp_imag = (wr * odd_imag + wi * odd_real)
                even_real = real[even_index]
                even_imag = imag[even_index]
                real[odd_index] = even_real - temp_real
                imag[odd_index] = even_imag - temp_imag
                real[even_index] = even_real + temp_real
                imag[even_index] = even_imag + temp_imag

        length <<= 1

def time_domain_to_frequency_vector(samples):
    # Remove the mean value from the vibration magnitude.
    # This helps the vector focus on vibration changes instead
    # of the static gravity component.
    mean_value = sum(samples) / len(samples)

    real = [
        sample - mean_value
        for sample in samples
    ]

    imag = [
        0.0
        for _ in range(VECTOR_SIZE)
    ]

    fft_1d(real, imag)
    magnitude_spectrum = []

    for index in range(VECTOR_SIZE):
        magnitude = math.sqrt(real[index] * real[index] + imag[index] * imag[index])
        magnitude_spectrum.append(magnitude)

    # Remove the DC bin after FFT as an additional precaution.
    magnitude_spectrum[0] = 0.0
    return normalize_to_byte_vector(magnitude_spectrum)

# -------------------------------------------------
# Vibration acquisition
# -------------------------------------------------
def acquire_vibration_vector():
    global latest_samples
    global latest_vector
    global latest_peak
    global latest_average

    raw_magnitude_samples = []
    for index in range(VECTOR_SIZE):
        M5.update()

        magnitude = accelerometer.read_magnitude()
        raw_magnitude_samples.append(magnitude)
        time.sleep_ms(SAMPLE_INTERVAL_MS)

    # Remove the average magnitude so the display and FFT focus on
    # vibration changes instead of the static gravity component.
    mean_value = (sum(raw_magnitude_samples) / len(raw_magnitude_samples))
    vibration_samples = []

    for value in raw_magnitude_samples:
        ac_value = value - mean_value

        # Apply a small deadband to suppress stationary sensor noise.
        if abs(ac_value) < NOISE_DEADBAND_G:
            ac_value = 0.0

        vibration_samples.append(ac_value)

    latest_samples = vibration_samples
    latest_peak = max(
        abs(value)
        for value in vibration_samples
    )
    latest_average = (
        sum(
            abs(value)
            for value in vibration_samples
        ) /
        len(vibration_samples)
    )

    vibration_vector = time_domain_to_frequency_vector(vibration_samples)
    latest_vector = vibration_vector
    draw_waveform(latest_samples)
    return vibration_vector

# -------------------------------------------------
# NMAI learning
# -------------------------------------------------
def learn_current_vibration():
    global learned_count
    global next_category

    if learned_count >= MAX_PROTOTYPES:
        update_status_display("Train", "Full")
        print("Learning rejected: maximum", MAX_PROTOTYPES, "vibration prototypes reached")
        Speaker.tone(BEEP_FREQUENCY_FORGET, BEEP_DURATION_MS)
        return

    update_status_display("Training", "Sampling...")
    vibration_vector = acquire_vibration_vector()
    category = next_category
    ai.learn(vibration_vector, category)
    learned_count += 1
    next_category += 1

    Speaker.tone(BEEP_FREQUENCY_LEARN, BEEP_DURATION_MS)
    update_status_display("Trained", "Cat:{}".format(category))
    update_learned_count_display()

    print("--------------------------------")
    print("LEARNED VIBRATION PROTOTYPE")
    print(
        "Prototype No: {}, Category: {}, Vector Len: {}, Committed Neurons: {}"
        .format(learned_count, category, len(vibration_vector), ai.count_committed_neurons())
    )
    print("Vector:", list(vibration_vector))
    print("--------------------------------")

# -------------------------------------------------
# NMAI forget all
# -------------------------------------------------
def forget_all_vibrations():
    global learned_count
    global next_category

    ai.forget()
    learned_count = 0
    next_category = 1
    Speaker.tone(BEEP_FREQUENCY_FORGET, BEEP_DURATION_MS)
    update_status_display("Cleared", "No model")
    update_learned_count_display()

    print("--------------------------------")
    print("FORGET ALL VIBRATION PROTOTYPES")
    print("Learned count:", learned_count)
    print("Next category:", next_category)
    print("Committed neurons:", ai.count_committed_neurons())
    print("--------------------------------")

# -------------------------------------------------
# NMAI monitoring / recognition
# -------------------------------------------------
def monitor_vibration():
    update_status_display("Monitor", "Sampling...")

    if learned_count == 0:
        vibration_vector = acquire_vibration_vector()
        update_status_display("Monitor", "No model")
        print("Monitoring -> no trained prototype yet")
        return

    vibration_vector = acquire_vibration_vector()
    result = ai.classify(vibration_vector)
    category = result["category"]
    distance = result["distance"]
    identified = result["identified"]
    uncertain = result["uncertain"]

    if identified:
        Speaker.tone(BEEP_FREQUENCY_MATCH, BEEP_DURATION_MS)

    update_status_display("Monitor", "C:{} D:{}".format(category, distance))
    print("Monitoring -> Cat: {}, Dist: {}, Identified: {}, Uncertain: {}" .format(category, distance, identified, uncertain))

# -------------------------------------------------
# Button processing
# -------------------------------------------------
def process_buttons():
    global previous_button_a
    global previous_button_b

    button_a_pressed = BtnA.isPressed()
    button_b_pressed = BtnB.isPressed()

    if button_a_pressed and not previous_button_a:
        learn_current_vibration()

    if button_b_pressed and not previous_button_b:
        forget_all_vibrations()

    previous_button_a = button_a_pressed
    previous_button_b = button_b_pressed

# -------------------------------------------------
# Periodic monitoring
# -------------------------------------------------
def process_monitoring():
    global last_monitoring_time

    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_monitoring_time) < MONITORING_INTERVAL_MS:
        return

    last_monitoring_time = current_time
    monitor_vibration()

# -------------------------------------------------
# Setup
# -------------------------------------------------
def setup():
    global i2c0
    global accelerometer
    global ai
    global last_monitoring_time

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(160)
    draw_static_screen()
    i2c0 = I2C(0, scl=Pin(10), sda=Pin(9), freq=400000)

    accelerometer = ADXL345(i2c0, ADXL345_ADDRESS)
    ai = NMAICore(network_size=NETWORK_SIZE, vector_size=VECTOR_SIZE)
    ai.set_context(context=1, norm=NORM_L1, minif=MINIF, maxif=MAXIF)
    ai.set_classifier_type(CLASSIFIER_RBF)

    Speaker.begin()
    Speaker.setVolume(160)
    Speaker.stop()

    last_monitoring_time = time.ticks_ms()
    update_status_display("Monitor", "No model")
    update_learned_count_display()

    print("NMAI Vibration Monitoring System")
    print("--------------------------------")
    print("Accelerometer Unit : ADXL345")
    print("I2C address        : 0x53")
    print("SCL / SDA          : GPIO10 / GPIO9")
    print("Samples per vector : 256")
    print("Sample interval    :", SAMPLE_INTERVAL_MS, "ms")
    print("Display deadband   :", NOISE_DEADBAND_G, "g")
    print("Waveform range     : +/-", WAVE_DISPLAY_RANGE_G, "g")
    print("Vector format      : 256-byte frequency-domain vector")
    print("NMAI network size  :", NETWORK_SIZE)
    print("NMAI vector size   :", VECTOR_SIZE)
    print("Maximum prototypes :", MAX_PROTOTYPES)
    print("Default mode       : Monitoring")
    print("Button A           : Train current vibration")
    print("Button B           : Forget all")
    print("LCD left panel     : Time-domain vibration")
    print("LCD right panel    : Instructions and AI result")
    print("--------------------------------")

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    M5.update()
    process_buttons()
    process_monitoring()
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
            Speaker.stop()

            from utility import print_error_msg
            print_error_msg(e)

        except ImportError:
            print(e)
