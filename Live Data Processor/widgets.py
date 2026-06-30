from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout


def format_value(value: Optional[float], decimals: int = 3, suffix: str = "") -> str:
    if value is None:
        return "--"
    return f"{value:.{decimals}f}{suffix}"


class SensorReadoutCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(190)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.line1 = QLabel("--")
        self.line2 = QLabel("--")
        self.line3 = QLabel("")

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.line1)
        layout.addWidget(self.line2)
        layout.addWidget(self.line3)
        self.setLayout(layout)

    def set_lines(self, line1: str, line2: str = "", line3: str = "") -> None:
        self.line1.setText(line1)
        self.line2.setText(line2)
        self.line3.setText(line3)
