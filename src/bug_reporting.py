from PySide6.QtWidgets import QDialog, QTextEdit, QPushButton, QVBoxLayout
import sentry_sdk
import os
import logging

logger = logging.getLogger(__name__)
"""
class BugReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report a Bug")
        layout = QVBoxLayout()

        self.description = QTextEdit()
        self.description.setPlaceholderText("Describe the bug here...")
        layout.addWidget(self.description)

        send_button = QPushButton("Send Report")
        send_button.clicked.connect(self.send_report)
        layout.addWidget(send_button)

        self.setLayout(layout)

    def send_report(self):
        desc = self.description.toPlainText()
        log_path = os.path.join(os.path.dirname(__file__), "data/application.log")
        try:
            with open(log_path, 'r') as log_file:
                log_content = log_file.read()
        except FileNotFoundError:
            log_content = "Log file not found."

        sentry_sdk.capture_message(
            desc,
            level="info",
            extra={"log_content": log_content}
        )
        logger.info("Bug report sent to Sentry")
        self.accept()
"""