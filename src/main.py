import sys
import logging
import sentry_sdk

from PySide6.QtWidgets import QApplication
from ui_window_manager import WindowManager

# Initialize Sentry once in your app (e.g., in main.py)
#sentry_sdk.init("your_sentry_dsn", traces_sample_rate=1.0)

# Configure logging once for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='data/application.log'  # Single log file for all modules
)

def main():
    """
    Initialize and run the application.

    This function sets up the core event loop by creating an instance of `QApplication`.
    It initializes the `WindowManager` to manage the different application windows 
    and then starts the main event loop to handle GUI events.
    """
    # Create the QApplication instance - necessary for managing all GUI components.
    app = QApplication(sys.argv)
    
    # Create the main window manager instance that handles all application windows and signals.
    window_manager = WindowManager(app)

    # Begin running the window manager to show and manage the app's windows.
    window_manager.run()

    # Execute the main Qt event loop, which processes user inputs and updates the GUI.
    sys.exit(app.exec())

if __name__ == "__main__":
    # Entry point of the application.
    main()
