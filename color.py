from machine import Pin, I2C
import time
import ustruct

class ColorSensor:
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
        time.sleep(0.1)
        integration_periods = 100
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

    def read_rgbc(self):
        self.set_led(True)
        
        # Start Integration (Enable ADC)
        self._write_byte(0x00, 0x01 | 0x02)
        
        # Wait for integration to complete (integration time + small buffer)
        #time.sleep_ms(int(self.integration_time_ms) + 20)

        while not self._is_data_ready():
            time.sleep_ms(10)  # Sleep briefly to avoid busy-waiting
        
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