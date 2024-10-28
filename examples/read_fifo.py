
from machine import Pin, I2C
from mpu6886 import MPU6886

import time
import struct
import array
    

def empty_array(typecode, length, value=0):
    return array.array(typecode, (value for _ in range(length)))
    
def mean(arr):
    m = sum(arr) / float(len(arr))
    return m

def main():
    i2c = I2C(sda=21, scl=22, freq=100000)
    mpu = MPU6886(i2c)

    # Enable FIFO at a fixed samplerate
    mpu.fifo_enable(True)
    mpu.set_odr(100)

    hop_length = 50
    chunk = bytearray(mpu.bytes_per_sample*hop_length)

    x_values = empty_array('h', hop_length)
    y_values = empty_array('h', hop_length)
    z_values = empty_array('h', hop_length)

    while True:

        count = mpu.get_fifo_count()
        if count >= hop_length:
            mpu.read_samples_into(chunk)
            mpu.deinterleave_samples(chunk, x_values, y_values, z_values)
            x, y, z = mean(x_values), mean(y_values), mean(z_values)
            print(f'xyz: \t{x:.0f} \t{y:.0f} \t{z:.0f}' )

        time.sleep_ms(1)


if __name__ == '__main__':
    main()
