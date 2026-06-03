from piostepper import DiscMotor
import machine
import time
from color import ColorSensor, rgbc_to_rgbw, distance

disc_motor = DiscMotor(9, revolutions_per_second=0.25) # 0.3 is max
color_sensor = ColorSensor(machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000), led_pin_num=2)

optocoupler_pin = machine.Pin(13, machine.Pin.IN)

timestamp = 0

def rotation_detected(pin):
    global timestamp
    time.sleep(0.02)  # Debounce delay
    disc_motor.stop()
    pin_state = pin.value()
    if pin_state == 1:  # Rising edge: bead in position
        # Start color reading
        timestamp = time.ticks_ms()
        color_sensor.start_read_rgbc()
    else:  # Falling edge: set flipper
        # Read color and set flipper
        elapsed = time.ticks_diff(time.ticks_ms(), timestamp)
        rgbc = color_sensor.finish_read_rgbc()
        print("RGBW: ", rgbc)
    disc_motor.start()

optocoupler_pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING,
                    handler=rotation_detected)

disc_motor.start()

time.sleep(10)

disc_motor.stop()

time.sleep(0.1)
