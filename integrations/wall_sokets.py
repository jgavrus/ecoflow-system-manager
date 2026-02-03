from loguru import logger
from typing import Optional

from miio import MiotDevice

from integrations.cuco_plug_v2eur.statuses import SmartPlug2Status, PowerOnState


class XiaomiSmartPlug2(MiotDevice):
    """
    Xiaomi Smart Plug 2 Wi-Fi  (cuco.plug.v2eur)
    ─────────────────────────────────────────────
    Повний MIoT маппинг:

        siid=2   Switch
            piid=1  on                          bool  RW
            piid=2  fault                       int   R
            piid=3  default_power_on_state      int   RW   (0/1/2 → PowerOnState)

        siid=4   Max Power Limit
            piid=1  on                          bool  RW
            piid=2  power                       int   RW   (кВ, наприклад 2 = 2000W)
            piid=3  protect_time                int   RW   (хвилини)

        siid=5   Cycle (Розклад)
            piid=1  status                      bool  RW
            piid=2  data_value                  str   RW   ("on_хв;off_хв;flag;flag")

        siid=7   Indicator Light
            piid=1  on                          bool  RW

        siid=9   Delay (Таймер)
            piid=1  on                          bool  RW
            piid=2  delay_time                  int   RW   (секунди)

        siid=11  Power Consumption
            piid=1  power_consumption           int   R    (Wh — завжди 0, баг)
            piid=2  electric_power              int   R    (W)

        siid=13  Physical Controls
            piid=1  locked                      bool  RW

        siid=14  Charging Protection
            piid=1  on                          bool  RW
            piid=2  power                       int   RW   (W)
            piid=3  remain / status             int   R    (недокументовано)
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
        """Отримати повний статус пристрою."""
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

    # ==================================================================
    # siid=2 — SWITCH
    # ==================================================================

    def on(self) -> None:
        self.set_property_by(siid=2, piid=1, value=True)

    def off(self) -> None:
        self.set_property_by(siid=2, piid=1, value=False)

    def toggle(self) -> None:
        """on->off/off-on"""
        current = self.get_property_by(siid=2, piid=1)[0]["value"]
        self.set_property_by(siid=2, piid=1, value=not current)

    @property
    def is_on(self) -> bool:
        return self.get_property_by(siid=2, piid=1)[0]["value"]

    @property
    def fault(self) -> int:
        """device error code. 0 = ОК."""
        return self.get_property_by(siid=2, piid=2)[0]["value"]

    def set_power_on_state(self, state: PowerOnState) -> None:
        """
        set default power on state.

        Args:
            state: PowerOnState.OFF / ON / LAST
        """
        self.set_property_by(siid=2, piid=3, value=int(state))

    @property
    def power(self) -> int:
        """current power (W)."""
        return self.get_property_by(siid=11, piid=2)[0]["value"]

    @property
    def power_consumption(self) -> int:
        """
        all charged power (Wh).

        ⚠️ firmware bug on cuco.plug.v2eur allways returns 0.
        see: hass-xiaomi-miot issue #1347
        """
        return self.get_property_by(siid=11, piid=1)[0]["value"]

    # ==================================================================
    # siid=7 — INDICATOR
    # ==================================================================

    def set_indicator(self, on: bool) -> None:
        """on/of LED indicator."""
        self.set_property_by(siid=7, piid=1, value=on)

    @property
    def indicator_on(self) -> bool:
        """LED indicator status."""
        return self.get_property_by(siid=7, piid=1)[0]["value"]

    def set_physical_controls_locked(self, locked: bool) -> None:
        """lock/unlock button."""
        self.set_property_by(siid=13, piid=1, value=locked)

    @property
    def physical_controls_locked(self) -> bool:
        """True if button is locked."""
        return self.get_property_by(siid=13, piid=1)[0]["value"]

    # ==================================================================
    # siid=9 — DELAY (таймер відключення)
    # ==================================================================

    def set_delay(self, seconds: int) -> None:
        """
        setup timer in secconds.

        Args:
            seconds: 0 or less = disable timer.
        """
        if seconds <= 0:
            self.set_property_by(siid=9, piid=1, value=False)
        else:
            self.set_property_by(siid=9, piid=2, value=seconds)
            self.set_property_by(siid=9, piid=1, value=True)

    def set_delay_minutes(self, minutes: float) -> None:
        """setup timer in minutes."""
        self.set_delay(int(minutes * 60))

    def cancel_delay(self) -> None:
        """cancel timer."""
        self.set_property_by(siid=9, piid=1, value=False)

    @property
    def delay_on(self) -> bool:
        """True if timer is on."""
        return self.get_property_by(siid=9, piid=1)[0]["value"]

    @property
    def delay_time_sec(self) -> int:
        """timer left time in seconds."""
        return self.get_property_by(siid=9, piid=2)[0]["value"]

    def set_max_power_limit(self, kw: Optional[int] = None) -> None:
        """
        setup max power limit.

        Args:
            kw: in kW (1 = 1000W, 2 = 2000W, 3 = 3000W).
                None = disable limit.

        example:
            plug.set_max_power_limit(2)     # лміт 2 кВ (2000W)
            plug.set_max_power_limit(None)  # вимкнути лміт
        """
        if kw is None:
            self.set_property_by(siid=4, piid=1, value=False)
        else:
            self.set_property_by(siid=4, piid=2, value=kw)
            self.set_property_by(siid=4, piid=1, value=True)

    @property
    def max_power_limit_on(self) -> bool:
        """True if power limit is enabled."""
        return self.get_property_by(siid=4, piid=1)[0]["value"]

    @property
    def max_power_limit_kw(self) -> int:
        """value in kW of power limit."""
        return self.get_property_by(siid=4, piid=2)[0]["value"]

    def set_charging_protection(self, watts: Optional[int] = None) -> None:
        """
        set charging protection.

        Args:
            watts: example 60.
                   None = disable charging protection.

        examples:
            plug.set_charging_protection(60)    # protect 60W
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
        """charging protection status (W)."""
        return self.get_property_by(siid=14, piid=2)[0]["value"]

    @property
    def charging_protection_remain(self) -> int:
        """
        remain time or status.

        ⚠️  not documented in openhab spec.
        value 0 = disabled or finished.
        """
        return self.get_property_by(siid=14, piid=3)[0]["value"]

    def set_protect_time(self, minutes: int) -> None:
        """
        Встановити час захисту зарядки.

        Args:
            minutes: час в хвилинах (наприклад 5).
        """
        self.set_property_by(siid=4, piid=3, value=minutes)

    @property
    def protect_time_min(self) -> int:
        """Час захисту зарядки (хвилини)."""
        return self.get_property_by(siid=4, piid=3)[0]["value"]

    # ==================================================================
    # siid=5 — CYCLE (розклад)
    # ==================================================================

    def set_cycle(self, on: bool) -> None:
        """on/off."""
        self.set_property_by(siid=5, piid=1, value=on)

    def set_cycle_data(self, data: str) -> None:
        """
        Встановити дані розкладу.

        Args:
            data: строка у форматі "on_хв;off_хв;flag;flag"
                  Приклад: "30;30;0;1"

        ⚠️  Точний формат undocumented.
             Рекомендовано: спочатку зміните розклад через Mi Home,
             потім читайте cycle_data через status() щоб зрозуміти формат.
        """
        self.set_property_by(siid=5, piid=2, value=data)

    @property
    def cycle_on(self) -> bool:
        """True якщо розклад активний."""
        return self.get_property_by(siid=5, piid=1)[0]["value"]

    @property
    def cycle_data(self) -> str:
        """Дані розкладу (raw строка)."""
        return self.get_property_by(siid=5, piid=2)[0]["value"]


if __name__ == "__main__":
    plug = XiaomiSmartPlug2("≈", "≈")
    print(plug.set_cycle_data())
