import subprocess
import time
import psutil
import platform
import difflib
import json
import logging
import re

from threading import Lock

# Get a logger for this module
logger = logging.getLogger(__name__)

# Platform-specific imports
if platform.system() == "Windows":
    try:
        import win32gui
        import win32process
    except ImportError:
        logger.warning("win32gui and win32process modules not available. Windows functionality will be limited.")

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
        self.cache_lock = Lock()

    def load_app_map(self):
        """Load and cache the application map from the text file."""
        current_time = time.time()
        # Reload the app map if cache is empty or expired
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
                logger.error("App map file not found: %s", self.map_path)
                self.app_map_cache = {}
                self.app_names_sorted = []
            except Exception as e:
                logger.error("Error loading app map: %s", e)
                self.app_map_cache = {}
                self.app_names_sorted = []
        return self.app_map_cache

    def load_shortcut_cache(self):
        """Load and cache the shortcut database from the JSON file."""
        # Reload the shortcut cache if empty or expired
        with self.cache_lock:
            if self.shortcut_cache is None or (time.time() - self.last_load_time) > self.cache_duration:
                try:
                    with open(self.db_path, "r") as f:
                        self.shortcut_cache = json.load(f)
                    self.last_load_time = time.time()
                    logger.info("Shortcut database loaded and cached")
                except FileNotFoundError:
                    logger.error("Shortcut database file not found: %s", self.db_path)
                    self.shortcut_cache = {}
                except json.JSONDecodeError:
                    logger.error("Error decoding JSON from shortcut database")
                    self.shortcut_cache = {}
                except Exception as e:
                    logger.error("Unexpected error loading shortcut database: %s", e)
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
        # Load the app map if not already loaded
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
        # If no app name is found, return empty dict
        if app_name:
            self.load_shortcut_cache()  # Ensure the cache is loaded
            logger.info("Available apps in shortcut_cache: %s", list(self.shortcut_cache.keys()))

            # First try exact match
            if app_name in self.shortcut_cache:
                logger.info("Exact match found for: '%s'", app_name)
                shortcuts = self.shortcut_cache[app_name]
                return shortcuts

            # Normalize app name for comparison
            normalized_input = normalize_app_name(app_name)
            available_apps = list(self.shortcut_cache.keys())

            # First pass: Look for strict matches (cutoff 0.9) with normalized names
            normalized_apps = {app: normalize_app_name(app) for app in available_apps}
            close_matches = difflib.get_close_matches(
                normalized_input,
                list(normalized_apps.values()),
                n=1,
                cutoff=0.9
            )

            if close_matches:
                matched_normalized = close_matches[0]
                # Find the original app name that corresponds to this normalized match
                try:
                    matched_app = next(app for app, norm in normalized_apps.items() if norm == matched_normalized)
                    similarity = difflib.SequenceMatcher(None, normalized_input, matched_normalized).ratio()
                    logger.info("Strict fuzzy matched '%s' to '%s' with similarity %.2f", app_name, matched_app, similarity)
                    shortcuts = self.shortcut_cache[matched_app]
                    return shortcuts
                except StopIteration:
                    logger.warning("No matching app found for normalized name '%s'", matched_normalized)
                    # Continue to the next matching strategy

            # Second pass: Look for partial matches (specifically for cases like "Chrome" -> "Google Chrome")
            best_match = None
            best_score = 0
            for app in available_apps:
                normalized_app = normalize_app_name(app)
                # Check if the input is a significant substring of the app name
                if normalized_input in normalized_app:
                    # Calculate a custom score based on length ratio and position
                    score = len(normalized_input) / len(normalized_app)
                    if normalized_app.startswith(normalized_input):
                        score += 0.2  # Bonus for starting match
                    if score > best_score and score >= 0.5:  # Require at least 50% length match
                        best_score = score
                        best_match = app

            # If a partial match is found, use it
            if best_match:
                logger.info("Partial match found: '%s' matched to '%s' with score %.2f", app_name, best_match, best_score)
                shortcuts = self.shortcut_cache[best_match]
                return shortcuts

            # If no match is found, return empty dict
            logger.info("No exact or close matches for: '%s' in the cache", app_name)
            return {}

def normalize_app_name(name):
        """Normalize application names for better matching by removing spaces and converting to lowercase"""
        return re.sub(r'\s+', '', name.lower())

def get_active_window_info():
    """
    Retrieves the title and process name of the currently active window.

    Returns:
    tuple: (window_title, process_name) or (None, None) if no active window is found.
    """
    # Cross-platform active window title retrieval
    try:
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
            # Use absolute paths to prevent security issues with partial paths
            xdotool_path = "/usr/bin/xdotool"  # Standard location on most Linux systems
            window_title = subprocess.check_output(
                [xdotool_path, "getwindowfocus", "getwindowname"], text=True
            ).strip()
            pid = subprocess.check_output(
                [xdotool_path, "getwindowfocus", "getwindowpid"], text=True
            ).strip()
            process = psutil.Process(int(pid))
            process_name = process.name()

        elif platform.system() == "Darwin":
            # Use AppleScript to get active application
            # Use absolute paths to prevent security issues with partial paths
            osascript_path = "/usr/bin/osascript"  # Standard location on macOS
            window_title = subprocess.check_output(
                [
                    osascript_path,
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
        logger.info("Error getting active window info: %s", e)
        return None, None

def is_my_app_active(active_window_title):
    """
    Check if the current application is active based on window title keywords.

    Args:
        active_window_title (str): The title of the active window.

    Returns:
        bool: True if the app is active, False otherwise.
    """
    # Check for specific keywords in the window title
    if not active_window_title:
        return False
    title_lower = active_window_title.lower()
    app_keywords = ["hotkey helper", "hotkey_manager"]
    return any(keyword in title_lower for keyword in app_keywords)
