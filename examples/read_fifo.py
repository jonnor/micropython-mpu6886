
from machine import Pin, I2C
from mpu6886 import MPU6886

import time
import struct
import array
    

def int16_from_bytes(buf):
    # workaround for MicroPython missing array.frombytes 

    

    gen = (struct.unpack(">h", buf[i:i+3])[0] for i in range(0, len(buf), 2))
    arr = array.array('h', gen)
    assert len(arr) == len(buf)//2

    return arr

def deinterleave_samples(buf : bytearray,
        xs, ys, zs):
    """
    Convert raw bytes into X,Y,Z int16 arrays
    """
    bytes_per_sample = 8
    assert (len(buf) % bytes_per_sample) == 0
    samples = len(buf) // bytes_per_sample
    assert len(xs) == samples
    assert len(ys) == samples
    assert len(zs) == samples

    #view = memoryview(buf)
    for i in range(samples):
        # NOTE: temperature (follows z) is ignored
        x, y, z = struct.unpack_from('>hhh', buf, i*bytes_per_sample)
        xs[i] = x
        ys[i] = y
        zs[i] = z

class AccelerometerWindower():
    def __init__(self, length, hop):
        self.length = length
        self.hop = hop

    #def 

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
    mpu.set_odr(10)

    threshold = 10
    bytes_per_sample = 8 # XXYYZZTT, where TT is temperature
    chunk = bytearray(bytes_per_sample*threshold)

    x_values = empty_array('h', threshold)
    y_values = empty_array('h', threshold)
    z_values = empty_array('h', threshold)

    next_log = time.time() + 1.0
    samples_read = 0
    while True:

        count = mpu.get_fifo_count()
        if count >= threshold:
            mpu.read_samples_into(chunk)
            samples_read += threshold
            after = mpu.get_fifo_count()
            #print('read', count, len(chunk)//bytes_per_sample, after)
            #print(chunk)
            #data = int16_from_bytes(chunk)

            deinterleave_samples(chunk, x_values, y_values, z_values)

            print('xyz', mean(x_values), mean(y_values), mean(z_values))
            #t = mpu.temperature

            #tt = [ (v/326.8)+25.0 for v in data ]
            #print(data, tt, t)
        #    print(data)

        if time.time() >= next_log:
            print('status', time.time(), samples_read)
            next_log = time.time() + 1.0

        time.sleep_ms(1)


if __name__ == '__main__':
    main()
