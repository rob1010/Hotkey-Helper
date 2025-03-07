import sentry_sdk
import os
import sys
import logging

from PySide6.QtWidgets import QApplication, QDialog, QTextEdit, QPushButton, QVBoxLayout, QLabel

logger = logging.getLogger(__name__)

# Global flag to track if the dialog has been shown
_dialog_shown = False

class BugReportDialog(QDialog):
    def __init__(self, parent=None, error_message=""):
        super().__init__(parent)
        self.setWindowTitle("Report a Bug")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"An error occurred: {error_message}"))
        self.description = QTextEdit()
        self.description.setPlaceholderText("Describe what you were doing when this happened...")
        layout.addWidget(self.description)
        send_button = QPushButton("Send Report")
        send_button.clicked.connect(self.send_report)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.accept)
        layout.addWidget(send_button)
        layout.addWidget(cancel_button)
        self.setLayout(layout)

    def send_report(self):
        desc = self.description.toPlainText()
        log_path = os.path.join(os.path.dirname(__file__), "data/application.log")
        try:
            with open(log_path, 'r') as log_file:
                log_content = ''.join(log_file.readlines()[-1000:])  # Last 1000 lines
        except FileNotFoundError:
            log_content = "Log file not found."

        # Send additional context to Sentry
        sentry_sdk.capture_message(
            f"User-reported crash: {desc}",
            level="error",
            extra={"log_content": log_content}
        )
        sentry_sdk.flush()  # Ensure the report is sent before exiting
        logger.info("Bug report sent to Sentry")
        
        # Close the dialog
        self.accept()

def exception_hook(exctype, value, traceback):
    global _dialog_shown
    
    # If the dialog is already shown, log the additional exception and exit
    if _dialog_shown:
        logger.error(
            f"Additional unhandled exception while dialog is shown: {exctype}, {value}",
            exc_info=(exctype, value, traceback)
        )
        sentry_sdk.capture_exception((exctype, value, traceback))
        sentry_sdk.flush()  # Ensure all reports are sent
        sys.exit(1)  # Exit the application cleanly
    
    # Mark the dialog as shown
    _dialog_shown = True
    
    # Log the initial exception
    logger.error(
        f"Unhandled exception: {exctype}, {value}",
        exc_info=(exctype, value, traceback)
    )
    
    # Send the exception to Sentry
    sentry_sdk.capture_exception((exctype, value, traceback))
    sentry_sdk.flush()  # Ensure the exception is sent immediately
    
    # Initialize QApplication if not already running
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Show the dialog and handle potential errors
    try:
        dialog = BugReportDialog(error_message=str(value))
        dialog.exec()  # Run the dialog's event loop
    except Exception as e:
        logger.error(f"Error in BugReportDialog: {e}", exc_info=True)
        sentry_sdk.capture_exception(e)
        sentry_sdk.flush()  # Send any dialog-related errors
    
    # After the dialog closes (or fails), exit the application
    sys.exit(1)