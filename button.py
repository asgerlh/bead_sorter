import machine
import time

class Button:
    def __init__(self, pin_num):
        self.pin = machine.Pin(pin_num,
                               mode=machine.Pin.IN,
                               pull=machine.Pin.PULL_UP)

    def is_pressed(self):
        return self.pin.value() == 0  # Active LOW
