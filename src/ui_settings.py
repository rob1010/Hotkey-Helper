import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, QSlider, QColorDialog

# Get a logger for this module
logger = logging.getLogger(__name__)

class SettingsWindow(QWidget):

    """
    The SettingsWindow class provides the UI for managing user preferences
    for the application's shortcut display. Users can customize themes,
    window dimensions, fonts, and more.
    """

    # Signals
    save_settings_signal = Signal()
    reset_settings_signal = Signal()
    close_settings_signal = Signal()

    def __init__(self, settings_manager, parent=None):
        """
        Initialize the SettingsWindow to manage application settings.

        Parameters:
        settings_manager (SettingsManager): The settings manager responsible for storing user preferences.
        parent (QWidget, optional): The parent widget for this settings window.
        """
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.parent = parent
        self.init_ui()
        self.load_settings_into_ui()
        self.move(self.x(), 0)

    def init_ui(self):
        """Set up the user interface for the settings window."""
        self.setWindowTitle('Settings')
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.layout = QVBoxLayout()

        # Theme selection
        self.theme_combo = self.add_combo_box_setting('Theme:', ['Light', 'Dark'], "Choose between Light and Dark themes.")

        # Search Shortcuts Checkbox
        self.search_shortcuts_checkbox = self.add_checkbox_setting('Enable search bar for shortcuts', 'Choose if the search bar should be enabled for shortcuts.')

        # Adapting window to list Checkbox
        self.adapt_window_checkbox = self.add_checkbox_setting('Adapting window', "Choose between adapting window to shortcut content or a fixed size")

        # Window width and height sliders (Corrected values to ensure integers are passed)
        self.width_slider = self.add_slider_setting('Shortcut window width:', 10, 50, "\nSet shortcut window width: 10-50%")
        self.height_slider = self.add_slider_setting('Shortcut window height:', 10, 100, "\nSet shortcut window height: 10-100%")

        # Opacity Slider
        self.opacity_slider = self.add_slider_setting('Shortcut window opacity:', 10, 100, "\nSet shortcut window opacity: 10-100%")

        # Position Priority
        self.position_priority_combo = self.add_combo_box_setting('Shortcut window position priority:',
                                   ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right'],
                                   "Choose the primary position for the shortcut window to appear.")

        # Font Settings
        self.font_family_combo = self.add_combo_box_setting('Set font family for shortcut window:',
                                   ['Arial', 'Verdana', 'Courier New', 'Times New Roman'])

        # Font color
        self.font_color_button = self.add_button_setting('Set font color for shortcut window:', 'Select Color', self.choose_font_color)

        # Font size
        self.font_size_slider = self.add_slider_setting_number('Set font size for windows:', 8, 24)

        # Save and Reset buttons
        self.add_button_setting(None, 'Save', self.save_settings_emit)
        self.add_button_setting('Reset for Recommended Settings', 'Reset', self.reset_settings_emit)

        self.setLayout(self.layout)

    def add_combo_box_setting(self, label_text, items, tooltip=None):
        """
        Add a combo box setting to the layout.

        Parameters:
        label_text (str): The text for the label.
        items (list): A list of items for the combo box.
        tooltip (str, optional): Tooltip text to provide additional information to the user.

        Returns:
        QComboBox: The created QComboBox instance.
        """
        # Create label and combo box
        label = QLabel(label_text)
        combo_box = QComboBox()
        combo_box.addItems(items)
        # Set tooltip if provided
        if tooltip:
            combo_box.setToolTip(tooltip)
        self.layout.addWidget(label)
        self.layout.addWidget(combo_box)
        return combo_box

    def add_checkbox_setting(self, label_text, tooltip=None):
        """
        Add a checkbox setting to the layout.

        Parameters:
        label_text (str): The text for the checkbox.
        tooltip (str, optional): Tooltip text to provide additional information to the user.

        Returns:
        QCheckBox: The created QCheckBox instance.
        """
        # Create checkbox
        checkbox = QCheckBox(label_text)
        if tooltip:
            checkbox.setToolTip(tooltip)
        self.layout.addWidget(checkbox)
        return checkbox

    def add_slider_setting(self, label_text, min_val, max_val, unit="%", tooltip=None):
        """
        Add a slider setting to the layout.

        Parameters:
        label_text (str): The text for the label.
        min_val (int): The minimum value of the slider.
        max_val (int): The maximum value of the slider.
        tooltip (str, optional): Tooltip text to provide additional information to the user.

        Returns:
        QSlider: The created QSlider instance.
        """
        # Create label, slider, and value label
        label = QLabel(label_text)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(int(min_val), int(max_val))
        value_label = QLabel(f"{slider.value()}{unit}")
        slider.valueChanged.connect(lambda value: value_label.setText(f"{value}{unit}"))
        # Set tooltip if provided
        if tooltip:
            slider.setToolTip(tooltip)
        self.layout.addWidget(label)
        self.layout.addWidget(slider)
        self.layout.addWidget(value_label)
        return slider

    def add_slider_setting_number(self, label_text, min_val, max_val, tooltip=None):
        """
        Add a slider setting to the layout.

        Parameters:
        label_text (str): The text for the label.
        min_val (int): The minimum value of the slider.
        max_val (int): The maximum value of the slider.
        tooltip (str, optional): Tooltip text to provide additional information to the user.

        Returns:
        QSlider: The created QSlider instance.
        """
        # Create label, slider, and value label
        label = QLabel(label_text)
        slider = QSlider(Qt.Horizontal)

        # Ensure min_val and max_val are integers (Corrected from previous usage)
        min_val = int(min_val)
        max_val = int(max_val)

        slider.setRange(min_val, max_val)
        value_label = QLabel(f"{slider.value()}")
        slider.valueChanged.connect(lambda value: value_label.setText(f"{value}"))
        # Set tooltip if provided
        if tooltip:
            slider.setToolTip(tooltip)

        # Add to layout
        self.layout.addWidget(label)
        self.layout.addWidget(slider)
        self.layout.addWidget(value_label)
        return slider

    def add_button_setting(self, label_text, button_text, click_handler):
        """
        Add a button with label to the layout.

        Parameters:
        label_text (str): The text for the label.
        button_text (str): The text displayed on the button.
        click_handler (callable): Function to be called when the button is clicked.

        Returns:
        QPushButton: The created QPushButton instance.
        """
        # Create label and button
        label = QLabel(label_text)
        button = QPushButton(button_text)
        button.clicked.connect(click_handler)
        self.layout.addWidget(label)
        self.layout.addWidget(button)
        return button

    def choose_font_color(self):
        """Open color picker for font color selection."""
        # Open color dialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.font_color_button.setStyleSheet(f"background-color:{color.name()};")
            self.save_settings_from_ui()  # Update via validated method

    def load_settings_into_ui(self):
        """Load current settings into the UI elements."""
        # Theme
        theme = self.settings_manager.get_setting('theme')
        self.theme_combo.setCurrentText(theme.capitalize())

        # Search Shortcuts
        search_shortcuts = self.settings_manager.get_setting('search_shortcuts')
        self.search_shortcuts_checkbox.setChecked(search_shortcuts)

        # Opacity
        opacity = self.settings_manager.get_setting('opacity')
        self.opacity_slider.setValue(int(opacity * 100))

        # Window Width and Height
        window_width = self.settings_manager.get_setting('max_window_width')
        self.width_slider.setValue(int(window_width * 100))  # Convert to percentage
        window_height = self.settings_manager.get_setting('max_window_height')
        self.height_slider.setValue(int(window_height * 100))  # Convert to percentage

        # Font Family
        font_family = self.settings_manager.get_setting('font_family')
        self.font_family_combo.setCurrentText(font_family)

        # Font Color
        font_color = self.settings_manager.get_setting('font_color')
        self.font_color_button.setStyleSheet(f"background-color:{font_color};")

        # Font Size
        font_size = self.settings_manager.get_setting('font_size')
        self.font_size_slider.setValue(font_size)

        # Adapting Window to List
        adapting_window = self.settings_manager.get_setting('adapting_window_to_list')
        self.adapt_window_checkbox.setChecked(adapting_window)

        # Position Priority
        position_priority = self.settings_manager.get_setting('position_priority')
        formatted_position = position_priority.replace('-', ' ').title()
        self.position_priority_combo.setCurrentText(formatted_position)

    def save_settings_from_ui(self):
        """Save settings from UI elements into the settings manager."""
        # Theme
        self.settings_manager.set_setting('theme', self.theme_combo.currentText().lower())

        # Search Shortcuts
        self.settings_manager.set_setting('search_shortcuts', self.search_shortcuts_checkbox.isChecked())

        # Opacity
        self.settings_manager.set_setting('opacity', self.opacity_slider.value() / 100)

        # Window Width and Height
        self.settings_manager.set_setting('max_window_width', self.width_slider.value() / 100)
        self.settings_manager.set_setting('max_window_height', self.height_slider.value() / 100)

        # Font Family
        self.settings_manager.set_setting('font_family', self.font_family_combo.currentText())

        # Font Color
        color = self.font_color_button.styleSheet().split(':')[-1].strip(';')
        self.settings_manager.set_setting('font_color', color)

        # Font Size
        self.settings_manager.set_setting('font_size', self.font_size_slider.value())

        # Adapting Window to List
        self.settings_manager.set_setting('adapting_window_to_list', self.adapt_window_checkbox.isChecked())

        # Position Priority
        self.settings_manager.set_setting('position_priority', self.position_priority_combo.currentText().replace(' ', '-').lower())

        # Save settings to the file
        self.settings_manager.save_settings()

    def save_settings_emit(self):
        """
        Emit the save settings signal and save current settings using the settings manager.
        """
        self.save_settings_from_ui()
        self.load_settings_into_ui()
        self.save_settings_signal.emit()

    def reset_settings_emit(self):
        """Emit the reset settings signal and reset settings to defaults."""
        self.settings_manager.reset_to_defaults()
        self.load_settings_into_ui()
        self.reset_settings_signal.emit()

    def close_settings_emit(self):
        """Close the settings window."""
        self.close_settings_signal.emit()
