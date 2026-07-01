from PySide6.QtWidgets import QLabel


class DropLabel(QLabel):
    def __init__(self, text, file_dropped_callback=None):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.file_dropped_callback = file_dropped_callback

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        file_path = urls[0].toLocalFile()

        if file_path.endswith(".xlsx"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return

        file_path = urls[0].toLocalFile()
        self.setText(f"Loaded file:\n{file_path}")

        if self.file_dropped_callback:
            self.file_dropped_callback(file_path)
