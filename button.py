import machine
import asyncio
import utime

class Button:
    def __init__(self, pin_num, debounce_time_ms=20, long_press_threshold_ms=500):
        """Initialize an async button with hardware IRQ support and debouncing.
        
        Parameters
        ----------
        pin_num: int
            GPIO pin number connected to the button.
        debounce_time_ms: int
            Debounce delay in milliseconds (default 20ms).
        long_press_threshold_ms: int
            Duration in milliseconds to consider a press as "long press" (default 500ms).
        """
        self.pin = machine.Pin(pin_num,
                               mode=machine.Pin.IN,
                               pull=machine.Pin.PULL_UP)
        self.debounce_time_ms = debounce_time_ms
        self.long_press_threshold_ms = long_press_threshold_ms
        
        self._pressed_event = asyncio.Event()
        self._released_event = asyncio.Event()
        self._long_press_event = asyncio.Event()
        self._last_state = self.pin.value()
        self._monitor_task = None
        self._state_changed = False
        self._press_time_ms = None
        
        # Register IRQ handler to detect edges
        self.pin.irq(trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING,
                     handler=self._irq_handler)
    
    def _irq_handler(self, pin):
        """Hardware IRQ handler - flag that state may have changed.
        
        Called on rising/falling edge. Just sets a flag for the async monitor task.
        """
        self._state_changed = True
    
    def is_pressed(self):
        """Synchronous check of button state.
        
        Returns
        -------
        bool
            True if button is currently pressed, False otherwise.
        """
        return self.pin.value() == 0  # Active LOW
    
    async def await_press(self):
        """Wait for button to be pressed.
        
        This is an async method that can be awaited in an asyncio task.
        Automatically starts the pin monitoring task if not already running.
        If the button is currently held, waits for it to be released first
        to ensure each call corresponds to a distinct press.
        """
        self._ensure_monitor()
        # If already pressed, wait for release before accepting a new press
        if self.is_pressed():
            self._released_event.clear()
            await self._released_event.wait()
        self._pressed_event.clear()  # Discard any stale press event
        print("Waiting for button press...")
        await self._pressed_event.wait()
        self._pressed_event.clear()
    
    async def await_release(self):
        """Wait for button to be released.
        
        This is an async method that can be awaited in an asyncio task.
        Automatically starts the pin monitoring task if not already running.
        """
        self._ensure_monitor()
        print("Waiting for button release...")
        await self._released_event.wait()
        self._released_event.clear()
    
    async def await_long_press(self):
        """Wait for button to be held down for long_press_threshold_ms.
        
        This is an async method that waits for the button to be continuously
        held for the configured duration. Returns as soon as the hold threshold
        is reached (does not wait for release).
        
        Automatically starts the pin monitoring task if not already running.
        """
        self._ensure_monitor()
        print("Waiting for long press...")
        await self._long_press_event.wait()
        self._long_press_event.clear()
    
    def get_hold_duration_ms(self):
        """Get how long the button has been held in milliseconds.
        
        Returns
        -------
        int or None
            Milliseconds the button has been held, or None if not currently pressed.
        """
        if self._press_time_ms is None:
            return None
        return utime.ticks_diff(utime.ticks_ms(), self._press_time_ms)
    
    def _ensure_monitor(self):
        """Start the monitoring task if not already running."""
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitor_pin())
    
    async def _monitor_pin(self):
        """Monitor pin state changes with debouncing and long press detection.
        
        Runs continuously in background. When IRQ flags a state change,
        debounces it and updates the pressed/released/long_press events.
        Also monitors how long button is held and triggers long press event.
        """
        while True:
            # Poll frequently but efficiently
            await asyncio.sleep_ms(5)
            
            if self._state_changed:
                self._state_changed = False
                # Debounce: wait and verify state didn't change back
                await asyncio.sleep_ms(self.debounce_time_ms)
                current_state = self.pin.value()
                
                if current_state != self._last_state:
                    # State change confirmed after debounce
                    self._last_state = current_state
                    if current_state == 0:  # Pressed (active LOW)
                        self._press_time_ms = utime.ticks_ms()
                        self._pressed_event.set()
                        print("Button pressed")
                        self._long_press_event.clear()
                    else:  # Released
                        self._press_time_ms = None
                        self._released_event.set()
                        print("Button released")
                        self._long_press_event.clear()
            
            # Check for long press while button is held
            if self._press_time_ms is not None:
                hold_duration = int(utime.ticks_ms() - self._press_time_ms)
                if hold_duration >= self.long_press_threshold_ms and not self._long_press_event.is_set():
                    self._long_press_event.set()
                    print("Button long pressed")
