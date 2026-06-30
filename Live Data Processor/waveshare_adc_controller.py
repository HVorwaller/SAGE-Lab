from __future__ import annotations

import random
import math
import time
from typing import Optional, Dict


class WaveshareADCController:


    def __init__(self, mock_mode: bool = True, v_ref: float = 5.0) -> None:
        self.mock_mode = mock_mode
        self.v_ref = v_ref
        self.connected = False
        self.adc = None
        self.start_time = time.monotonic()

    def connect(self) -> None:
        if self.mock_mode:
            self.connected = True
        
        try:
            import ADS1256 # type: ignore

            self.adc =  ADS1256.ADS1256()

            result = self.adc.ADS1256_init()
            if result == -1:
                raise RuntimeError("ADS1256 initializtion failed.")
            
            self.connected = True

        except Exception as exc:
            self.connected = False
            raise RuntimeError(
                "Could not connect to the Waveshare ADS1256 Board." \
                "Check that ADS 1256.py and config.py are present, SPI is enabled," \
                "and the board is wired correctly."
            ) from exc


    def disconnect(self) -> None:
        if self.adc and not self.mock_mode:
            try:
                if hasattr(self.adc, "ADS1256_Exit"):
                    self.adc.ADS1256_Exit()
            except Exception:
                pass
        self.connected = False

    def read_voltage_mV(self, channel: int) -> Optional[float]:
        if not self.connected:
            return None
        
        if self.mock_mode:
            return self._mock_voltage_mV(channel)
        
        try:
            raw = self.adc.ADS1256_GetChannalValue(channel)

            #Convert signed 24-bit value
            if raw & 0x800000:
                raw -= 0x1000000

            voltage = raw * self.v_ref / 0x7FFFFF

            return voltage * 1000.0

        except Exception as exc:
            print(f"ADC Read Error: {exc}") 
            return None   

    def read_all(self) -> Dict[str, Optional[float]]:
        apogee_pos_mV = self.read_voltage_mV(0)
        apogee_neg_mV = self.read_voltage_mV(1)

        if apogee_pos_mV is None and apogee_neg_mV is None:
            apogee_voltage_V = None

        else:
            apogee_voltage_V = (apogee_pos_mV - apogee_neg_mV) / 1000.0
            
        return {
            apogee_voltage_V: apogee_voltage_V,
            "ZAB1_mV": self.read_voltage_mV(2),
            "ZAB2_mV": self.read_voltage_mV(3),
            "Zab3_mV": self.read_voltage_mV(4),
        }

    def _mock_voltage_mV(self, channel: int) -> float:
        t = time.monotonic() - self.start_time

        if channel == 0:
            base = 820.0 + 60.0 * math.sin(t / 18.0)
        elif channel == 1:
            base = 910.0 + 45.0 * math.sin(t / 21.0 + 1.2)
        elif channel == 2:
            base = 760.0 + 70.0 * math.sin(t / 16.0 + 2.0)
        elif channel == 3:
            # Apogee channel in mV, around 2.1 V at room O2 in mock mode.
            base = 2100.0 + 250.0 * math.sin(t / 45.0)
        else:
            base = 0.0

        return max(0.0, base + random.uniform(-6.0, 6.0))
