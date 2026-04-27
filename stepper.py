from machine import Pin
import time

class Stepper:
    def __init__(self, pins):
        self.pins = [Pin(pin, Pin.OUT) for pin in pins]
        self.sequence = [
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [0, 1, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 1, 1],
            [0, 0, 0, 1],
            [1, 0, 0, 1]
        ]
        self.step_delay = 1000  # 1ms delay for speed control

    def _step(self, step_sequence):
        # Use time.ticks_diff for more preceise timing
        t_start = time.ticks_us()
        for i, p in enumerate(self.pins):
            p.value(step_sequence[i])
            t_delta = time.ticks_diff(time.ticks_us(), t_start)
            time.sleep_us((i + 1) * self.step_delay - t_delta)

    def step(self, steps):
        """
        Rotate the motor.
        :param steps: Number of steps to rotate.
        """
        for _ in range(abs(steps)):
            for step in self.sequence if steps >= 0 else reversed(self.sequence):
                self._step(step)
        
        for p in self.pins:
            p.value(0)  # Turn off all pins after rotation
        
