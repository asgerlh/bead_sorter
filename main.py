import os
import machine
import time

from piostepper import DiscMotor, FlipperMotor
from button import Button
from color import ColorSensor, normalize_rgbc, distance
from led import LED

# Distance from normalized (0.0 - 1.0) reference color to consider a match.
distance_thresholds = 0.05

# One hole is 16 steps for a 28BYJ-48 stepper motor
holes = 16
one_hole = 512 // holes
color_steps = 3
flipper_steps = 40
backlash = 3

disc_motor = DiscMotor(9, revolutions_per_second=3/holes)  # 1 hole per second
flipper_motor = FlipperMotor(26, revolutions_per_second=0.32)
button1 = Button(4)
button2 = Button(5)
color_sensor = ColorSensor(machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000), led_pin_num=2)
led = LED(pin_num=16, brightness=50.0, gamma=2.2)

reference_color = None
flipper_position = False
new_color = False
rgbc = (0, 0, 0, 0)

def irq_handler(sm):
    global reference_color
    global flipper_position
    global new_color
    global rgbc

    rgbc = color_sensor.read_rgbc()
    new_color = True
    rgb = normalize_rgbc(rgbc)

    if reference_color is None:
        reference_color = rgb
        flipper_motor.flip(True)  # Move flipper to initial position
        flipper_position = True
        led.set_color(reference_color[:3], brightness=50.0, gamma=2.2)  # Show reference color with LED
    else:
        dist = distance(rgb, reference_color)

        match = dist < distance_thresholds

        if match and flipper_position == False:
            #disc_motor.pause()
            flipper_motor.flip(True)
            flipper_position = True
            #disc_motor.resume()
        elif not match and flipper_position == True:
            #disc_motor.pause()
            flipper_motor.flip(False)
            flipper_position = False
            #disc_motor.resume()

disc_motor.set_irq_handler(irq_handler)

file_number = 0
files = os.listdir("data")
for file in files:
    if file.startswith("colors") and file.endswith(".csv"):
        num = int(file[len("colors"):-4])
        if num > file_number:
            file_number = num

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

    file_number += 1
    with open("data/colors{}.csv".format(file_number), "w") as fh:
        fh.write("R, G, B, C\n")

        disc_motor.step(backlash)

        reference_color = None
        disc_motor.start()

        while initializing == False:
            if new_color:
                fh.write("{}, {}, {}, {}\n".format(*rgbc))
                new_color = False
            if button1.is_pressed() or button2.is_pressed():
                disc_motor.stop()
                disc_motor.step(-int(2.3 * one_hole))  # Rotate back to allow placemnet of new reference bead
                break
            time.sleep(0.1)
