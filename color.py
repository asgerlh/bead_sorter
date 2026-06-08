from machine import Pin
import machine
import asyncio
import time
import ustruct

import asyncio
from machine import Pin, I2C

class ColorSensor:
    """Class to interface with the TCS34725 color sensor, including LED control and RGBC data reading.
    
    The sensor is initialized with the I2C interface with interrupt and an LED pin for illumination control.
    
    Parameters
    ----------
    i2c: I2C
        An initialized I2C object for communication with the sensor.
    int_pin_num: int
        GPIO pin number for the interrupt pin.
    led_pin_num: int
        GPIO pin number for controlling the sensor's LED.
    """
    TCS34725_ADDR = 0x29
    CMD_BIT = 0x80
    REG_ENABLE = 0x00
    REG_ATIME = 0x01
    REG_AILT = 0x04
    REG_AIHT = 0x06
    REG_APERS = 0x0C
    REG_CONTROL = 0x0F
    REG_CDATAL = 0x14

    # Enable register states
    ENABLE_ON = 0x13   # AIEN (Interrupt), AEN (ADC), PON (Power On)
    ENABLE_OFF = 0x00  # Completely powered down

    CMD_CLEAR_INT = 0xE6

    def __init__(self, i2c : I2C, int_pin_num, led_pin_num):
        self.i2c = i2c
        
        # Setup Interrupt Pin (Sensor INT pulls LOW)
        self.int_pin = Pin(int_pin_num, Pin.IN, Pin.PULL_UP)
        self.data_ready = asyncio.Event()
        self.int_pin.irq(trigger=Pin.IRQ_FALLING, handler=self._irq_handler)
        
        # Setup LED Control Pin
        self.led_pin = Pin(led_pin_num, Pin.OUT)
        self.led_pin.value(0) # Start with LED off
        
        self.running = False

    def _irq_handler(self, pin):
        # Only trigger the event if the driver is actively running
        if self.running:
            self.data_ready.set()

    def _write_reg(self, reg, value):
        self.i2c.writeto_mem(self.TCS34725_ADDR, self.CMD_BIT | reg, bytes([value]))

    def _write_reg16(self, reg, value):
        data = bytes([value & 0xFF, (value >> 8) & 0xFF])
        self.i2c.writeto_mem(self.TCS34725_ADDR, self.CMD_BIT | reg, data)

    def set_led(self, on):
        """Control the sensor's LED state.
        
        Parameters
        ----------
        on: bool
            True to turn the LED on, False to turn it off.
        """
        self.led_pin.value(1 if on else 0)

    def start(self):
        """Turn on LED, configure registers, and enable reading loop"""
        if self.running:
            return # Already running
            
        self.set_led(True)
        
        # Configure thresholds to force an interrupt every single cycle
        self._write_reg(self.REG_APERS, 0x00)
        self._write_reg16(self.REG_AILT, 0xFFFF) # Low Threshold
        self._write_reg16(self.REG_AIHT, 0x0000) # High Threshold

        # Set integration time and gain
        integration_time_periods = 3
        self._write_reg(self.REG_ATIME, 0xFF - (integration_time_periods - 1))
        self._write_reg(self.REG_CONTROL, 0x03) # 60x gain
        
        # Power up the internal ADC and enable interrupts
        self._write_reg(self.REG_ENABLE, self.ENABLE_ON)
        
        # Clear any old interrupts to kickstart the hardware line
        self.clear_sensor_interrupt()
        self.data_ready.clear()
        
        self.running = True

    def stop(self):
        """Turn off LED, power down sensor state, and halt readings"""
        self.running = False
        
        self.set_led(False)
        
        # Put sensor state machine into lower power / disabled mode
        self._write_reg(self.REG_ENABLE, self.ENABLE_OFF)
        self.data_ready.clear()

    def clear_sensor_interrupt(self):
        self.i2c.writeto(self.TCS34725_ADDR, bytes([self.CMD_CLEAR_INT]))

    async def read_rgbc(self):
        await self.data_ready.wait()
        self.data_ready.clear()

        data = self.i2c.readfrom_mem(self.TCS34725_ADDR, self.CMD_BIT | self.REG_CDATAL, 8)
        self.clear_sensor_interrupt()
        
        # Unpack the 8 bytes into 4 unsigned little-endian shorts ('<HHHH')
        # Order in memory: Clear, Red, Green, Blue
        c, r, g, b = ustruct.unpack('<HHHH', data)
        
        return r, g, b, c


def norm(v):
    """Returns the Euclidean norm (magnitude) of a vector v."""
    return sum(x**2 for x in v)**0.5


def distance(v1, v2):
    """Calculates the Euclidean distance between two vectors.
    v1, v2: Vectors (e.g., RGB tuples) to compare.
    """
    return sum((a - b) ** 2 for a, b in zip(v1, v2)) ** 0.5

def rgbc_to_rgbw(rgbc, calibration=[0.54, 0.75, 1.0], clear_normalization=30*1024):
    """Convert raw RGBC values to normalized RGBW values using calibration factors and clear channel normalization.

    If the clear channel value is zero, it returns (0, 0, 0, 0) to indicate no color.

    Parameters
    ----------
    rgbc: tuple
        Tuple of raw RGBC values (e.g., from the sensor).
    calibration: list
        List of scaling factors for R, G, B channels to account for sensor sensitivity differences.
    clear_normalization: int
        Value to normalize the clear channel, representing the maximum expected clear value (e.g., 30ms integration time at 16-bit resolution).
    """
    if rgbc[3] == 0: # Avoid division by zero
        return 0, 0, 0, 0
    rgbw = tuple(x / rgbc[3] * c for x, c in zip(rgbc[:3], calibration))
    rgbw += (rgbc[3] / clear_normalization,)  # Add normalized clear channel
    return rgbw

def normalize_color(rgb, threshold=500):
    """Normalizes an RGB color tuple to the range 0.0 - 1.0, applying a threshold to filter out very dark colors.

    If the norm of the RGB vector is below the threshold, it returns (0, 0, 0) to indicate no color.

    Parameters
    ----------
    rgb: tuple
        Tuple of raw RGB values (e.g., from the sensor).
    threshold: int
        Minimum norm value to consider the color valid.
    """
    n = norm(rgb)
    if n < threshold:
        return 0, 0, 0
    return tuple(x / n for x in rgb)

def weighted_color(rgbc):
    """Calculates a weighted color vector from RGBC values.

    Parameters
    ----------
    rgbc: tuple
        Tuple of raw RGBC values (e.g., from the sensor).

    Returns
    -------
    list
        List of normalized RGB values with the clear channel as weight.
    """
    clear_norm = 100000
    rgbw = list(normalize_color(rgbc[:3]))
    rgbw.append(rgbc[3] / clear_norm)  # Add normalized clear channel as weight
    return rgbw
