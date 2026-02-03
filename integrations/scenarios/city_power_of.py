import asyncio

from devices.xiaomi import XiaomiSmartPlug2
from integrations.telegram.bot import send_message


class PlugScenario:

    def __init__(self, *devices: XiaomiSmartPlug2, power_threshold_w: int = 250, light: bool = True):
        self.devices = {device.name: device for device in devices}
        self.power_threshold_w = power_threshold_w
        self.light = light

    async def check_devices_power_status(self, device: XiaomiSmartPlug2, turn_on: bool = True):
        status = await device.status()

        if turn_on:  # turn on if not on
            if not status.on:
                await device.on()
                status.on = True
                return status, True

        if status.on and status.electric_power_w > self.power_threshold_w:  # turn off if power is too high
            await device.off()
            status.on = False
            return status, True

        return status, False

    async def run(self, delay: int = 10):
        while True:
            await asyncio.sleep(delay)
            for device in self.devices.values():
                status, changed = await self.check_devices_power_status(device, self.light)
                if not status.on and changed:
                    await send_message(f"{device.name} is now off, power: {status.electric_power_w}W")
                elif status.on and changed:
                    await send_message(f"{device.name} is now on")
