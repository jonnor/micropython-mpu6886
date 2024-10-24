
from machine import Pin, I2C
from mpu6886 import MPU6886

import time
import struct
import array
    

def int16_from_bytes(buf):
    # workaround for MicroPython missing array.frombytes 

    

    gen = (struct.unpack("<h", buf[i:i+3])[0] for i in range(0, len(buf), 2))
    arr = array.array('h', gen)
    assert len(arr) == len(buf)//2

    return arr

def main():

    i2c = I2C(sda=21, scl=22, freq=100000)
    mpu = MPU6886(i2c)

    threshold = 10
    chunk = bytearray(3*2*threshold)

    while True:

        count = mpu.get_fifo_count()
        if count >= threshold:
            accel.read_samples_into(chunk_buf)
            data = int16_from_bytes(chunk)

            print(data)

        time.sleep_ms(100)
