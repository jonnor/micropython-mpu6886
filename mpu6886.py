# Copyright (c) 2020 Mika Tuupola
# Copyright (c) 2024 Jon Nordby (FIFO support)
#
# License: MIT
# https://github.com/jonnor/micropython-mpu6886

"""
MicroPython I2C driver for MPU6886 6-axis motion tracking device
"""

__version__ = "0.2.0-dev"

# pylint: disable=import-error
import struct
import time
from machine import I2C, Pin
from micropython import const
# pylint: enable=import-error

_CONFIG = const(0x1a)
_GYRO_CONFIG = const(0x1b)
_ACCEL_CONFIG = const(0x1c)
_ACCEL_CONFIG2 = const(0x1d)
_ACCEL_XOUT_H = const(0x3b)
_ACCEL_XOUT_L = const(0x3c)
_ACCEL_YOUT_H = const(0x3d)
_ACCEL_YOUT_L = const(0x3e)
_ACCEL_ZOUT_H = const(0x3f)
_ACCEL_ZOUT_L = const(0x40)
_TEMP_OUT_H = const(0x41)
_TEMP_OUT_L = const(0x42)
_GYRO_XOUT_H = const(0x43)
_GYRO_XOUT_L = const(0x44)
_GYRO_YOUT_H = const(0x45)
_GYRO_YOUT_L = const(0x46)
_GYRO_ZOUT_H = const(0x47)
_GYRO_ZOUT_L = const(0x48)
_PWR_MGMT_1 = const(0x6b)
_WHO_AM_I = const(0x75)

ACCEL_FS_SEL_2G = const(0b00000000)
ACCEL_FS_SEL_4G = const(0b00001000)
ACCEL_FS_SEL_8G = const(0b00010000)
ACCEL_FS_SEL_16G = const(0b00011000)

_ACCEL_SO_2G = 16384 # 1 / 16384 ie. 0.061 mg / digit
_ACCEL_SO_4G = 8192 # 1 / 8192 ie. 0.122 mg / digit
_ACCEL_SO_8G = 4096 # 1 / 4096 ie. 0.244 mg / digit
_ACCEL_SO_16G = 2048 # 1 / 2048 ie. 0.488 mg / digit

GYRO_FS_SEL_250DPS = const(0b00000000)
GYRO_FS_SEL_500DPS = const(0b00001000)
GYRO_FS_SEL_1000DPS = const(0b00010000)
GYRO_FS_SEL_2000DPS = const(0b00011000)

_GYRO_SO_250DPS = 131
_GYRO_SO_500DPS = 62.5
_GYRO_SO_1000DPS = 32.8
_GYRO_SO_2000DPS = 16.4

_TEMP_SO = 326.8
_TEMP_OFFSET = 25

SF_G = 1
SF_M_S2 = 9.80665 # 1 g = 9.80665 m/s2 ie. standard gravity
SF_DEG_S = 1
SF_RAD_S = 0.017453292519943 # 1 deg/s is 0.017453292519943 rad/s

class MPU6886:
    """Class which provides interface to MPU6886 6-axis motion tracking device."""
    def __init__(
        self, i2c, address=0x68,
        accel_fs=ACCEL_FS_SEL_2G, gyro_fs=GYRO_FS_SEL_250DPS,
        accel_sf=SF_M_S2, gyro_sf=SF_RAD_S,
        gyro_offset=(0, 0, 0)
    ):
        self.i2c = i2c
        self.address = address

        if 0x19 != self.whoami:
            raise RuntimeError("MPU6886 not found in I2C bus.")

        self._register_char(_PWR_MGMT_1, 0b10000000) # reset
        time.sleep_ms(100)
        self._register_char(_PWR_MGMT_1, 0b00000001) # autoselect clock

        self._accel_so = self._accel_fs(accel_fs)
        self._gyro_so = self._gyro_fs(gyro_fs)
        self._accel_sf = accel_sf
        self._gyro_sf = gyro_sf
        self._gyro_offset = gyro_offset

        self.bytes_per_sample = 8 # 3x2 bytes accelerometer, 2 bytes temperature

    @property
    def acceleration(self):
        """
        Acceleration measured by the sensor. By default will return a
        3-tuple of X, Y, Z axis acceleration values in m/s^2 as floats. Will
        return values in g if constructor was provided `accel_sf=SF_M_S2`
        parameter.
        """
        so = self._accel_so
        sf = self._accel_sf

        xyz = self._register_three_shorts(_ACCEL_XOUT_H)
        return tuple([value / so * sf for value in xyz])

    @property
    def gyro(self):
        """
        X, Y, Z radians per second as floats.
        """
        so = self._gyro_so
        sf = self._gyro_sf
        ox, oy, oz = self._gyro_offset

        xyz = self._register_three_shorts(_GYRO_XOUT_H)
        xyz = [value / so * sf for value in xyz]

        xyz[0] -= ox
        xyz[1] -= oy
        xyz[2] -= oz

        return tuple(xyz)

    @property
    def temperature(self):
        """
        Die temperature in celcius as a float.
        """
        temp = self._register_short(_TEMP_OUT_H)
        # return ((temp - _TEMP_OFFSET) / _TEMP_SO) + _TEMP_OFFSET
        return (temp / _TEMP_SO) +  _TEMP_OFFSET

    @property
    def whoami(self):
        """ Value of the whoami register. """
        return self._register_char(_WHO_AM_I)

    def calibrate(self, count=256, delay=0):
        ox, oy, oz = (0.0, 0.0, 0.0)
        self._gyro_offset = (0.0, 0.0, 0.0)
        n = float(count)

        while count:
            time.sleep_ms(delay)
            gx, gy, gz = self.gyro
            ox += gx
            oy += gy
            oz += gz
            count -= 1

        self._gyro_offset = (ox / n, oy / n, oz / n)
        return self._gyro_offset

    def _register_short(self, register, value=None, buf=bytearray(2)):
        if value is None:
            self.i2c.readfrom_mem_into(self.address, register, buf)
            return struct.unpack(">h", buf)[0]

        struct.pack_into(">h", buf, 0, value)
        return self.i2c.writeto_mem(self.address, register, buf)

    def _register_three_shorts(self, register, buf=bytearray(6)):
        self.i2c.readfrom_mem_into(self.address, register, buf)
        return struct.unpack(">hhh", buf)

    def _register_char(self, register, value=None, buf=bytearray(1)):
        if value is None:
            self.i2c.readfrom_mem_into(self.address, register, buf)
            return buf[0]

        struct.pack_into("<b", buf, 0, value)
        return self.i2c.writeto_mem(self.address, register, buf)

    def _accel_fs(self, value):
        self._register_char(_ACCEL_CONFIG, value)

        # Return the sensitivity divider
        if ACCEL_FS_SEL_2G == value:
            return _ACCEL_SO_2G
        elif ACCEL_FS_SEL_4G == value:
            return _ACCEL_SO_4G
        elif ACCEL_FS_SEL_8G == value:
            return _ACCEL_SO_8G
        elif ACCEL_FS_SEL_16G == value:
            return _ACCEL_SO_16G

    def _gyro_fs(self, value):
        self._register_char(_GYRO_CONFIG, value)

        # Return the sensitivity divider
        if GYRO_FS_SEL_250DPS == value:
            return _GYRO_SO_250DPS
        elif GYRO_FS_SEL_500DPS == value:
            return _GYRO_SO_500DPS
        elif GYRO_FS_SEL_1000DPS == value:
            return _GYRO_SO_1000DPS
        elif GYRO_FS_SEL_2000DPS == value:
            return _GYRO_SO_2000DPS

    def fifo_enable(self, enable):

        value = self._register_char(_CONFIG)
        FIFO_MODE_BIT = 6
        # should be cleared by user
        value &= ~(1 << 7)
        # clear FIFO_MODE, replace oldest data
        value &= ~(1 << FIFO_MODE_BIT)
        # set FIFO_MODE, no new writes
        #value |= (1 << FIFO_MODE_BIT)
        self._register_char(_CONFIG, value)

        REG_FIFO_EN = 0x23
        GYRO_FIFO_EN = 4
        ACCEL_FIFO_EN = 3

        value = self._register_char(REG_FIFO_EN)
        value |= (1 << ACCEL_FIFO_EN)
        self._register_char(REG_FIFO_EN, value)

        # TODO: support gyro
        #value |= (1 << GYRO_FIFO_EN)

        REG_USER_CTRL = 0x6A
        FIFO_EN = 6
        FIFO_RST = 2
        value = self._register_char(REG_USER_CTRL)
        value |= (1 << FIFO_EN)
        value |= (1 << FIFO_RST)
        self._register_char(REG_USER_CTRL, value)


    def set_odr(self, odr):
        REG_PWR_MGMT_1 = 0x6B
        CYCLE_BIT = 5
        REG_SMPLRT_DIV = 0x19
        REG_ACCEL_CONFIG2 = 0x1D
        REG_LP_MODE_CFG = 0x1E

        # enable low-power mode
        value = self._register_char(REG_PWR_MGMT_1)
        value |= (1 << CYCLE_BIT)
        self._register_char(REG_PWR_MGMT_1, value=value)

        samplerate_div = {
            10: 99,
            50: 19,
            100: 9,
            200: 4,
            250: 3,
        }

        value = self._register_char(REG_ACCEL_CONFIG2)
        # clear register
        value &= ~(0b111111)
        # average 4x samples
        # DEC2_CFG = 0
        # bits 5:4 and 3 stay cleared
        # low pass filter, A_DLPF_CFG = 7
        value |= 0b111        
        self._register_char(REG_ACCEL_CONFIG2, value=value)

        # NOTE: SMPLRT_DIV register is only effective when
        # FCHOICE_B register bits are 2’b00, and (0 < DLPF_CFG < 7).
        div = samplerate_div[odr]
        self._register_char(REG_SMPLRT_DIV, value=div)

        REG_GYRO_CONFIG = 0x1B
        value = self._register_char(REG_GYRO_CONFIG)
        value &= ~(0b11)  # FCHOICE_B = 0b00
        self._register_char(REG_GYRO_CONFIG, value=value)

        value = self._register_char(_CONFIG)
        value &= ~(1 << 7) # should be cleared by user
        # DLPF_CFG = 0b01
        value &= ~(0b111)
        value |= 0b1
        self._register_char(_CONFIG, value)

        # TODO: also setup gyro filters
        # REG_LP_MODE_CFG
        #G_AVGCFG = 2
        # 

    def get_fifo_count(self):
        """
        Return the number of samples ready in the FIFO
        """
        REG_FIFO_COUNTH = 0x72
        buf = bytearray(2)
        self.i2c.readfrom_mem_into(self.address, REG_FIFO_COUNTH, buf)
        fifo_bytes = struct.unpack('>H', buf)[0]
        fifo_count = fifo_bytes // self.bytes_per_sample
        return fifo_count

    def read_samples_into(self, buf):
        """
        Read accelerometer samples from the FIFO

        NOTE: caller is responsible for ensuring that enough samples are ready.
        Typically by calling get_fifo_count() first
        """
        n_bytes = len(buf)
        if (n_bytes % self.bytes_per_sample) != 0:
            raise ValueError("Buffer should be a multiple of 6")
        samples = n_bytes // self.bytes_per_sample
        if n_bytes > 1024:
            raise ValueError("Requested samples exceeds FIFO capacity")

        REG_FIFO_R_W = 0x74
        self.i2c.readfrom_mem_into(self.address, REG_FIFO_R_W, buf)

    def deinterleave_samples(self, buf : bytearray,
            xs, ys, zs):
        """
        Convert raw bytes into X,Y,Z int16 arrays
        """
        assert (len(buf) % self.bytes_per_sample) == 0
        samples = len(buf) // self.bytes_per_sample
        assert len(xs) == samples
        assert len(ys) == samples
        assert len(zs) == samples

        #view = memoryview(buf)
        for i in range(samples):
            # NOTE: temperature (follows z) is ignored
            x, y, z = struct.unpack_from('>hhh', buf, i*self.bytes_per_sample)
            xs[i] = x
            ys[i] = y
            zs[i] = z

