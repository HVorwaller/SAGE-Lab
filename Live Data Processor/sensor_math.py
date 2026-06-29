from __future__ import annotations

import math
from typing import Optional


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_zab_current_mA(voltage_mV: Optional[float], load_resistor_ohms: float) -> Optional[float]:
    """
    ZAB current formula:
        current_mA = (5000 - voltage_mV) / load_resistor_ohms
    """
    if voltage_mV is None:
        return None
    if load_resistor_ohms <= 0:
        return None
    return (5000.0 - float(voltage_mV)) / float(load_resistor_ohms)


def calculate_apogee_o2_percent(current_voltage: Optional[float], calibration_voltage: float) -> Optional[float]:
    """
    Apogee O2 formula:
        O2_percent = 20.95 / calibration_voltage * current_apogee_voltage
    """
    if current_voltage is None:
        return None
    if calibration_voltage <= 0:
        return None
    return (20.95 / float(calibration_voltage)) * float(current_voltage)


def calculate_zab_o2_percent(zab_current_mA: Optional[float], zab_avg_mA: Optional[float]) -> Optional[float]:
    """
    Calculated ZAB O2 formula from the user's calibration equation:

        O2 = (-0.8966 + sqrt(0.80389156 + 0.0232 * (0.1873 + ((20.95 / ZABavg) * ZAB)))) / 0.011595

    where:
        ZAB = current ZAB current in mA
        ZABavg = averaged room-air calibration current in mA
    """
    if zab_current_mA is None or zab_avg_mA is None:
        return None
    if zab_avg_mA <= 0:
        return None

    inside = 0.80389156 + 0.0232 * (0.1873 + ((20.95 / zab_avg_mA) * zab_current_mA))
    if inside < 0:
        return None

    return (-0.8966 + math.sqrt(inside)) / 0.011595


def c_to_f(temp_c: Optional[float]) -> Optional[float]:
    if temp_c is None:
        return None
    return temp_c * 9.0 / 5.0 + 32.0


def dew_point_c(temp_c: Optional[float], rh_percent: Optional[float]) -> Optional[float]:
    if temp_c is None or rh_percent is None or rh_percent <= 0:
        return None
    a = 17.62
    b = 243.12
    gamma = (a * temp_c / (b + temp_c)) + math.log(rh_percent / 100.0)
    return (b * gamma) / (a - gamma)
