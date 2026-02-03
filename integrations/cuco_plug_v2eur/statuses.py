from dataclasses import dataclass
from enum import IntEnum


class PowerOnState(IntEnum):
    """Стан розетки після включення живлення (siid=2, piid=3)."""

    OFF = 0  # завжди вимкнута після включення
    ON = 1  # завжди включена після включення
    LAST = 2  # запам'ятовує останній стан



@dataclass(frozen=True)
class SmartPlug2Status:
    """
    Повний статус пристрою — отримається одним запитом через status().

    Атрибути сгрупповані за siid (service).
    """

    # --- siid=2  Switch ------------------------------------------------
    on: bool  # розетка включена / вимкнута
    fault: int  # код помилки пристрою (0 = ОК)
    default_power_on_state: int  # стан після включення живлення (PowerOnState)

    # --- siid=4  Max Power Limit ---------------------------------------
    max_power_limit_on: bool  # обмеження макс. потужності активне
    max_power_limit_kw: int  # порог обмеження (кВ, наприклад 2 = 2000W)
    protect_time_min: int  # час захисту зарядки (хвилини)

    # --- siid=5  Cycle (Розклад) ---------------------------------------
    cycle_on: bool  # розклад активний
    cycle_data: str  # дані розкладу (формат "on_хв;off_хв;flag;flag")

    # --- siid=7  Indicator ---------------------------------------------
    indicator_on: bool  # індикаторна лампа включена

    # --- siid=9  Delay (Таймер) ----------------------------------------
    delay_on: bool  # таймер відключення активний
    delay_time_sec: int  # часовий інтервал таймера (секунди)

    # --- siid=11 Power Consumption --------------------------------------
    power_consumption_wh: int  # загальна потужність (Wh) — ЗАВЖДИ 0 на цій моделі (firmware баг)
    electric_power_w: int  # поточна потужність (W)

    # --- siid=13 Physical Controls --------------------------------------
    physical_controls_locked: bool  # кнопка на корпусі заблокована

    # --- siid=14 Charging Protection ------------------------------------
    charging_protection_on: bool  # захист від перезарядки активний
    charging_protection_w: int  # порог захисту (W)
    charging_protection_remain: int  # залишковий час або статус (недокументовано)

    # ------------------------------------------------------------------
    # Зручні похідні власні атрибути
    # ------------------------------------------------------------------

    @property
    def power_on_state(self) -> PowerOnState:
        return PowerOnState(self.default_power_on_state)

    @property
    def max_power_limit_w(self) -> int:
        """Порог обмеження потужності в ватах (кВ * 1000)."""
        return self.max_power_limit_kw * 1000

    @property
    def delay_time_min(self) -> float:
        """Час таймера в хвилинах."""
        return self.delay_time_sec / 60

    @property
    def is_healthy(self) -> bool:
        """True якщо fault == 0."""
        return self.fault == 0

    # ------------------------------------------------------------------
    # __str__ — читабельний вивід
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        lines = [
            "┌── Xiaomi Smart Plug 2 (cuco.plug.v2eur) ──",
            f"│  Розетка:            {'ВКЛ' if self.on else 'ВИМК'}",
            f"│  Потужність:         {self.electric_power_w} W",
            f"│  Fault:              {self.fault}{'  ⚠ помилка!' if not self.is_healthy else ''}",
            f"│  Стан після включ:  {self.power_on_state.name}",
            "│",
            f"│  Індикатор:          {'ВКЛ' if self.indicator_on else 'ВИМК'}",
            f"│  Кнопка блок.:       {'ТАК' if self.physical_controls_locked else 'НІ'}",
            "│",
            "├── Таймер (Delay) ───",
            f"│  Активний:           {'ТАК' if self.delay_on else 'НІ'}",
            f"│  Час:                {self.delay_time_sec} сек ({self.delay_time_min:.1f} хв)",
            "│",
            "├── Обмеження потужності ───",
            f"│  Активне:            {'ТАК' if self.max_power_limit_on else 'НІ'}",
            f"│  Порог:              {self.max_power_limit_kw} кВ ({self.max_power_limit_w} W)",
            "│",
            "├── Захист зарядки ───",
            f"│  Активний:           {'ТАК' if self.charging_protection_on else 'НІ'}",
            f"│  Порог:              {self.charging_protection_w} W",
            f"│  Залишок/статус:     {self.charging_protection_remain}",
            f"│  Час захисту:        {self.protect_time_min} хв",
            "│",
            "├── Розклад (Cycle) ───",
            f"│  Активний:           {'ТАК' if self.cycle_on else 'НІ'}",
            f"│  Дані:               {self.cycle_data}",
            "│",
            "├── Споживання ───",
            f"│  Поточна потужність: {self.electric_power_w} W",
            f"│  Загальне (Wh):      {self.power_consumption_wh} (завжди 0 — firmware баг)",
            "└─────────────────────────────────────────────",
        ]
        return "\n".join(lines)

