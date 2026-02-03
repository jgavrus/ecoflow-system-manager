from dataclasses import dataclass
from enum import IntEnum


class PowerOnState(IntEnum):
    """Socket state after power is turned on (siid=2, piid=3)."""

    OFF = 0  # always off after power-on
    ON = 1  # always on after power-on
    LAST = 2  # remembers the last state


@dataclass
class SmartPlug2Status:
    """
    Full device status — obtained with a single request via status().

    Attributes are grouped by siid (service).
    """

    # --- siid=2  Switch ------------------------------------------------
    on: bool  # socket is on / off
    fault: int  # device error code (0 = OK)
    default_power_on_state: int  # state after power-on (PowerOnState)

    # --- siid=4  Max Power Limit ---------------------------------------
    max_power_limit_on: bool  # max power limit is active
    max_power_limit_kw: int  # limit threshold (kW, e.g. 2 = 2000W)
    protect_time_min: int  # charging protection time (minutes)

    # --- siid=5  Cycle (Schedule) ---------------------------------------
    cycle_on: bool  # schedule is active
    cycle_data: str  # schedule data (format "on_min;off_min;flag;flag")

    # --- siid=7  Indicator ---------------------------------------------
    indicator_on: bool  # indicator LED is on

    # --- siid=9  Delay (Timer) ----------------------------------------
    delay_on: bool  # power-off timer is active
    delay_time_sec: int  # timer interval (seconds)

    # --- siid=11 Power Consumption --------------------------------------
    power_consumption_wh: int  # total energy (Wh) — ALWAYS 0 on this model (firmware bug)
    electric_power_w: int  # current power (W)

    # --- siid=13 Physical Controls --------------------------------------
    physical_controls_locked: bool  # the device button is locked

    # --- siid=14 Charging Protection ------------------------------------
    charging_protection_on: bool  # overcharge protection is active
    charging_protection_w: int  # protection threshold (W)
    charging_protection_remain: int  # remaining time or status (undocumented)

    # ------------------------------------------------------------------
    # Convenient derived custom attributes
    # ------------------------------------------------------------------

    @property
    def power_on_state(self) -> PowerOnState:
        return PowerOnState(self.default_power_on_state)

    @property
    def max_power_limit_w(self) -> int:
        """Power limit threshold in watts (kW * 1000)."""
        return self.max_power_limit_kw * 1000

    @property
    def delay_time_min(self) -> float:
        """Timer duration in minutes."""
        return self.delay_time_sec / 60

    @property
    def is_healthy(self) -> bool:
        """True if fault == 0."""
        return self.fault == 0

    # ------------------------------------------------------------------
    # __str__ — human-readable output
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        lines = [
            "┌── Xiaomi Smart Plug 2 (cuco.plug.v2eur) ──",
            f"│  Socket:             {'ON' if self.on else 'OFF'}",
            f"│  Power:              {self.electric_power_w} W",
            f"│  Fault:              {self.fault}{'  ⚠ error!' if not self.is_healthy else ''}",
            f"│  State after power:  {self.power_on_state.name}",
            "│",
            f"│  Indicator:          {'ON' if self.indicator_on else 'OFF'}",
            f"│  Button locked:      {'YES' if self.physical_controls_locked else 'NO'}",
            "│",
            "├── Timer (Delay) ───",
            f"│  Active:             {'YES' if self.delay_on else 'NO'}",
            f"│  Time:               {self.delay_time_sec} sec ({self.delay_time_min:.1f} min)",
            "│",
            "├── Power limit ───",
            f"│  Active:             {'YES' if self.max_power_limit_on else 'NO'}",
            f"│  Threshold:          {self.max_power_limit_kw} kW ({self.max_power_limit_w} W)",
            "│",
            "├── Charging protection ───",
            f"│  Active:             {'YES' if self.charging_protection_on else 'NO'}",
            f"│  Threshold:          {self.charging_protection_w} W",
            f"│  Remaining/status:   {self.charging_protection_remain}",
            f"│  Protection time:    {self.protect_time_min} min",
            "│",
            "├── Schedule (Cycle) ───",
            f"│  Active:             {'YES' if self.cycle_on else 'NO'}",
            f"│  Data:               {self.cycle_data}",
            "│",
            "├── Consumption ───",
            f"│  Current power:      {self.electric_power_w} W",
            f"│  Total (Wh):         {self.power_consumption_wh} (always 0 — firmware bug)",
            "└─────────────────────────────────────────────",
        ]
        return "\n".join(lines)
