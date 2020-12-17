import logging
from .waveshare_config import WaveshareConfig

# Display resolution.
WIDTH = 800
HEIGHT = 480

class Waveshare7in5V2:
    def __init__(self):
        self.width = WIDTH
        self.height = HEIGHT
        self.pin_cs = WaveshareConfig.PIN_CS
        self.pin_dc = WaveshareConfig.PIN_DC
        self.pin_busy = WaveshareConfig.PIN_BUSY
        self.pin_reset = WaveshareConfig.PIN_RESET

        self.waveshare_config = WaveshareConfig()

    # Hardware reset.
    def do_reset(self):
        logging.debug('Resetting the display controller')

        self.waveshare_config.digital_write(self.pin_reset, 1)
        self.waveshare_config.delay_ms(200)

        self.waveshare_config.digital_write(self.pin_reset, 0)
        self.waveshare_config.delay_ms(2)

        self.waveshare_config.digital_write(self.pin_reset, 1)
        self.waveshare_config.delay_ms(200)

    def send_command(self, command):
        #logging.debug('Sending command = 0x%.2X', command)

        self.waveshare_config.digital_write(self.pin_dc, 0)
        self.waveshare_config.digital_write(self.pin_cs, 0)

        self.waveshare_config.spi_write_byte([command])

        self.waveshare_config.digital_write(self.pin_cs, 1)

    def send_data(self, data):
        self.waveshare_config.digital_write(self.pin_dc, 1)
        self.waveshare_config.digital_write(self.pin_cs, 0)

        self.waveshare_config.spi_write_byte([data])

        self.waveshare_config.digital_write(self.pin_cs, 1)

    def read_busy(self):
        logging.debug('Display busy')

        self.send_command(0x71)

        busy = self.waveshare_config.digital_read(self.pin_busy)

        while(busy == 0):
            self.send_command(0x71)

            busy = self.waveshare_config.digital_read(self.pin_busy)

        self.waveshare_config.delay_ms(200)

    def init(self):
        logging.debug('Initialising')

        if (self.waveshare_config.init() != 0):
            return -1

        self.do_reset()
        
        self.send_command(0x01) # Power setting.

        self.send_data(0x07)
        self.send_data(0x07) # VGH = 20V, VGL = -20V.
        self.send_data(0x3f) # VDH = 15V.
        self.send_data(0x3f) # VDL = -15V.

        self.send_command(0x04) # Power on.

        self.waveshare_config.delay_ms(100)

        self.read_busy()

        self.send_command(0X00) # Panel setting.

        self.send_data(0x1F)

        self.send_command(0x61) # TRES.

        self.send_data(0x03) # Source 800.
        self.send_data(0x20)
        self.send_data(0x01) # Gate 480.
        self.send_data(0xE0)

        self.send_command(0X15)
    
        self.send_data(0x00)

        self.send_command(0X50) # VCOM amd data interval settings.

        self.send_data(0x10)
        self.send_data(0x07)

        self.send_command(0X60) # TCON setting.

        self.send_data(0x22)

        return 0

    def get_image_buffer(self, image):
        logging.debug('Getting image buffer')

        image_monocolor = image.convert('1')
        image_width, image_height = image_monocolor.size
        image_pixels = image_monocolor.load()

        buffer = [0xFF] * (int(self.width / 8) * self.height)

        if((image_width == self.width) and (image_height == self.height)):
            for y in range(image_height):
                for x in range(image_width):
                    # Set the bits for the column of pixels at the current position.
                    if image_pixels[x, y] == 0:
                        buffer[int((x + y * self.width) / 8)] &= ~(0x80 >> (x % 8))
        elif((image_width == self.height) and (image_width == self.width)):
            for y in range(image_width):
                for x in range(image_width):
                    new_x = y
                    new_y = self.height - x - 1

                    if image_pixels[x, y] == 0:
                        buffer[int((new_x + new_y * self.width) / 8)] &= ~(0x80 >> (y % 8))

        return buffer

    def display(self, image):
        logging.debug('Displaying')

        self.send_command(0x13)

        for i in range(0, int((self.width * self.height) / 8)):
            self.send_data(~image[i])

        self.send_command(0x12)
        self.waveshare_config.delay_ms(100)

        self.read_busy()

    def do_clear(self):
        logging.debug('Clearing display')

        self.send_command(0x10)

        for _ in range(0, int((self.width * self.height) / 8)):
            self.send_data(0x00)

        self.send_command(0x13)

        for _ in range(0, int((self.width * self.height) / 8)):
            self.send_data(0x00)

        self.send_command(0x12)
        self.waveshare_config.delay_ms(100)

        self.read_busy()

    def do_sleep(self):
        logging.debug('Going to sleep')

        self.send_command(0x02) # Power off.

        self.read_busy()

        self.send_command(0x07) # Deep sleep.
        self.send_data(0XA5)

        self.waveshare_config.exit()
