import machine
import asyncio
import math

import optocoupler
from piostepper import DiscMotor, FlipperMotor
from button import Button
from color import ColorSensor, rgbc_to_rgbw, distance
from led import LED
from ColorDataFile import ColorDataFile
from optocoupler import Optocoupler


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
    rgb_distance_threshold = 0.032
    clear_distance_threshold = 1.0

    steps_per_revolution = 512
    holes_per_revolution = 24
    steps_per_hole = steps_per_revolution // holes_per_revolution

    def __init__(self):
        self.led = LED(16, brightness=50.0, gamma=2.2)
        self.button1 = Button(4)
        self.button2 = Button(5)
        self.color_sensor = ColorSensor(machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000), led_pin_num=2)
        self.flipper_motor = FlipperMotor(26, revolutions_per_second=0.30)
        self.disc_motor = DiscMotor(9, revolutions_per_second=0.25)
        self.color_data_file = ColorDataFile()
        self.reference_color = None
        self.optocoupler = Optocoupler(13)
        self.flipper_position = False
        self.initial_state = self.alignment_state
        self.state_machine_task = None

    # --- States ---

    async def alignment_state(self):
        """Rotate disc backwards to align hole for bead insertion.

        Press button1 to start

        Returns next state.
        """
        if self.reference_color is None:
            self.led.set_color((0.0, 0.0, 0.0))  # Turn off LED until reference color is set

        self.disc_motor.step(-2 * self.steps_per_hole)
        while not self.optocoupler.is_blocked():
            self.disc_motor.step(-1)
        
        print("Insert bead and press button 1 to start sorting.")
        await self.button1.await_press()

        return self.bead_into_position_state

    async def bead_into_position_state(self):
        """Rotate disc forward until bead is in position for color reading.

        Returns next state.
        """
        self.disc_motor.start()
        success = await self.optocoupler.await_clear(timeout=0.3)
        self.disc_motor.stop()

        if success:
            return self.read_color_state
        else:
            return self.stuck_state
    
    async def read_color_state(self):
        """Read color while rotating disc forward.
        
        Returns next state.
        """

        self.color_sensor.start_read_rgbc()
        self.disc_motor.start()
        success = await self.optocoupler.await_block(timeout=0.3)
        self.disc_motor.stop()
        self.rgbc = await self.color_sensor.finish_read_rgbc()

        if success:
            return self.analyze_color_state
        else:
            return self.stuck_state
        
    async def analyze_color_state(self):
        """Analyze color and update flipper and LED.

        Returns next state.
        """
        rgbw = rgbc_to_rgbw(self.rgbc)

        if self.reference_color is None:
            self.reference_color = rgbw
            self.color_data_file.open()  # Closes any previous file and opens a new one
        
        self.color_data_file.write(self.rgbc)

        dist = distance(rgbw[:3], self.reference_color[:3])
        dist_clear = math.log2(abs(rgbw[3] - self.reference_color[3]) + 1e-10)
        match = dist < self.rgb_distance_threshold and dist_clear < self.clear_distance_threshold
        if match and not self.flipper_position:
            self.flipper_motor.flip(True)
            self.flipper_position = True
            await asyncio.sleep(0.3)  # Wait for flipper to fully flip before allowing next action
        elif not match and self.flipper_position:
            self.flipper_motor.flip(False)
            self.flipper_position = False
            await asyncio.sleep(0.3)  # Wait for flipper to fully flip before allowing next action
        
        print("RGBC: {rgbc}, RGBW: {rgbw}, Distance: {dist:.4f}, Clear Distance: {dist_clear:.4f}, Match: {match}".format(rgbc=self.rgbc, rgbw=["{:.3f}".format(x) for x in rgbw ], dist=dist, dist_clear=dist_clear, match=match))
        
        return self.bead_into_position_state
    
    async def stuck_state(self):
        """Handle stuck by rewinding and go to bead_into_position_state to try again."""
        self.disc_motor.stop()

        print("Bead is stuck. Rewinding and restarting...")
        self.disc_motor.step(-self.steps_per_hole)
        await asyncio.sleep(1)
        
        return self.bead_into_position_state
    
    async def restart_on_button2(self):
        """Wait for button2 press to restart alignment state."""
        while True:
            await self.button2.await_press()
            print("Restarting...")
            self.color_sensor.set_led(False)
            if self.state_machine_task is not None:
                self.state_machine_task.cancel()
            self.reference_color = None
            self.color_data_file.close()
            self.initial_state = self.alignment_state
            self.state_machine_task = asyncio.create_task(self.state_machine())

    async def state_machine(self):
        """Main state machine loop."""
        state = self.initial_state
        while True:
            state = await state() # type: ignore

    # --- Main loop ---

    async def run(self):
        self.state_machine_task = asyncio.create_task(self.state_machine())
        while True:
            await self.restart_on_button2()

asyncio.run(BeadSorter().run())
