import os
import sys
import time
import spidev
import logging
import RPi.GPIO

class WaveshareConfig:
    PIN_CS = 8
    PIN_DC = 25
    PIN_BUSY = 24
    PIN_RESET = 17

    def __init__(self):
        self.GPIO = RPi.GPIO

        # SPI device, bus = 0, device = 0.
        self.SPI = spidev.SpiDev(0, 0)

    def digital_write(self, pin, value):
        self.GPIO.output(pin, value)

    def digital_read(self, pin):
        return self.GPIO.input(pin)

    def delay_ms(self, duration):
        time.sleep(duration / 1000.0)

    def spi_write_byte(self, data):
        self.SPI.writebytes(data)

    def init(self):
        logging.debug('SPI init')

        self.GPIO.setwarnings(False)
        self.GPIO.setmode(self.GPIO.BCM)

        self.GPIO.setup(self.PIN_DC, self.GPIO.OUT)
        self.GPIO.setup(self.PIN_CS, self.GPIO.OUT)
        self.GPIO.setup(self.PIN_BUSY, self.GPIO.IN)
        self.GPIO.setup(self.PIN_RESET, self.GPIO.OUT)

        self.SPI.mode = 0b00
        self.SPI.max_speed_hz = 4000000

        return 0

    def exit(self):
        logging.debug('SPI exit')

        self.SPI.close()

        logging.debug('Turning off display power')

        self.GPIO.output(self.PIN_RESET, 0)
        self.GPIO.output(self.PIN_DC, 0)

        self.GPIO.cleanup()
