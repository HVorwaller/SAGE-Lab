from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime

import matplotlib.dates as mdates
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


PLOT_OPTIONS = {
    "zab1_current_mA": ("ZAB 1 Current", "Current (mA)"),
    "zab2_current_mA": ("ZAB 2 Current", "Current (mA)"),
    "zab3_current_mA": ("ZAB 3 Current", "Current (mA)"),

    "zab1_o2_percent": ("ZAB 1 Calculated O2", "ZAB O2 (%)"),
    "zab2_o2_percent": ("ZAB 2 Calculated O2", "ZAB O2 (%)"),
    "zab3_o2_percent": ("ZAB 3 Calculated O2", "ZAB O2 (%)"),

    "apogee_o2_percent": ("Apogee O2", "Apogee O2 (%)"),

    "sht1_temp_C": ("SHT 1 Temp", "Temperature (°C)"),
    "sht2_temp_C": ("SHT 2 Temp", "Temperature (°C)"),

    "sht1_humidity_percent": ("SHT 1 Humidity", "Humidity (%RH)"),
    "sht2_humidity_percent": ("SHT 2 Humidity", "Humidity (%RH)"),
}


PLOT_STYLES = {
    "zab1_current_mA": {"color": "tab:blue", "linestyle": "-"},
    "zab2_current_mA": {"color": "tab:orange", "linestyle": "-"},
    "zab3_current_mA": {"color": "tab:green", "linestyle": "-"},

    "zab1_o2_percent": {"color": "tab:red", "linestyle": "-"},
    "zab2_o2_percent": {"color": "tab:purple", "linestyle": "-"},
    "zab3_o2_percent": {"color": "tab:brown", "linestyle": "-"},

    "apogee_o2_percent": {"color": "black", "linestyle": ":"},

    "sht1_temp_C": {"color": "tab:pink", "linestyle": "-"},
    "sht2_temp_C": {"color": "tab:gray", "linestyle": "-"},

    "sht1_humidity_percent": {"color": "tab:olive", "linestyle": "-"},
    "sht2_humidity_percent": {"color": "tab:cyan", "linestyle": "-"},
}


class GraphManager:
    def __init__(self) -> None:
        self.figure = Figure(figsize=(8, 5), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, None)

        self.axes_by_unit = {}
        self._drag_start = None

        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_drag)
        self.canvas.mpl_connect("scroll_event", self.on_scroll_zoom)

    def parse_timestamp(self, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                try:
                    return datetime.strptime(value, "%H:%M:%S")
                except ValueError:
                    return None

        return None

    def get_x_value(self, row: Dict[str, Any], x_mode: str):
        if x_mode == "Time":
            return self.parse_timestamp(row.get("timestamp"))
        return row.get("apogee_o2_percent")

    def update_graph(self, history: List[Dict[str, Any]], x_mode: str, selected_keys: List[str]) -> None:
        self.figure.clear()
        self.axes_by_unit = {}

        ax_main = self.figure.add_subplot(111)

        if not history:
            ax_main.set_title("No data yet")
            ax_main.set_xlabel("Timestamp" if x_mode == "Time" else "Apogee O2 (%)")
            self.canvas.draw()
            return

        x_label = "Timestamp" if x_mode == "Time" else "Apogee O2 (%)"

        if x_mode != "Time":
            selected_keys = [key for key in selected_keys if key != "apogee_o2_percent"]

        selected_keys = [key for key in selected_keys if key in PLOT_OPTIONS]

        if not selected_keys:
            ax_main.set_title("Select at least one sensor value to graph")
            ax_main.set_xlabel(x_label)
            self.canvas.draw()
            return

        offset_count = 0

        for key in selected_keys:
            label, unit = PLOT_OPTIONS[key]

            if unit not in self.axes_by_unit:
                if not self.axes_by_unit:
                    axis = ax_main
                    axis.set_ylabel(unit)
                else:
                    axis = ax_main.twinx()
                    axis.spines["right"].set_position(("axes", 1.0 + 0.12 * offset_count))
                    axis.set_ylabel(unit)
                    offset_count += 1

                self.axes_by_unit[unit] = axis

            axis = self.axes_by_unit[unit]

            x_values = []
            y_values = []
            for row in history:
                x = self.get_x_value(row, x_mode)
                y = row.get(key)
                if x is None or y is None:
                    continue
                x_values.append(x)
                y_values.append(y)

            if x_values and y_values:
                style = PLOT_STYLES.get(key, {})
                axis.plot(
                    x_values,
                    y_values,
                    label=label,
                    color=style.get("color"),
                    linestyle=style.get("linestyle", "-"),
                    linewidth=2.0 if key == "apogee_o2_percent" else 1.5,
                )

        ax_main.set_xlabel(x_label)
        ax_main.set_title("Live Sensor Graph")

        if x_mode == "Time":
            ax_main.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            ax_main.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.figure.autofmt_xdate()

        handles = []
        labels = []
        for axis in self.axes_by_unit.values():
            h, l = axis.get_legend_handles_labels()
            handles.extend(h)
            labels.extend(l)

        if handles:
            ax_main.legend(handles, labels, loc="best")

        ax_main.grid(True)
        self.canvas.draw()

    def on_mouse_press(self, event) -> None:
        if event.button != 1 or event.inaxes is None:
            return

        if getattr(self.toolbar, "mode", ""):
            return

        x_limits = {axis: axis.get_xlim() for axis in self.figure.axes}

        self._drag_start = {
            "mouse_x_px": event.x,
            "x_limits": x_limits,
        }

    def on_mouse_release(self, event) -> None:
        self._drag_start = None

    def on_mouse_drag(self, event) -> None:
        if self._drag_start is None:
            return
        if event.inaxes is None:
            return

        for axis, xlim in self._drag_start["x_limits"].items():
            x0_px = axis.transData.transform((xlim[0], 0))[0]
            x1_px = axis.transData.transform((xlim[1], 0))[0]
            px_per_data = (x1_px - x0_px) / (xlim[1] - xlim[0])

            if px_per_data == 0:
                continue

            mouse_dx_px = event.x - self._drag_start["mouse_x_px"]
            data_dx = mouse_dx_px / px_per_data

            axis.set_xlim(xlim[0] - data_dx, xlim[1] - data_dx)

        self.canvas.draw_idle()

    def on_scroll_zoom(self, event) -> None:
        if event.inaxes is None:
            return

        if getattr(self.toolbar, "mode", ""):
            return

        for axis in self.figure.axes:
            x_min, x_max = axis.get_xlim()

            x_center = axis.transData.inverted().transform((event.x, event.y))[0]

            if event.button == "up":
                scale = 0.8
            elif event.button == "down":
                scale = 1.25
            else:
                return

            new_left = x_center - (x_center - x_min) * scale
            new_right = x_center + (x_max - x_center) * scale

            axis.set_xlim(new_left, new_right)

        self.canvas.draw_idle()
