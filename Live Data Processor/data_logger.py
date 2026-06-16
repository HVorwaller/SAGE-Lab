from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Dict, Any


CSV_COLUMNS = [
    "timestamp",
    "elapsed_s",

    "zab1_voltage_mV",
    "zab1_current_mA",
    "zab1_avg_mA",
    "zab1_o2_percent",

    "zab2_voltage_mV",
    "zab2_current_mA",
    "zab2_avg_mA",
    "zab2_o2_percent",

    "zab3_voltage_mV",
    "zab3_current_mA",
    "zab3_avg_mA",
    "zab3_o2_percent",

    "apogee_voltage_V",
    "apogee_o2_percent",

    "sht1_temp_C",
    "sht1_humidity_percent",
    "sht2_temp_C",
    "sht2_humidity_percent",

    "load_resistor_ohms",
    "apogee_calibration_voltage_V",
]


class CSVLogger:
    def __init__(self) -> None:
        self.path: Optional[Path] = None
        self.file = None
        self.writer: Optional[csv.DictWriter] = None
        self.is_logging = False
        self.rows_written = 0

    def start(self, path: str | Path) -> None:
        if self.is_logging:
            self.stop()

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.file = self.path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=CSV_COLUMNS)
        self.writer.writeheader()
        self.file.flush()

        self.is_logging = True
        self.rows_written = 0

    def log_row(self, row: Dict[str, Any]) -> None:
        if not self.is_logging or self.writer is None or self.file is None:
            return

        clean_row = {}

        for key in CSV_COLUMNS:
            value = row.get(key, "")

            if isinstance(value, float):
                value = round(value, 4)

            clean_row[key] = value

        self.writer.writerow(clean_row)
        self.rows_written += 1
        self.file.flush()

    def stop(self) -> None:
        if self.file:
            self.file.flush()
            self.file.close()

        self.file = None
        self.writer = None
        self.is_logging = False

    def __del__(self) -> None:
        self.stop()
