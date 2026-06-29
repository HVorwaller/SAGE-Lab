from __future__ import annotations

import random
import math
import time
from typing import Optional, Dict


class WaveshareADCController:
    """
    Hardware wrapper for the Waveshare High-Precision AD/DA board.

    This first version is intentionally defensive:
    - It supports mock mode for development on Windows/Mac.
    - It tries to import a Waveshare ADS1263 driver on the Raspberry Pi.
    - If your exact Waveshare library has different method names, only this file
      should need edits.

    Expected channels:
        ZAB1 -> ADC channel 0
        ZAB2 -> ADC channel 1
        ZAB3 -> ADC channel 2
        Apogee -> ADC channel 3
    """

    def __init__(self, mock_mode: bool = True, v_ref: float = 5.0) -> None:
        self.mock_mode = mock_mode
        self.v_ref = v_ref
        self.connected = False
        self.adc = None
        self.start_time = time.monotonic()

    def connect(self) -> None:
        if self.mock_mode:
            self.connected = True
            return

        # Common Waveshare Python examples use something like:
        #   import ADS1263
        #   ADC = ADS1263.ADS1263()
        #
        # Depending on your installed library/repo, the import path may need adjustment.
        try:
            try:
                import ADS1263  # type: ignore
            except ImportError:
                from lib import ADS1263  # type: ignore

            self.adc = ADS1263.ADS1263()

            if hasattr(self.adc, "ADS1263_init_ADC1"):
                result = self.adc.ADS1263_init_ADC1("ADS1263_400SPS")
                if result == -1:
                    raise RuntimeError("ADS1263 initialization failed.")
            elif hasattr(self.adc, "init"):
                self.adc.init()
            else:
                raise RuntimeError("Could not find a supported ADS1263 initialization method.")

            self.connected = True

        except Exception as exc:
            self.connected = False
            raise RuntimeError(
                "Could not connect to the Waveshare ADC board. "
                "Use Mock Mode on a non-Pi computer, or update waveshare_adc_controller.py "
                "to match your installed Waveshare ADS1263 library."
            ) from exc

    def disconnect(self) -> None:
        if self.adc and not self.mock_mode:
            try:
                if hasattr(self.adc, "ADS1263_Exit"):
                    self.adc.ADS1263_Exit()
            except Exception:
                pass
        self.connected = False

    def read_voltage_mV(self, channel: int) -> Optional[float]:
        if not self.connected:
            return None

        if self.mock_mode:
            return self._mock_voltage_mV(channel)

        try:
            raw = None

            if hasattr(self.adc, "ADS1263_GetChannalValue"):
                raw = self.adc.ADS1263_GetChannalValue(channel)
            elif hasattr(self.adc, "read_channel"):
                return float(self.adc.read_channel(channel)) * 1000.0
            elif hasattr(self.adc, "read_voltage"):
                return float(self.adc.read_voltage(channel)) * 1000.0
            else:
                raise RuntimeError("No supported ADC read method found.")

            # Waveshare examples often convert signed 32-bit ADC code to voltage.
            # This is a reasonable default for ADS1263 32-bit bipolar codes.
            if raw is None:
                return None

            raw = int(raw)
            if raw >> 31 == 1:
                raw = raw - (1 << 32)

            voltage = raw * self.v_ref / 0x7FFFFFFF
            return voltage * 1000.0

        except Exception:
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
