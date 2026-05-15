import os
import machine
import asyncio

from piostepper import DiscMotor, FlipperMotor
from button import Button
from color import ColorSensor, normalize_rgbc, distance
from led import LED

# Distance from normalized (0.0 - 1.0) reference color to consider a match.
distance_thresholds = 0.035

# One hole is 16 steps for a 28BYJ-48 stepper motor
holes = 16
one_hole = 512 // holes
color_steps = 3
flipper_steps = 40
start_offset = -5

disc_motor = DiscMotor(9, revolutions_per_second=4/holes)  # 1 hole per second
flipper_motor = FlipperMotor(26, revolutions_per_second=0.30)
button1 = Button(4)
button2 = Button(5)
color_sensor = ColorSensor(machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000), led_pin_num=2)
led = LED(pin_num=16, brightness=50.0, gamma=2.2)

reference_color = None
flipper_position = False
rgbc = (0, 0, 0, 0)
color_event = asyncio.Event()

class ColorDataFile:
    """Manages color data file creation and writing."""
    def __init__(self):
        self.file = None
        self.file_number = 0
        self._load_file_number()
    
    def _load_file_number(self):
        """Pre-scan existing files to set file_number."""
        files = os.listdir("data")
        for f in files:
            if f.startswith("colors") and f.endswith(".csv"):
                num = int(f[len("colors"):-4])
                if num > self.file_number:
                    self.file_number = num
    
    def open(self):
        """Open a new color data file and write header.
        
        Closes any existing file first to ensure clean state.
        """
        self.close()  # Close existing file if any
        self.file_number += 1
        try:
            self.file = open("data/colors{}.csv".format(self.file_number), "w")
            self.file.write("R, G, B, C\n")
        except Exception:
            self.file = None
            raise
    
    def write(self, rgbc):
        """Write RGBC data to file if open."""
        if self.file is not None:
            try:
                self.file.write("{}, {}, {}, {}\n".format(*rgbc))
            except Exception:
                self.close()
                raise
    
    def close(self):
        """Safely close the color data file."""
        try:
            if self.file is not None:
                self.file.close()
        except Exception:
            pass
        finally:
            self.file = None

color_data = ColorDataFile()

def irq_handler(sm):
    color_event.set()

disc_motor.set_irq_handler(irq_handler)

# --- Helpers ---

async def process_color():
    """Main color processing loop with reference tracking."""
    global reference_color, flipper_position, rgbc
    
    try:
        print("Starting color processing loop...")
        while True:
            await color_event.wait()
            color_event.clear()
            print("Color event triggered")

            rgbc = await color_sensor.read_rgbc()
            rgb = normalize_rgbc(rgbc)

            # Open file and set reference if needed
            if reference_color is None:
                reference_color = rgb
                flipper_motor.flip(True)
                flipper_position = True
                led.set_color(reference_color[:3], brightness=50.0, gamma=2.2)
                color_data.open()  # Closes any previous file and opens a new one
            else:
                dist = distance(rgb, reference_color)
                match = dist < distance_thresholds
                if match and not flipper_position:
                    flipper_motor.flip(True)
                    flipper_position = True
                elif not match and flipper_position:
                    flipper_motor.flip(False)
                    flipper_position = False
                color_data.write(rgbc)
                print("Read color RGB: {:.2f} {:.2f} {:.2f}, distance from reference: {:.4f}, match: {}".format(*rgb, dist, match))
    finally:
        color_data.close()

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

# --- States ---

async def alignment_state():
    """User manually adjusts disc position.

    button1 held: step disc back one step at a time
    button2 pressed: confirm position and transition to RUNNING

    Returns next state.
    """
    print("ALIGNMENT: Hold button1 to step back, press button2 to confirm.")
    if reference_color is None:
        led.set_color((0.0, 0.0, 0.0))  # Turn off LED until reference color is set

    async def step_while_held():
        while True:
            while button1.is_pressed():
                disc_motor.step(-1)
                await asyncio.sleep_ms(120)
            await button1.await_press()

    color_sensor.set_led(True)
    await race(step_while_held(), button2.await_press())
    color_sensor.set_led(False)

    return running_state

async def running_state():
    """Disc motor runs and color data is recorded to CSV.

    button1 pressed: stop motor, step back, transition to ALIGNMENT
    button2 pressed: stop motor, reset reference color, transition to ALIGNMENT

    Returns next state.
    """
    print("RUNNING: Press button1 to stop and realign, button2 to stop and reset reference color.")
    global reference_color

    disc_motor.step(start_offset)  # Also includes backlash
    disc_motor.start()

    winner = await race(button1.await_press(), button2.await_press())

    disc_motor.stop()
    if winner == 0:
        # Step back a little and allow manual re-alignment
        print("Stepping back for realignment...")
        disc_motor.step(-5)
    else:
        # Rotate back for a new reference bead
        print("Resetting reference color and rotating disc for new bead...")
        disc_motor.step(-int(2.3 * one_hole))
        reference_color = None

    return alignment_state

# --- Main loop ---

async def main():
    process_color_task = asyncio.create_task(process_color())
    state = alignment_state
    while True:
        state = await state() # type: ignore

asyncio.run(main())
