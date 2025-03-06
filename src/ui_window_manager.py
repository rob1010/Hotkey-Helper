import sys
import webbrowser
import logging

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication
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
        
    def initialize_startup_dialog(self):
        """
        Lazily initialize the startup dialog if it has not been created yet.
        """
        if self.startup_dialog is None:
            self.startup_dialog = StartupDialog()
        self.connect_signals_startup_dialog()

    def initialize_shortcut_display(self):
        """
        Lazily initialize the shortcut display if it has not been created yet.
        """
        if self.shortcut_display is None:
            self.shortcut_display = ShortcutDisplay(self.settings_manager)
        self.connect_signals_shortcut_display()

    def initialize_settings_window(self):
        """
        Lazily initialize the settings window if it has not been created yet.
        """
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.settings_manager)
        self.connect_signals_settings_window()
        
    def disconnect_startup_dialog(self):
        """
        Disconnect all signals connected to the startup dialog.
        """
        self.startup_dialog.start_app_signal.disconnect()
        self.startup_dialog.open_website_signal.disconnect()
        self.startup_dialog.open_settings_signal.disconnect()
        self.startup_dialog.quit_app_signal.disconnect()
        self.startup_dialog = None

    def disconnect_shortcut_display(self):
        """
        Disconnect all signals connected to the shortcut display.
        """
        self.shortcut_display.tray_icon.open_startup_signal.disconnect()
        self.shortcut_display.tray_icon.quit_app_signal.disconnect()
        self.shortcut_display = None

    def disconnect_settings_window(self):
        """
        Disconnect all signals connected to the settings window.
        """
        self.settings_window.save_settings_signal.disconnect()
        self.settings_window.reset_settings_signal.disconnect()
        self.settings_window.close_settings_signal.disconnect()
        self.settings_window = None
        
    def run(self):
        """
        Start the application by checking if a database update is needed and initializing
        the appropriate window components.
        """
        # Step 1: Set up the connection for update completion
        self.setup_signal_connection()

        # Step 2: Check if an update is needed
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
        if self.loading_window:
            self.loading_window.close()
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

    def load_stylesheet(self, file_path):
        """
        Load the QSS stylesheet from the given file path.

        Parameters:
        file_path (str): The path to the QSS file.

        Returns:
        str: The contents of the stylesheet file.
        """
        try:
            with open(file_path, "r") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Failed to load stylesheet: {e}")

    def start_app(self):
        """
        Transition from the StartupDialog to the ShortcutDisplay window.
        """
        self.initialize_shortcut_display()
        self.shortcut_display.timer.start()
        self.shortcut_display.show()
        if self.startup_dialog:
            self.startup_dialog.close()
            self.disconnect_startup_dialog()
            
    def open_website(self):
        """
        Placeholder method for opening the website.
        """
        url="https://hotkey-helper.web.app/index.html"
        webbrowser.open(url)

    def quit_app(self):
        """
        Quit the application.
        """
        if self.shortcut_display:
            self.shortcut_display.tray_icon.close()
            self.disconnect_shortcut_display()
        if self.startup_dialog:
            self.startup_dialog.close()
            self.disconnect_startup_dialog()
        QApplication.quit()

    def show_startup(self):
        """
        Show the StartupDialog, closing other windows if necessary.
        """
        self.initialize_startup_dialog()
        self.startup_dialog.show()
        self.shortcut_display.timer.stop()
        if self.shortcut_display:
            self.shortcut_display.close()
            self.disconnect_shortcut_display()
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()

    def open_settings(self):
        """
        Transition from the StartupDialog to the SettingsWindow.
        """
        self.initialize_settings_window()
        self.settings_window.show()
        if self.startup_dialog:
            self.startup_dialog.close() 
            self.disconnect_startup_dialog()

    def save_settings(self):
        """
        Save the settings and return to the StartupDialog.
        """
        self.initialize_startup_dialog()
        # Apply the theme based on updated settings
        if self.settings_manager.get_setting("theme") == "dark":
            stylesheet = self.load_stylesheet("data/dark.qss")
        else:
            stylesheet = self.load_stylesheet("data/light.qss")
        self.app.setStyleSheet(stylesheet)
        self.startup_dialog.show()
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()

    def reset_settings(self):
        """
        Reset settings to their default values and return to the StartupDialog.
        """
        self.initialize_startup_dialog()
        # Apply the default theme
        if self.settings_manager.get_setting("theme") == "dark":
            stylesheet = self.load_stylesheet("data/dark.qss")
        else:
            stylesheet = self.load_stylesheet("data/light.qss")
        self.app.setStyleSheet(stylesheet)
        self.startup_dialog.show()
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()

    def close_settings(self):
        """
        Close the SettingsWindow and return to the StartupDialog.
        """
        self.initialize_startup_dialog()
        self.startup_dialog.show()
        if self.settings_window:
            self.settings_window.close()
            self.disconnect_settings_window()