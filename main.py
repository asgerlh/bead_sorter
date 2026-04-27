import machine
import time
import neopixel


from stepper import Stepper
from button import Button
from color import ColorSensor

# One hole is 16 steps for a 28BYJ-48 stepper motor
holes = 16
one_hole = 512 // holes

motor = Stepper([9, 10, 11, 12])
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


while True:
    print("Align hole by pressing button 1. Insert bead and press second button to start.")

    color_sensor.set_led(True)
    led(5, 5, 5)  # Red LED to indicate initialization mode

    initializing = True
    while initializing:
        if button1.is_pressed():
            motor.step(-1)  # Rotate backwards
        if button2.is_pressed():
            initializing = False  # Exit loop to start main operation
        time.sleep(0.12)

    color_sensor.set_led(False)

    motor.step(3) # Backlash correction

    print("Sorting started! Press any button to stop.")

    while initializing == False:
        motor.step(one_hole)
        r, g, b, c = color_sensor.read_rgbc()
        g = int(g * 1.3)
        b = int(b * 1.6)
        r_v, g_v, b_v = get_vibrant_color(r, g, b, c, gamma=3, brightness=150)
        print(f"RGB Clear Data: R={r}, G={g}, B={b}, C={c}, Vibrant RGB: ({r_v}, {g_v}, {b_v})")

        if c > 0:
            led(r_v, g_v, b_v)
        else:
            led(0, 0, 0)

        if button1.is_pressed() or button2.is_pressed():
            print("Stopping sorting...")
            break
