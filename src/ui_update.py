import logging

from PySide6.QtCore import Signal, QThread, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from update_manager import fetch_hotkeys

# Get a logger for this module
logger = logging.getLogger(__name__)

class DbUpdateWorker(QThread):
    """
    Worker thread to manage the database update process.
    """
    # Signals
    finished = Signal()
    error = Signal(str)

    def __init__(self):
        """
        Initialize the DbUpdateWorker.
        """
        super().__init__()
        self.success = False

    def run(self):
        """
        Run the update process in a separate thread.
        """
        # Attempt to fetch the hotkeys from the server
        try:
            self.success = fetch_hotkeys()
            if not self.success:
                self.finished.emit()
            else:
                self.finished.emit()

        except Exception as e:
            if not self.success:
                self.error.emit(str(e))

    def stop(self):
        """
        Stop the update process.
        """
        self.success = True
        self.wait()

class LoadingWindow(QWidget):
    """
    Loading window that provides feedback during the database update process.
    """
    # Signals
    update_completed_signal = Signal()

    def __init__(self):
        """
        Initialize the LoadingWindow with a text label and cancel button.
        """
        # Initialize the QWidget
        super().__init__()
        self.setWindowTitle("Loading")
        self.resize(400, 150)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.status = None

        # Update text label
        self.text_label = QLabel("Updating database, please wait...")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.text_label)

        # Setup the worker thread
        self.worker = DbUpdateWorker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        # Set up worker and connect signals
        self.setup_worker_connections()

    def setup_worker_connections(self):
        """
        Set up the worker connections for handling completion and errors.
        """
        self.worker.finished.connect(self.update_finished)
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)

    def start_update(self):
        """
        Start the worker thread to begin the update process.
        """
        self.show()
        self.thread.start()
        
    def update_finished(self):
        """
        Handle actions to take once the update process is finished.
        """
        # Update the text label based on the success of the update
        if self.worker.success:
            self.text_label.setText("Update completed successfully!")
        else:
            self.text_label.setText("Update failed. Please try again later.")
            
        # Emit the signal to indicate the update is completed
        self.thread.quit()
        self.thread.wait()
        self.update_completed_signal.emit()
        self.cleanup()

    def cleanup(self):
        """
        Clean up worker signals and resources.
        """
        # Disconnect signals and delete the worker
        for signal in [self.worker.finished, self.worker.error]:
            signal.disconnect()
        self.worker.deleteLater()
        self.worker = None

    def handle_error(self, error_message):
        """
        Handle errors that occur during the update process.

        Parameters:
        error_message (str): Error message to be logged.
        """
        logger.error(f"Error during update: {error_message}")
        self.close()