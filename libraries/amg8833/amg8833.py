"""
AMG8833 Grid-EYE MicroPython library for M5StickS3 / UIFlow 2.0.

Features
--------
- Default I2C address 0x69
- Reads the 8 x 8 thermopile temperature array
- Reads the internal thermistor temperature
- Configurable frame rate and operating mode
- Software emissivity correction using the thermistor as reflected temperature
- Flattened and 2-D sensor data
- Minimum, maximum, average, and pixel-location helpers
- Thermal-image rendering on the M5StickS3 LCD
- RGB888 rainbow colour map: cold is blue, mid-range is cyan/green/yellow, hot is red

The AMG8833 returns 64 pixels in row-major order. Pixel index 0 is row 0,
column 0; pixel index 63 is row 7, column 7.
"""

__version__ = "1.2.3-rgb888-rainbow-no-flicker"

try:
    import math
except ImportError:
    math = None


class AMG8833:
    DEFAULT_ADDRESS = 0x69
    ROWS = 8
    COLS = 8
    PIXEL_COUNT = 64

    # Register map
    REG_PCTL = 0x00
    REG_RST = 0x01
    REG_FPSC = 0x02
    REG_INTC = 0x03
    REG_STAT = 0x04
    REG_SCLR = 0x05
    REG_AVE = 0x07
    REG_TTHL = 0x0E
    REG_TTHH = 0x0F
    REG_PIXEL_BASE = 0x80

    # Operating modes
    MODE_NORMAL = 0x00
    MODE_SLEEP = 0x10
    MODE_STANDBY_60S = 0x20
    MODE_STANDBY_10S = 0x21

    # Reset commands
    RESET_FLAG = 0x30
    RESET_INITIAL = 0x3F

    # Frame-rate values
    FPS_10 = 0x00
    FPS_1 = 0x01

    def __init__(self, i2c, address=DEFAULT_ADDRESS, emissivity=1.0,
                 frame_rate=10, auto_start=True):
        self.i2c = i2c
        self.address = address
        self._emissivity = 1.0
        self._pixels = [0.0] * self.PIXEL_COUNT
        self._thermistor = 0.0

        # Display cache used by draw_thermal_image() to avoid redrawing
        # unchanged cells and to reduce visible flicker.
        self._last_draw_colors = None
        self._last_hot_index = None
        self._last_draw_geometry = None

        self.set_emissivity(emissivity)

        if auto_start:
            self.begin(frame_rate=frame_rate)

    # -------------------------------------------------------------
    # Low-level I2C helpers
    # -------------------------------------------------------------
    def _write8(self, register, value):
        self.i2c.writeto_mem(
            self.address,
            register,
            bytes((value & 0xFF,))
        )

    def _read(self, register, length):
        return self.i2c.readfrom_mem(
            self.address,
            register,
            length
        )

    # -------------------------------------------------------------
    # Device configuration
    # -------------------------------------------------------------
    def begin(self, frame_rate=10):
        self.set_mode(self.MODE_NORMAL)
        self.reset()
        self.set_frame_rate(frame_rate)
        return True

    def reset(self):
        self._write8(self.REG_RST, self.RESET_INITIAL)

    def clear_status(self):
        self._write8(self.REG_SCLR, 0x0E)

    def set_mode(self, mode):
        if mode not in (
            self.MODE_NORMAL,
            self.MODE_SLEEP,
            self.MODE_STANDBY_60S,
            self.MODE_STANDBY_10S
        ):
            raise ValueError("Unsupported AMG8833 operating mode")

        self._write8(self.REG_PCTL, mode)

    def sleep(self):
        self.set_mode(self.MODE_SLEEP)

    def wake(self):
        self.set_mode(self.MODE_NORMAL)

    def set_frame_rate(self, frames_per_second):
        if frames_per_second == 10:
            value = self.FPS_10
        elif frames_per_second == 1:
            value = self.FPS_1
        else:
            raise ValueError("Frame rate must be 1 or 10 frames per second")

        self._write8(self.REG_FPSC, value)

    def set_moving_average(self, enabled):
        # Panasonic's moving-average control uses the undocumented-looking
        # sequence commonly specified for the AMG88xx family.
        if enabled:
            self._write8(0x1F, 0x50)
            self._write8(0x1F, 0x45)
            self._write8(0x1F, 0x57)
            self._write8(self.REG_AVE, 0x20)
            self._write8(0x1F, 0x00)
        else:
            self._write8(0x1F, 0x50)
            self._write8(0x1F, 0x45)
            self._write8(0x1F, 0x57)
            self._write8(self.REG_AVE, 0x00)
            self._write8(0x1F, 0x00)

    # -------------------------------------------------------------
    # Emissivity
    # -------------------------------------------------------------
    def set_emissivity(self, emissivity):
        emissivity = float(emissivity)
        if emissivity <= 0.0 or emissivity > 1.0:
            raise ValueError("Emissivity must be greater than 0 and at most 1")
        self._emissivity = emissivity

    def get_emissivity(self):
        return self._emissivity

    # -------------------------------------------------------------
    # Temperature conversion
    # -------------------------------------------------------------
    @staticmethod
    def _signed_12bit(raw):
        raw &= 0x0FFF
        if raw & 0x0800:
            raw -= 0x1000
        return raw

    def read_thermistor(self):
        data = self._read(self.REG_TTHL, 2)
        raw = data[0] | (data[1] << 8)
        raw = self._signed_12bit(raw)
        self._thermistor = raw * 0.0625
        return self._thermistor

    def _apply_emissivity(self, measured_c, reflected_c):
        """Apply software emissivity correction.

        The sensor pixel is treated as an apparent radiant temperature. The
        internal thermistor is used as an approximation of reflected ambient
        temperature. For emissivity 1.0, the measured value is returned.
        """
        e = self._emissivity
        if e >= 0.9999 or math is None:
            return measured_c

        measured_k = measured_c + 273.15
        reflected_k = reflected_c + 273.15

        if measured_k <= 0.0 or reflected_k <= 0.0:
            return measured_c

        radiant_4 = measured_k ** 4
        reflected_4 = reflected_k ** 4
        corrected_4 = (
            radiant_4 - ((1.0 - e) * reflected_4)
        ) / e

        if corrected_4 <= 0.0:
            return measured_c

        return (corrected_4 ** 0.25) - 273.15

    def read_pixels_flat(self, apply_emissivity=True):
        """Read and return all 64 temperatures as a flat row-major list."""
        data = self._read(self.REG_PIXEL_BASE, self.PIXEL_COUNT * 2)

        if apply_emissivity and self._emissivity < 0.9999:
            reflected_c = self.read_thermistor()
        else:
            reflected_c = 0.0

        pixels = self._pixels
        for index in range(self.PIXEL_COUNT):
            offset = index * 2
            raw = data[offset] | (data[offset + 1] << 8)
            raw = self._signed_12bit(raw)
            temperature = raw * 0.25

            if apply_emissivity:
                temperature = self._apply_emissivity(
                    temperature,
                    reflected_c
                )

            pixels[index] = temperature

        return list(pixels)

    # Alias requested by many applications
    def get_flattened_data(self, refresh=True, apply_emissivity=True):
        if refresh:
            return self.read_pixels_flat(apply_emissivity)
        return list(self._pixels)

    def read_pixels(self, apply_emissivity=True):
        flat = self.read_pixels_flat(apply_emissivity)
        return [
            flat[row * self.COLS:(row + 1) * self.COLS]
            for row in range(self.ROWS)
        ]

    def get_pixels(self, refresh=True, apply_emissivity=True):
        if refresh:
            return self.read_pixels(apply_emissivity)

        flat = self._pixels
        return [
            list(flat[row * self.COLS:(row + 1) * self.COLS])
            for row in range(self.ROWS)
        ]

    # -------------------------------------------------------------
    # Statistical helpers
    # -------------------------------------------------------------
    def _data(self, refresh):
        if refresh:
            return self.read_pixels_flat()
        return self._pixels

    def get_highest_temperature(self, refresh=True):
        return max(self._data(refresh))

    def get_lowest_temperature(self, refresh=True):
        return min(self._data(refresh))

    def get_average_temperature(self, refresh=True):
        data = self._data(refresh)
        return sum(data) / len(data)

    def get_highest_index(self, refresh=True):
        data = self._data(refresh)
        highest = max(data)
        return data.index(highest)

    def get_lowest_index(self, refresh=True):
        data = self._data(refresh)
        lowest = min(data)
        return data.index(lowest)

    def index_to_location(self, index):
        if index < 0 or index >= self.PIXEL_COUNT:
            raise ValueError("Pixel index must be from 0 to 63")
        return index // self.COLS, index % self.COLS

    def get_highest_location(self, refresh=True):
        index = self.get_highest_index(refresh)
        row, column = self.index_to_location(index)
        return row, column

    def get_lowest_location(self, refresh=True):
        index = self.get_lowest_index(refresh)
        row, column = self.index_to_location(index)
        return row, column

    def get_statistics(self, refresh=True):
        data = self._data(refresh)
        minimum = min(data)
        maximum = max(data)
        min_index = data.index(minimum)
        max_index = data.index(maximum)

        return {
            "minimum": minimum,
            "maximum": maximum,
            "average": sum(data) / len(data),
            "minimum_index": min_index,
            "maximum_index": max_index,
            "minimum_location": self.index_to_location(min_index),
            "maximum_location": self.index_to_location(max_index),
        }

    # -------------------------------------------------------------
    # Thermal image display
    # -------------------------------------------------------------
    @staticmethod
    def _rgb888(red, green, blue):
        """Return a 24-bit RGB colour for UIFlow 2.0 LCD drawing.

        UIFlow 2.0 display functions use 0xRRGGBB-style colours.
        Therefore red must be 0xFF0000 and blue must be 0x0000FF.
        Using RGB565 values such as 0xF800 can appear greenish on the
        M5StickS3 LCD because 0xF800 is interpreted as 0x00F800.
        """
        red = int(red) & 0xFF
        green = int(green) & 0xFF
        blue = int(blue) & 0xFF
        return (red << 16) | (green << 8) | blue

    @classmethod
    def _heat_color(cls, value):
        """Map 0.0 to 1.0 onto an RGB888 rainbow heat map.

        Colour scale:
        0.00 -> blue
        0.25 -> cyan
        0.50 -> green
        0.75 -> yellow
        1.00 -> red

        This uses 24-bit RGB colours for UIFlow 2.0 LCD drawing.
        """
        if value < 0.0:
            value = 0.0
        elif value > 1.0:
            value = 1.0

        position = value * 4.0
        segment = int(position)
        fraction = position - segment

        if segment <= 0:
            # Blue to cyan
            red = 0
            green = 255 * fraction
            blue = 255

        elif segment == 1:
            # Cyan to green
            red = 0
            green = 255
            blue = 255 * (1.0 - fraction)

        elif segment == 2:
            # Green to yellow
            red = 255 * fraction
            green = 255
            blue = 0

        elif segment == 3:
            # Yellow to red
            red = 255
            green = 255 * (1.0 - fraction)
            blue = 0

        else:
            red = 255
            green = 0
            blue = 0

        return cls._rgb888(red, green, blue)

    @staticmethod
    def _lcd_fill_rect(lcd, x, y, width, height, color):
        if hasattr(lcd, "fillRect"):
            lcd.fillRect(x, y, width, height, color)
        elif hasattr(lcd, "fill_rect"):
            lcd.fill_rect(x, y, width, height, color)
        else:
            raise AttributeError("LCD object does not provide fillRect/fill_rect")

    @staticmethod
    def _lcd_draw_text(lcd, text, x, y, color, background=0x0000):
        try:
            if hasattr(lcd, "setTextColor"):
                lcd.setTextColor(color, background)
            if hasattr(lcd, "drawString"):
                lcd.drawString(str(text), x, y)
            elif hasattr(lcd, "text"):
                lcd.text(str(text), x, y, color)
        except Exception:
            pass


    def reset_display_cache(self):
        """Clear the display cache used by draw_thermal_image().

        Call this after changing colour palettes, screen rotation, drawing
        size, or after overwriting the image area manually.
        """
        self._last_draw_colors = None
        self._last_hot_index = None
        self._last_draw_geometry = None

    def draw_thermal_image(
        self,
        lcd=None,
        x=0,
        y=0,
        width=192,
        height=128,
        minimum=None,
        maximum=None,
        refresh=True,
        show_hotspot=True,
        show_values=False,
        background=0x0000,
        clear_background=False,
        only_changed=True,
        color_steps=32
    ):
        """Draw an 8 x 8 thermal image with reduced flicker.

        The image area is not erased before each frame unless
        ``clear_background`` is True. When ``only_changed`` is True, only
        cells whose displayed colour changed are redrawn. ``color_steps``
        reduces small colour changes caused by sensor noise.
        """
        if lcd is None:
            import M5
            lcd = M5.Lcd

        if refresh:
            data = self.read_pixels_flat()
        else:
            data = list(self._pixels)

        frame_min = min(data)
        frame_max = max(data)
        scale_min = frame_min if minimum is None else float(minimum)
        scale_max = frame_max if maximum is None else float(maximum)

        if scale_max <= scale_min:
            scale_max = scale_min + 1.0

        cell_width = max(1, width // self.COLS)
        cell_height = max(1, height // self.ROWS)
        draw_width = cell_width * self.COLS
        draw_height = cell_height * self.ROWS
        geometry = (x, y, cell_width, cell_height, draw_width, draw_height)

        if color_steps is None or color_steps < 2:
            color_steps = 256

        colors = [0] * self.PIXEL_COUNT

        for index in range(self.PIXEL_COUNT):
            normalized = (data[index] - scale_min) / (scale_max - scale_min)

            if normalized < 0.0:
                normalized = 0.0
            elif normalized > 1.0:
                normalized = 1.0

            # Quantise the palette so tiny temperature fluctuations do not
            # force every cell to be repainted on every frame.
            normalized = round(normalized * (color_steps - 1)) / (color_steps - 1)
            colors[index] = self._heat_color(normalized)

        hot_index = data.index(frame_max)

        geometry_changed = self._last_draw_geometry != geometry
        first_frame = self._last_draw_colors is None or geometry_changed

        # A full clear is needed only for the first frame, changed geometry,
        # or when explicitly requested by the application.
        if clear_background or geometry_changed:
            self._lcd_fill_rect(
                lcd, x, y, draw_width, draw_height, background
            )

        # Batch LCD writes when the UIFlow display driver supports it.
        started_write = False
        if hasattr(lcd, "startWrite"):
            try:
                lcd.startWrite()
                started_write = True
            except Exception:
                started_write = False

        try:
            previous_colors = self._last_draw_colors
            previous_hot = self._last_hot_index

            for row in range(self.ROWS):
                for column in range(self.COLS):
                    index = row * self.COLS + column

                    redraw = first_frame or not only_changed

                    if not redraw and previous_colors[index] != colors[index]:
                        redraw = True

                    # Redraw the previous and current hotspot cells so the old
                    # white border disappears and the new one is accurate.
                    if index == previous_hot or index == hot_index:
                        redraw = True

                    if not redraw:
                        continue

                    cell_x = x + (column * cell_width)
                    cell_y = y + (row * cell_height)
                    color = colors[index]

                    self._lcd_fill_rect(
                        lcd,
                        cell_x,
                        cell_y,
                        cell_width,
                        cell_height,
                        color
                    )

                    if (
                        show_values and
                        cell_width >= 22 and
                        cell_height >= 14
                    ):
                        self._lcd_draw_text(
                            lcd,
                            "{:.0f}".format(data[index]),
                            cell_x + 2,
                            cell_y + 2,
                            0xFFFFFF,
                            color
                        )

            if show_hotspot:
                hot_row, hot_column = self.index_to_location(hot_index)
                hot_x = x + hot_column * cell_width
                hot_y = y + hot_row * cell_height

                self._lcd_fill_rect(
                    lcd, hot_x, hot_y, cell_width, 1, 0xFFFFFF
                )
                self._lcd_fill_rect(
                    lcd,
                    hot_x,
                    hot_y + cell_height - 1,
                    cell_width,
                    1,
                    0xFFFFFF
                )
                self._lcd_fill_rect(
                    lcd, hot_x, hot_y, 1, cell_height, 0xFFFFFF
                )
                self._lcd_fill_rect(
                    lcd,
                    hot_x + cell_width - 1,
                    hot_y,
                    1,
                    cell_height,
                    0xFFFFFF
                )

        finally:
            if started_write and hasattr(lcd, "endWrite"):
                try:
                    lcd.endWrite()
                except Exception:
                    pass

        self._last_draw_colors = colors
        self._last_hot_index = hot_index
        self._last_draw_geometry = geometry

        return {
            "minimum": frame_min,
            "maximum": frame_max,
            "average": sum(data) / len(data),
            "maximum_index": hot_index,
            "maximum_location": self.index_to_location(hot_index),
            "scale_minimum": scale_min,
            "scale_maximum": scale_max,
        }

    # Friendly aliases
    thermal_image = draw_thermal_image
    get_max_temperature = get_highest_temperature
    get_min_temperature = get_lowest_temperature
    get_mean_temperature = get_average_temperature
