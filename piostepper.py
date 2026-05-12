import time
import rp2
import machine

class DiscMotor:
    def __init__(self, first_pin_nr, revolutions_per_second):
        """Stepper motor control using RP2040's PIO for precise timing and efficient operation.
        
        Parameters
        ----------
        first_pin_nr: int
            The first GPIO pin number connected to the stepper motor.
        revolutions_per_second: float
            The desired speed of the motor in revolutions per second.
        """
        @rp2.asm_pio(set_init=[rp2.PIO.OUT_LOW] * 4,
                 out_init=[rp2.PIO.OUT_HIGH] * 4)
        def pio():
            pull()                        # type: ignore
            mov(y, osr)                   # type: ignore
            set(x, 31)                    # type: ignore
            wrap_target()                 # type: ignore
            jmp(not_osre, "skip_reload")  # type: ignore
            mov(osr, y)                   # type: ignore
            jmp(x_dec, "skip_reload")     # type: ignore
            irq(rel(0))                   # type: ignore
            set(x, 31)                    # type: ignore
            label("skip_reload")          # type: ignore
            out(pins, 4) [31]             # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            wrap()                        # type: ignore

        instructions_per_step = 24 * 32
        self.revolutions_per_cycle = 512
        self.steps_per_cycle = 8
        freq = int(instructions_per_step * self.steps_per_cycle * self.revolutions_per_cycle * revolutions_per_second)
        self.sm = rp2.StateMachine(0, pio, set_base=machine.Pin(first_pin_nr), out_base=machine.Pin(first_pin_nr), freq=freq)

        # For stepping a specific number of steps, we need to encode the patterns as instructions to be executed in sequence.
        # We pre-encode the forward and reverse patterns so the step() method can execute them efficiently without needing to re-encode on each call.
        self.forward_pattern_encoded = (
            rp2.asm_pio_encode("set(pins, 0b1001)", 0),
            rp2.asm_pio_encode("set(pins, 0b0001)", 0),
            rp2.asm_pio_encode("set(pins, 0b0011)", 0),
            rp2.asm_pio_encode("set(pins, 0b0010)", 0),
            rp2.asm_pio_encode("set(pins, 0b0110)", 0),
            rp2.asm_pio_encode("set(pins, 0b0100)", 0),
            rp2.asm_pio_encode("set(pins, 0b1100)", 0),
            rp2.asm_pio_encode("set(pins, 0b1000)", 0),
        )

        self.reverse_pattern_encoded = (
            rp2.asm_pio_encode("set(pins, 0b1000)", 0),
            rp2.asm_pio_encode("set(pins, 0b1100)", 0),
            rp2.asm_pio_encode("set(pins, 0b0100)", 0),
            rp2.asm_pio_encode("set(pins, 0b0110)", 0),
            rp2.asm_pio_encode("set(pins, 0b0010)", 0),
            rp2.asm_pio_encode("set(pins, 0b0011)", 0),
            rp2.asm_pio_encode("set(pins, 0b0001)", 0),
            rp2.asm_pio_encode("set(pins, 0b1001)", 0),
        )

    def set_irq_handler(self, irq_handler):
        """Sets the interrupt handler for when a full cycle of steps is completed.
        
        Parameters
        ----------
        irq_handler: function
            The function to be called when the interrupt occurs.
        """
        self.sm.irq(irq_handler)

    def start(self, forward=True):
        """Starts the motor in the specified direction.

        Note: This method is non-blocking and will return immediately after starting the motor.

        Parameters
        ----------
        forward: bool
            If True, the motor will rotate forward. If False, it will rotate in reverse.
        """
        if forward:
            pattern = 0b1001_0001_0011_0010_0110_0100_1100_1000 # Forward half step pattern
        else:
            pattern = 0b1000_1100_0100_0110_0010_0011_0001_1001 # Reverse half step pattern
        self.sm.put(pattern)
        self.sm.active(1)
  
    def pause(self):
        """Pauses the motor."""
        self.sm.active(0)
    
    def resume(self):
        """Resumes the motor."""
        self.sm.active(1)
    
    def stop(self):
        """Stops the motor."""
        self.sm.active(0)
        self.sm.restart()
        self.sm.exec("set(pins, 0)")  # Turn off all pins after stopping
    
    def step(self, steps : int = 1):
        """Steps the motor a specific number of steps.

        Note: This method is blocking and will wait until the steps are completed.
        
        Parameters
        ----------
        steps: int
            Number of steps to move. Positive for forward, negative for reverse.
        """
        if self.sm.active():
            raise RuntimeError("Cannot call step() while motor is running. Please stop the motor first.")

        if steps > 0:
            pattern = self.forward_pattern_encoded
        else:
            pattern = self.reverse_pattern_encoded
        
        for _ in range(abs(steps)):
            for p in pattern:
                self.sm.exec(p)
                time.sleep_ms(2)
        self.sm.exec("set(pins, 0)")  # Turn off all pins after stepping


class FlipperMotor:
    def __init__(self, first_pin_nr, revolutions_per_second=0.3):
        """Stepper motor control using RP2040's PIO for precise timing and efficient operation.
        
        Parameters
        ----------
        first_pin_nr: int
            The first GPIO pin number connected to the stepper motor.
        revolutions_per_second: float
            The desired speed of the motor in revolutions per second.
        """
        @rp2.asm_pio(set_init=[rp2.PIO.OUT_LOW] * 4,
                 out_init=[rp2.PIO.OUT_HIGH] * 4)
        def pio():
            label("start")                # type: ignore
            pull()                        # type: ignore
            mov(y, osr)                   # type: ignore
            pull()                        # type: ignore
            mov(x, osr)                   # type: ignore
            wrap_target()                 # type: ignore
            jmp(not_osre, "skip_reload")  # type: ignore
            mov(osr, y)                   # type: ignore
            jmp(x_dec, "skip_reload")     # type: ignore
            jmp("start")                  # type: ignore
            label("skip_reload")          # type: ignore
            out(pins, 4) [31]             # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            nop() [31]                    # type: ignore
            wrap()                        # type: ignore

        instructions_per_step = 23 * 32
        self.revolutions_per_cycle = 512
        self.steps_per_cycle = 8
        freq = int(instructions_per_step * self.steps_per_cycle * self.revolutions_per_cycle * revolutions_per_second)
        self.sm = rp2.StateMachine(4, pio, set_base=machine.Pin(first_pin_nr), out_base=machine.Pin(first_pin_nr), freq=freq)

        # For stepping a specific number of steps, we need to encode the patterns as instructions to be executed in sequence.
        # We pre-encode the forward and reverse patterns so the step() method can execute them efficiently without needing to re-encode on each call.
        self.forward_pattern_encoded = (
            rp2.asm_pio_encode("set(pins, 0b1001)", 0),
            rp2.asm_pio_encode("set(pins, 0b0001)", 0),
            rp2.asm_pio_encode("set(pins, 0b0011)", 0),
            rp2.asm_pio_encode("set(pins, 0b0010)", 0),
            rp2.asm_pio_encode("set(pins, 0b0110)", 0),
            rp2.asm_pio_encode("set(pins, 0b0100)", 0),
            rp2.asm_pio_encode("set(pins, 0b1100)", 0),
            rp2.asm_pio_encode("set(pins, 0b1000)", 0),
        )

        self.reverse_pattern_encoded = (
            rp2.asm_pio_encode("set(pins, 0b1000)", 0),
            rp2.asm_pio_encode("set(pins, 0b1100)", 0),
            rp2.asm_pio_encode("set(pins, 0b0100)", 0),
            rp2.asm_pio_encode("set(pins, 0b0110)", 0),
            rp2.asm_pio_encode("set(pins, 0b0010)", 0),
            rp2.asm_pio_encode("set(pins, 0b0011)", 0),
            rp2.asm_pio_encode("set(pins, 0b0001)", 0),
            rp2.asm_pio_encode("set(pins, 0b1001)", 0),
        )

    def set_irq_handler(self, irq_handler):
        """Sets the interrupt handler for when a full cycle of steps is completed.
        
        Parameters
        ----------
        irq_handler: function
            The function to be called when the interrupt occurs.
        """
        self.sm.irq(irq_handler)

    def start(self, forward=True, steps=40):
        """Starts the motor in the specified direction.

        Note: This method is non-blocking and will return immediately after starting the motor.

        Parameters
        ----------
        forward: bool
            If True, the motor will rotate forward. If False, it will rotate in reverse.
        """
        if forward:
            pattern = 0b1001_0001_0011_0010_0110_0100_1100_1000 # Forward half step pattern
        else:
            pattern = 0b1000_1100_0100_0110_0010_0011_0001_1001 # Reverse half step pattern
        self.sm.put(pattern)
        self.sm.put(steps)
        self.sm.active(1)
  
    def pause(self):
        """Pauses the motor."""
        self.sm.active(0)
    
    def resume(self):
        """Resumes the motor."""
        self.sm.active(1)
    
    def stop(self):
        """Stops the motor."""
        self.sm.active(0)
        self.sm.restart()
        self.sm.exec("set(pins, 0)")  # Turn off all pins after stopping
    
    def step(self, steps : int = 1):
        """Steps the motor a specific number of steps.

        Note: This method is blocking and will wait until the steps are completed.
        
        Parameters
        ----------
        steps: int
            Number of steps to move. Positive for forward, negative for reverse.
        """
        if self.sm.active():
            raise RuntimeError("Cannot call step() while motor is running. Please stop the motor first.")

        if steps > 0:
            pattern = self.forward_pattern_encoded
        else:
            pattern = self.reverse_pattern_encoded
        
        for _ in range(abs(steps)):
            for p in pattern:
                self.sm.exec(p)
                time.sleep_ms(2)
        self.sm.exec("set(pins, 0)")  # Turn off all pins after stepping
    
    def flip(self, direction=True):
        """Flips the motor in the specified direction by a fixed number of steps.

        Note: This method is blocking and will wait until the flip is completed.
        
        Parameters
        ----------
        direction: bool
            If True, the motor will flip forward. If False, it will flip in reverse.
        """
        self.start(forward=direction, steps=36)
