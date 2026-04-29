from machine import Pin
import time

class Stepper:
    def __init__(self, pins, rpm=1.0, mode='wave', duty_cycle=1.0, steps_per_revolution=512):
        self.pins = [Pin(pin, Pin.OUT) for pin in pins]
        if mode == 'wave':
            self.sequence = [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]
        elif mode == 'full':
            self.sequence = [
                [1, 1, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 1, 1],
                [1, 0, 0, 1],
            ]
        elif mode == 'half':
            self.sequence = [
                [1, 0, 0, 0],
                [1, 1, 0, 0],
                [0, 1, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 1, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 1],
            ]
        else:
            raise ValueError("Invalid mode. Choose 'wave', 'full', or 'half'.")
        
        self.step_delay = int(60e6 / (steps_per_revolution * rpm * len(self.sequence)))  # Delay in microseconds
        self.on_time = int(self.step_delay * duty_cycle)  # Time to keep the pin on

    def step(self, steps):
        """
        Rotate the motor.
        :param steps: Number of steps to rotate.
        """
        for _ in range(abs(steps)):
            for step in self.sequence if steps >= 0 else reversed(self.sequence):
                for i, p in enumerate(self.pins):
                    p.value(step[i])
                if self.on_time < self.step_delay:
                    time.sleep_us(self.on_time)  # Keep the pin on for the duty cycle duration
                    for p in self.pins:
                        p.value(0)  # Turn off all pins before the next step
                    time.sleep_us(self.step_delay - self.on_time)  # Wait for the rest of the step delay
                else:
                    time.sleep_us(self.step_delay)  # Wait for the full step delay if duty cycle is 1.0
        
        for p in self.pins:
            p.value(0)  # Turn off all pins after rotation
        
