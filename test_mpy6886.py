
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

    mpu.fifo_enable(True)
    mpu.set_odr(10)

    threshold = 5
    chunk = bytearray(3*2*threshold)

    next_log = time.time() + 1.0
    samples_read = 0
    while True:

        #a = mpu.acceleration
        #print(a)

        count = mpu.get_fifo_count()
        #print(count)
        if count >= threshold:
            mpu.read_samples_into(chunk)
        #    data = int16_from_bytes(chunk)
            samples_read += threshold
        #    print(data)

        if time.time() >= next_log:
            print(time.time(), samples_read)
            next_log = time.time() + 1.0

        time.sleep_ms(1)


if __name__ == '__main__':
    main()
