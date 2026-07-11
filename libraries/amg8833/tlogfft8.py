"""
thermal_logfft8.py

MicroPython library for converting an 8 x 8 flattened thermal image into
a normalized log-FFT 1D feature vector of the same size.

Designed for M5StickS3 / UIFlow 2.0 MicroPython.

Main use case
-------------
Input:
    64 thermal pixel values arranged as a flattened 8 x 8 image.

Processing:
    1. Normalize the flattened thermal image.
    2. Perform a 2-D FFT.
    3. Convert FFT coefficients into log magnitude values.
    4. Optionally apply FFT shift.
    5. Normalize the output vector.

Output:
    64-value 1D log-FFT feature vector.

Notes
-----
- No NumPy is required.
- The 2-D FFT is implemented using a radix-2 1-D FFT on rows and columns.
- The default size is 8 x 8, which matches the AMG8833 thermal array.
- The flattened input and output use row-major order.
"""

import math


class ThermalLogFFT8:
    # Input normalization modes
    NORMALIZE_MINMAX = "minmax"
    NORMALIZE_ZSCORE = "zscore"
    NORMALIZE_FIXED = "fixed"
    NORMALIZE_NONE = "none"

    # Output normalization modes
    OUTPUT_NONE = "none"
    OUTPUT_MINMAX = "minmax"
    OUTPUT_BYTE = "byte"

    def __init__(
        self,
        input_normalization=NORMALIZE_MINMAX,
        output_normalization=OUTPUT_MINMAX,
        fixed_min=20.0,
        fixed_max=40.0,
        epsilon=1e-6,
        remove_dc=False
    ):
        self.size = 8
        self.pixel_count = 64

        self.input_normalization = input_normalization
        self.output_normalization = output_normalization

        self.fixed_min = float(fixed_min)
        self.fixed_max = float(fixed_max)
        self.epsilon = float(epsilon)
        self.remove_dc = bool(remove_dc)

        # Precompute twiddle-factor tables for 8-point FFT.
        self._cos_table = [0.0] * (self.size // 2)
        self._sin_table = [0.0] * (self.size // 2)

        for index in range(self.size // 2):
            angle = -2.0 * math.pi * index / self.size
            self._cos_table[index] = math.cos(angle)
            self._sin_table[index] = math.sin(angle)

    # -------------------------------------------------------------
    # Utility helpers
    # -------------------------------------------------------------
    @staticmethod
    def _clamp(value, low, high):
        if value < low:
            return low

        if value > high:
            return high

        return value

    def _check_flat_image(self, flat_pixels):
        if flat_pixels is None:
            raise ValueError("flat_pixels cannot be None")

        if len(flat_pixels) != self.pixel_count:
            raise ValueError(
                "Expected 64 pixels for an 8 x 8 image"
            )

    # -------------------------------------------------------------
    # Input normalization
    # -------------------------------------------------------------
    def normalize_pixels(self, flat_pixels, mode=None):
        """Normalize the 8 x 8 flattened thermal image before FFT.

        Supported modes:
            minmax : current frame minimum maps to 0.0 and maximum to 1.0
            zscore : subtract mean and divide by standard deviation
            fixed  : fixed_min maps to 0.0 and fixed_max maps to 1.0
            none   : use the original values as floats
        """
        self._check_flat_image(flat_pixels)

        if mode is None:
            mode = self.input_normalization

        data = [float(value) for value in flat_pixels]

        if mode == self.NORMALIZE_NONE:
            return data

        if mode == self.NORMALIZE_MINMAX:
            minimum = min(data)
            maximum = max(data)
            span = maximum - minimum

            if abs(span) < self.epsilon:
                return [0.0] * self.pixel_count

            return [
                (value - minimum) / span
                for value in data
            ]

        if mode == self.NORMALIZE_FIXED:
            span = self.fixed_max - self.fixed_min

            if abs(span) < self.epsilon:
                return [0.0] * self.pixel_count

            return [
                self._clamp(
                    (value - self.fixed_min) / span,
                    0.0,
                    1.0
                )
                for value in data
            ]

        if mode == self.NORMALIZE_ZSCORE:
            mean = sum(data) / len(data)

            variance = sum(
                (value - mean) * (value - mean)
                for value in data
            ) / len(data)

            stddev = math.sqrt(variance)

            if stddev < self.epsilon:
                return [0.0] * self.pixel_count

            return [
                (value - mean) / stddev
                for value in data
            ]

        raise ValueError(
            "Unsupported normalization mode: " + str(mode)
        )

    # -------------------------------------------------------------
    # 1-D FFT
    # -------------------------------------------------------------
    def _fft_1d_inplace(self, real, imag):
        """In-place radix-2 Cooley-Tukey FFT for 8 samples."""
        n = self.size

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

        # FFT butterfly stages
        length = 2

        while length <= n:
            half = length // 2
            table_step = n // length

            for start in range(0, n, length):
                table_index = 0

                for offset in range(half):
                    index_even = start + offset
                    index_odd = index_even + half

                    wr = self._cos_table[table_index]
                    wi = self._sin_table[table_index]

                    odd_real = real[index_odd]
                    odd_imag = imag[index_odd]

                    temp_real = (
                        wr * odd_real -
                        wi * odd_imag
                    )

                    temp_imag = (
                        wr * odd_imag +
                        wi * odd_real
                    )

                    even_real = real[index_even]
                    even_imag = imag[index_even]

                    real[index_odd] = even_real - temp_real
                    imag[index_odd] = even_imag - temp_imag

                    real[index_even] = even_real + temp_real
                    imag[index_even] = even_imag + temp_imag

                    table_index += table_step

            length <<= 1

    # -------------------------------------------------------------
    # 2-D FFT
    # -------------------------------------------------------------
    def fft2d(self, normalized_pixels):
        """Return 2-D FFT result as flattened real and imaginary lists."""
        self._check_flat_image(normalized_pixels)

        n = self.size

        real = [float(value) for value in normalized_pixels]
        imag = [0.0] * self.pixel_count

        # Apply 1-D FFT to each row.
        for row in range(n):
            start = row * n
            end = start + n

            row_real = real[start:end]
            row_imag = imag[start:end]

            self._fft_1d_inplace(row_real, row_imag)

            real[start:end] = row_real
            imag[start:end] = row_imag

        # Apply 1-D FFT to each column.
        for column in range(n):
            column_real = [0.0] * n
            column_imag = [0.0] * n

            for row in range(n):
                index = row * n + column
                column_real[row] = real[index]
                column_imag[row] = imag[index]

            self._fft_1d_inplace(
                column_real,
                column_imag
            )

            for row in range(n):
                index = row * n + column
                real[index] = column_real[row]
                imag[index] = column_imag[row]

        return real, imag

    # -------------------------------------------------------------
    # Log magnitude
    # -------------------------------------------------------------
    def log_magnitude(self, real, imag):
        """Convert FFT real/imaginary values into log-magnitude values."""
        self._check_flat_image(real)
        self._check_flat_image(imag)

        output = [0.0] * self.pixel_count

        for index in range(self.pixel_count):
            magnitude = math.sqrt(
                real[index] * real[index] +
                imag[index] * imag[index]
            )

            output[index] = math.log(
                1.0 + magnitude
            )

        if self.remove_dc:
            output[0] = 0.0

        return output

    # -------------------------------------------------------------
    # FFT shift
    # -------------------------------------------------------------
    def fftshift_flat(self, flat_values):
        """Move the zero-frequency component to the centre.

        This is useful if the log-FFT vector is displayed as an 8 x 8 image.
        For AI use, shifted or unshifted vectors are both acceptable as long
        as the same setting is used during training and inference.
        """
        self._check_flat_image(flat_values)

        n = self.size
        half = n // 2

        shifted = [0.0] * self.pixel_count

        for row in range(n):
            for column in range(n):
                source_index = row * n + column

                target_row = (row + half) % n
                target_column = (column + half) % n
                target_index = target_row * n + target_column

                shifted[target_index] = flat_values[source_index]

        return shifted

    # -------------------------------------------------------------
    # Output normalization
    # -------------------------------------------------------------
    def normalize_output(self, values, mode=None):
        """Normalize the 64-value log-FFT vector."""
        self._check_flat_image(values)

        if mode is None:
            mode = self.output_normalization

        data = [float(value) for value in values]

        if mode == self.OUTPUT_NONE:
            return data

        minimum = min(data)
        maximum = max(data)
        span = maximum - minimum

        if abs(span) < self.epsilon:
            if mode == self.OUTPUT_BYTE:
                return [0] * self.pixel_count

            return [0.0] * self.pixel_count

        if mode == self.OUTPUT_MINMAX:
            return [
                (value - minimum) / span
                for value in data
            ]

        if mode == self.OUTPUT_BYTE:
            return [
                int(
                    self._clamp(
                        round(
                            ((value - minimum) / span) * 255.0
                        ),
                        0,
                        255
                    )
                )
                for value in data
            ]

        raise ValueError(
            "Unsupported output normalization mode: " + str(mode)
        )

    # -------------------------------------------------------------
    # Complete conversion pipeline
    # -------------------------------------------------------------
    def transform(
        self,
        flat_pixels,
        input_normalization=None,
        output_normalization=None,
        shift=False
    ):
        """Convert 8 x 8 flattened thermal pixels into a 64-value log-FFT vector.

        Args:
            flat_pixels:
                A list, tuple, or bytearray containing 64 thermal pixels.

            input_normalization:
                Optional override for the input normalization mode.

            output_normalization:
                Optional override for output vector normalization.

            shift:
                If True, apply FFT shift before output normalization.

        Returns:
            A 64-value 1D log-FFT feature vector.
        """
        normalized = self.normalize_pixels(
            flat_pixels,
            mode=input_normalization
        )

        real, imag = self.fft2d(
            normalized
        )

        log_fft = self.log_magnitude(
            real,
            imag
        )

        if shift:
            log_fft = self.fftshift_flat(
                log_fft
            )

        return self.normalize_output(
            log_fft,
            mode=output_normalization
        )

    def transform_to_bytes(
        self,
        flat_pixels,
        input_normalization=None,
        shift=False
    ):
        """Return the log-FFT vector as 64 byte values from 0 to 255."""
        byte_values = self.transform(
            flat_pixels,
            input_normalization=input_normalization,
            output_normalization=self.OUTPUT_BYTE,
            shift=shift
        )

        return bytearray(byte_values)

    # -------------------------------------------------------------
    # Convenience helpers
    # -------------------------------------------------------------
    def get_vector_length(self):
        return self.pixel_count

    def get_image_size(self):
        return self.size, self.size


# Friendly aliases
LogFFT8 = ThermalLogFFT8
ThermalFFT8 = ThermalLogFFT8
