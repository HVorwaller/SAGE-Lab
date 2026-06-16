import sys
from PySide6.QtWidgets import QApplication
from gui import SensorDashboard


def main() -> None:
    app = QApplication(sys.argv)
    window = SensorDashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
