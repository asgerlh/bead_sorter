import neopixel
import machine

class LED:
    """Class to control a single NeoPixel LED with brightness and gamma correction."""
    def __init__(self, pin_num, brightness=255.0, gamma=2.2):
        """Initialize the LED on the specified pin with optional brightness and gamma settings.
        pin_num: GPIO pin number where the NeoPixel is connected.
        brightness: Initial brightness (0.0 to 255.0).
        gamma: Gamma correction factor to apply to the color values.
        """
        self.neo = neopixel.NeoPixel(machine.Pin(pin_num), 1, 3)
        self.brightness = brightness
        self.gamma = gamma
    
    @property
    def brightness(self):
        """Get the current brightness setting for the LED."""
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        """Set the brightness for the LED."""
        if value < 0.0 or value > 255.0:
            raise ValueError("Brightness must be between 0.0 and 255.0")

        self._brightness = max(0.0, min(255.0, value))
    
    @property
    def gamma(self):
        """Get the current gamma correction factor."""
        return self._gamma
    
    @gamma.setter
    def gamma(self, value):
        """Set the gamma correction factor."""
        if value <= 0.0:
            raise ValueError("Gamma must be a positive number")
        self._gamma = value

    def set_color(self, rgb, brightness=None, gamma=None):
        """Set the color of the NeoPixel LED.

        Parameters
        ----------
        rgb: tuple
            Tuple of values between 0.0 and 1.0 for red, green, and blue.
        brightness: float
            Value between 0.0 and 255.0 to scale the brightness.
        gamma: float
            Gamma correction factor to apply to the color values.
        """
        if brightness is not None:
            brightness = max(0.0, min(255.0, brightness))
        else:
            brightness = self._brightness

        if gamma is None:
            gamma = self._gamma

        rgb = tuple(pow(x, gamma) for x in rgb)

        self.neo[0] = tuple(int(x * brightness) for x in rgb)
        self.neo.write()
