import win32gui
import win32process
import subprocess
import time
import psutil
import platform
import difflib
import os
import json
import logging

# Get a logger for this module
logger = logging.getLogger(__name__)

class ShortcutManager:
    """Manages application shortcuts with caching and optimized matching.""" 
   
    def __init__(self, map_path, db_path, cache_duration=1):
        """
        Initialize the ShortcutManager with paths and cache settings.

        Args:
            map_path (str): Path to the application mapping text file.
            db_path (str): Path to the local shortcut JSON database.
            cache_duration (int): Cache duration in seconds (default: 60).
        """
        self.map_path = map_path
        self.db_path = db_path
        self.cache_duration = cache_duration
        self.app_map_cache = None
        self.app_names_sorted = None
        self.shortcut_cache = None
        self.last_load_time = 0

    def load_app_map(self):
        """Load and cache the application map from the text file."""
        current_time = time.time()
        if self.app_map_cache is None or (current_time - self.last_load_time) > self.cache_duration:
            try:
                with open(self.map_path, "r") as file:
                    app_map = {}
                    for line in file:
                        if ":" in line:
                            parts = line.strip().split(": ", 1)
                            if len(parts) == 2:
                                app_name, version = parts
                                app_name = app_name.strip('"')  # Remove double quotes
                                app_map[app_name] = {"name": app_name, "version": version}
                    self.app_map_cache = app_map
                    self.app_names_sorted = sorted(app_map.keys(), key=len, reverse=True)
                    self.last_load_time = time.time()
                    logger.info("App map loaded and cached")
            except FileNotFoundError:
                logger.error(f"App map file not found: {self.map_path}")
                self.app_map_cache = {}
                self.app_names_sorted = []
            except Exception as e:
                logger.error(f"Error loading app map: {e}")
                self.app_map_cache = {}
                self.app_names_sorted = []
        return self.app_map_cache

    def load_shortcut_cache(self):
        """Load and cache the shortcut database from the JSON file."""
        current_time = time.time()
        if self.shortcut_cache is None or (current_time - self.last_load_time) > self.cache_duration:
            try:
                with open(self.db_path, "r") as f:
                    self.shortcut_cache = json.load(f)
                self.last_load_time = time.time()
                logger.info("Shortcut database loaded and cached")
            except FileNotFoundError:
                logger.error(f"Shortcut database file not found: {self.db_path}")
                self.shortcut_cache = {}
            except json.JSONDecodeError:
                logger.error("Error decoding JSON from shortcut database")
                self.shortcut_cache = {}
            except Exception as e:
                logger.error(f"Unexpected error loading shortcut database: {e}")
                self.shortcut_cache = {}
        return self.shortcut_cache
    
    def find_best_match(self, window_title):
        """
        Find the best matching application name based on the window title.
        
        Args:
            window_title (str): The title of the active window.
            
        Returns:
            str or None: The standardized application name or None if no match.
        """
        self.load_app_map()
        if not window_title:
            return None
        
        # Attempt exact match based on phrases in the window title
        window_title_lower = window_title.lower()
        for app_name in self.app_names_sorted:
            if app_name.lower() in window_title_lower:
                return self.app_map_cache[app_name].get("name", app_name)
        
        # Extract the last part of the window title after " - " for better matching
        if " - " in window_title:
            window_title = window_title.split(" - ")[-1].strip()

        window_title_lower = window_title.lower()

        # If no exact match, use difflib to find the closest partial match
        close_matches = difflib.get_close_matches(window_title_lower, self.app_map_cache.keys(), n=1, cutoff=0.5)
        if close_matches:
            best_match = close_matches[0]
            return self.app_map_cache[best_match].get("name", best_match)
        return None
    
    def get_shortcuts(self, window_title):
        """
        Retrieve shortcuts for the active window.
        
        Args:
            window_title (str): The title of the active window.
            
        Returns:
            dict: Shortcuts for the matched application or empty dict if none.
        """
        app_name = self.find_best_match(window_title)
        
        if app_name:
            self.load_shortcut_cache()  # Ensure the cache is loaded
            logger.info(f"Available apps in shortcut_cache: {list(self.shortcut_cache.keys())}")
            
            if app_name in self.shortcut_cache:
                shortcuts = self.shortcut_cache[app_name]
                return shortcuts
            else:
                logger.info(f"No shortcuts for: '{app_name}' in the cache")
                return {}
        else:
            logger.info(f"No app matched for: '{window_title}'")
            return {}
                
def get_active_window_info():
    """
    Retrieves the title and process name of the currently active window.

    Returns:
    tuple: (window_title, process_name) or (None, None) if no active window is found.
    """
    try:
        # Cross-platform active window title
        if platform.system() == "Windows":
            # Get the active window handle
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            
            # Get the PID of the active window
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name()

        elif platform.system() == "Linux":
            # Use xdotool to get the active window title and PID
            window_title = subprocess.check_output(
                ["xdotool", "getwindowfocus", "getwindowname"], text=True
            ).strip()
            pid = subprocess.check_output(
                ["xdotool", "getwindowfocus", "getwindowpid"], text=True
            ).strip()
            process = psutil.Process(int(pid))
            process_name = process.name()

        elif platform.system() == "Darwin":
            # Use AppleScript to get active application
            window_title = subprocess.check_output(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of (process 1 where frontmost is true)'
                ],
                text=True,
            ).strip()
            process_name = window_title  # For macOS, title matches app name

        else:
            raise NotImplementedError(f"Unsupported platform: {platform.system()}")

        return window_title, process_name
    except Exception as e:
        logger.info(f"Error getting active window info: {e}")
        return None, None

def is_my_app_active(active_window_title):
    """
    Check if the current application is active based on window title keywords.
    
    Args:
        active_window_title (str): The title of the active window.
        
    Returns:
        bool: True if the app is active, False otherwise.
    """
    if not active_window_title:
        return False
    title_lower = active_window_title.lower()
    app_keywords = ["hotkey helper", "hotkey_manager"]
    return any(keyword in title_lower for keyword in app_keywords)