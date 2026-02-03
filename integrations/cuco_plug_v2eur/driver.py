import logging
import os
import warnings
from typing import Optional

# remove useless future warning
warnings.filterwarnings("ignore", category=FutureWarning, module=r"miio\.miot_device")
from miio import MiotDevice

from integrations.cuco_plug_v2eur.statuses import SmartPlug2Status, PowerOnState

logging.getLogger("miio").setLevel(logging.ERROR)  # remove warning about undoc device


class XiaomiSmartPlug2(MiotDevice):
    """
    Xiaomi Smart Plug 2 Wi-Fi (cuco.plug.v2eur)
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

    def __init__(self, ip: str, token: str):
        super().__init__(ip, token, mapping=self.MAPPING)

    def status(self) -> SmartPlug2Status:
        """Get full device status."""
        props = self.get_properties_for_mapping()
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

    def on(self) -> None:
        self.set_property_by(siid=2, piid=1, value=True)

    def off(self) -> None:
        self.set_property_by(siid=2, piid=1, value=False)

    def toggle(self) -> None:
        """on->off/off->on"""
        current = self.get_property_by(siid=2, piid=1)[0]["value"]
        self.set_property_by(siid=2, piid=1, value=not current)

    @property
    def is_on(self) -> bool:
        return self.get_property_by(siid=2, piid=1)[0]["value"]

    @property
    def fault(self) -> int:
        """Device error code. 0 = OK."""
        return self.get_property_by(siid=2, piid=2)[0]["value"]

    def set_power_on_state(self, state: PowerOnState) -> None:
        """
        Set the default power-on state.

        Args:
            state: PowerOnState.OFF / ON / LAST
        """
        self.set_property_by(siid=2, piid=3, value=int(state))

    @property
    def power(self) -> int:
        """Current power (W)."""
        return self.get_property_by(siid=11, piid=2)[0]["value"]

    @property
    def power_consumption(self) -> int:
        """
        Total charged energy (Wh).

        ⚠️ Firmware bug on cuco.plug.v2eur always returns 0.
        See: hass-xiaomi-miot issue #1347
        """
        return self.get_property_by(siid=11, piid=1)[0]["value"]

    # ==================================================================
    # siid=7 — INDICATOR
    # ==================================================================

    def set_indicator(self, on: bool) -> None:
        """Turn the LED indicator on/off."""
        self.set_property_by(siid=7, piid=1, value=on)

    @property
    def indicator_on(self) -> bool:
        """LED indicator status."""
        return self.get_property_by(siid=7, piid=1)[0]["value"]

    def set_physical_controls_locked(self, locked: bool) -> None:
        """Lock/unlock the physical button."""
        self.set_property_by(siid=13, piid=1, value=locked)

    @property
    def physical_controls_locked(self) -> bool:
        """True if the button is locked."""
        return self.get_property_by(siid=13, piid=1)[0]["value"]

    def set_delay(self, seconds: int) -> None:
        """
        Set up a timer in seconds.

        Args:
            seconds: 0 or less = disable timer.
        """
        if seconds <= 0:
            self.set_property_by(siid=9, piid=1, value=False)
        else:
            self.set_property_by(siid=9, piid=2, value=seconds)
            self.set_property_by(siid=9, piid=1, value=True)

    def set_delay_minutes(self, minutes: float) -> None:
        """Set up a timer in minutes."""
        self.set_delay(int(minutes * 60))

    def cancel_delay(self) -> None:
        """Cancel the timer."""
        self.set_property_by(siid=9, piid=1, value=False)

    @property
    def delay_on(self) -> bool:
        """True if the timer is enabled."""
        return self.get_property_by(siid=9, piid=1)[0]["value"]

    @property
    def delay_time_sec(self) -> int:
        """Remaining timer time in seconds."""
        return self.get_property_by(siid=9, piid=2)[0]["value"]

    def set_max_power_limit(self, kw: Optional[int] = None) -> None:
        """
        Set up the maximum power limit.

        Args:
            kw: in kW (1 = 1000W, 2 = 2000W, 3 = 3000W).
                None = disable the limit.

        Example:
            plug.set_max_power_limit(2) limit 2 kW (2000W)
            plug.set_max_power_limit(None) disable the limit
        """
        if kw is None:
            self.set_property_by(siid=4, piid=1, value=False)
        else:
            self.set_property_by(siid=4, piid=2, value=kw)
            self.set_property_by(siid=4, piid=1, value=True)

    @property
    def max_power_limit_on(self) -> bool:
        """True if the power limit is enabled."""
        return self.get_property_by(siid=4, piid=1)[0]["value"]

    @property
    def max_power_limit_kw(self) -> int:
        """Power limit value in kW."""
        return self.get_property_by(siid=4, piid=2)[0]["value"]

    def set_charging_protection(self, watts: Optional[int] = None) -> None:
        """
        Set charging protection.

        Args:
            watts: e.g. 60.
                   None = disable charging protection.

        Examples:
            plug.set_charging_protection(60)    # protect at 60W
            plug.set_charging_protection(None)  # remove protection
        """
        if watts is None:
            self.set_property_by(siid=14, piid=1, value=False)
        else:
            self.set_property_by(siid=14, piid=2, value=watts)
            self.set_property_by(siid=14, piid=1, value=True)

    @property
    def charging_protection_on(self) -> bool:
        """True if protection is enabled."""
        return self.get_property_by(siid=14, piid=1)[0]["value"]

    @property
    def charging_protection_w(self) -> int:
        """Charging protection value/status (W)."""
        return self.get_property_by(siid=14, piid=2)[0]["value"]

    @property
    def charging_protection_remain(self) -> int:
        """
        Remaining time or status.

        ⚠️ Not documented in the openHAB spec.
        Value 0 = disabled or finished.
        """
        return self.get_property_by(siid=14, piid=3)[0]["value"]

    def set_protect_time(self, minutes: int) -> None:
        """
        Set charging protection time.

        Args:
            minutes: time in minutes (e.g. 5).
        """
        self.set_property_by(siid=4, piid=3, value=minutes)

    @property
    def protect_time_min(self) -> int:
        """Charging protection time (minutes)."""
        return self.get_property_by(siid=4, piid=3)[0]["value"]

    # ==================================================================
    # siid=5 — CYCLE (schedule)
    # ==================================================================

    def set_cycle(self, on: bool) -> None:
        """Enable/disable the schedule."""
        self.set_property_by(siid=5, piid=1, value=on)

    def set_cycle_data(self, data: str) -> None:
        """
        Set schedule data.

        Args:
            data: string in the format "on_min;off_min;flag;flag"
                  Example: "30;30;0;1"

        ⚠️ The exact format is undocumented.
           Recommended: first change the schedule via Mi Home,
           then read cycle_data via status() to understand the format.
        """
        self.set_property_by(siid=5, piid=2, value=data)

    @property
    def cycle_on(self) -> bool:
        """True if the schedule is active."""
        return self.get_property_by(siid=5, piid=1)[0]["value"]

    @property
    def cycle_data(self) -> str:
        """Schedule data (raw string)."""
        return self.get_property_by(siid=5, piid=2)[0]["value"]


if __name__ == "__main__":
    plug = XiaomiSmartPlug2(os.getenv("PLUG_ADDRESS"), os.getenv("PLUG_TOKEN"))
    plug.off()
