import machine
import asyncio
import time

class Optocoupler:
    def __init__(self, pin_num=13):
        self.pin = machine.Pin(pin_num, machine.Pin.IN)
        self.pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=self._irq_handler)
        self.event_clear = asyncio.Event()
        self.event_block = asyncio.Event()

    def _irq_handler(self, pin):
        time.sleep_ms(1) # debounce delay
        if self.is_blocked():
            self.event_block.set()
        else:
            self.event_clear.set()

    def is_blocked(self):
        return self.pin.value() == 0
    
    async def await_clear(self, timeout=None):
        if timeout is not None:
            try:
                await asyncio.wait_for(self.event_clear.wait(), timeout)
            except asyncio.TimeoutError:
                return False
        else:
            await self.event_clear.wait()
        self.event_clear.clear()
        return True
    
    async def await_block(self, timeout=None):
        if timeout is not None:
            try:
                await asyncio.wait_for(self.event_block.wait(), timeout)
            except asyncio.TimeoutError:
                return False
        else:
            await self.event_block.wait()   
        self.event_block.clear()
        return True
