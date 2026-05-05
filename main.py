import machine
import time

from stepper import Stepper
from button import Button
from color import ColorSensor, normalize_color, distance
from led import LED

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
led = LED(pin_num=16, brightness=50.0, gamma=2.2)

while True:
    print("Align hole by pressing button 1. Insert reference bead and press second button to start.")

    color_sensor.set_led(True)
    led.set_color((1.0, 0.0, 0.0))  # Red LED to indicate initialization mode

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

    print("Reference color is:\nrgb: {:.2f}, {:.2f}, {:.2f}, raw: {:5}, {:5}, {:5}, {:5}".format(*ref_rgb, *ref_rgbc))

    led.set_color(ref_rgb)  # Show reference color with LED

    print("Homing flipper")
    flipper_motor.step(flipper_steps)  # Move flipper to initial position
    flipper_position = True

    last_rgbc = ref_rgbc
    same_color_count = 0
    while initializing == False:
        disc_motor.step(one_hole)
        
        rgbc = color_sensor.read_rgbc()

        if distance(rgbc, last_rgbc) < 1000:
            same_color_count += 1
            if same_color_count > 3:
                print("Warning: Color readings are not changing. Backing up to try to get unstuck.")
                disc_motor.step(-15)
                same_color_count = 0
        else:
            same_color_count = 0

        last_rgbc = rgbc
        
        rgb = normalize_color(rgbc[:3])
        
        led.set_color(rgb)  # Show current color with LED

        dist = distance(rgb, ref_rgb)
        match = dist < distance_thresholds

        if match and flipper_position == False:
            flipper_motor.step(flipper_steps)
            flipper_position = True
        elif not match and flipper_position == True:
            flipper_motor.step(-flipper_steps)
            flipper_position = False

        print("rgb: {:.2f}, {:.2f}, {:.2f}, raw: {:5}, {:5}, {:5}, {:5}, dist: {:.2f}, match: {}".format(*rgb, *rgbc, dist, match))

        if button1.is_pressed() or button2.is_pressed():
            print("Stopping sorting...")
            break
