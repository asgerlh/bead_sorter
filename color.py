from machine import Pin
import machine
import asyncio
import time
import ustruct

class ColorSensor:
    """Class to interface with the TCS34725 color sensor, including LED control and RGB/C data reading.
    The sensor is initialized with the I2C interface and an optional LED pin for illumination control.
    i2c: An initialized I2C object for communication with the sensor.
    led_pin_num: GPIO pin number for controlling the sensor's LED (optional).
    address: I2C address of the TCS34725 sensor (default is 0x29).
    """
    def __init__(self, i2c, led_pin_num=None, address=0x29):
        self.i2c = i2c
        self.address = address
        
        # LED Control Setup
        if led_pin_num is not None:
            self.led = Pin(led_pin_num, Pin.OUT)
            self.led.value(0)
        else:
            self.led = None

        # Check ID (Should be 0x44 or 0x4D)
        cid = self._read_byte(0x12)
        if cid not in (0x44, 0x4D):
            raise RuntimeError(f"TCS34725 not found at 0x{address:02x}")

        # Enable the device (Power ON)
        self._write_byte(0x00, 0x01) # Power ON
        time.sleep_ms(100)
        integration_periods = 25  # 25 periods = 60ms integration time
        self.integration_time_ms = 2.4 * integration_periods
        self._write_byte(0x01, 0xFF - integration_periods) # Integration time
        self._write_byte(0x0F, 0x02) # Gain

    def _write_byte(self, reg, value):
        # 0x80 is the command bit required for every transaction
        self.i2c.writeto_mem(self.address, 0x80 | reg, bytes([value]))

    def _read_byte(self, reg):
        return self.i2c.readfrom_mem(self.address, 0x80 | reg, 1)[0]

    def _read_word(self, reg):
        data = self.i2c.readfrom_mem(self.address, 0x80 | reg, 2)
        return ustruct.unpack('<H', data)[0]

    def set_led(self, state):
        """Sets the LED state (True for ON, False for OFF)."""
        if self.led:
            self.led.value(1 if state else 0)

    def _read_rgbc(self):
        """
        Reads Clear, Red, Green, and Blue 16-bit values 
        atomically in one transaction.
        """
        # Start reading from CDATA (0x14). Read 8 bytes (2 bytes x 4 channels)
        # The command bit 0x80 is still required.
        data = self.i2c.readfrom_mem(self.address, 0x80 | 0x14, 8)
        
        # Unpack the 8 bytes into 4 unsigned little-endian shorts ('<HHHH')
        # Order in memory: Clear, Red, Green, Blue
        c, r, g, b = ustruct.unpack('<HHHH', data)
        
        return r, g, b, c
    
    def _is_data_ready(self):
        """
        Returns True if the integration cycle is complete (AVALID bit is 1).
        """
        # Read the STATUS register (0x13)
        status = self._read_byte(0x13)
        
        # Check if the 0th bit is set (0x01)
        return (status & 0x01) == 0x01

    async def read_rgbc(self):
        self.set_led(True)

        # Start Integration (Enable ADC)
        self._write_byte(0x00, 0x01 | 0x02)

        await asyncio.sleep_ms(int(self.integration_time_ms))  # Yield for most of integration
        while not self._is_data_ready():
            await asyncio.sleep_ms(1)  # Tight poll for the last stretch
        
        # Get the data
        data = self._read_rgbc()
        
        # Clean up
        self.set_led(False)
        self._write_byte(0x00, 0x01) # Disable ADC again
        
        return data
    
# --- Usage Example for RP2040-Zero ---
#i2c0 = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
#sensor = ColorSensor(i2c0, led_pin_num=2)

#sensor.set_led(True)
#print("RGB Clear Data:", sensor.read_rgbc())
#sensor.set_led(False)

#while True:
#    sensor.set_led(True)
#    data = sensor.read_rgbc()
#    sensor.set_led(False)
#    print("Data:", data)
#    time.sleep(.5)

def norm(v):
    """Returns the Euclidean norm (magnitude) of a vector v."""
    return sum(x**2 for x in v)**0.5


def distance(v1, v2):
    """Calculates the Euclidean distance between two vectors.
    v1, v2: Vectors (e.g., RGB tuples) to compare.
    """
    return sum((a - b) ** 2 for a, b in zip(v1, v2)) ** 0.5

def normalize_rgbc(rgbc):
    """Normalizes an RGBC color tuple by its clear channel.

    If the clear channel value is zero, it returns (0, 0, 0) to indicate no color.
    rgbc: Tuple of raw RGBC values (e.g., from the sensor).
    """
    if rgbc[3] == 0: # Avoid division by zero
        return 0, 0, 0
    return tuple(x / rgbc[3] for x in rgbc[:3])

def normalize_color(rgb, threshold=500):
    """Normalizes an RGB color tuple to the range 0.0 - 1.0, applying a threshold to filter out very dark colors.

    If the norm of the RGB vector is below the threshold, it returns (0, 0, 0) to indicate no color.
    rgb: Tuple of raw RGB values (e.g., from the sensor).
    threshold: Minimum norm value to consider the color valid.
    """
    n = norm(rgb)
    if n < threshold:
        return 0, 0, 0
    return tuple(x / n for x in rgb)

def weighted_color(rgbc):
    clear_norm = 100000
    rgbw = list(normalize_color(rgbc[:3]))
    rgbw.append(rgbc[3] / clear_norm)  # Add normalized clear channel as weight
    return rgbw
