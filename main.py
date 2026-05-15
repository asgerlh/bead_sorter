import machine
import asyncio

from piostepper import DiscMotor, FlipperMotor
from button import Button
from color import ColorSensor, normalize_rgbc, distance
from led import LED
from ColorDataFile import ColorDataFile


async def race(*coros):
    """Run coroutines concurrently, cancel losers, return index of winner."""
    winner = [None]
    done = asyncio.Event()

    async def run(i, coro):
        await coro
        if not done.is_set():
            winner[0] = i
            done.set()

    tasks = [asyncio.create_task(run(i, c)) for i, c in enumerate(coros)]
    await done.wait()
    for t in tasks:
        t.cancel()
    return winner[0]


class BeadSorter:
    """Main application class for bead sorting system.
    
    User flow:
        1. Hold button1 to step disc back until aligned with insertion hole.
        2. Insert bead and press button2 to start sorting.
           First bead sets reference color, LED shows reference color.
        3. If a bead gets stuck, hold button1 to step disc back and realign.
           Then press button2 to continue.
        4. To reset reference color, press button2.
           Then align with hole and insert new reference bead.
    """

    # Distance from normalized (0.0 - 1.0) reference color to consider a match.
    distance_thresholds = 0.035

    # One hole is 16 steps for a 28BYJ-48 stepper motor
    steps_per_revolution = 512
    holes_per_revolution = 16
    one_hole = steps_per_revolution // holes_per_revolution
    start_offset = -5

    def __init__(self):
        self.led = LED(16, brightness=50.0, gamma=2.2)
        self.button1 = Button(4)
        self.button2 = Button(5)
        self.color_sensor = ColorSensor(machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000), led_pin_num=2)
        self.flipper_motor = FlipperMotor(26, revolutions_per_second=0.30)
        self.disc_motor = DiscMotor(9, revolutions_per_second=4/self.holes_per_revolution)  # 1 hole per second
        self.disc_motor.set_irq_handler(self.disc_irq_handler)
        self.color_data_file = ColorDataFile()
        self.bead_ready_event = asyncio.Event()
        self.reference_color = None

    def disc_irq_handler(self, sm):
        self.bead_ready_event.set()

    # --- Helpers ---

    async def process_bead(self):
        """Waits for bead to be in position, reads color, updates flipper and LED, and logs data."""
        flipper_position = False
        try:
            while True:
                await self.bead_ready_event.wait()
                self.bead_ready_event.clear()

                rgbc = await self.color_sensor.read_rgbc()
                rgb = normalize_rgbc(rgbc)

                # Open file and set reference if needed
                if self.reference_color is None:
                    self.reference_color = rgb
                    self.flipper_motor.flip(True)
                    flipper_position = True
                    self.led.set_color(self.reference_color[:3], brightness=50.0, gamma=2.2)
                    self.color_data_file.open()  # Closes any previous file and opens a new one
                else:
                    dist = distance(rgb, self.reference_color)
                    match = dist < self.distance_thresholds
                    if match and not flipper_position:
                        self.flipper_motor.flip(True)
                        flipper_position = True
                    elif not match and flipper_position:
                        self.flipper_motor.flip(False)
                        flipper_position = False
                    self.color_data_file.write(rgbc)
        finally:
            self.color_data_file.close()

    # --- States ---

    async def alignment_state(self):
        """User manually adjusts disc position.

        button1 held: step disc back one step at a time
        button2 pressed: confirm position and transition to RUNNING

        Returns next state.
        """
        if self.reference_color is None:
            self.led.set_color((0.0, 0.0, 0.0))  # Turn off LED until reference color is set

        async def step_while_held():
            while True:
                while self.button1.is_pressed():
                    self.disc_motor.step(-1)
                    await asyncio.sleep_ms(120)
                await self.button1.await_press()

        self.color_sensor.set_led(True)
        await race(step_while_held(), self.button2.await_press())
        self.color_sensor.set_led(False)

        return self.running_state

    async def running_state(self):
        """Disc motor runs and color data is recorded to CSV.

        button1 pressed: stop motor, transition to ALIGNMENT
        button2 pressed: stop motor, reset reference color, transition to ALIGNMENT

        Returns next state.
        """
        self.disc_motor.step(self.start_offset)  # Also includes backlash
        self.disc_motor.start()

        winner = await race(self.button1.await_press(), self.button2.await_press())

        self.disc_motor.stop()
        if winner == 0:
            # Step back a little and allow manual re-alignment
            self.disc_motor.step(-5)
        else:
            # Rotate back for a new reference bead
            self.disc_motor.step(-int(2.3 * self.one_hole))
            self.reference_color = None

        return self.alignment_state

    # --- Main loop ---

    async def run(self):
        asyncio.create_task(self.process_bead())
        state = self.alignment_state
        while True:
            state = await state()  # type: ignore


asyncio.run(BeadSorter().run())
