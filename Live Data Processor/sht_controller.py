from __future__ import annotations

import random
import math
import time
from typing import Optional, Dict, Tuple

class SHTController:

    def __init__(self, mock_mode: bool = True, addresses: tuple[int, int] = (0x44, 0x45)) -> None:
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
            import board
            import adafruit_hdc302x

            i2c = board.I2C()
            self.sensors = []

            for address in self.addresses:
                sensor = adafruit_hdc302x.HDC302x(i2c, address=address)
                self.sensors.append(sensor)

            self.connected = True

        except Exception as exc:
            self.connected = False
            raise RuntimeError(f"Could not connect to HDC302x sensors: {exc}") from exc

    def disconnect(self) -> None:
        self.sensors = []
        self.connected = False

    def read_all(self) -> Dict[str, Optional[float]]:
        if not self.connected:
            return{
                "sht1_temp_C": None,
                "sht1_humidity_percent": None,
                "sht2_temp_C": None,
                "sht2_humidity_percent": None,    
            }
        
        if self.mock_mode:
            return self._mock_read_all()
        
        values = {}

        for i in range(2):
            try:
                sensor = self.sensors[i]
                values[f"sht{i+1}_temp_C"] = float(sensor.temperature)
                values[f"sht{i+1}_humidity percent"] = float(sensor.relative_humidity)
            except Exception as exc:
                print(f"HDC READ FAILED for sensor {i+1}: {repr(exc)}")
                values[f"sht{i+1}_temp_C"] = None
                values[f"sht{i+1}_humidity_percent"] = None

        
        return values
    
    def _mock_read_all(self) -> Dict[str, Optional[float]]:
        t = time.monotonic() - self.start_time
        return{
            "sht1_temp_C": 22.0 + 0.7 * math.sin(t/30.0) + random.uniform(-0.05, 0.05),
            "sht1_humidity_percent": 42.0 + 3.0 * math.sin(t/40.0) + random.uniform(-0.2, 0.2),
            "sht2_temp_C": 22.5 + 0.6 * math.sin(t/35.0 + 1.2) + random.uniform(-0.05, 0.05),
            "sht2_humidity_percent": 44.0 + 2.5 * math.sin(t/38.0 + 0.8) + random.uniform(-0.2, 0.2),
        }

    


