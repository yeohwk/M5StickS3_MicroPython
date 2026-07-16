import os, sys, io
import M5
from M5 import *
import time
import math

# -------------------------------------------------
# Global variables
# -------------------------------------------------
label_status = None
label_gx = None
label_gy = None
label_gz = None
label_roll = None
label_pitch = None

last_time = 0

# Integrated tilt angles in degrees.
# The gyroscope measures angular velocity, so the angle is estimated
# by integrating the gyro readings over time.
roll_angle = 0.0
pitch_angle = 0.0
yaw_angle = 0.0

# Gyroscope offset values measured during startup calibration.
gyro_offset_x = 0.0
gyro_offset_y = 0.0
gyro_offset_z = 0.0

# Small gyro readings around zero are treated as noise.
GYRO_DEADBAND_DPS = 0.5

# Tilt direction threshold in degrees.
TILT_THRESHOLD_DEG = 10.0

# Startup calibration settings.
# Keep the M5StickS3 flat and still during calibration.
CALIBRATION_SAMPLES = 30
CALIBRATION_DELAY_MS = 20

# -------------------------------------------------
# Apply a small deadband to reduce stationary gyro noise
# -------------------------------------------------
def apply_deadband(value, deadband):
    if abs(value) < deadband:
        return 0.0
    return value

# -------------------------------------------------
# Determine tilt direction from gyro-integrated angle
# -------------------------------------------------
def get_tilt_direction(roll, pitch):
    if roll > TILT_THRESHOLD_DEG:
        return "Tilt Right"
    elif roll < -TILT_THRESHOLD_DEG:
        return "Tilt Left"
    elif pitch > TILT_THRESHOLD_DEG:
        return "Tilt Up"
    elif pitch < -TILT_THRESHOLD_DEG:
        return "Tilt Down"
    else:
        return "Flat / Stable"

# -------------------------------------------------
# Limit angle value to a practical display range
# -------------------------------------------------
def limit_angle(angle):
    if angle > 90.0:
        return 90.0
    if angle < -90.0:
        return -90.0
    return angle

# -------------------------------------------------
# Reset the integrated tilt angles
# -------------------------------------------------
def reset_tilt_reference():
    global roll_angle
    global pitch_angle
    global yaw_angle

    roll_angle = 0.0
    pitch_angle = 0.0
    yaw_angle = 0.0

# -------------------------------------------------
# Calibrate gyroscope zero offsets
# -------------------------------------------------
def calibrate_gyro():
    global gyro_offset_x
    global gyro_offset_y
    global gyro_offset_z

    total_x = 0.0
    total_y = 0.0
    total_z = 0.0

    for count in range(CALIBRATION_SAMPLES):
        M5.update()
        gyro = Imu.getGyro()

        total_x += gyro[0]
        total_y += gyro[1]
        total_z += gyro[2]

        time.sleep_ms(CALIBRATION_DELAY_MS)

    gyro_offset_x = total_x / CALIBRATION_SAMPLES
    gyro_offset_y = total_y / CALIBRATION_SAMPLES
    gyro_offset_z = total_z / CALIBRATION_SAMPLES

# -------------------------------------------------
# Update roll, pitch and yaw by integrating gyroscope values
# -------------------------------------------------
def update_gyro_tilt(gx, gy, gz, delta_time):
    global roll_angle
    global pitch_angle
    global yaw_angle

    # Remove startup offset.
    gx = gx - gyro_offset_x
    gy = gy - gyro_offset_y
    gz = gz - gyro_offset_z

    gx = apply_deadband(gx, GYRO_DEADBAND_DPS)
    gy = apply_deadband(gy, GYRO_DEADBAND_DPS)
    gz = apply_deadband(gz, GYRO_DEADBAND_DPS)

    # Axis mapping for M5StickS3 in landscape display rotation.
    #
    # The earlier version used gx for left/right and gy for up/down.
    # On the M5StickS3 with screen rotation set to 1, this can cause
    # a left/right tilt to move the dot vertically.
    #
    # Corrected mapping:
    #   left/right tilt  -> roll  -> use gy
    #   up/down tilt     -> pitch -> use gx
    #
    # The signs below make the dot move in the same direction as the tilt.
    roll_angle = roll_angle + (gy * delta_time)
    pitch_angle = pitch_angle - (gx * delta_time)
    yaw_angle = yaw_angle + (gz * delta_time)

    roll_angle = limit_angle(roll_angle)
    pitch_angle = limit_angle(pitch_angle)

# -------------------------------------------------
# Draw simple visual indicator
# -------------------------------------------------
def draw_tilt_indicator(roll, pitch):
    # Clear the drawing area
    Widgets.Rectangle(0, 84, 240, 51, 0x000000, 0x000000)

    center_x = 120
    center_y = 110

    # Roll controls horizontal movement.
    # Pitch controls vertical movement.
    #
    # Display convention used here:
    #   Tilt Left  -> dot moves Right
    #   Tilt Right -> dot moves Left
    #   Tilt Up    -> dot moves Down
    #   Tilt Down  -> dot moves Up
    #
    # This is intentionally opposite to the physical tilt direction,
    # similar to a bubble-level indicator where the marker moves
    # toward the higher side.
    dot_x = int(center_x - (roll / 45.0) * 70)
    dot_y = int(center_y + (pitch / 45.0) * 35)

    # Limit dot position within screen area
    if dot_x < 10:
        dot_x = 10
    if dot_x > 230:
        dot_x = 230

    if dot_y < 90:
        dot_y = 90
    if dot_y > 130:
        dot_y = 130

    # Draw centre reference and moving dot
    Widgets.Circle(center_x, center_y, 4, 0xFFFFFF, 0xFFFFFF)
    Widgets.Circle(dot_x, dot_y, 8, 0x00FF00, 0x00FF00)

# -------------------------------------------------
# Setup function
# -------------------------------------------------
def setup():
    global label_status
    global label_gx
    global label_gy
    global label_gz
    global label_roll
    global label_pitch
    global last_time

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)
    Widgets.setBrightness(150)

    label_status = Widgets.Label(
        "Status: Calibrating",
        10, 2, 1.0,
        0x00FFFF, 0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_gx = Widgets.Label(
        "Gx: --",
        10, 22, 1.0,
        0xFFFF00, 0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_gy = Widgets.Label(
        "Gy: --",
        90, 22, 1.0,
        0xFFFF00, 0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_gz = Widgets.Label(
        "Gz: --",
        170, 22, 1.0,
        0xFFFF00, 0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_roll = Widgets.Label(
        "Roll: -- deg",
        10, 42, 1.0,
        0xFF8000, 0x000000,
        Widgets.FONTS.Montserrat18
    )

    label_pitch = Widgets.Label(
        "Pitch: -- deg",
        10, 62, 1.0,
        0xFF8000, 0x000000,
        Widgets.FONTS.Montserrat18
    )

    calibrate_gyro()
    reset_tilt_reference()

    label_status.setText("Status: Flat / Stable")
    last_time = time.ticks_ms()

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def loop():
    global last_time

    M5.update()

    current_time = time.ticks_ms()
    elapsed_ms = time.ticks_diff(current_time, last_time)

    # Button A resets the current position as the new flat reference.
    if BtnA.isPressed():
        reset_tilt_reference()

    # Update about 10 times per second
    if elapsed_ms >= 100:
        last_time = current_time
        delta_time = elapsed_ms / 1000.0

        # Native M5StickS3 gyroscope reading.
        # Expected values are angular rates in degrees per second.
        gyro = Imu.getGyro()

        gx = gyro[0]
        gy = gyro[1]
        gz = gyro[2]

        update_gyro_tilt(gx, gy, gz, delta_time)

        tilt_direction = get_tilt_direction(
            roll_angle,
            pitch_angle
        )

        label_status.setText(
            "Status: " + tilt_direction
        )

        label_gx.setText(
            "Gx: {:.1f}".format(gx - gyro_offset_x)
        )

        label_gy.setText(
            "Gy: {:.1f}".format(gy - gyro_offset_y)
        )

        label_gz.setText(
            "Gz: {:.1f}".format(gz - gyro_offset_z)
        )

        label_roll.setText(
            "Roll: {:.1f} deg".format(roll_angle)
        )

        label_pitch.setText(
            "Pitch: {:.1f} deg".format(pitch_angle)
        )

        draw_tilt_indicator(
            roll_angle,
            pitch_angle
        )

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
