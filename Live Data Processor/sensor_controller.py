from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Any, Optional

from sensor_math import (
    calculate_zab_current_mA,
    calculate_apogee_o2_percent,
    calculate_zab_o2_percent,
)
from waveshare_adc_controller import WaveshareADCController
from sht_controller import SHTController


class SensorController:
    """
    Combines ADC, Apogee, ZAB math, and SHT readings into one row of data.
    """

    def __init__(self, mock_mode: bool = True) -> None:
        self.mock_mode = mock_mode
        self.adc = WaveshareADCController(mock_mode=mock_mode)
        self.sht = SHTController(mock_mode=mock_mode)
        self.connected = False
        self.start_monotonic = time.monotonic()

    def connect(self) -> None:
        self.adc.mock_mode = self.mock_mode
        self.sht.mock_mode = self.mock_mode

        try:
            self.adc.connect()
            print("ADC connected")
        except Exception as exc:
            print("ADC connect failed")
            print(repr(exc))
            raise

        try:
            self.sht.connect()
            print("SHT connected")
        except Exception as exc:
            print("SHT connect failed")
            print(repr(exc))
            raise

        self.connected = True
        self.start_monotonic = time.monotonic()

    def disconnect(self) -> None:
        self.adc.disconnect()
        self.connected = False

    def read_sample(
        self,
        load_resistor_ohms: float,
        apogee_calibration_voltage: float,
        zab_averages_mA: Optional[Dict[str, Optional[float]]] = None,
    ) -> Dict[str, Any]:
        now = datetime.now()
        elapsed_s = time.monotonic() - self.start_monotonic

        row: Dict[str, Any] = {
            "timestamp": now.isoformat(timespec="seconds"),
            "elapsed_s": round(elapsed_s, 3),
            "load_resistor_ohms": load_resistor_ohms,
            "apogee_calibration_voltage_V": apogee_calibration_voltage,
        }

        adc_values = self.adc.read_all()
        sht_values = self.sht.read_all()

        row.update(adc_values)
        row.update(sht_values)

        row["zab1_current_mA"] = calculate_zab_current_mA(row.get("zab1_voltage_mV"), load_resistor_ohms)
        row["zab2_current_mA"] = calculate_zab_current_mA(row.get("zab2_voltage_mV"), load_resistor_ohms)
        row["zab3_current_mA"] = calculate_zab_current_mA(row.get("zab3_voltage_mV"), load_resistor_ohms)

        row["apogee_o2_percent"] = calculate_apogee_o2_percent(
            row.get("apogee_voltage_V"),
            apogee_calibration_voltage,
        )

        averages = zab_averages_mA or {}
        for index in range(1, 4):
            avg_key = f"zab{index}_avg_mA"
            current_key = f"zab{index}_current_mA"
            o2_key = f"zab{index}_o2_percent"

            row[avg_key] = averages.get(avg_key)
            row[o2_key] = calculate_zab_o2_percent(row.get(current_key), row.get(avg_key))

        return row
