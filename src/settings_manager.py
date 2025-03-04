import json
import os
import shutil
# Solve the issue by adding a check for the settings file !!!
# Missing directory existence checks before file writes !!!
# Loaded settings aren’t type-checked. Add type-checking for settings !!!
# Add configuration flexibility for settings validation !!!

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data/config.json")
BACKUP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data/config_backup.json")

class SettingsManager:
    def __init__(self, settings_file=CONFIG_PATH):
        self.settings_file = settings_file
        self.default_settings = {
            'theme': 'light', 'search_shortcuts': True, 'opacity': 0.7,
            'max_window_width': 0.25, 'max_window_height': 0.5,
            'font_family': 'Times New Roman', 'font_color': '#000000',
            'font_size': 8, 'adapting_window_to_list': True,
            'position_priority': 'top-right'
        }
        
        self.settings = self.default_settings.copy()
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                print("Corrupted JSON, attempting to restore from backup.")
                if os.path.exists(BACKUP_CONFIG_PATH):
                    shutil.copy(BACKUP_CONFIG_PATH, self.settings_file)
                    with open(self.settings_file, 'r') as file:
                        return json.load(file)
                self.settings = self.default_settings.copy()
                self.save_settings()
        else:
            print("Settings file missing, using defaults.")
            self.save_settings()
        return self.default_settings.copy()

    def save_settings(self):
        try:
            if os.path.exists(self.settings_file):
                shutil.copy(self.settings_file, BACKUP_CONFIG_PATH)
            with open(self.settings_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def reset_to_defaults(self):
        """
        Reset settings to default values and save them.
        """
        self.settings = self.default_settings.copy()
        self.save_settings()

    def get_setting(self, key):
        """
        Get a specific setting by key.

        Parameters:
        key (str): The key of the setting to retrieve.

        Returns:
        The value of the setting if it exists, otherwise the default value.
        """
        return self.settings.get(key, self.default_settings.get(key))

    def set_setting(self, key, value):
        """
        Set a specific setting by key and save the updated settings.

        Parameters:
        key (str): The key of the setting to update.
        value: The new value for the setting.
        """
        # Enhanced validation example
        if key == 'opacity':
            if not (0.1 <= value <= 1.0):
                print("Invalid value for opacity. Must be between 0.0 and 1.0.")
                return
        elif key == 'font_size':
            if not isinstance(value, int) or value <= 0:
                print("Invalid value for font size. Must be a positive integer.")
                return
        elif key == 'max_window_width' or key == 'max_window_height':
            if not (0.1 < value <= 1.0):
                print(f"Invalid value for {key}. Must be between 0.0 and 1.0.")
                return
        elif key == 'theme':
            if value not in ['light', 'dark']:
                print("Invalid value for theme. Must be 'light' or 'dark'.")
                return
        elif key == 'position_priority':
            if value not in ['top-right', 'top-left', 'bottom-right', 'bottom-left']:
                print("Invalid value for position_priority. Must be one of ['top-right', 'top-left', 'bottom-right', 'bottom-left'].")
                return
        elif key == 'font_color':
            if not isinstance(value, str) or not value.startswith('#') or len(value) != 7:
                print("Invalid value for font_color. Must be a hex string like '#000000'.")
                return
        elif key == 'font_family':
            if not isinstance(value, str) or len(value.strip()) == 0:
                print("Invalid value for font_family. Must be a non-empty string.")
                return
        elif key == 'search_shortcuts' or key == 'adapting_window_to_list':
            if not isinstance(value, bool):
                print(f"Invalid value for {key}. Must be a boolean (True or False).")
                return

        # Update setting and save
        self.settings[key] = value
        self.save_settings()
