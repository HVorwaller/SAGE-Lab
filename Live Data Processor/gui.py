from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from sensor_controller import SensorController
from data_logger import CSVLogger
from graph_manager import GraphManager
from widgets import SensorReadoutCard, format_value


class SensorDashboard(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("ZAB Sensor Dashboard")
        self.resize(1550, 900)

        self.controller = SensorController(mock_mode=True)
        self.logger = CSVLogger()
        self.graph_manager = GraphManager()
        self.history: List[Dict[str, Any]] = []
        self.max_history_points = 3000

        self.zab_averages_mA: Dict[str, Optional[float]] = {
            "zab1_avg_mA": None,
            "zab2_avg_mA": None,
            "zab3_avg_mA": None,
        }

        self.calibration_active = False
        self.calibration_elapsed_ms = 0
        self.calibration_samples: Dict[str, List[float]] = {
            "zab1_current_mA": [],
            "zab2_current_mA": [],
            "zab3_current_mA": [],
        }

        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.read_update)

        self.calibration_timer = QTimer(self)
        self.calibration_timer.timeout.connect(self.update_calibration_timer)

        self._build_ui()
        self.update_status("Disconnected")

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout()

        title = QLabel("ZAB Sensor Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        root.addWidget(title)

        top = QHBoxLayout()
        top.addWidget(self._build_connection_box())
        top.addWidget(self._build_settings_box())
        top.addWidget(self._build_calibration_box())
        top.addWidget(self._build_logging_box())
        top.addWidget(self._build_pinout_button_box())
        root.addLayout(top)

        middle = QHBoxLayout()
        middle.addWidget(self._build_readout_box(), stretch=0)
        middle.addWidget(self._build_graph_box(), stretch=1)
        root.addLayout(middle, stretch=1)

        central.setLayout(root)
        self.setCentralWidget(central)

    def _build_connection_box(self) -> QGroupBox:
        box = QGroupBox("Connection")
        layout = QGridLayout()

        self.mock_checkbox = QCheckBox("Mock Mode")
        self.mock_checkbox.setChecked(True)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_sensors)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_sensors)
        self.disconnect_button.setEnabled(False)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("font-weight: bold;")

        layout.addWidget(self.mock_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.connect_button, 1, 0)
        layout.addWidget(self.disconnect_button, 1, 1)
        layout.addWidget(QLabel("Status:"), 2, 0)
        layout.addWidget(self.status_label, 2, 1)

        box.setLayout(layout)
        return box

    def _build_settings_box(self) -> QGroupBox:
        box = QGroupBox("Processing Settings")
        layout = QGridLayout()

        self.load_resistor_spin = QDoubleSpinBox()
        self.load_resistor_spin.setRange(1.0, 100000.0)
        self.load_resistor_spin.setValue(220.0)
        self.load_resistor_spin.setDecimals(2)
        self.load_resistor_spin.setSuffix(" Ω")

        self.apogee_cal_spin = QDoubleSpinBox()
        self.apogee_cal_spin.setRange(0.0001, 1000.0)
        self.apogee_cal_spin.setValue(2.100)
        self.apogee_cal_spin.setDecimals(4)
        self.apogee_cal_spin.setSuffix(" V")

        self.sample_interval_spin = QSpinBox()
        self.sample_interval_spin.setRange(100, 60000)
        self.sample_interval_spin.setValue(1000)
        self.sample_interval_spin.setSuffix(" ms")
        self.sample_interval_spin.valueChanged.connect(self.update_timer_interval)

        layout.addWidget(QLabel("ZAB Load Resistor:"), 0, 0)
        layout.addWidget(self.load_resistor_spin, 0, 1)
        layout.addWidget(QLabel("Apogee Cal Voltage:"), 1, 0)
        layout.addWidget(self.apogee_cal_spin, 1, 1)
        layout.addWidget(QLabel("Sample Interval:"), 2, 0)
        layout.addWidget(self.sample_interval_spin, 2, 1)

        box.setLayout(layout)
        return box

    def _build_calibration_box(self) -> QGroupBox:
        box = QGroupBox("ZAB O₂ Calibration")
        layout = QGridLayout()

        self.calibration_minutes_spin = QDoubleSpinBox()
        self.calibration_minutes_spin.setRange(0.1, 120.0)
        self.calibration_minutes_spin.setValue(5.0)
        self.calibration_minutes_spin.setDecimals(2)
        self.calibration_minutes_spin.setSuffix(" min")

        self.start_zab_avg_button = QPushButton("Collect ZAB Avg")
        self.start_zab_avg_button.clicked.connect(self.start_zab_average_collection)
        self.start_zab_avg_button.setEnabled(False)

        self.cancel_zab_avg_button = QPushButton("Cancel")
        self.cancel_zab_avg_button.clicked.connect(self.cancel_zab_average_collection)
        self.cancel_zab_avg_button.setEnabled(False)

        self.calibration_status_label = QLabel("No ZAB averages collected")
        self.calibration_time_label = QLabel("Timer: 5:00")

        self.zab1_avg_label = QLabel("ZAB 1 avg: --")
        self.zab2_avg_label = QLabel("ZAB 2 avg: --")
        self.zab3_avg_label = QLabel("ZAB 3 avg: --")

        layout.addWidget(QLabel("Average Time:"), 0, 0)
        layout.addWidget(self.calibration_minutes_spin, 0, 1)
        layout.addWidget(self.start_zab_avg_button, 1, 0)
        layout.addWidget(self.cancel_zab_avg_button, 1, 1)
        layout.addWidget(self.calibration_status_label, 2, 0, 1, 2)
        layout.addWidget(self.calibration_time_label, 3, 0, 1, 2)
        layout.addWidget(self.zab1_avg_label, 4, 0, 1, 2)
        layout.addWidget(self.zab2_avg_label, 5, 0, 1, 2)
        layout.addWidget(self.zab3_avg_label, 6, 0, 1, 2)

        box.setLayout(layout)
        return box

    def _build_logging_box(self) -> QGroupBox:
        box = QGroupBox("CSV Logging")
        layout = QGridLayout()

        self.csv_path_edit = QLineEdit(str(Path.home() / "zab_sensor_log.csv"))
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.choose_csv_path)

        self.start_logging_button = QPushButton("Start Logging")
        self.start_logging_button.clicked.connect(self.start_logging)
        self.start_logging_button.setEnabled(False)

        self.stop_logging_button = QPushButton("Stop Logging")
        self.stop_logging_button.clicked.connect(self.stop_logging)
        self.stop_logging_button.setEnabled(False)

        self.logging_status_label = QLabel("Not logging")
        self.row_count_label = QLabel("Rows: 0")

        layout.addWidget(QLabel("CSV File:"), 0, 0)
        layout.addWidget(self.csv_path_edit, 0, 1)
        layout.addWidget(self.browse_button, 0, 2)
        layout.addWidget(self.start_logging_button, 1, 0)
        layout.addWidget(self.stop_logging_button, 1, 1)
        layout.addWidget(self.logging_status_label, 2, 0, 1, 2)
        layout.addWidget(self.row_count_label, 2, 2)

        box.setLayout(layout)
        return box

    def _build_pinout_button_box(self) -> QGroupBox:
        box = QGroupBox("Reference")
        layout = QVBoxLayout()

        self.pinout_button = QPushButton("Open Pinout Map")
        self.pinout_button.clicked.connect(self.show_pinout_map)

        layout.addWidget(self.pinout_button)
        layout.addStretch()
        box.setLayout(layout)
        return box

    def show_pinout_map(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Sensor and ZAB Pinout Map")
        dialog.resize(900, 520)

        layout = QVBoxLayout()

        title = QLabel("Sensor and ZAB Pinout Map")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        note = QLabel(
            "Default ADC map shown below."
        )
        layout.addWidget(note)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Device",
            "Signal",
            "Pi / Board Connection",
            "Expected Unit",
            "Notes",
        ])

        pinout_rows = [
            ["ZAB 1", "Voltage sense", "Waveshare ADC CH0", "mV", "Used for ZAB 1 current calculation"],
            ["ZAB 2", "Voltage sense", "Waveshare ADC CH1", "mV", "Used for ZAB 2 current calculation"],
            ["ZAB 3", "Voltage sense", "Waveshare ADC CH2", "mV", "Used for ZAB 3 current calculation"],
            ["Apogee O₂", "Analog voltage", "Waveshare ADC CH3", "mV", "Used for Apogee calculated O₂"],
            ["SHT 1", "I²C SDA", "Pi GPIO 2 / SDA", "Digital", "I²C data line"],
            ["SHT 1", "I²C SCL", "Pi GPIO 3 / SCL", "Digital", "I²C clock line"],
            ["SHT 1", "Power", "3.3V", "V", "Use 3.3V unless your breakout requires otherwise"],
            ["SHT 1", "Ground", "GND", "V", "Common ground"],
            ["SHT 2", "I²C SDA", "Pi GPIO 2 / SDA", "Digital", "May require I²C mux if same address as SHT 1"],
            ["SHT 2", "I²C SCL", "Pi GPIO 3 / SCL", "Digital", "May require I²C mux if same address as SHT 1"],
            ["SHT 2", "Power", "3.3V", "V", "Use 3.3V unless your breakout requires otherwise"],
            ["SHT 2", "Ground", "GND", "V", "Common ground"],
            ["Waveshare ADC", "SPI MOSI", "Pi GPIO 10 / MOSI", "Digital", "SPI data from Pi to ADC board"],
            ["Waveshare ADC", "SPI MISO", "Pi GPIO 9 / MISO", "Digital", "SPI data from ADC board to Pi"],
            ["Waveshare ADC", "SPI SCLK", "Pi GPIO 11 / SCLK", "Digital", "SPI clock"],
            ["Waveshare ADC", "Chip Select", "Pi GPIO 8 / CE0", "Digital", "Default SPI CE0"],
            ["Waveshare ADC", "Power", "3.3V or 5V", "V", "Match Waveshare board documentation"],
            ["Waveshare ADC", "Ground", "GND", "V", "Common ground with sensors"],
        ]

        table.setRowCount(len(pinout_rows))

        for row_index, row_data in enumerate(pinout_rows):
            for col_index, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                table.setItem(row_index, col_index, item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)

        layout.addWidget(table)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        dialog.setLayout(layout)
        dialog.exec()

    def _build_readout_box(self) -> QGroupBox:
        box = QGroupBox("Live Sensor Readouts")
        layout = QVBoxLayout()

        self.zab1_card = SensorReadoutCard("ZAB 1")
        self.zab2_card = SensorReadoutCard("ZAB 2")
        self.zab3_card = SensorReadoutCard("ZAB 3")
        self.apogee_card = SensorReadoutCard("Apogee O₂")
        self.sht1_card = SensorReadoutCard("SHT 1")
        self.sht2_card = SensorReadoutCard("SHT 2")

        for card in [
            self.zab1_card,
            self.zab2_card,
            self.zab3_card,
            self.apogee_card,
            self.sht1_card,
            self.sht2_card,
        ]:
            layout.addWidget(card)

        layout.addStretch()
        box.setLayout(layout)
        return box

    def _build_graph_box(self) -> QGroupBox:
        box = QGroupBox("Graph")
        layout = QVBoxLayout()

        controls = QHBoxLayout()

        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["Time", "Apogee Calculated O2"])
        self.x_axis_combo.currentTextChanged.connect(self.update_graph)

        controls.addWidget(QLabel("X-axis:"))
        controls.addWidget(self.x_axis_combo)

        self.freeze_graph_checkbox = QCheckBox("Freeze Graph View")
        self.freeze_graph_checkbox.setToolTip(
            "Pause live graph redraws so you can pan, drag, and zoom without the view resetting."
        )
        controls.addWidget(self.freeze_graph_checkbox)

        self.plot_checks: Dict[str, QCheckBox] = {}

        options = [
            ("zab1_current_mA", "ZAB 1 Current"),
            ("zab2_current_mA", "ZAB 2 Current"),
            ("zab3_current_mA", "ZAB 3 Current"),

            ("zab1_o2_percent", "ZAB 1 Calc O₂"),
            ("zab2_o2_percent", "ZAB 2 Calc O₂"),
            ("zab3_o2_percent", "ZAB 3 Calc O₂"),

            ("apogee_o2_percent", "Apogee O₂"),
            ("sht1_temp_C", "SHT 1 Temp"),
            ("sht2_temp_C", "SHT 2 Temp"),
            ("sht1_humidity_percent", "SHT 1 RH"),
            ("sht2_humidity_percent", "SHT 2 RH"),
        ]

        for key, text in options:
            check = QCheckBox(text)
            check.stateChanged.connect(self.update_graph)
            if key.startswith("zab") and "current" in key:
                check.setChecked(True)
            self.plot_checks[key] = check
            controls.addWidget(check)

        controls.addStretch()
        layout.addLayout(controls)
        layout.addWidget(self.graph_manager.canvas, stretch=1)

        box.setLayout(layout)
        return box

    def connect_sensors(self) -> None:
        try:
            self.controller = SensorController(mock_mode=self.mock_checkbox.isChecked())
            self.controller.connect()

            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.start_logging_button.setEnabled(True)
            self.start_zab_avg_button.setEnabled(True)
            self.mock_checkbox.setEnabled(False)

            self.read_timer.start(self.sample_interval_spin.value())
            self.update_status("Connected")
        except Exception as exc:
            QMessageBox.critical(self, "Connection Error", str(exc))
            self.update_status("Connection failed")

    def disconnect_sensors(self) -> None:
        self.read_timer.stop()
        self.stop_logging()
        self.cancel_zab_average_collection()
        self.controller.disconnect()

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.start_logging_button.setEnabled(False)
        self.start_zab_avg_button.setEnabled(False)
        self.mock_checkbox.setEnabled(True)

        self.update_status("Disconnected")

    def update_status(self, text: str) -> None:
        self.status_label.setText(text)

    def update_timer_interval(self) -> None:
        if self.read_timer.isActive():
            self.read_timer.start(self.sample_interval_spin.value())

    def choose_csv_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose CSV Log File",
            self.csv_path_edit.text(),
            "CSV Files (*.csv);;All Files (*)",
        )
        if path:
            if not path.lower().endswith(".csv"):
                path += ".csv"
            self.csv_path_edit.setText(path)

    def start_logging(self) -> None:
        try:
            self.logger.start(self.csv_path_edit.text())
            self.logging_status_label.setText(f"Logging: {self.csv_path_edit.text()}")
            self.start_logging_button.setEnabled(False)
            self.stop_logging_button.setEnabled(True)
            self.browse_button.setEnabled(False)
            self.csv_path_edit.setEnabled(False)
        except Exception as exc:
            QMessageBox.critical(self, "Logging Error", str(exc))

    def stop_logging(self) -> None:
        if self.logger.is_logging:
            self.logger.stop()

        self.logging_status_label.setText("Not logging")
        self.start_logging_button.setEnabled(self.controller.connected)
        self.stop_logging_button.setEnabled(False)
        self.browse_button.setEnabled(True)
        self.csv_path_edit.setEnabled(True)

    def start_zab_average_collection(self) -> None:
        if not self.controller.connected:
            QMessageBox.warning(self, "Not Connected", "Connect sensors before collecting ZAB averages.")
            return

        self.calibration_active = True
        self.calibration_elapsed_ms = 0
        self.calibration_samples = {
            "zab1_current_mA": [],
            "zab2_current_mA": [],
            "zab3_current_mA": [],
        }

        self.zab_averages_mA = {
            "zab1_avg_mA": None,
            "zab2_avg_mA": None,
            "zab3_avg_mA": None,
        }

        duration_ms = self.get_calibration_duration_ms()
        self.calibration_minutes_spin.setEnabled(False)
        self.start_zab_avg_button.setEnabled(False)
        self.cancel_zab_avg_button.setEnabled(True)
        self.calibration_status_label.setText("Collecting ZAB average...")
        self.calibration_time_label.setText(f"Timer: {self.format_remaining_time(duration_ms)}")
        self.update_average_labels()
        self.calibration_timer.start(1000)

    def cancel_zab_average_collection(self) -> None:
        self.calibration_active = False
        self.calibration_timer.stop()
        self.cancel_zab_avg_button.setEnabled(False)
        self.start_zab_avg_button.setEnabled(self.controller.connected)
        self.calibration_minutes_spin.setEnabled(True)
        if self.controller.connected:
            self.calibration_status_label.setText("ZAB average collection cancelled")

    def get_calibration_duration_ms(self) -> int:
        return int(self.calibration_minutes_spin.value() * 60 * 1000)

    def format_remaining_time(self, remaining_ms: int) -> str:
        remaining_s = max(0, remaining_ms // 1000)
        minutes = remaining_s // 60
        seconds = remaining_s % 60
        return f"{minutes}:{seconds:02d}"

    def update_calibration_timer(self) -> None:
        if not self.calibration_active:
            return

        self.calibration_elapsed_ms += 1000
        duration_ms = self.get_calibration_duration_ms()
        remaining_ms = max(0, duration_ms - self.calibration_elapsed_ms)
        self.calibration_time_label.setText(f"Timer: {self.format_remaining_time(remaining_ms)}")

        if self.calibration_elapsed_ms >= duration_ms:
            self.finish_zab_average_collection()

    def collect_calibration_sample(self, row: Dict[str, Any]) -> None:
        if not self.calibration_active:
            return

        for key in self.calibration_samples:
            value = row.get(key)
            if value is not None:
                self.calibration_samples[key].append(float(value))

        self.update_running_zab_averages()

        counts = [len(values) for values in self.calibration_samples.values()]
        sample_count = min(counts) if counts else 0
        self.calibration_status_label.setText(f"Collecting ZAB average... samples: {sample_count}")

    def update_running_zab_averages(self) -> None:
        mapping = {
            "zab1_current_mA": "zab1_avg_mA",
            "zab2_current_mA": "zab2_avg_mA",
            "zab3_current_mA": "zab3_avg_mA",
        }

        for sample_key, avg_key in mapping.items():
            samples = self.calibration_samples.get(sample_key, [])
            self.zab_averages_mA[avg_key] = sum(samples) / len(samples) if samples else None

        self.update_average_labels()

    def finish_zab_average_collection(self) -> None:
        self.calibration_active = False
        self.calibration_timer.stop()

        # Running averages are already updated every sample.
        self.update_running_zab_averages()

        self.cancel_zab_avg_button.setEnabled(False)
        self.start_zab_avg_button.setEnabled(self.controller.connected)
        self.calibration_minutes_spin.setEnabled(True)
        self.calibration_status_label.setText("ZAB averages collected")
        self.update_average_labels()

    def update_average_labels(self) -> None:
        self.zab1_avg_label.setText(f"ZAB 1 avg: {format_value(self.zab_averages_mA.get('zab1_avg_mA'), 4, ' mA')}")
        self.zab2_avg_label.setText(f"ZAB 2 avg: {format_value(self.zab_averages_mA.get('zab2_avg_mA'), 4, ' mA')}")
        self.zab3_avg_label.setText(f"ZAB 3 avg: {format_value(self.zab_averages_mA.get('zab3_avg_mA'), 4, ' mA')}")

    def read_update(self) -> None:
        load_resistor = self.load_resistor_spin.value()
        apogee_cal = self.apogee_cal_spin.value()

        # During averaging, this row uses the running average from the previous sample.
        row = self.controller.read_sample(load_resistor, apogee_cal, self.zab_averages_mA)

        self.collect_calibration_sample(row)

        # Recalculate once after collecting the sample so the displayed/logged ZAB O2 uses
        # the newest running average.
        if self.calibration_active:
            row = self.controller.read_sample(load_resistor, apogee_cal, self.zab_averages_mA)

        self.history.append(row)
        if len(self.history) > self.max_history_points:
            self.history = self.history[-self.max_history_points:]

        self.update_readouts(row)

        if self.logger.is_logging:
            self.logger.log_row(row)
            self.row_count_label.setText(f"Rows: {self.logger.rows_written}")

        # When frozen, the graph does not redraw every sample.
        # This lets the Matplotlib toolbar pan/drag/zoom stay where the user put it.
        if not self.freeze_graph_checkbox.isChecked():
            self.update_graph()

    def update_readouts(self, row: Dict[str, Any]) -> None:
        self.zab1_card.set_lines(
            f"Voltage: {format_value(row.get('zab1_voltage_mV'), 2, ' mV')}",
            f"Current: {format_value(row.get('zab1_current_mA'), 4, ' mA')}",
            f"Calc O₂: {format_value(row.get('zab1_o2_percent'), 3, ' %')}",
        )
        self.zab2_card.set_lines(
            f"Voltage: {format_value(row.get('zab2_voltage_mV'), 2, ' mV')}",
            f"Current: {format_value(row.get('zab2_current_mA'), 4, ' mA')}",
            f"Calc O₂: {format_value(row.get('zab2_o2_percent'), 3, ' %')}",
        )
        self.zab3_card.set_lines(
            f"Voltage: {format_value(row.get('zab3_voltage_mV'), 2, ' mV')}",
            f"Current: {format_value(row.get('zab3_current_mA'), 4, ' mA')}",
            f"Calc O₂: {format_value(row.get('zab3_o2_percent'), 3, ' %')}",
        )
        self.apogee_card.set_lines(
            f"Voltage: {format_value(row.get('apogee_voltage_V'), 4, ' V')}",
            f"O₂: {format_value(row.get('apogee_o2_percent'), 3, ' %')}",
        )
        self.sht1_card.set_lines(
            f"Temp: {format_value(row.get('sht1_temp_C'), 2, ' °C')}",
            f"RH: {format_value(row.get('sht1_humidity_percent'), 2, ' %')}",
        )
        self.sht2_card.set_lines(
            f"Temp: {format_value(row.get('sht2_temp_C'), 2, ' °C')}",
            f"RH: {format_value(row.get('sht2_humidity_percent'), 2, ' %')}",
        )

    def selected_plot_keys(self) -> List[str]:
        return [key for key, check in self.plot_checks.items() if check.isChecked()]

    def update_graph(self) -> None:
        x_mode = self.x_axis_combo.currentText()
        self.graph_manager.update_graph(self.history, x_mode, self.selected_plot_keys())

    def closeEvent(self, event) -> None:
        self.stop_logging()
        self.read_timer.stop()
        self.calibration_timer.stop()
        try:
            self.controller.disconnect()
        except Exception:
            pass
        event.accept()
