import os
import platform

from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QIcon, QAction, QCursor
from PySide6.QtWidgets import (
    QSystemTrayIcon,
    QScrollArea,
    QWidget,
    QMenu,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QApplication,
)
from shortcuts_manager import ShortcutManager
from shortcuts_manager import (
    get_active_window_info,
    load_local_map,
    find_best_match,
    is_my_app_active,
)

# Constants for file paths
APP_NAME_MAP_PATH = os.path.join(os.path.dirname(__file__), "data/app_name_map.txt")
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "data/local_shortcut_db.json")


class TrayIcon(QSystemTrayIcon):
    """
    Represents the system tray icon for the application.

    Features:
    - Displays a tray icon with menu options.
    - Emits signals for opening the startup dialog or quitting the application.

    Attributes:
    - settings_manager (dict): Settings manager for app configurations.
    - is_action_in_progress (bool): Flag to prevent multiple overlapping actions.

    Signals:
    - open_startup_signal: Emitted when the "Show Startup" action is triggered.
    - quit_app_signal: Emitted when the "Quit" action is triggered.
    """

    open_startup_signal = Signal()
    quit_app_signal = Signal()

    def __init__(self, settings_manager=None, is_action_in_progress=False, parent=None):
        super().__init__(parent)
        self.base_dir = os.path.dirname(__file__)
        self.settings_manager = settings_manager or {}
        self.is_action_in_progress = is_action_in_progress
        self.init_ui()

    def init_ui(self):
        """
        Initializes the tray icon UI, setting up the icon and context menu.
        """
        self.setup_icon_paths(self.base_dir)
        self.setup_tray_icon()

    def setup_icon_paths(self, base_dir):
        """
        Configures the appropriate icon path based on the operating system.

        Parameters:
        - base_dir (str): Base directory containing icon files.
        """
        self.icon_path_win = os.path.join(base_dir, "data/icon.ico")
        self.icon_path_mac = os.path.join(base_dir, "data/icon.icns")
        self.icon_path_linux = os.path.join(base_dir, "data/icon.png")

        self.icon_path = (
            self.icon_path_win if platform.system() == "Windows"
            else self.icon_path_mac if platform.system() == "Darwin"
            else self.icon_path_linux
        )

    def setup_tray_icon(self):
        """
        Configures the system tray icon and context menu actions.
        """
        self.setIcon(QIcon(self.icon_path))

        tray_menu = QMenu()
        show_startup_action = tray_menu.addAction("Show Startup")
        quit_action = tray_menu.addAction("Quit")

        show_startup_action.triggered.connect(self.emit_open_startup_signal)
        quit_action.triggered.connect(self.emit_quit_application_signal)

        self.setContextMenu(tray_menu)
        self.activated.connect(self.on_tray_icon_activated)
        self.showMessage("HotKey Helper", "Click here to access options!", QSystemTrayIcon.Information, 3000)

    def on_tray_icon_activated(self, reason):
        """
        Handles tray icon activation events, such as clicks.

        Parameters:
        - reason (QSystemTrayIcon.ActivationReason): The reason for activation.
        """
        if reason in {QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick}:
            self.open_startup_signal.emit()

    def emit_open_startup_signal(self):
        """
        Emits the signal to open the startup dialog if no other action is in progress.
        """
        if not self.is_action_in_progress:
            self.is_action_in_progress = True
            self.open_startup_signal.emit()

    def emit_quit_application_signal(self):
        """
        Emits the signal to quit the application.
        """
        self.quit_app_signal.emit()


class ShortcutDisplay(QWidget):
    """
    Displays shortcuts relevant to the active application.

    Features:
    - Detects the active window and retrieves corresponding shortcuts.
    - Provides a search bar to filter shortcuts.

    Attributes:
    - settings_manager (dict): Manages UI and functional settings.
    - map_path (str): Path to the application name map file.
    - local_db_path (str): Path to the local shortcut database.
    """

    def __init__(self, settings_manager, map_path=APP_NAME_MAP_PATH, local_db_path=LOCAL_DB_PATH, interval=250, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager or {}
        self.shortcut_manager = ShortcutManager()
        self.map_path = map_path
        self.local_db_path = local_db_path
        self.interval = interval
        self.timer = QTimer()
        self.text = ""
        self.is_search_active = False
        self.last_active_app_name = None
        self.current_shortcuts = {}
        self.SEARCH_ICON_PATH = os.path.join(os.path.dirname(__file__), "data/search.png")
        self.app_name_map = load_local_map(self.map_path)
        self.local_shortcuts = self.shortcut_manager.load_local_shortcuts(self.local_db_path)
        self.SCREEN_SIZE_WIDTH = self.settings_manager.get_setting('max_window_width')
        self.SCREEN_SIZE_HEIGHT = self.settings_manager.get_setting('max_window_height')
        self.adapt = self.settings_manager.get_setting('adapting_window_to_list')
        self.position_priority = self.settings_manager.get_setting("position_priority")
        self.corner_index = 0
        self.counter = 0
        self.use_counter = True

        # UI settings
        self.tray_icon = TrayIcon(parent=self)
        self.tray_icon.show()
        self.tray_icon.open_startup_signal.connect(self.tray_icon.emit_open_startup_signal)
        self.tray_icon.quit_app_signal.connect(self.tray_icon.emit_quit_application_signal)

        self.init_ui()
        self.timer.timeout.connect(self.update_shortcuts)
        self.timer.start(self.interval)

    def init_ui(self):
        """
        Initializes the user interface for the shortcut display.
        """
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setup_search_bar()
        self.setup_labels()
        self.setLayout(self.layout)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.apply_styles_from_settings()

    def update_shortcuts(self):
        """
        Updates the shortcuts displayed in the application.

        This method detects the currently active application window and retrieves relevant shortcuts.
        If a search is active, it filters the shortcuts based on the search query.
        Additionally, it adapts the display and position of the window as needed.

        Steps:
        1. Get the active window's title and process name.
        2. Match the title with the app name map.
        3. Retrieve shortcuts for the detected application or the previously active app.
        4. Apply filtering if a search query is active.
        5. Update the display and adjust the window size and position.

        Notes:
        - The search state is reset when switching to a new application.
        """
        # Step 1: Retrieve the active window's title and process name
        window_title, process_name = get_active_window_info()

        if not window_title:
            #print("No active window detected.")
            return

        # Step 2: Load app names mapping
        try:
            app_names_map = load_local_map(self.map_path)
        except FileNotFoundError:
            app_names_map = {}
            print("Warning: app_name_map.txt not found.")

        # Step 3: Match the active window title to an application name
        app_name = find_best_match(app_names_map, window_title)
        if not app_name:
            #print(f"No shortcuts found for the window title: '{window_title}'")
            return

        # Step 4: Determine if the current window belongs to this application
        is_my_app = is_my_app_active(window_title)

        # Step 5: Load shortcuts based on the app detection and previous state
        if is_my_app and self.last_active_app_name is None:
            shortcuts = self.shortcut_manager.load_local_shortcuts(app_name)
        elif is_my_app and self.last_active_app_name is not None:
            shortcuts = self.shortcut_manager.load_local_shortcuts(self.last_active_app_name)
        elif not is_my_app:
            shortcuts = self.shortcut_manager.load_local_shortcuts(app_name)
            self.last_active_app_name = app_name

        # Step 6: Handle active search state and filter shortcuts
        if self.is_search_active:
            filtered_shortcuts = {
                key: value for key, value in self.current_shortcuts.items()
                if self.text.lower() in key.lower() or
                self.text.lower() in value.get("fields", {}).get("Description", "").lower()
            }

            # Update the display with filtered shortcuts
            self.display_shortcuts(filtered_shortcuts)

            if not is_my_app:
                # Reset search state on app switch
                self.is_search_active = False
                self.search_bar.clear()
        else:
            # Update display with the new set of shortcuts
            self.current_shortcuts = shortcuts
            self.display_shortcuts(self.current_shortcuts)

        # Step 7: Adjust the window's size and position
        self.adjust_size_and_position()

    def apply_styles_from_settings(self):
        """
        Applies styles to UI elements such as the main window and search bar
        based on user-defined or default settings.
        """
        padding = 3
        theme = self.settings_manager.get_setting('theme')
        font_family = self.settings_manager.get_setting('font_family')
        font_color = self.settings_manager.get_setting('font_color')
        font_size = self.settings_manager.get_setting('font_size')
        opacity = self.settings_manager.get_setting('opacity')

        # Predefined themes with corresponding styles
        themes = {
            'dark': {
                'background': '#444444',
                'font_color': '#ffffff',
                'search_bar': {
                    'background': '#333333',
                    'border': '1px solid #444444',
                    'focus_border': '1px solid #1E88E5'
                }
            },
            'light': {
                'background': '#f0f0f0',
                'font_color': '#000000',
                'search_bar': {
                    'background': '#FFFFFF',
                    'border': '1px solid #DADADA',
                    'focus_border': '1px solid #4CAF50'
                }
            }
        }

        # Default to light theme if an unrecognized theme is selected
        theme_properties = themes.get(theme, themes['light'])

        # Override font color only if it matches the theme's default
        if font_color in {themes['dark']['font_color'], themes['light']['font_color']}:
            font_color = theme_properties['font_color']

        # Apply styles to the main window
        stylesheet = f"""
            padding: {padding}px;
            font-family: {font_family};
            font-size: {font_size}px;
            color: {font_color};
            background-color: {theme_properties['background']};
        """
        self.setStyleSheet(stylesheet)

        # Apply styles specifically to the search bar
        search_bar_styles = f"""
            QLineEdit {{
                background-color: {theme_properties['search_bar']['background']};
                border: {theme_properties['search_bar']['border']};
                border-radius: 15px;
                padding: 8px 8px;
                font-size: {font_size}px;
                color: {font_color};
                font-family: {font_family};
            }}
            QLineEdit:focus {{
                border: {theme_properties['search_bar']['focus_border']};
                outline: none;
            }}
        """
        self.search_bar.setStyleSheet(search_bar_styles)

        # Set window opacity
        self.setWindowOpacity(opacity)

    def setup_search_bar(self):
        """
        Configures the search bar, adding a placeholder and an optional leading icon.
        """
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search shortcuts...")

        # Optionally add a leading search icon
        search_icon = QIcon(self.SEARCH_ICON_PATH)
        search_action = QAction(search_icon, "", self.search_bar)
        self.search_bar.addAction(search_action, QLineEdit.LeadingPosition)

        # Connect text changes to trigger real-time filtering
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        self.layout.addWidget(self.search_bar)

    def setup_labels(self):
        """
        Creates labels for displaying shortcuts and their descriptions. 
        These are embedded in scrollable areas for better usability.
        """
        self.horizontal_layout = QHBoxLayout()
        self.descriptionLabel = QLabel("Descriptions will be displayed here")
        self.shortcutLabel = QLabel("Shortcuts will be displayed here")

        # Configure labels to enable word wrapping and alignment
        self.descriptionLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.shortcutLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        #self.descriptionLabel.setWordWrap(True)
        #self.shortcutLabel.setWordWrap(True)

        # Add labels to scrollable areas
        #self.description_scroll_area = QScrollArea()
        #self.shortcut_scroll_area = QScrollArea()
        #self.description_scroll_area.setWidget(self.descriptionLabel)
        #self.shortcut_scroll_area.setWidget(self.shortcutLabel)

        # Ensure scroll areas resize with content
        #self.description_scroll_area.setWidgetResizable(True)
        #self.shortcut_scroll_area.setWidgetResizable(True)

        # Add scroll areas to the layout
        self.horizontal_layout.addWidget(self.descriptionLabel)
        self.horizontal_layout.addWidget(self.shortcutLabel)
        self.layout.addLayout(self.horizontal_layout)

    @Slot(str)
    def on_search_text_changed(self, text):
        """
        Updates the state of the search bar and filters shortcuts in real-time.

        Parameters:
        - text (str): Current input from the search bar.
        """
        self.text = text
        self.is_search_active = True

    def display_shortcuts(self, shortcuts):
        """
        Updates the shortcut and description labels with the provided shortcuts.

        Parameters:
        - shortcuts (dict): Dictionary containing shortcuts and their metadata.
        """
        if shortcuts:
            descriptions = "\n".join(
                shortcut_data.get("fields", {}).get("Description", "No Description")
                for shortcut_data in shortcuts.values()
            )
            shortcuts_text = "\n".join(shortcut for shortcut in shortcuts.keys())

            self.descriptionLabel.setText(descriptions)
            self.shortcutLabel.setText(shortcuts_text)
        else:
            self.descriptionLabel.setText("No matching shortcuts found")
            self.shortcutLabel.setText("")

    def scale_value(self, num):
        """
        Scales a numeric value for UI adjustment purposes.

        Parameters:
        - num (int): Input value to scale.

        Returns:
        - float: Scaled value.
        """
        return 4 + (num - 8) * (2 - 4) / (24 - 8)

    def adjust_size_and_position(self):
        """
        Dynamically adjusts the window size and repositions it based on screen size,
        user preferences, and the cursor's current location.
        """
        screen = QApplication.screenAt(QCursor.pos())
        if not screen:
            return
        
        # Handle adaptive resizing based on content and screen dimensions
        screen_geometry = screen.geometry()
        cursor_pos = QCursor.pos()

        if self.adapt:
            content_size = self.layout.sizeHint()
            max_width = screen_geometry.width()
            max_height = screen_geometry.height()
            content_width = min(content_size.width(), max_width) * 0.5
            content_height = min(content_size.height(), max_height)
            self.resize(content_width, content_height)
        else:
            width = screen_geometry.width() * self.SCREEN_SIZE_WIDTH
            height = screen_geometry.height() * self.SCREEN_SIZE_HEIGHT
            self.setFixedSize(width, height)

        # Determine preferred corner placement
        preferred_position = self.settings_manager.get_setting("position_priority")

        position_map = {
            "top-left": 0,
            "top-right": 1,
            "bottom-right": 2,
            "bottom-left": 3
        }
        font_size = self.settings_manager.get_setting('font_size')
        width = self.width()
        height = self.height()

        # Map screen corners and adjust position accordingly
        corners = [
            (screen_geometry.left(), screen_geometry.top()),
            (screen_geometry.right() - width, screen_geometry.top()),
            (screen_geometry.right() - width, screen_geometry.bottom() - height),
            (screen_geometry.left(), screen_geometry.bottom() - height)
        ]

        preferred_index = position_map.get(preferred_position, 1)

        # Adjust position dynamically to avoid cursor overlap
        window_geometry = self.geometry()
        search_bar_rect = self.search_bar.geometry()
        scaled_value = self.scale_value(font_size)
        padding_above_search_bar = font_size * scaled_value

        adjusted_window_geometry = window_geometry.adjusted(
            0,
            padding_above_search_bar + search_bar_rect.top(),
            0,
            0
        )

        if adjusted_window_geometry.contains(cursor_pos):
            if self.use_counter:
                self.counter = (self.counter + 1) % len(corners)
                if self.counter == preferred_index:
                    self.counter = (self.counter + 1) % len(corners)

                self.corner_index = self.counter
            else:
                self.corner_index = preferred_index

            self.use_counter = not self.use_counter

        new_position = corners[self.corner_index]
        self.move(*new_position)
