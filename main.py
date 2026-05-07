import machine
import time

from stepper import Stepper
from button import Button
from color import ColorSensor, weighted_color, distance
from led import LED

# Distance from normalized (0.0 - 1.0) reference color to consider a match.
distance_thresholds = 0.08

# One hole is 16 steps for a 28BYJ-48 stepper motor
holes = 16
one_hole = 512 // holes
color_steps = 3
flipper_steps = 40
backlash = 3

disc_motor = Stepper([9, 10, 11, 12], rpm=3*60/holes, mode='full')
flipper_motor = Stepper([26, 27, 28, 29], rpm=22, mode='full')
button1 = Button(4)
button2 = Button(5)
color_sensor = ColorSensor(machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000), led_pin_num=2)
led = LED(pin_num=16, brightness=50.0, gamma=2.2)

def move_and_read_color():
    disc_motor.step(one_hole - 2 * color_steps)  # Move to position for color reading, accounting for color reading steps
    
    num_readings = 3
    rgbc = color_sensor.read_rgbc()
    #print("RGBC:", rgbc)
    for _ in range(1, num_readings):
        disc_motor.step(color_steps)
        tmp = color_sensor.read_rgbc()
        #print("RGBC:", tmp)
        if tmp[3] > rgbc[3]:  # Compare clear channel to find the reading with the most light (best reading)
            rgbc = tmp
    
    return rgbc

while True:
    #print("Align hole by pressing button 1. Insert reference bead and press second button to start.")

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

    #print("Scanning reference color.")

    ref_rgbc = move_and_read_color()
    ref_rgbw = weighted_color(ref_rgbc)

    #print("Reference color is:\nrgbw: {:.2f}, {:.2f}, {:.2f}, {:.2f}, raw: {:5}, {:5}, {:5}, {:5}".format(*ref_rgbw, *ref_rgbc))

    led.set_color(ref_rgbw)  # Show reference color with LED

    #print("Homing flipper")
    flipper_motor.step(flipper_steps)  # Move flipper to initial position
    flipper_position = True

    #last_rgbc = ref_rgbc
    #same_color_count = 0
    while initializing == False:
        rgbc = move_and_read_color()

        #if distance(rgbc, last_rgbc) < 1000:
        #    same_color_count += 1
        #    if same_color_count > 3:
        #        print("Warning: Color readings are not changing. Backing up to try to get unstuck.")
        #        disc_motor.step(-15)
        #        same_color_count = 0
        #else:
        #    same_color_count = 0
        #
        #last_rgbc = rgbc
        
        #rgb = normalize_color(rgbc[:3])
        rgbw = weighted_color(rgbc)
        
        #led.set_color(rgbw[:3])  # Show current color with LED

        dist = distance(rgbw, ref_rgbw)
        match = dist < distance_thresholds

        if match and flipper_position == False:
            flipper_motor.step(flipper_steps)
            flipper_position = True
        elif not match and flipper_position == True:
            flipper_motor.step(-flipper_steps)
            flipper_position = False

        #print("rgbw: {:.2f}, {:.2f}, {:.2f}, {:.2f}, raw: {:5}, {:5}, {:5}, {:5}, dist: {:.2f}, match: {}".format(*rgbw, *rgbc, dist, match))

        if button1.is_pressed() or button2.is_pressed():
            #print("Stopping sorting...")
            break
