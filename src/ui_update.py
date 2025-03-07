import logging
from PySide6.QtCore import Signal, QThread, Qt, QCoreApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QProgressBar
from update_manager import download_all_collections

# Get a logger for this module
logger = logging.getLogger(__name__)

class DbUpdateWorker(QThread):
    """
    Worker thread to manage the database update process.

    This thread handles downloading and updating the database while providing feedback on progress,
    and allowing cancellation if necessary.
    """
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, callback=None):
        """
        Initialize the DbUpdateWorker.

        Parameters:
        callback (callable, optional): A function that can be used as a callback during the update process.
        """
        super().__init__()
        self.cancelled = False 

    def run(self):
        """
        Run the update process in a separate thread.

        Downloads the database collections and emits signals for progress, errors, and completion.
        """
        try:
            def cancel():
                return self.cancelled

            success = download_all_collections(callback=self.emit_progress, cancel=cancel)

            if not self.cancelled:
                self.finished.emit()
            else:
                self.finished.emit()

        except Exception as e:
            if not self.cancelled:
                self.error.emit(str(e))

    def emit_progress(self, value):
        """
        Emit progress signal with the given value.

        Parameters:
        value (int): Progress value to emit.
        """
        if not self.cancelled:
            self.progress.emit(value)

    def stop(self):
        """
        Stop the update process.
        """
        self.cancelled = True
        self.wait()

class LoadingWindow(QWidget):
    """
    Loading window that provides feedback during the database update process.

    The window includes a progress bar, a cancel button, and handles starting and monitoring the update.
    """
    update_completed_signal = Signal()

    def __init__(self):
        """
        Initialize the LoadingWindow with UI elements like progress bar and cancel button.
        """
        super().__init__()
        self.setWindowTitle("Loading")
        self.resize(400, 150)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Progress label
        self.progress_label = QLabel("Updating database, please wait...")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.progress_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.layout.addWidget(self.progress_bar)

        # Cancel button
        self.cancel_update_button = QPushButton("Cancel")
        self.cancel_update_button.clicked.connect(self.cancel_update)
        self.layout.addWidget(self.cancel_update_button)

        # Setup the worker thread
        self.worker = DbUpdateWorker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        # Set up worker and connect signals
        self.setup_worker_connections()
    
    def setup_worker_connections(self):
        """
        Set up the worker connections for updating progress and handling completion.
        """
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.update_finished)
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)

    def start_update(self):
        """
        Start the worker thread to begin the update process.
        """
        self.show()
        self.thread.start()

    def update_progress(self, value):
        """
        Update the progress bar with the given value.

        Parameters:
        value (int): Progress value to update the progress bar.
        """
        self.progress_bar.setValue(value)
        QCoreApplication.processEvents()

    def update_finished(self):
        """
        Handle actions to take once the update process is finished.
        """
        self.progress_label.setText("Update completed successfully!")
        self.cancel_update_button.setText("Close")
        self.cancel_update_button.clicked.disconnect()
        self.cancel_update_button.clicked.connect(self.close)
        self.thread.quit()
        self.thread.wait()
        self.update_completed_signal.emit()
        self.cleanup()

    def cleanup(self):
        for signal in [self.worker.finished, self.worker.progress, self.worker.error]:
            signal.disconnect()
        self.worker.deleteLater()
        self.worker = None

    def cancel_update(self):
        """
        Cancel the ongoing update process and update the UI accordingly.
        """
        if self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            
            # Adjust label and button for user feedback
            self.progress_label.setText("Update canceled.")
            self.cancel_update_button.setText("Close")
            self.cancel_update_button.clicked.disconnect()
            self.cleanup()
            self.update_completed_signal.emit()
            self.cancel_update_button.clicked.connect(self.close)

    def handle_error(self, error_message):
        """
        Handle errors that occur during the update process.

        Parameters:
        error_message (str): Error message to be displayed.
        """
        self.progress_bar.setValue(0)
        self.close()
