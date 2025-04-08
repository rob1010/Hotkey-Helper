import webbrowser
import logging
import os
import platform

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui_startup import StartupDialog
from ui_shortcuts import ShortcutDisplay
from ui_settings import SettingsWindow
from ui_update import LoadingWindow
from settings_manager import SettingsManager
from update_manager import check_for_db_updates

# Get a logger for this module
logger = logging.getLogger(__name__)

class WindowManager:
    """
    Manages the different UI components of the application, including the startup dialog,
    settings window, and shortcut display. It handles initialization, signal connections,
    and transitions between these components.
    """
    
    def __init__(self, app):
        """
        Initialize the WindowManager.

        Parameters:
        app (QApplication): The main application instance.
        """
        self.app = app
        self.settings_manager = SettingsManager()
        # Load the appropriate stylesheet based on the theme
        if self.settings_manager.get_setting("theme") == "dark":
            stylesheet = self.load_stylesheet("data/dark.qss")
        else:
            stylesheet = self.load_stylesheet("data/light.qss")
        self.app.setStyleSheet(stylesheet)

        # Initialize window components as None; they will be lazily created
        self.startup_dialog = None
        self.settings_window = None
        self.shortcut_display = None
        self.loading_window = None

        # Set the application icon based on the operating system
        self.base_dir = os.path.dirname(__file__)
        self.app.setWindowIcon(QIcon(self.setup_icon_paths(self.base_dir)))

    def setup_icon_paths(self, base_dir):
        """
        Configures the appropriate icon path based on the operating system.

        Parameters:
        - base_dir (str): Base directory containing icon files.
        """
        # Set the icon path based on the operating system
        self.icon_path_win = os.path.join(base_dir, "data/icon.ico")
        self.icon_path_mac = os.path.join(base_dir, "data/icon.icns")
        self.icon_path_linux = os.path.join(base_dir, "data/icon.png")

        # Return the appropriate icon path based on the operating system
        self.icon_path = (
            self.icon_path_win if platform.system() == "Windows"
            else self.icon_path_mac if platform.system() == "Darwin"
            else self.icon_path_linux
        )

    def initialize_startup_dialog(self):
        """Lazily initialize the startup dialog if it has not been created yet."""
        if self.startup_dialog is None:
            self.startup_dialog = StartupDialog()
        self.connect_signals_startup_dialog()

    def initialize_shortcut_display(self):
        """Lazily initialize the shortcut display if it has not been created yet."""
        if self.shortcut_display is None:
            self.shortcut_display = ShortcutDisplay(self.settings_manager)
        self.connect_signals_shortcut_display()

    def initialize_settings_window(self):
        """Lazily initialize the settings window if it has not been created yet."""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.settings_manager)
        self.connect_signals_settings_window()

    def disconnect_startup_dialog(self):
        """Disconnect all signals connected to the startup dialog."""
        self.startup_dialog.start_app_signal.disconnect()
        self.startup_dialog.open_website_signal.disconnect()
        self.startup_dialog.open_settings_signal.disconnect()
        self.startup_dialog.quit_app_signal.disconnect()
        self.startup_dialog = None

    def disconnect_shortcut_display(self):
        """Disconnect all signals connected to the shortcut display."""
        self.shortcut_display.tray_icon.open_startup_signal.disconnect()
        self.shortcut_display.tray_icon.quit_app_signal.disconnect()
        self.shortcut_display = None

    def disconnect_settings_window(self):
        """Disconnect all signals connected to the settings window."""
        self.settings_window.save_settings_signal.disconnect()
        self.settings_window.reset_settings_signal.disconnect()
        self.settings_window.close_settings_signal.disconnect()
        self.settings_window = None

    def run(self):
        """
        Start the application by checking if a database update is needed and initializing
        the appropriate window components.
        """
        # Set up the connection for update completion
        self.setup_signal_connection()

        # Check if an update is needed
        if check_for_db_updates():
            self.loading_window.start_update()
        else:
            # Proceed to first run if no update is needed
            QTimer.singleShot(0, self.first_run)

        # Ensure the event loop processes all pending events
        QCoreApplication.processEvents()

    def setup_signal_connection(self):
        """
        Set up the connection between the LoadingWindow and the WindowManager to handle
        transitions after the update process completes.
        """
        # Create the LoadingWindow, which will emit a signal when the update completes
        self.loading_window = LoadingWindow()
        self.loading_window.update_completed_signal.connect(lambda: self.first_run())

    def first_run(self):
        """
        Perform the first run actions, such as closing the loading window and showing the
        startup dialog.
        """
        # Close the loading window if it exists
        if self.loading_window:
            self.loading_window.close()
        # Show the startup dialog
        self.initialize_startup_dialog()
        self.startup_dialog.show()
        self.loading_window = None

    def connect_signals_startup_dialog(self):
        """
        Connect the signals emitted by the startup dialog to their respective handlers.
        """
        self.startup_dialog.start_app_signal.connect(self.start_app)
        self.startup_dialog.open_website_signal.connect(self.open_website)
        self.startup_dialog.open_settings_signal.connect(self.open_settings)
        self.startup_dialog.quit_app_signal.connect(self.quit_app)

    def connect_signals_shortcut_display(self):
        """
        Connect the signals emitted by the shortcut display to their respective handlers.
        """
        self.shortcut_display.tray_icon.open_startup_signal.connect(self.show_startup)
        self.shortcut_display.tray_icon.quit_app_signal.connect(self.quit_app)

    def connect_signals_settings_window(self):
        """
        Connect the signals emitted by the settings window to their respective handlers.
        """
        self.settings_window.save_settings_signal.connect(self.save_settings)
        self.settings_window.reset_settings_signal.connect(self.reset_settings)
        self.settings_window.close_settings_signal.connect(self.close_settings)

    @staticmethod
    def load_stylesheet(file_path):
        """
        Load the QSS stylesheet from the given file path.

        Parameters:
        file_path (str): The path to the QSS file.

        Returns:
        str: The contents of the stylesheet file.
        """
        # Attempt to load the stylesheet from the file path
        try:
            # Validate that the file path is within the expected directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            abs_file_path = os.path.abspath(file_path)

            # Check if the file path is within the base directory
            if not abs_file_path.startswith(base_dir):
                logger.error("Invalid file path: %s is outside the application directory", file_path)
                return ""

            # Check if the file exists
            if not os.path.isfile(abs_file_path):
                logger.error("File not found: %s", abs_file_path)
                return ""

            # Open the file with the validated path
            with open(abs_file_path, "r") as file:
                return file.read()
        except Exception as e:
            logger.error("Failed to load stylesheet: %s", e)
            return ""

    def start_app(self):
        """Transition from the StartupDialog to the ShortcutDisplay window."""
        # Initialize the ShortcutDisplay and show it
        self.initialize_shortcut_display()
        self.shortcut_display.timer.start()
        self.shortcut_display.show()
        # Close the StartupDialog if it exists
        if self.startup_dialog:
            self.startup_dialog.close()
            self.disconnect_startup_dialog()

    @staticmethod
    def open_website():
        """Placeholder method for opening the website."""
        url = "https://hotkey-helper.web.app/index.html"
        webbrowser.open(url)

    def quit_app(self):
        """Quit the application."""
        # Close the ShortcutDisplay and StartupDialog if they exist
        if self.shortcut_display:
            self.shortcut_display.tray_icon.close()
            self.disconnect_shortcut_display()

        # Close the StartupDialog if it exists
        if self.startup_dialog:
            self.startup_dialog.close()
            self.disconnect_startup_dialog()
        QApplication.quit()

    def show_startup(self):
        """Show the StartupDialog, closing other windows if necessary."""
        # Initialize the StartupDialog and show it
        self.initialize_startup_dialog()
        self.startup_dialog.show()
        self.shortcut_display.timer.stop()
        # Close the ShortcutDisplay if it exists
        if self.shortcut_display:
            self.shortcut_display.close()
            self.disconnect_shortcut_display()
        # Close the SettingsWindow if it exists
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()

    def open_settings(self):
        """Transition from the StartupDialog to the SettingsWindow."""
        self.initialize_settings_window()
        self.settings_window.show()
        # Close the StartupDialog if it exists
        if self.startup_dialog:
            self.startup_dialog.close()
            self.disconnect_startup_dialog()

    def save_settings(self):
        """Save the settings and return to the StartupDialog."""
        self.initialize_startup_dialog()
        # Apply the theme based on updated settings
        if self.settings_manager.get_setting("theme") == "dark":
            stylesheet = self.load_stylesheet("data/dark.qss")
        else:
            stylesheet = self.load_stylesheet("data/light.qss")
        self.app.setStyleSheet(stylesheet)
        self.startup_dialog.show()
        # Close the SettingsWindow if it exists
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()

    def reset_settings(self):
        """Reset settings to their default values and return to the StartupDialog."""
        self.initialize_startup_dialog()
        # Apply the default theme
        if self.settings_manager.get_setting("theme") == "dark":
            stylesheet = self.load_stylesheet("data/dark.qss")
        else:
            stylesheet = self.load_stylesheet("data/light.qss")
        self.app.setStyleSheet(stylesheet)
        self.startup_dialog.show()
        # Close the SettingsWindow if it exists
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()

    def close_settings(self):
        """Close the SettingsWindow and return to the StartupDialog."""
        self.initialize_startup_dialog()
        self.startup_dialog.show()
        # Close the SettingsWindow if it exists
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()
