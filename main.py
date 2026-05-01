import machine
import time
import neopixel

from stepper import Stepper
from button import Button
from color import ColorSensor

# Distance from normalized (0.0 - 1.0) reference color to consider a match.
distance_thresholds = 0.1

# One hole is 16 steps for a 28BYJ-48 stepper motor
holes = 16
one_hole = 512 // holes
flipper_steps = 40
backlash = 3

disc_motor = Stepper([9, 10, 11, 12], rpm=1.5*60/holes, mode='wave')
flipper_motor = Stepper([26, 27, 28, 29], rpm=10, mode='wave')
button1 = Button(4)
button2 = Button(5)
color_sensor = ColorSensor(machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000), led_pin_num=2)
neo = neopixel.NeoPixel(machine.Pin(16), 1, 3)

def led(r, g, b):
    neo[0] = (r, g, b)
    neo.write()

def get_vibrant_color(r_raw, g_raw, b_raw, c_raw, gamma=2.2, brightness=255):
    # 1. Get initial 0.0 - 1.0 ratios
    if c_raw == 0:
        return 0, 0, 0
    
    # We use a slightly aggressive normalization
    r = r_raw / c_raw
    g = g_raw / c_raw
    b = b_raw / c_raw

    # 2. Apply Gamma Correction (Power of 2.2 or 2.5)
    # This deepens the colors significantly
    r = pow(r, gamma)
    g = pow(g, gamma)
    b = pow(b, gamma)

    # 3. Scale back to 0-255 for NeoPixel
    # We multiply by a 'gain' because Gamma darkens the image
    scale = brightness
    return (int(r * scale), int(g * scale), int(b * scale))

def normalize_color(rgb, threshold=2400):
    norm = sum([x**2 for x in rgb])**0.5
    if norm < threshold:
        return 0, 0, 0
    return tuple(x / norm for x in rgb)

def color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5

while True:
    print("Align hole by pressing button 1. Insert reference bead and press second button to start.")

    color_sensor.set_led(True)
    led(5, 5, 5)  # Red LED to indicate initialization mode

    initializing = True
    while initializing:
        if button1.is_pressed():
            disc_motor.step(-1)  # Rotate backwards
        if button2.is_pressed():
            initializing = False  # Exit loop to start main operation
        time.sleep(0.12)

    color_sensor.set_led(False)

    disc_motor.step(backlash)

    disc_motor.step(one_hole)
    
    print("Scanning reference color.")

    ref_rgbc = color_sensor.read_rgbc()
    ref_rgb = normalize_color(ref_rgbc[:3])

    print("Reference color is:\nrgb: {:.2f}, {:.2f}, {:.2f}".format(*ref_rgb))

    led(*(int(x ** 3 * 50) for x in ref_rgb))  # Show reference color with LED

    print("Homing flipper")
    flipper_motor.step(flipper_steps)  # Move flipper to initial position
    flipper_position = True

    while initializing == False:
        disc_motor.step(one_hole)
        
        rgbc = color_sensor.read_rgbc()
        
        rgb = normalize_color(rgbc[:3])
        
        led(*(int(x ** 3 * 50) for x in rgb))  # Show current color with LED

        distance = color_distance(rgb, ref_rgb)
        match = distance < distance_thresholds

        if match and flipper_position == False:
            flipper_motor.step(flipper_steps)
            flipper_position = True
        elif not match and flipper_position == True:
            flipper_motor.step(-flipper_steps)
            flipper_position = False

        print("rgb: {:.2f}, {:.2f}, {:.2f}, dist: {:.2f}, match: {}".format(*rgb, distance, match))

        if button1.is_pressed() or button2.is_pressed():
            print("Stopping sorting...")
            break
