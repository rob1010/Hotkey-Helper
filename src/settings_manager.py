import json
import os
import shutil
import logging

from typing import Any, Dict, Optional

# Get a logger for this module
logger = logging.getLogger(__name__)

# Configurable paths with environment variable support
CONFIG_PATH = os.environ.get(
    'HOTKEY_HELPER_CONFIG_PATH', 
    os.path.join(os.path.dirname(__file__), "data/config.json")
)
BACKUP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data/config_backup.json")

class SettingsManager:
    def __init__(self, settings_file: str = CONFIG_PATH):
        """
        Initialize SettingsManager with configurable settings file path.

        Args:
            settings_file (str): Path to the settings file. Defaults to CONFIG_PATH.
        """
        self.settings_file = settings_file
        
        # Define expected types for settings validation
        self.settings_types = {
            'theme': str,
            'search_shortcuts': bool,
            'opacity': float,
            'max_window_width': float,
            'max_window_height': float,
            'font_family': str,
            'font_color': str,
            'font_size': int,
            'adapting_window_to_list': bool,
            'position_priority': str
        }
        
        # Default settings with type-safe values
        self.default_settings: Dict[str, Any] = {
            'theme': 'light', 
            'search_shortcuts': True, 
            'opacity': 0.7,
            'max_window_width': 0.25, 
            'max_window_height': 0.5,
            'font_family': 'Times New Roman', 
            'font_color': '#000000',
            'font_size': 8, 
            'adapting_window_to_list': True,
            'position_priority': 'top-right'
        }
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        
        # Load settings, ensuring type safety
        self.settings = self._load_settings()

    def _validate_setting(self, key: str, value: Any) -> bool:
        """
        Validate a setting against its expected type and constraints.

        Args:
            key (str): Setting key to validate
            value (Any): Value to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Type checking
        if not isinstance(value, self.settings_types.get(key, type(value))):
            logger.warning(f"Type mismatch for {key}: expected {self.settings_types.get(key)}")
            return False

        # Additional specific validations
        if key == 'opacity':
            return 0.1 <= value <= 1.0
        elif key == 'font_size':
            return value > 0
        elif key in ['max_window_width', 'max_window_height']:
            return 0.1 < value <= 1.0
        elif key == 'theme':
            return value in ['light', 'dark']
        elif key == 'position_priority':
            return value in ['top-right', 'top-left', 'bottom-right', 'bottom-left']
        elif key == 'font_color':
            return isinstance(value, str) and value.startswith('#') and len(value) == 7
        
        return True

    def _load_settings(self) -> Dict[str, Any]:
        """
        Load settings with robust error handling and type validation.

        Returns:
            Dict[str, Any]: Validated settings or default settings
        """
        try:
            # Try loading from primary config
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as file:
                    loaded_settings = json.load(file)
                    
                    # Validate and merge loaded settings
                    validated_settings = self.default_settings.copy()
                    for key, value in loaded_settings.items():
                        if key in self.default_settings and self._validate_setting(key, value):
                            validated_settings[key] = value
                        else:
                            logger.warning(f"Invalid setting: {key} = {value}")
                    
                    logger.info("Settings loaded successfully")
                    return validated_settings
            
            # If no settings file exists, use defaults
            logger.warning("No settings file found. Using defaults.")
            self.save_settings()
            return self.default_settings.copy()
        
        except json.JSONDecodeError:
            # Attempt to restore from backup
            logger.error("JSON decode error. Attempting to restore from backup.")
            try:
                if os.path.exists(BACKUP_CONFIG_PATH):
                    shutil.copy(BACKUP_CONFIG_PATH, self.settings_file)
                    return self._load_settings()
            except Exception as backup_error:
                logger.error(f"Backup restoration failed: {backup_error}")
        
        except Exception as e:
            logger.error(f"Unexpected error loading settings: {e}")
        
        # Fallback to defaults if all else fails
        return self.default_settings.copy()

    def save_settings(self) -> None:
        """
        Save settings with backup and error handling.
        """
        try:
            # Create backup of existing settings
            if os.path.exists(self.settings_file):
                shutil.copy(self.settings_file, BACKUP_CONFIG_PATH)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            # Save settings
            with open(self.settings_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
            
            logger.info("Settings saved successfully")
        
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get_setting(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Retrieve a specific setting with optional default.

        Args:
            key (str): Setting key to retrieve
            default (Optional[Any]): Default value if key not found

        Returns:
            Any: Setting value or provided default
        """
        return self.settings.get(key, default or self.default_settings.get(key))

    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a specific setting with validation.

        Args:
            key (str): Setting key to update
            value (Any): New value for the setting

        Returns:
            bool: True if setting was successfully updated, False otherwise
        """
        if key not in self.default_settings:
            logger.warning(f"Unknown setting key: {key}")
            return False

        if not self._validate_setting(key, value):
            logger.warning(f"Invalid value for {key}: {value}")
            return False

        self.settings[key] = value
        self.save_settings()
        return True

    def reset_to_defaults(self) -> None:
        """
        Reset all settings to their default values.
        """
        self.settings = self.default_settings.copy()
        self.save_settings()
        logger.info("Settings reset to defaults")