import asyncio
import logging
import os
import warnings
from typing import Optional

# remove useless future warning
warnings.filterwarnings("ignore", category=FutureWarning, module=r"miio\.miot_device")
from miio import MiotDevice

from .statuses import SmartPlug2Status, PowerOnState

logging.getLogger("miio").setLevel(logging.ERROR)  # remove warning about an undoc device


class XiaomiSmartPlug2(MiotDevice):
    """
    Xiaomi Smart Plug 2 Wi-Fi (cuco.plug.v2eur) - Async version
    ───────────────────────────────────────────
    Full MIoT mapping:

        siid=2   Switch
            piid=1  on                          bool  RW
            piid=2  fault                       int   R
            piid=3  default_power_on_state      int   RW   (0/1/2 → PowerOnState)

        siid=4   Max Power Limit
            piid=1  on                          bool  RW
            piid=2  power                       int   RW   (kW, e.g. 2 = 2000W)
            piid=3  protect_time                int   RW   (minutes)

        siid=5   Cycle (Schedule)
            piid=1  status                      bool  RW
            piid=2  data_value                  str   RW   ("on_min;off_min;flag;flag")

        siid=7   Indicator Light
            piid=1  on                          bool  RW

        siid=9   Delay (Timer)
            piid=1  on                          bool  RW
            piid=2  delay_time                  int   RW   (seconds)

        siid=11  Power Consumption
            piid=1  power_consumption           int   R    (Wh — always 0, bug)
            piid=2  electric_power              int   R    (W)

        siid=13  Physical Controls
            piid=1  locked                      bool  RW

        siid=14  Charging Protection
            piid=1  on                          bool  RW
            piid=2  power                       int   RW   (W)
            piid=3  remain / status             int   R    (undocumented)
    """

    MAPPING = {
        # Switch (siid=2)
        "on": {"siid": 2, "piid": 1},
        "fault": {"siid": 2, "piid": 2},
        "default_power_on_state": {"siid": 2, "piid": 3},
        # Max Power Limit (siid=4)
        "max_power_limit_on": {"siid": 4, "piid": 1},
        "max_power_limit_kw": {"siid": 4, "piid": 2},
        "protect_time_min": {"siid": 4, "piid": 3},
        # Cycle (siid=5)
        "cycle_on": {"siid": 5, "piid": 1},
        "cycle_data": {"siid": 5, "piid": 2},
        # Indicator (siid=7)
        "indicator_on": {"siid": 7, "piid": 1},
        # Delay (siid=9)
        "delay_on": {"siid": 9, "piid": 1},
        "delay_time_sec": {"siid": 9, "piid": 2},
        # Power Consumption (siid=11)
        "power_consumption_wh": {"siid": 11, "piid": 1},
        "electric_power_w": {"siid": 11, "piid": 2},
        # Physical Controls (siid=13)
        "physical_controls_locked": {"siid": 13, "piid": 1},
        # Charging Protection (siid=14)
        "charging_protection_on": {"siid": 14, "piid": 1},
        "charging_protection_w": {"siid": 14, "piid": 2},
        "charging_protection_remain": {"siid": 14, "piid": 3},
    }

    def __init__(self, ip: str, token: str, name: str):
        self.name = name
        super().__init__(ip, token, mapping=self.MAPPING)

    async def status(self) -> SmartPlug2Status:
        """Get full device status."""
        props = await asyncio.to_thread(self.get_properties_for_mapping)
        v = {p["did"]: p.get("value") for p in props}

        return SmartPlug2Status(
            on=v["on"],
            fault=v["fault"],
            default_power_on_state=v["default_power_on_state"],
            max_power_limit_on=v["max_power_limit_on"],
            max_power_limit_kw=v["max_power_limit_kw"],
            protect_time_min=v["protect_time_min"],
            cycle_on=v["cycle_on"],
            cycle_data=v["cycle_data"],
            indicator_on=v["indicator_on"],
            delay_on=v["delay_on"],
            delay_time_sec=v["delay_time_sec"],
            power_consumption_wh=v["power_consumption_wh"],
            electric_power_w=v["electric_power_w"],
            physical_controls_locked=v["physical_controls_locked"],
            charging_protection_on=v["charging_protection_on"],
            charging_protection_w=v["charging_protection_w"],
            charging_protection_remain=v["charging_protection_remain"],
        )

    async def on(self) -> None:
        await asyncio.to_thread(self.set_property_by, siid=2, piid=1, value=True)

    async def off(self) -> None:
        await asyncio.to_thread(self.set_property_by, siid=2, piid=1, value=False)

    async def toggle(self) -> None:
        """on->off/off->on"""
        current = await self.get_is_on()
        await asyncio.to_thread(self.set_property_by, siid=2, piid=1, value=not current)

    async def get_is_on(self) -> bool:
        result = await asyncio.to_thread(self.get_property_by, siid=2, piid=1)
        return result[0]["value"]

    async def get_fault(self) -> int:
        """Device error code. 0 = OK."""
        result = await asyncio.to_thread(self.get_property_by, siid=2, piid=2)
        return result[0]["value"]

    async def set_power_on_state(self, state: PowerOnState) -> None:
        """
        Set the default power-on state.

        Args:
            state: PowerOnState.OFF / ON / LAST
        """
        await asyncio.to_thread(self.set_property_by, siid=2, piid=3, value=int(state))

    async def get_power(self) -> int:
        """Current power (W)."""
        result = await asyncio.to_thread(self.get_property_by, siid=11, piid=2)
        return result[0]["value"]

    async def get_power_consumption(self) -> int:
        """
        Total charged energy (Wh).

        Firmware bug on cuco.plug.v2eur always returns 0.
        See: hass-xiaomi-miot issue #1347
        """
        result = await asyncio.to_thread(self.get_property_by, siid=11, piid=1)
        return result[0]["value"]

    # ==================================================================
    # siid=7 — INDICATOR
    # ==================================================================

    async def set_indicator(self, on: bool) -> None:
        """Turn the LED indicator on/off."""
        await asyncio.to_thread(self.set_property_by, siid=7, piid=1, value=on)

    async def get_indicator_on(self) -> bool:
        """LED indicator status."""
        result = await asyncio.to_thread(self.get_property_by, siid=7, piid=1)
        return result[0]["value"]

    async def set_physical_controls_locked(self, locked: bool) -> None:
        """Lock/unlock the physical button."""
        await asyncio.to_thread(self.set_property_by, siid=13, piid=1, value=locked)

    async def get_physical_controls_locked(self) -> bool:
        """True if the button is locked."""
        result = await asyncio.to_thread(self.get_property_by, siid=13, piid=1)
        return result[0]["value"]

    async def set_delay(self, seconds: int) -> None:
        """
        Set up a timer in seconds.

        Args:
            seconds: 0 or less = disable timer.
        """
        if seconds <= 0:
            await asyncio.to_thread(self.set_property_by, siid=9, piid=1, value=False)
        else:
            await asyncio.to_thread(self.set_property_by, siid=9, piid=2, value=seconds)
            await asyncio.to_thread(self.set_property_by, siid=9, piid=1, value=True)

    async def set_delay_minutes(self, minutes: float) -> None:
        """Set up a timer in minutes."""
        await self.set_delay(int(minutes * 60))

    async def cancel_delay(self) -> None:
        """Cancel the timer."""
        await asyncio.to_thread(self.set_property_by, siid=9, piid=1, value=False)

    async def get_delay_on(self) -> bool:
        """True if the timer is enabled."""
        result = await asyncio.to_thread(self.get_property_by, siid=9, piid=1)
        return result[0]["value"]

    async def get_delay_time_sec(self) -> int:
        """Remaining timer time in seconds."""
        result = await asyncio.to_thread(self.get_property_by, siid=9, piid=2)
        return result[0]["value"]

    async def set_max_power_limit(self, kw: Optional[int] = None) -> None:
        """
        Set up the maximum power limit.

        Args:
            kw: in kW (1 = 1000W, 2 = 2000W, 3 = 3000W).
                None = disable the limit.

        Example:
            await plug.set_max_power_limit(2)    # limit 2 kW (2000W)
            await plug.set_max_power_limit(None) # disable the limit
        """
        if kw is None:
            await asyncio.to_thread(self.set_property_by, siid=4, piid=1, value=False)
        else:
            await asyncio.to_thread(self.set_property_by, siid=4, piid=2, value=kw)
            await asyncio.to_thread(self.set_property_by, siid=4, piid=1, value=True)

    async def get_max_power_limit_on(self) -> bool:
        """True if the power limit is enabled."""
        result = await asyncio.to_thread(self.get_property_by, siid=4, piid=1)
        return result[0]["value"]

    async def get_max_power_limit_kw(self) -> int:
        """Power limit value in kW."""
        result = await asyncio.to_thread(self.get_property_by, siid=4, piid=2)
        return result[0]["value"]

    async def set_charging_protection(self, watts: Optional[int] = None) -> None:
        """
        Set charging protection.

        Args:
            watts: e.g. 60.
                   None = disable charging protection.

        Examples:
            await plug.set_charging_protection(60)    # protect at 60W
            await plug.set_charging_protection(None)  # remove protection
        """
        if watts is None:
            await asyncio.to_thread(self.set_property_by, siid=14, piid=1, value=False)
        else:
            await asyncio.to_thread(self.set_property_by, siid=14, piid=2, value=watts)
            await asyncio.to_thread(self.set_property_by, siid=14, piid=1, value=True)

    async def get_charging_protection_on(self) -> bool:
        """True if protection is enabled."""
        result = await asyncio.to_thread(self.get_property_by, siid=14, piid=1)
        return result[0]["value"]

    async def get_charging_protection_w(self) -> int:
        """Charging protection value/status (W)."""
        result = await asyncio.to_thread(self.get_property_by, siid=14, piid=2)
        return result[0]["value"]

    async def get_charging_protection_remain(self) -> int:
        """
        Remaining time or status.

        Not documented in the openHAB spec.
        Value 0 = disabled or finished.
        """
        result = await asyncio.to_thread(self.get_property_by, siid=14, piid=3)
        return result[0]["value"]

    async def set_protect_time(self, minutes: int) -> None:
        """
        Set charging protection time.

        Args:
            minutes: time in minutes (e.g. 5).
        """
        await asyncio.to_thread(self.set_property_by, siid=4, piid=3, value=minutes)

    async def get_protect_time_min(self) -> int:
        """Charging protection time (minutes)."""
        result = await asyncio.to_thread(self.get_property_by, siid=4, piid=3)
        return result[0]["value"]

    async def set_cycle(self, on: bool) -> None:
        """Enable/disable the schedule."""
        await asyncio.to_thread(self.set_property_by, siid=5, piid=1, value=on)

    async def set_cycle_data(self, data: str) -> None:
        """
        Set schedule data.

        Args:
            data: string in the format "on_min;off_min;flag;flag"
                  Example: "30;30;0;1"

        ⚠️ The exact format is undocumented.
           Recommended: first change the schedule via Mi Home,
           then read cycle_data via status() to understand the format.
        """
        await asyncio.to_thread(self.set_property_by, siid=5, piid=2, value=data)

    async def get_cycle_on(self) -> bool:
        """True if the schedule is active."""
        result = await asyncio.to_thread(self.get_property_by, siid=5, piid=1)
        return result[0]["value"]

    async def get_cycle_data(self) -> str:
        """Schedule data (raw string)."""
        result = await asyncio.to_thread(self.get_property_by, siid=5, piid=2)
        return result[0]["value"]


async def main():
    plug = XiaomiSmartPlug2(os.getenv("PLUG_ADDRESS"), os.getenv("PLUG_TOKEN"), name="Test Plug")
    await plug.off()
    status = await plug.status()
    print(status)


if __name__ == "__main__":
    asyncio.run(main())
