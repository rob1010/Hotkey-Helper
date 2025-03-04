import win32gui
import win32process
import subprocess
import time
import psutil
import platform
import difflib
import os
import json
# Add error handling for loading the local map !!!
# Add threading to load the local map in the background !!!
# Add event driven design to update the shortcuts when the active window changes !!!
# Add logging and diagnostics for debugging !!!
# Add support for different platforms (Windows, Linux, macOS) !!!

LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "data/local_shortcut_db.json")

class ShortcutManager:
    def __init__(self):
        self.shortcut_cache = None
        self.last_load_time = 0
        self.cache_duration = 60  # seconds
        
    def load_local_shortcuts(self, window_title):
        current_time = time.time()
        if (self.shortcut_cache is None or 
            (current_time - self.last_load_time) > self.cache_duration):
            if not os.path.exists(LOCAL_DB_PATH):
                print(f"Local shortcut file not found: {LOCAL_DB_PATH}")
                return {}
            with open(LOCAL_DB_PATH, "r") as f:
                self.shortcut_cache = json.load(f)
            self.last_load_time = current_time

        window_title_lower = window_title.lower()
        for app_name in self.shortcut_cache.keys():
            if app_name.lower() in window_title_lower:
                print(f"Shortcuts found for: '{app_name}'")
                return self.shortcut_cache.get(app_name, {})
        print(f"No shortcuts for: '{window_title}'")
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
        print(f"Error getting active window info: {e}")
        return None, None

def is_my_app_active(active_window_title):
    """
    Determines if the current application is the active window by checking keywords in the title.

    Parameters:
    active_window_title (str): The title of the active window.

    Returns:
    bool: True if the active window matches the application name, otherwise False.
    """
    if not active_window_title:
        return False

    # Convert the window title to lowercase for case-insensitive comparison
    title_lower = active_window_title.lower()

    # List of keywords to check for
    app_keywords = ["hotkey helper", "hotkey_manager"]

    # Check if any keyword is present in the title
    return any(keyword in title_lower for keyword in app_keywords)

def find_best_match(app_map, window_title):
    """
    Finds the best match for an application based on the active window title.

    Parameters:
    app_map (dict): Dictionary of application names and their details.
    window_title (str): The title of the active window.
    verbose (bool): If True, prints debugging output. Default is True.

    Returns:
    tuple: (Standardized application name, version) or (None, None) if no match is found.
    """
    # Extract the last part of the window title after " - " for better matching
    if " - " in window_title:
        window_title = window_title.split(" - ")[-1].strip()

    window_title_lower = window_title.lower()


    # Attempt exact match based on phrases in the window title
    for app_name, app_info in app_map.items():
        if app_name.lower() in window_title_lower:
            return app_info.get("name", app_name)

    # If no exact match, use difflib to find the closest partial match
    close_matches = difflib.get_close_matches(window_title_lower, app_map.keys(), n=1, cutoff=0.5)
    if close_matches:
        best_match = close_matches[0]
        return app_map[best_match].get("name", best_match)

    return None

def load_local_map(file_path):
    """
    Loads a local application mapping file and parses it into a dictionary.
    
    Parameters:
    file_path (str): Path to the application mapping text file.
    
    Returns:
    dict: Dictionary mapping application names to their standardized name and version.
    """
    app_map = {}
    
    # Read and parse the mapping file line by line
    with open(file_path, "r") as file:
        for line in file:
            # Each line should contain "app_name: version"
            if ":" in line:
                app_name, version = line.strip().split(": ")
                app_map[app_name] = {"name": app_name, "version": version}
    
    return app_map