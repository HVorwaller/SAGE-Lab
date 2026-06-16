from __future__ import annotations

import random
import math
import time
from typing import Optional, Dict, Tuple


class SHTController:
    """
    Reads up to two SHT sensors.

    Hardware notes:
    - If both SHT sensors have the same fixed I2C address, you will need an I2C
      multiplexer such as a TCA9548A.
    - This file supports mock mode immediately.
    - For real hardware, it first tries adafruit_sht4x.

    Default I2C addresses:
    - SHT4x commonly uses 0x44.
    - Some SHT3x sensors can use 0x44 or 0x45.
    """

    def __init__(self, mock_mode: bool = True, addresses: Tuple[int, int] = (0x44, 0x45)) -> None:
        self.mock_mode = mock_mode
        self.addresses = addresses
        self.connected = False
        self.sensors = []
        self.start_time = time.monotonic()

    def connect(self) -> None:
        if self.mock_mode:
            self.connected = True
            return

        try:
            import board  # type: ignore
            import adafruit_sht4x  # type: ignore

            i2c = board.I2C()
            self.sensors = []
            for address in self.addresses:
                try:
                    sensor = adafruit_sht4x.SHT4x(i2c, address=address)
                    sensor.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
                    self.sensors.append(sensor)
                except Exception:
                    self.sensors.append(None)

            if not any(self.sensors):
                raise RuntimeError("No SHT sensors found at the configured addresses.")

            self.connected = True

        except Exception as exc:
            self.connected = False
            raise RuntimeError(
                "Could not connect to SHT sensors. "
                "Use Mock Mode for testing, or check I2C wiring/address/multiplexer setup."
            ) from exc

    def read_all(self) -> Dict[str, Optional[float]]:
        if not self.connected:
            return {
                "sht1_temp_C": None,
                "sht1_humidity_percent": None,
                "sht2_temp_C": None,
                "sht2_humidity_percent": None,
            }

        if self.mock_mode:
            return self._mock_read_all()

        values = {}
        for i in range(2):
            sensor = self.sensors[i] if i < len(self.sensors) else None
            if sensor is None:
                values[f"sht{i+1}_temp_C"] = None
                values[f"sht{i+1}_humidity_percent"] = None
                continue

            try:
                temp_c, rh = sensor.measurements
                values[f"sht{i+1}_temp_C"] = float(temp_c)
                values[f"sht{i+1}_humidity_percent"] = float(rh)
            except Exception:
                values[f"sht{i+1}_temp_C"] = None
                values[f"sht{i+1}_humidity_percent"] = None

        return values

    def _mock_read_all(self) -> Dict[str, Optional[float]]:
        t = time.monotonic() - self.start_time
        return {
            "sht1_temp_C": 22.0 + 0.7 * math.sin(t / 30.0) + random.uniform(-0.05, 0.05),
            "sht1_humidity_percent": 42.0 + 3.0 * math.sin(t / 40.0) + random.uniform(-0.2, 0.2),
            "sht2_temp_C": 22.5 + 0.6 * math.sin(t / 35.0 + 1.2) + random.uniform(-0.05, 0.05),
            "sht2_humidity_percent": 44.0 + 2.5 * math.sin(t / 38.0 + 0.8) + random.uniform(-0.2, 0.2),
        }
