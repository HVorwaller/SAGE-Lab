import sys

from mfc_controller import MFCController
from sequence_validator import validate_sequence_preflight, build_targets_from_step
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QGroupBox,
    QComboBox,
    QTextEdit,
    QGridLayout,
    QLineEdit,
)

from gas_math import calculate_mfc_flows
from humidity_controller import SHTController
from humidity_math import calculate_feedback_humidity_flows, calculate_open_loop_humidity_flows
from graph_manager import GraphManager
from mfc_ui_helpers import (
    build_manual_targets,
    build_mfc_config,
    reset_mfc_flow_labels,
    update_filler_display,
    update_manual_max_flow_labels,
    update_visible_mfcs,
    validate_mfc_setup,
)
from sequence_loader import load_sequence_from_excel
from widgets import DropLabel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MFC Control App")
        self.setMinimumSize(1000, 700)

        self.current_time = 0
        self.time_data = [0]
        self.sequence_steps = []
        self.current_step_number = None
        self.current_humidity_target_rh = None
        self.current_wet_fraction = 0.5
        self.humidity_control_active = False
        self.latest_measured_rh = None
        self.latest_humidity_error_abs = None
        self.manual_active_result = None
        self.current_normal_total_flow_lpm = 0.0
        self.mfc_controller = MFCController(mock_mode=True)
        self.sht_controller = SHTController(mock_mode=True)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graph)

        self.flow_read_timer = QTimer()
        self.flow_read_timer.timeout.connect(self.update_actual_flow_display)
        self.flow_read_timer.start(1000)

        self.humidity_timer = QTimer()
        self.humidity_timer.timeout.connect(self.update_humidity_feedback_loop)
        self.humidity_timer.start(5000)

        main_widget = QWidget()
        main_layout = QGridLayout()

        main_widget.setLayout(main_layout)
        main_layout.setColumnStretch(0, 3)
        main_layout.setColumnStretch(1, 1)
        main_layout.setRowStretch(0, 1)
        main_layout.setRowStretch(1, 3)
        main_layout.setRowStretch(2, 0)
        main_layout.setRowStretch(3, 1)
        self.setCentralWidget(main_widget)

        self.build_instruction_panel(main_layout)
        self.build_mfc_setup_panel(main_layout)
        self.build_graph_panel(main_layout)
        self.build_sequence_control_panel(main_layout)
        self.build_connection_panel(main_layout)
        self.build_runtime_log_panel(main_layout)

        self.update_visible_mfcs()
        self.update_filler_display()
        self.update_manual_max_flow_labels()
        self.activate_excel_mode()
        self.update_mfc_connection_status_display(False)

    # -------------------------------------------------------------------------
    # UI BUILDERS
    # -------------------------------------------------------------------------

    def build_instruction_panel(self, main_layout):
        instruction_box = QGroupBox("Instructions / Status")
        instruction_layout = QVBoxLayout()

        self.instruction_label = QLabel("Choose the number of MFCs and assign gases")
        self.instruction_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        instruction_layout.addWidget(self.instruction_label)
        instruction_box.setLayout(instruction_layout)
        main_layout.addWidget(instruction_box, 0, 0)

    def build_mfc_setup_panel(self, main_layout):
        mfc_box = QGroupBox("MFC Setup")
        mfc_layout = QVBoxLayout()

        self.mfc_selector = QComboBox()
        self.mfc_selector.addItems(["1 MFC", "2 MFCs", "3 MFCs", "4 MFCs"])

        mfc_layout.addWidget(QLabel("Number of MFCs"))
        mfc_layout.addWidget(self.mfc_selector)

        mfc_grid = QGridLayout()
        mfc_grid.addWidget(QLabel("MFC"), 0, 0)
        mfc_grid.addWidget(QLabel("Gas"), 0, 1)
        mfc_grid.addWidget(QLabel("Max Flow Rate"), 0, 2)
        mfc_grid.addWidget(QLabel("Address"), 0, 3)
        mfc_grid.addWidget(QLabel("Current Flow"), 0, 4)

        self.mfc_rows = []
        self.mfc_config_widgets = []

        for i in range(1, 5):
            mfc_grid.addWidget(QLabel(f"MFC {i}"), i, 0)

            gas_selector = QComboBox()
            gas_selector.addItems([
                "None",
                "O2",
                "N2",
                "CH4/N2 Mix",
                "CO2",
                "Air",
                "Other"
            ])

            flow_rate_selector = QComboBox()
            flow_rate_selector.addItems([
                "None",
                "0.5 L/min",
                "2.0 L/min"
            ])
            flow_rate_selector.currentIndexChanged.connect(self.update_manual_max_flow_labels)

            address_selector = QComboBox()
            address_selector.addItems([
                "N/A",
                "0",
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
            ])

            flow_label = QLabel("0.000 L/min")

            row_widgets = [
                mfc_grid.itemAtPosition(i, 0).widget(),
                gas_selector,
                flow_rate_selector,
                address_selector,
                flow_label,
            ]

            self.mfc_config_widgets.append({
                "mfc_number": i,
                "gas": gas_selector,
                "max_flow_rate": flow_rate_selector,
                "address": address_selector,
                "current_flow": flow_label
            })

            self.mfc_rows.append(row_widgets)

            mfc_grid.addWidget(gas_selector, i, 1)
            mfc_grid.addWidget(flow_rate_selector, i, 2)
            mfc_grid.addWidget(address_selector, i, 3)
            mfc_grid.addWidget(flow_label, i, 4)

        self.mfc_selector.currentIndexChanged.connect(self.update_visible_mfcs)

        mfc_layout.addLayout(mfc_grid)
        mfc_box.setLayout(mfc_layout)
        main_layout.addWidget(mfc_box, 0, 1)

    def build_graph_panel(self, main_layout):
        self.graph_box = QGroupBox("Live Concentration Sequence")
        graph_layout = QVBoxLayout()

        self.graph_manager = GraphManager()
        graph_layout.addWidget(self.graph_manager.graph_widget)

        self.graph_box.setLayout(graph_layout)
        main_layout.addWidget(self.graph_box, 1, 0)

    def build_sequence_control_panel(self, main_layout):
        sequence_box = QGroupBox("Sequence Control")
        sequence_layout = QVBoxLayout()

        # Control mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Control Mode:"))

        self.manual_mode_button = QPushButton("Manual Single Step")
        self.excel_mode_button = QPushButton("Excel Sequence")

        self.manual_mode_button.setCheckable(True)
        self.excel_mode_button.setCheckable(True)
        self.excel_mode_button.setChecked(True)

        mode_row.addWidget(self.manual_mode_button)
        mode_row.addWidget(self.excel_mode_button)
        sequence_layout.addLayout(mode_row)

        # Flow mode selector. This can be changed while a sequence is running.
        flow_mode_row = QHBoxLayout()
        flow_mode_row.addWidget(QLabel("Flow Mode:"))

        self.continuous_flow_button = QPushButton("Continuous Flow")
        self.timed_flow_button = QPushButton("Timed Flow")
        self.adaptive_flow_button = QPushButton("Adaptive Mode")

        self.continuous_flow_button.setCheckable(True)
        self.timed_flow_button.setCheckable(True)
        self.adaptive_flow_button.setCheckable(True)
        self.continuous_flow_button.setChecked(True)

        flow_mode_row.addWidget(self.continuous_flow_button)
        flow_mode_row.addWidget(self.timed_flow_button)
        flow_mode_row.addWidget(self.adaptive_flow_button)
        sequence_layout.addLayout(flow_mode_row)

        flow_settings_row = QHBoxLayout()
        flow_settings_row.addWidget(QLabel("Timed Flow Duration sec:"))
        self.timed_flow_duration_input = QLineEdit("90")
        flow_settings_row.addWidget(self.timed_flow_duration_input)
        flow_settings_row.addWidget(QLabel("Adaptive RH Threshold %:"))
        self.adaptive_rh_threshold_input = QLineEdit("2.5")
        flow_settings_row.addWidget(self.adaptive_rh_threshold_input)
        sequence_layout.addLayout(flow_settings_row)

        self.manual_mode_button.clicked.connect(self.activate_manual_mode)
        self.excel_mode_button.clicked.connect(self.activate_excel_mode)
        self.continuous_flow_button.clicked.connect(self.activate_continuous_flow_mode)
        self.timed_flow_button.clicked.connect(self.activate_timed_flow_mode)
        self.adaptive_flow_button.clicked.connect(self.activate_adaptive_flow_mode)

        self.build_humidity_control_box(sequence_layout)
        self.build_manual_single_step_box(sequence_layout)
        self.build_excel_drop_box(sequence_layout)
        self.build_runtime_buttons(sequence_layout)

        sequence_box.setLayout(sequence_layout)
        main_layout.addWidget(sequence_box, 1, 1)


    def build_humidity_control_box(self, sequence_layout):
        self.humidity_box = QGroupBox("Humidity Control")
        humidity_layout = QVBoxLayout()

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Humidity Mode:"))

        self.humidity_mode_button = QPushButton("Humidity Mode Off")
        self.humidity_mode_button.setCheckable(True)
        self.humidity_mode_button.clicked.connect(self.toggle_humidity_mode)
        mode_row.addWidget(self.humidity_mode_button)
        humidity_layout.addLayout(mode_row)

        setup_grid = QGridLayout()
        setup_grid.addWidget(QLabel("Wet MFC Address"), 0, 0)
        setup_grid.addWidget(QLabel("Dry MFC Address"), 0, 1)
        setup_grid.addWidget(QLabel("SHT Address"), 0, 2)

        address_options = ["N/A"] + [str(i) for i in range(0, 16)]

        self.humidity_wet_address_selector = QComboBox()
        self.humidity_wet_address_selector.addItems(address_options)
        self.humidity_wet_address_selector.setCurrentText("4")
        self.humidity_wet_address_selector.currentIndexChanged.connect(
            lambda: self.update_mfc_connection_status_display(self.mfc_controller.connected)
        )

        self.humidity_dry_address_selector = QComboBox()
        self.humidity_dry_address_selector.addItems(address_options)
        self.humidity_dry_address_selector.setCurrentText("5")
        self.humidity_dry_address_selector.currentIndexChanged.connect(
            lambda: self.update_mfc_connection_status_display(self.mfc_controller.connected)
        )

        self.sht_address_selector = QComboBox()
        self.sht_address_selector.addItems(["0x44", "0x45", "0x46", "0x47"])
        self.sht_address_selector.currentIndexChanged.connect(
            lambda: self.update_mfc_connection_status_display(self.mfc_controller.connected)
        )

        setup_grid.addWidget(self.humidity_wet_address_selector, 1, 0)
        setup_grid.addWidget(self.humidity_dry_address_selector, 1, 1)
        setup_grid.addWidget(self.sht_address_selector, 1, 2)

        setup_grid.addWidget(QLabel("Humidity Flow Offset L/min"), 2, 0)
        setup_grid.addWidget(QLabel("Humidifier Output RH %"), 2, 1)
        setup_grid.addWidget(QLabel("Feedback Kp"), 2, 2)

        self.humidity_flow_offset_input = QLineEdit("0.0")
        self.humidifier_output_rh_input = QLineEdit("100")
        self.humidity_kp_input = QLineEdit("0.01")

        setup_grid.addWidget(self.humidity_flow_offset_input, 3, 0)
        setup_grid.addWidget(self.humidifier_output_rh_input, 3, 1)
        setup_grid.addWidget(self.humidity_kp_input, 3, 2)

        setup_grid.addWidget(QLabel("Manual Target RH %"), 4, 0)
        setup_grid.addWidget(QLabel("Measured RH"), 4, 1)
        setup_grid.addWidget(QLabel("Wet / Dry Flow"), 4, 2)

        self.manual_humidity_target_input = QLineEdit("50")
        self.measured_rh_label = QLabel("-- %")
        self.humidity_flow_label = QLabel("Wet: -- L/min | Dry: -- L/min")

        setup_grid.addWidget(self.manual_humidity_target_input, 5, 0)
        setup_grid.addWidget(self.measured_rh_label, 5, 1)
        setup_grid.addWidget(self.humidity_flow_label, 5, 2)

        self.humidity_config_widgets = []
        for item_index in range(setup_grid.count()):
            item = setup_grid.itemAt(item_index)
            widget = item.widget()

            if widget is not None:
                self.humidity_config_widgets.append(widget)

        humidity_layout.addLayout(setup_grid)
        self.humidity_box.setLayout(humidity_layout)
        sequence_layout.addWidget(self.humidity_box)
        self.update_humidity_ui_enabled()

    def build_manual_single_step_box(self, sequence_layout):
        self.manual_box = QGroupBox("Manual Single Step")
        manual_layout = QVBoxLayout()

        manual_layout.addWidget(QLabel("Set gas percentages manually for a single step."))

        manual_grid = QGridLayout()
        self.manual_rows = []

        for i in range(1, 5):
            mfc_label = QLabel(f"MFC {i}")
            max_flow_label = QLabel("From MFC Setup")

            percent_input = QLineEdit()
            percent_input.setPlaceholderText("example: 15 for 15% or 500 for 500 ppm")

            manual_grid.addWidget(mfc_label, i, 0)
            manual_grid.addWidget(max_flow_label, i, 1)
            manual_grid.addWidget(percent_input, i, 2)

            self.manual_rows.append([
                mfc_label,
                max_flow_label,
                percent_input
            ])

        manual_layout.addLayout(manual_grid)

        filler_row = QHBoxLayout()
        filler_row.addWidget(QLabel("Filler MFC:"))

        self.filler_selector = QComboBox()
        self.filler_selector.addItems(["MFC 1", "MFC 2", "MFC 3", "MFC 4"])
        self.filler_selector.currentIndexChanged.connect(self.update_filler_display)

        filler_row.addWidget(self.filler_selector)
        manual_layout.addLayout(filler_row)

        self.manual_box.setLayout(manual_layout)
        sequence_layout.addWidget(self.manual_box)

    def build_excel_drop_box(self, sequence_layout):
        self.drop_label = DropLabel("Drag and drop Excel step sequence here", self.load_sequence_file)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("""
            border: 2px dashed gray;
            font-size: 16px;
            padding: 40px;
        """)
        self.drop_label.setAcceptDrops(True)

        sequence_layout.addWidget(self.drop_label)

    def build_runtime_buttons(self, sequence_layout):
        control_row = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.reset_button = QPushButton("Reset")

        self.start_button.clicked.connect(self.start_sequence)
        self.pause_button.clicked.connect(self.pause_sequence)
        self.stop_button.clicked.connect(self.stop_sequence)
        self.reset_button.clicked.connect(self.reset_gui)

        control_row.addWidget(self.start_button)
        control_row.addWidget(self.pause_button)
        control_row.addWidget(self.stop_button)
        control_row.addWidget(self.reset_button)

        sequence_layout.addLayout(control_row)

    def build_connection_panel(self, main_layout):
        connection_box = QGroupBox("MFC Connection")
        connection_layout = QVBoxLayout()

        top_row = QHBoxLayout()

        top_row.addWidget(QLabel("Mode:"))

        self.mock_mode_selector = QComboBox()
        self.mock_mode_selector.addItems(["Mock Mode", "Real Hardware"])
        top_row.addWidget(self.mock_mode_selector)

        top_row.addWidget(QLabel("COM Port:"))

        self.com_port_selector = QComboBox()
        self.com_port_selector.addItems([
            "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9", "COM10",
            "COM11", "COM12", "COM13", "COM14", "COM15",
            "COM16", "COM17", "COM18", "COM19", "COM20",
            "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2", "/dev/ttyUSB3"
        ])
        top_row.addWidget(self.com_port_selector)

        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")

        top_row.addWidget(self.connect_button)
        top_row.addWidget(self.disconnect_button)

        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("font-weight: bold;")
        top_row.addWidget(self.connection_status_label)

        connection_layout.addLayout(top_row)

        status_grid = QGridLayout()
        status_grid.addWidget(QLabel("MFC"), 0, 0)
        status_grid.addWidget(QLabel("Address"), 0, 1)
        status_grid.addWidget(QLabel("Status"), 0, 2)

        self.mfc_connection_status_rows = []

        for i in range(1, 5):
            mfc_label = QLabel(f"MFC {i}")
            address_label = QLabel("N/A")
            status_label = QLabel("Disconnected")

            status_grid.addWidget(mfc_label, i, 0)
            status_grid.addWidget(address_label, i, 1)
            status_grid.addWidget(status_label, i, 2)

            self.mfc_connection_status_rows.append({
                "mfc_label": mfc_label,
                "address_label": address_label,
                "status_label": status_label,
            })

        self.wet_mfc_connection_status_row = self.add_connection_status_row(
            status_grid,
            5,
            "Wet MFC"
        )
        self.dry_mfc_connection_status_row = self.add_connection_status_row(
            status_grid,
            6,
            "Dry MFC"
        )
        self.sht_connection_status_row = self.add_connection_status_row(
            status_grid,
            7,
            "SHT Sensor"
        )

        connection_layout.addLayout(status_grid)

        self.connect_button.clicked.connect(self.connect_mfc_controller)
        self.disconnect_button.clicked.connect(self.disconnect_mfc_controller)

        connection_box.setLayout(connection_layout)
        main_layout.addWidget(connection_box, 2, 0, 1, 2)

    def add_connection_status_row(self, status_grid, row_number, label_text):
        name_label = QLabel(label_text)
        address_label = QLabel("—")
        status_label = QLabel("Disabled")

        status_grid.addWidget(name_label, row_number, 0)
        status_grid.addWidget(address_label, row_number, 1)
        status_grid.addWidget(status_label, row_number, 2)

        return {
            "mfc_label": name_label,
            "address_label": address_label,
            "status_label": status_label,
        }

    def build_runtime_log_panel(self, main_layout):
        log_box = QGroupBox("Runtime Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Runtime log will be displayed here...")

        log_layout.addWidget(self.log_text)
        log_box.setLayout(log_layout)
        main_layout.addWidget(log_box, 3, 0, 1, 2)

    # -------------------------------------------------------------------------
    # UI HELPER WRAPPERS
    # -------------------------------------------------------------------------

    def update_manual_max_flow_labels(self):
        update_manual_max_flow_labels(self)

    def update_visible_mfcs(self):
        update_visible_mfcs(self)

        if hasattr(self, "mfc_connection_status_rows"):
            self.update_mfc_connection_status_display(
                self.mfc_controller.connected
            )

    def update_filler_display(self):
        update_filler_display(self)

    def validate_mfc_setup(self):
        return validate_mfc_setup(self)

    def build_mfc_config(self):
        return build_mfc_config(self)

    def build_manual_targets(self):
        return build_manual_targets(self)

    def update_ppm_view(self):
        self.graph_manager.update_ppm_view()

    def humidity_mode_enabled(self):
        return self.humidity_mode_button.isChecked()

    def toggle_humidity_mode(self):
        self.update_humidity_ui_enabled()
        self.update_mfc_connection_status_display(self.mfc_controller.connected)

        if self.humidity_mode_enabled():
            self.instruction_label.setText("Humidity mode selected.")
        else:
            self.humidity_control_active = False
            self.current_humidity_target_rh = None
            self.stop_humidity_flows()
            self.instruction_label.setText("Humidity mode disabled.")

    def update_humidity_ui_enabled(self):
        enabled = self.humidity_mode_enabled() if hasattr(self, "humidity_mode_button") else False

        if hasattr(self, "humidity_mode_button"):
            self.humidity_mode_button.setText("Humidity Mode On" if enabled else "Humidity Mode Off")

        if hasattr(self, "humidity_config_widgets"):
            for widget in self.humidity_config_widgets:
                widget.setVisible(enabled)
                widget.setEnabled(enabled)

    # -------------------------------------------------------------------------
    # MODE / CONTROL LOGIC
    # -------------------------------------------------------------------------

    def activate_manual_mode(self):
        self.manual_mode_button.setChecked(True)
        self.excel_mode_button.setChecked(False)

        self.manual_box.setVisible(True)
        self.drop_label.setVisible(False)

        # Manual mode is a single setpoint, not a timed sequence.
        # Hide the live sequence graph to reduce operator confusion.
        self.graph_box.setVisible(False)

        self.instruction_label.setText("Manual single-step mode selected.")

    def activate_excel_mode(self):
        self.manual_mode_button.setChecked(False)
        self.excel_mode_button.setChecked(True)

        self.manual_box.setVisible(False)
        self.drop_label.setVisible(True)

        # Excel mode is sequence-based, so show the graph again.
        self.graph_box.setVisible(True)

        self.instruction_label.setText("Excel sequence mode selected.")

    def activate_continuous_flow_mode(self):
        self.continuous_flow_button.setChecked(True)
        self.timed_flow_button.setChecked(False)
        self.adaptive_flow_button.setChecked(False)
        self.instruction_label.setText("Continuous flow mode selected.")

    def activate_timed_flow_mode(self):
        self.continuous_flow_button.setChecked(False)
        self.timed_flow_button.setChecked(True)
        self.adaptive_flow_button.setChecked(False)
        self.instruction_label.setText("Timed flow mode selected.")

    def activate_adaptive_flow_mode(self):
        self.continuous_flow_button.setChecked(False)
        self.timed_flow_button.setChecked(False)
        self.adaptive_flow_button.setChecked(True)
        self.instruction_label.setText("Adaptive humidity flow mode selected.")

    def get_timed_flow_duration_seconds(self):
        duration = float(self.timed_flow_duration_input.text().strip())
        if duration < 0:
            raise ValueError("Timed flow duration cannot be negative.")
        return duration

    def get_adaptive_rh_threshold(self):
        threshold = float(self.adaptive_rh_threshold_input.text().strip())
        if threshold < 0:
            raise ValueError("Adaptive RH threshold cannot be negative.")
        return threshold

    def get_flow_mode_text(self):
        if self.timed_flow_button.isChecked():
            return f"Timed Flow ({self.get_timed_flow_duration_seconds():.0f} sec)"

        if self.adaptive_flow_button.isChecked():
            return f"Adaptive Mode (±{self.get_adaptive_rh_threshold():.1f}% RH)"

        return "Continuous Flow"

    def update_latest_humidity_reading(self):
        try:
            reading = self.sht_controller.read()
            measured_rh = float(reading["rh"])
            self.latest_measured_rh = measured_rh
            self.measured_rh_label.setText(f"{measured_rh:.1f} %")
            return measured_rh
        except Exception:
            self.measured_rh_label.setText("Read Error")
            return None

    def get_adaptive_flow_allowed(self, target_rh):
        if target_rh is None:
            return False

        measured_rh = self.update_latest_humidity_reading()
        if measured_rh is None:
            self.latest_humidity_error_abs = None
            # If the sensor cannot be read, allow flow so the system can fall back
            # to the open-loop humidifier estimate instead of silently doing nothing.
            return True

        error_abs = abs(float(target_rh) - measured_rh)
        self.latest_humidity_error_abs = error_abs
        return error_abs > self.get_adaptive_rh_threshold()

    def should_flow_during_step(self, step):
        if self.continuous_flow_button.isChecked():
            return True

        if self.timed_flow_button.isChecked():
            step_elapsed_time = self.current_time - step["start_time"]
            return step_elapsed_time <= self.get_timed_flow_duration_seconds()

        if self.adaptive_flow_button.isChecked():
            if not self.humidity_mode_enabled():
                return False
            return self.get_adaptive_flow_allowed(step.get("humidity_target_rh"))

        return True

    def start_sequence(self):
        if not self.mfc_controller.connected:
            self.instruction_label.setText("Connect to the MFC controller before starting.")
            self.log_text.append("Cannot start: MFC controller is not connected.")
            return

        if not self.validate_mfc_setup():
            return

        if self.humidity_mode_enabled():
            if self.mock_mode_selector.currentText() != "Real Hardware":
                self.instruction_label.setText(
                    "Humidity mode requires Real Hardware mode on the Raspberry Pi."
                )
                self.log_text.append(
                    "Cannot start: Humidity mode requires Real Hardware mode on the Raspberry Pi."
                )
                return

            if not self.sht_controller.connected:
                self.instruction_label.setText(
                    "Humidity mode unavailable. No SHT sensor detected."
                )
                self.log_text.append(
                    "Cannot start: No SHT sensor detected. Connect in Real Hardware mode with the SHT sensor attached."
                )
                return

        try:
            self.get_flow_mode_text()
            self.validate_humidity_setup()

            if self.adaptive_flow_button.isChecked() and not self.humidity_mode_enabled():
                raise ValueError("Adaptive flow mode requires Humidity Mode to be enabled.")

            if self.manual_mode_button.isChecked():
                self.run_manual_step()
                return

            self.manual_active_result = None

            if self.humidity_mode_enabled():
                if not self.sequence_steps:
                    raise ValueError("No Excel sequence has been loaded.")

                if not any(step.get("humidity_target_rh") is not None for step in self.sequence_steps):
                    raise ValueError("Humidity mode is enabled, but the Excel file does not contain RH_% values.")

            mfc_config = self.build_mfc_config()
            validate_sequence_preflight(self.sequence_steps, mfc_config)

            self.instruction_label.setText("Sequence preflight passed. Sequence started.")
            self.humidity_control_active = self.humidity_mode_enabled()
            self.log_text.append("Sequence preflight passed.")
            self.log_text.append("Sequence started.")
            self.timer.start(1000)

        except Exception as e:
            self.instruction_label.setText("Cannot start.")
            self.log_text.append(f"Preflight error: {e}")


    def update_mfc_connection_status_display(self, connected=False):
        if not hasattr(self, "mfc_connection_status_rows"):
            return

        selected_count = self.mfc_selector.currentIndex() + 1

        for index, row in enumerate(self.mfc_connection_status_rows):
            should_show = index < selected_count

            row["mfc_label"].setVisible(should_show)
            row["address_label"].setVisible(should_show)
            row["status_label"].setVisible(should_show)

            if not should_show:
                continue

            address = self.mfc_config_widgets[index]["address"].currentText()
            row["address_label"].setText(address)

            if address == "N/A":
                row["status_label"].setText("No Address")
            elif connected:
                row["status_label"].setText("Connected")
            else:
                row["status_label"].setText("Disconnected")

        self.update_humidity_connection_status_display(connected)

    def update_humidity_connection_status_display(self, connected=False):
        if not hasattr(self, "wet_mfc_connection_status_row"):
            return

        humidity_enabled = self.humidity_mode_enabled()

        wet_address = self.humidity_wet_address_selector.currentText()
        dry_address = self.humidity_dry_address_selector.currentText()
        sht_address = self.sht_address_selector.currentText()

        self.update_single_humidity_status_row(
            self.wet_mfc_connection_status_row,
            wet_address,
            humidity_enabled,
            connected,
            "No Address" if wet_address == "N/A" else "Disconnected",
        )
        self.update_single_humidity_status_row(
            self.dry_mfc_connection_status_row,
            dry_address,
            humidity_enabled,
            connected,
            "No Address" if dry_address == "N/A" else "Disconnected",
        )

        self.sht_connection_status_row["address_label"].setText(
            sht_address if humidity_enabled else "—"
        )

        if not humidity_enabled:
            self.sht_connection_status_row["status_label"].setText("Disabled")
        elif self.sht_controller.connected:
            self.sht_connection_status_row["status_label"].setText("Connected")
        elif connected:
            self.sht_connection_status_row["status_label"].setText("Not Found")
        else:
            self.sht_connection_status_row["status_label"].setText("Disconnected")

    def update_single_humidity_status_row(
        self,
        row,
        address_text,
        humidity_enabled,
        connected,
        disconnected_text,
    ):
        row["address_label"].setText(address_text if humidity_enabled else "—")

        if not humidity_enabled:
            row["status_label"].setText("Disabled")
        elif address_text == "N/A":
            row["status_label"].setText("No Address")
        elif connected:
            row["status_label"].setText("Connected")
        else:
            row["status_label"].setText(disconnected_text)

    def connect_mfc_controller(self):
        try:
            mock_mode = self.mock_mode_selector.currentText() == "Mock Mode"
            port_text = self.com_port_selector.currentText()

            addresses = []
            selected_count = self.mfc_selector.currentIndex() + 1

            for i in range(selected_count):
                address_text = self.mfc_config_widgets[i]["address"].currentText()

                if address_text != "N/A":
                    addresses.append(int(address_text))

            if self.humidity_mode_enabled():
                self.validate_humidity_setup()
                wet_address, dry_address = self.get_humidity_addresses()
                addresses.extend([wet_address, dry_address])

            addresses = sorted(set(addresses))

            self.mfc_controller.mock_mode = mock_mode
            self.mfc_controller.connect(
                port=port_text,
                addresses=addresses
            )

            if self.humidity_mode_enabled():
                self.sht_controller.mock_mode = mock_mode
                self.sht_controller.connect(self.sht_address_selector.currentText())

            mode_text = "Mock" if mock_mode else "Real Hardware"

            self.connection_status_label.setText(f"Connected ({mode_text}, {port_text})")
            self.update_mfc_connection_status_display(True)
            self.instruction_label.setText("MFC controller connected.")
            self.log_text.append(f"MFC controller connected in {mode_text} mode on {port_text}.")

        except Exception as e:
            self.connection_status_label.setText("Connection Failed")
            self.update_mfc_connection_status_display(False)
            self.instruction_label.setText("MFC controller connection failed.")
            self.log_text.append(f"Connection error: {e}")

    def disconnect_mfc_controller(self):
        try:
            self.humidity_control_active = False
            self.current_humidity_target_rh = None
            self.mfc_controller.disconnect()
            self.sht_controller.disconnect()

            self.connection_status_label.setText("Disconnected")
            self.update_mfc_connection_status_display(False)
            self.instruction_label.setText("MFC controller disconnected.")
            self.log_text.append("MFC controller disconnected.")

        except Exception as e:
            self.connection_status_label.setText("Disconnect Failed")
            self.update_mfc_connection_status_display(False)
            self.log_text.append(f"Disconnect error: {e}")

    def pause_sequence(self):
        self.instruction_label.setText("Sequence paused.")
        self.log_text.append("Sequence paused.")
        self.timer.stop()

    def stop_sequence(self):
        self.instruction_label.setText("Sequence stopped. All Flows set to 0.000 L/min")
        self.log_text.append("Sequence stopped. All Flows set to 0.000 L/min")

        self.humidity_control_active = False
        self.current_humidity_target_rh = None
        self.mfc_controller.stop_all()
        self.timer.stop()
        self.current_time = 0
        self.current_step_number = None
        self.manual_active_result = None
        self.current_normal_total_flow_lpm = 0.0
        self.graph_manager.set_current_time_seconds(0)
        self.humidity_flow_label.setText("Wet: 0.000 L/min | Dry: 0.000 L/min")
        reset_mfc_flow_labels(self)

    def reset_gui(self):
        self.timer.stop()
        self.current_time = 0
        self.current_step_number = None
        self.current_humidity_target_rh = None
        self.current_wet_fraction = 0.5
        self.humidity_control_active = False
        self.current_normal_total_flow_lpm = 0.0
        self.time_data = [0]
        self.sequence_steps = []

        self.graph_manager.reset()

        self.mfc_selector.setCurrentIndex(0)
        self.update_visible_mfcs()

        for mfc in self.mfc_config_widgets:
            mfc["gas"].setCurrentIndex(0)
            mfc["max_flow_rate"].setCurrentIndex(0)
            mfc["address"].setCurrentIndex(0)
            mfc["current_flow"].setText("0.000 L/min")

        self.drop_label.setText("Drag and drop Excel step sequence here")
        self.humidity_mode_button.setChecked(False)
        self.update_humidity_ui_enabled()
        self.manual_humidity_target_input.setText("50")
        self.humidity_flow_offset_input.setText("0.0")
        self.humidifier_output_rh_input.setText("100")
        self.humidity_kp_input.setText("0.01")
        self.measured_rh_label.setText("-- %")
        self.humidity_flow_label.setText("Wet: -- L/min | Dry: -- L/min")
        self.instruction_label.setText("Choose the number of MFCs and assign gases")
        self.log_text.clear()

        self.update_manual_max_flow_labels()
        self.update_filler_display()
        self.timed_flow_duration_input.setText("90")
        self.adaptive_rh_threshold_input.setText("2.5")
        self.activate_continuous_flow_mode()
        self.activate_excel_mode()

    # -------------------------------------------------------------------------
    # SEQUENCE / FLOW LOGIC
    # -------------------------------------------------------------------------

    def update_graph(self):
        self.current_time += 1

        sequence_end_time = self.time_data[-1]

        if self.current_time > sequence_end_time:
            self.timer.stop()
            self.mfc_controller.stop_all()
            self.humidity_control_active = False
            self.current_step_number = None
            self.current_humidity_target_rh = None
            self.manual_active_result = None
            self.current_normal_total_flow_lpm = 0.0
            self.current_time = sequence_end_time
            self.instruction_label.setText("Sequence complete. All flows set to 0.000 L/min")
            self.log_text.append("Sequence complete. All flows set to 0.000 L/min")
            return

        self.graph_manager.set_current_time_seconds(self.current_time)

        try:
            self.update_flows_for_current_step()
        except Exception as e:
            self.timer.stop()
            self.instruction_label.setText("Sequence stopped due to flow calculation error.")
            self.log_text.append(f"Flow calculation error: {e}")

    def load_sequence_file(self, file_path):
        try:
            sequence = load_sequence_from_excel(file_path)

            if sequence["added_balance_n2"]:
                self.log_text.append("Added calculated N2_% balance gas.")

            detected_gas_count = sequence["detected_gas_count"]
            self.mfc_selector.setCurrentIndex(detected_gas_count - 1)
            self.update_visible_mfcs()

            self.graph_manager.plot_sequence(
                sequence["gas_data"],
                sequence["percent_columns"],
                sequence["ppm_columns"]
            )

            self.sequence_steps = sequence["sequence_steps"]
            self.time_data = [0, sequence["total_duration_seconds"]]
            self.current_time = 0

            self.instruction_label.setText("Excel sequence loaded successfully.")
            self.log_text.append(f"Loaded sequence file: {file_path}")
            self.log_text.append("")
            self.log_text.append("Sequence Summary:")
            self.log_text.append(f"Percent gases detected: {sequence['percent_columns']}")
            self.log_text.append(f"PPM gases detected: {sequence['ppm_columns']}")
            if sequence.get("has_humidity_column"):
                self.log_text.append("Humidity targets detected: RH_%")
            elif self.humidity_mode_enabled():
                self.log_text.append("Humidity mode is on, but no RH_% column was found.")
            self.log_text.append(f"Steps loaded: {sequence['row_count']}")
            self.log_text.append(
                f"Total duration: {sequence['total_duration_seconds'] / 60:.2f} minutes"
            )

        except Exception as e:
            self.instruction_label.setText("Error loading Excel file.")
            self.log_text.append(f"Error loading file: {e}")

    def update_flows_for_current_step(self):
        if not self.sequence_steps:
            return

        for step in self.sequence_steps:
            if step["start_time"] <= self.current_time <= step["end_time"]:
                targets = build_targets_from_step(step)
                result = calculate_mfc_flows(targets, self.build_mfc_config())
                self.current_normal_total_flow_lpm = result["total_flow_lpm"]

                step_changed = self.current_step_number != step["step"]
                self.current_humidity_target_rh = step.get("humidity_target_rh")

                if step_changed and self.humidity_mode_enabled() and self.current_humidity_target_rh is not None:
                    self.initialize_humidity_wet_fraction(self.current_humidity_target_rh)

                flow_allowed = self.should_flow_during_step(step)
                self.humidity_control_active = self.humidity_mode_enabled() and flow_allowed

                if flow_allowed:
                    self.send_flows_to_controller(result)
                    if self.humidity_mode_enabled() and self.current_humidity_target_rh is not None:
                        self.update_humidity_feedback_loop()
                else:
                    self.mfc_controller.stop_all()
                    if self.humidity_mode_enabled():
                        self.humidity_flow_label.setText("Wet: 0.000 L/min | Dry: 0.000 L/min")

                if step_changed:
                    self.current_step_number = step["step"]

                    self.log_text.append("")
                    self.log_text.append(f"Entering Step {step['step']}")

                    self.log_text.append("Target Concentrations:")

                    for gas_column, value in step["gases"].items():

                        if gas_column.endswith("_%"):
                            gas_name = gas_column.replace("_%", "")
                            self.log_text.append(
                                f"{gas_name}: {value:.2f}%"
                            )

                        elif gas_column.endswith("_ppm"):
                            gas_name = gas_column.replace("_ppm", "")
                            self.log_text.append(
                                f"{gas_name}: {value:.0f} ppm"
                            )

                    self.log_text.append(
                        f"Flow Mode: {self.get_flow_mode_text()}"
                    )

                    if self.humidity_mode_enabled():
                        if self.current_humidity_target_rh is None:
                            self.log_text.append("Humidity Target: missing RH_% value")
                        else:
                            self.log_text.append(f"Humidity Target: {self.current_humidity_target_rh:.1f}% RH")
                            if self.adaptive_flow_button.isChecked() and self.latest_humidity_error_abs is not None:
                                self.log_text.append(f"Adaptive RH Error: {self.latest_humidity_error_abs:.1f}%")

                    for mfc_number, info in result["flows"].items():
                        displayed_flow = info["flow_lpm"] if flow_allowed else 0.0
                        self.log_text.append(
                            f"MFC {mfc_number} ({info['gas']}): "
                            f"{displayed_flow:.3f} L/min"
                        )

                step_time_remaining = step["end_time"] - self.current_time
                minutes = int(step_time_remaining // 60)
                seconds = int(step_time_remaining % 60)

                flow_mode_text = self.get_flow_mode_text()
                flow_state_text = "Flowing" if flow_allowed else "Flow Off"

                status_text = (
                    f"Running Step {step['step']}/{len(self.sequence_steps)}\n\n"
                    f"Time Left In Step: {minutes:02d}:{seconds:02d}\n"
                    f"Flow Mode: {flow_mode_text}\n"
                    f"Flow State: {flow_state_text}\n\n"
                    f"Total Flow: {result['total_flow_lpm']:.3f} L/min\n\n"
                )

                status_text += "Target Concentrations:\n"

                for gas_column, value in step["gases"].items():

                    if gas_column.endswith("_%"):
                        gas_name = gas_column.replace("_%", "")
                        status_text += f"{gas_name}: {value:.2f}%\n"

                    elif gas_column.endswith("_ppm"):
                        gas_name = gas_column.replace("_ppm", "")
                        status_text += f"{gas_name}: {value:.0f} ppm\n"

                if self.humidity_mode_enabled():
                    if self.current_humidity_target_rh is None:
                        status_text += "Humidity Target: missing RH_% value\n"
                    else:
                        status_text += f"Humidity Target: {self.current_humidity_target_rh:.1f}% RH\n"

                status_text += "\n"

                self.update_actual_flow_display()

                self.instruction_label.setText(status_text)
                return

    def run_manual_step(self):
        mfc_config = self.build_mfc_config()
        targets = self.build_manual_targets()

        result = calculate_mfc_flows(targets, mfc_config)
        self.manual_active_result = result
        self.current_normal_total_flow_lpm = result["total_flow_lpm"]

        manual_flow_allowed = True
        if self.humidity_mode_enabled():
            self.current_humidity_target_rh = self.get_manual_humidity_target()
            self.initialize_humidity_wet_fraction(self.current_humidity_target_rh)
            if self.adaptive_flow_button.isChecked():
                manual_flow_allowed = self.get_adaptive_flow_allowed(self.current_humidity_target_rh)

        self.humidity_control_active = self.humidity_mode_enabled() and manual_flow_allowed

        if manual_flow_allowed:
            self.send_flows_to_controller(result)
            if self.humidity_mode_enabled():
                self.update_humidity_feedback_loop()
        else:
            self.mfc_controller.stop_all()
            if self.humidity_mode_enabled():
                self.humidity_flow_label.setText("Wet: 0.000 L/min | Dry: 0.000 L/min")

        self.log_text.append("")
        self.log_text.append("Manual single-step calculation:")
        self.log_text.append(f"Total flow: {result['total_flow_lpm']:.3f} L/min")
        self.log_text.append("Target Concentrations:")

        concentration_text = self.format_resulting_concentrations(result)

        for line in concentration_text.splitlines():
            self.log_text.append(line)

        self.log_text.append("MFC Flow Rates:")

        for mfc_number, info in result["flows"].items():
            flow = info["flow_lpm"]
            gas = info["gas"]

            self.log_text.append(
                f"MFC {mfc_number} ({gas}): {flow:.3f} L/min"
            )

        self.update_actual_flow_display()

        manual_flow_state = "Flowing" if manual_flow_allowed else "Flow Off"

        status_text = (
            "Manual Single Step Active\n\n"
            f"Flow Mode: {self.get_flow_mode_text()}\n"
            f"Flow State: {manual_flow_state}\n"
            f"Total Flow: {result['total_flow_lpm']:.3f} L/min\n\n"
            "Target Concentrations:\n"
            f"{concentration_text}\n\n"
        )

        if self.humidity_mode_enabled():
            status_text += f"Humidity Target: {self.current_humidity_target_rh:.1f}% RH\n\n"

        status_text += "MFC Flow Rates:\n"

        for mfc_number, info in result["flows"].items():
            status_text += (
                f"MFC {mfc_number} ({info['gas']}): "
                f"{info['flow_lpm']:.3f} L/min\n"
            )

        self.instruction_label.setText(status_text)


    # -------------------------------------------------------------------------
    # HUMIDITY CONTROL LOGIC
    # -------------------------------------------------------------------------

    def stop_humidity_flows(self):
        if not self.mfc_controller.connected:
            self.humidity_flow_label.setText("Wet: 0.000 L/min | Dry: 0.000 L/min")
            return

        try:
            wet_address, dry_address = self.get_humidity_addresses()
            self.mfc_controller.set_flow(wet_address, 0.0)
            self.mfc_controller.set_flow(dry_address, 0.0)
        except Exception:
            pass

        self.humidity_flow_label.setText("Wet: 0.000 L/min | Dry: 0.000 L/min")

    def get_humidity_addresses(self):
        wet_text = self.humidity_wet_address_selector.currentText()
        dry_text = self.humidity_dry_address_selector.currentText()

        if wet_text == "N/A" or dry_text == "N/A":
            raise ValueError("Humidity mode requires both wet and dry MFC addresses.")

        wet_address = int(wet_text)
        dry_address = int(dry_text)

        if wet_address == dry_address:
            raise ValueError("Wet and dry humidity MFC addresses cannot match.")

        return wet_address, dry_address

    def get_normal_mfc_addresses(self):
        selected_count = self.mfc_selector.currentIndex() + 1
        addresses = []

        for i in range(selected_count):
            address_text = self.mfc_config_widgets[i]["address"].currentText()
            if address_text != "N/A":
                addresses.append(int(address_text))

        return addresses

    def get_humidity_flow_offset(self):
        return float(self.humidity_flow_offset_input.text().strip())

    def get_humidity_total_flow(self):
        total_flow = self.current_normal_total_flow_lpm + self.get_humidity_flow_offset()

        if total_flow < 0:
            raise ValueError(
                "Humidity total flow cannot be negative. "
                "Increase the humidity flow offset or normal MFC total flow."
            )

        return total_flow

    def get_manual_humidity_target(self):
        value_text = self.manual_humidity_target_input.text().strip()
        if value_text == "":
            raise ValueError("Manual humidity target RH is required when humidity mode is on.")

        target_rh = float(value_text)
        if target_rh < 0 or target_rh > 100:
            raise ValueError("Manual humidity target must be between 0 and 100% RH.")

        return target_rh

    def validate_humidity_setup(self):
        if not self.humidity_mode_enabled():
            return True

        wet_address, dry_address = self.get_humidity_addresses()
        normal_addresses = self.get_normal_mfc_addresses()

        if wet_address in normal_addresses:
            raise ValueError("Wet humidity MFC address duplicates a normal gas MFC address.")

        if dry_address in normal_addresses:
            raise ValueError("Dry humidity MFC address duplicates a normal gas MFC address.")

        self.get_humidity_flow_offset()

        if self.humidity_control_active or self.current_normal_total_flow_lpm > 0:
            total_flow = self.get_humidity_total_flow()
            if total_flow <= 0:
                raise ValueError(
                    "Humidity total flow must be greater than 0 when humidity control is active."
                )

        humidifier_output_rh = float(self.humidifier_output_rh_input.text().strip())
        if humidifier_output_rh <= 0 or humidifier_output_rh > 100:
            raise ValueError("Humidifier output RH must be greater than 0 and no more than 100%.")

        kp = float(self.humidity_kp_input.text().strip())
        if kp < 0:
            raise ValueError("Humidity feedback Kp cannot be negative.")

        if self.manual_mode_button.isChecked():
            self.get_manual_humidity_target()

        return True

    def get_active_humidity_target(self):
        if not self.humidity_mode_enabled():
            return None

        if self.manual_mode_button.isChecked():
            return self.get_manual_humidity_target()

        return self.current_humidity_target_rh

    def initialize_humidity_wet_fraction(self, target_rh):
        try:
            open_loop = calculate_open_loop_humidity_flows(
                target_rh,
                float(self.humidifier_output_rh_input.text().strip()),
                self.get_humidity_total_flow(),
            )
            self.current_wet_fraction = open_loop["wet_fraction"]
        except Exception:
            pass

    def update_humidity_feedback_loop(self):
        if not self.humidity_mode_enabled():
            return

        if not self.mfc_controller.connected:
            return

        try:
            self.validate_humidity_setup()

            target_rh = self.get_active_humidity_target()
            if target_rh is None:
                self.humidity_flow_label.setText("Wet: -- L/min | Dry: -- L/min")
                return

            if self.adaptive_flow_button.isChecked():
                flow_allowed = self.get_adaptive_flow_allowed(target_rh)
                self.humidity_control_active = flow_allowed

                if not flow_allowed:
                    self.mfc_controller.stop_all()
                    self.humidity_flow_label.setText("Wet: 0.000 L/min | Dry: 0.000 L/min")
                    return

                if self.manual_mode_button.isChecked() and self.manual_active_result is not None:
                    self.send_flows_to_controller(self.manual_active_result)

            elif not self.humidity_control_active:
                return

            total_flow = self.get_humidity_total_flow()
            humidifier_output_rh = float(self.humidifier_output_rh_input.text().strip())
            kp = float(self.humidity_kp_input.text().strip())
            wet_address, dry_address = self.get_humidity_addresses()

            try:
                reading = self.sht_controller.read()
            except Exception:
                # If feedback is unavailable, start with an open-loop estimate.
                open_loop = calculate_open_loop_humidity_flows(
                    target_rh,
                    humidifier_output_rh,
                    total_flow,
                )
                self.current_wet_fraction = open_loop["wet_fraction"]
                wet_flow = open_loop["wet_flow_lpm"]
                dry_flow = open_loop["dry_flow_lpm"]
                self.measured_rh_label.setText("Read Error")
            else:
                measured_rh = float(reading["rh"])
                self.latest_measured_rh = measured_rh
                if target_rh is not None:
                    self.latest_humidity_error_abs = abs(float(target_rh) - measured_rh)
                feedback = calculate_feedback_humidity_flows(
                    target_rh=target_rh,
                    measured_rh=measured_rh,
                    total_flow_lpm=total_flow,
                    current_wet_fraction=self.current_wet_fraction,
                    kp=kp,
                )
                self.current_wet_fraction = feedback["wet_fraction"]
                wet_flow = feedback["wet_flow_lpm"]
                dry_flow = feedback["dry_flow_lpm"]
                self.measured_rh_label.setText(f"{measured_rh:.1f} %")

            self.mfc_controller.set_flow(wet_address, wet_flow)
            self.mfc_controller.set_flow(dry_address, dry_flow)
            self.humidity_flow_label.setText(
                f"Wet: {wet_flow:.3f} L/min | Dry: {dry_flow:.3f} L/min"
            )

        except Exception as e:
            self.humidity_flow_label.setText("Humidity Error")
            self.log_text.append(f"Humidity control error: {e}")

    def format_resulting_concentrations(self, result):
        lines = []

        for gas, fraction in result["fractions"].items():
            if gas == "CH4/N2 Mix":
                # The source gas is 1000 ppm CH4 in N2, so the final
                # CH4 concentration is source fraction * 1000 ppm.
                ch4_ppm = fraction * 1000
                lines.append(f"CH4: {ch4_ppm:.0f} ppm")
            else:
                lines.append(f"{gas}: {fraction * 100:.2f}%")

        return "\n".join(lines)

    def send_flows_to_controller(self, result):
        for mfc_number, info in result["flows"].items():
            mfc = self.mfc_config_widgets[mfc_number - 1]

            address_text = mfc["address"].currentText()

            if address_text == "N/A":
                raise ValueError(f"MFC {mfc_number} does not have a valid address.")

            address = int(address_text)
            flow = info["flow_lpm"]

            self.mfc_controller.set_flow(address, flow)

    def update_actual_flow_display(self):

        if not self.mfc_controller.connected:
            return

        selected_count = self.mfc_selector.currentIndex() + 1

        for i in range(selected_count):

            mfc = self.mfc_config_widgets[i]

            address_text = mfc["address"].currentText()

            if address_text == "N/A":
                mfc["current_flow"].setText("N/A")
                continue

            try:
                measured_flow = self.mfc_controller.read_flow(int(address_text))
                mfc["current_flow"].setText(
                    f"{measured_flow:.3f} L/min"
                )

            except Exception:
                mfc["current_flow"].setText("Read Error")


def run_gui():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
