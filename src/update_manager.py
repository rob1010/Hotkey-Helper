import os
import json
import logging
import requests

# Get a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Define local storage paths for shortcut data and update log files
BASE_DIR = os.path.dirname(__file__)
LOCAL_DB_PATH = os.path.join(BASE_DIR, "data/local_shortcut_db.json")
TEMP_DB_PATH = os.path.join(BASE_DIR, "data/temp_shortcut_db.json")
UPDATE_LOG_PATH = os.path.join(BASE_DIR, "data/update_log.json")

def load_api_key():
    """Load the Firestore API key from a local file."""
    # Define the path to the API key file
    api_file = "data/api_key.txt"
    try:
        with open(api_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error("API key file not found: %s", api_file)
    return None

# Define Firestore project details        
PROJECT_ID = "hotkey-helper"
API_KEY = load_api_key()
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def fetch_hotkeys():
    """
    Fetch the 'hotkeys' collection from Firestore, transform it, and save to local storage.

    Args:
        cancel (callable, optional): A function to call to determine if the process should be canceled.

    Returns:
        bool: True if completed successfully, False if canceled or an error occurred.
    """
    # Fetch data from Firestore with error handling
    try:
        hotkeys_response = requests.get(f"{FIRESTORE_URL}/hotkeys/?key={API_KEY}")
        hotkeys_response.raise_for_status()  # Raise an exception for HTTP errors
        db_temp = hotkeys_response.json()
    except requests.exceptions.RequestException:
        logger.error("Error fetching hotkeys from Firestore")
        return False
    except json.JSONDecodeError as e:
        logger.error("Error decoding JSON response: %s", e)
        return False

    # Transform the data from Firestore format to a simplified structure
    db = transform_firestore_data(db_temp)

    # Write the transformed data to a temporary file
    try:
        with open(TEMP_DB_PATH, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logger.error("Error writing to temporary file %s: %s", TEMP_DB_PATH, e)
        return False

    # Read the temporary file to verify it was written correctly
    try:
        with open(TEMP_DB_PATH, "r") as f:
            json.load(f)  # Just verify it can be loaded
    except Exception as e:
        logger.error("Error reading temporary file %s: %s", TEMP_DB_PATH, e)
        return False

    # Update update log with the number of processed shortcuts
    db_lenght = get_total_shortcuts_count()
    log_update(db_lenght)
    return True

def transform_firestore_data(firestore_data):
    """
    Transform Firestore data into a simplified structure.

    Args:
        firestore_data (dict): The Firestore response data.

    Returns:
        dict: The transformed data in a simplified structure.
    """
    simplified_data = {}

    # Iterate through each document in the Firestore response
    for doc in firestore_data.get("documents", []):
        # Extract the document name (e.g., "Adobe Acrobat" from the path)
        doc_name = doc["name"].split("/")[-1]

        # Initialize the structure for this document
        simplified_data[doc_name] = {}

        # Process the fields (e.g., "Windows", "macOS")
        for os_key, os_value in doc["fields"].items():
            simplified_data[doc_name][os_key] = {}

            # Extract the map of hotkeys
            hotkeys_map = os_value.get("mapValue", {}).get("fields", {})

            # Process each hotkey
            for hotkey, hotkey_details in hotkeys_map.items():
                details = hotkey_details.get("mapValue", {}).get("fields", {})
                simplified_hotkey = {
                    "Description": details.get("Description", {}).get("stringValue", ""),
                    "Category": details.get("Category", {}).get("stringValue", "")
                }
                simplified_data[doc_name][os_key][hotkey] = simplified_hotkey

    return simplified_data

def get_total_shortcuts_count():
    """
    Get the total number of shortcuts from Firestore's 'hotkeys_metadata/counters'
    document (reading the 'total_shortcuts' field).

    Returns:
        int: Total number of shortcuts, or 0 if an error occurs.
    """
    # Fetch data from Firestore with error handling
    try:
        url = f"{FIRESTORE_URL}/hotkeys_metadata/counters?key={API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            total = data.get("fields", {}).get("total_shortcuts", {}).get("integerValue")
            if total is not None:
                return int(total)
            logger.error("Total shortcuts field not found in the response.")
        else:
            logger.error("Error getting total shortcuts count: %s %s", response.status_code, response.text)
        return 0
    except requests.exceptions.RequestException:
        logger.error("Error getting total shortcuts count: %s %s", response.status_code, response.text)
        return 0
    except Exception as e:
        logger.error("Exception in get_total_shortcuts_count: %s", e)
        return 0

def get_local_shortcuts_count():
    """
    Get the total number of shortcuts from the local update log file.

    Returns:
    int: The number of local shortcuts, or 0 if an error occurs.
    """
    # Check if the file exists before trying to open it
    try:
        if not os.path.exists(UPDATE_LOG_PATH):
            return 0

        # Open and read the local update log file
        try:
            with open(UPDATE_LOG_PATH, 'r') as update_log_file:
                update_log = json.load(update_log_file)
        except json.JSONDecodeError:
            logger.error("Error reading update log file: Invalid JSON format.")
            return 0

        # Retrieve the stored count, defaulting to 0 if the key is missing
        stored_count = update_log.get('processed_shortcuts', 0)
        return stored_count
    except Exception as e:
        logger.error("Unexpected error reading update log file: %s", e)
        return 0

# Function to determine if an update is needed
def check_for_db_updates():
    """
    Check if a database update is needed by comparing local and remote shortcut counts.

    Returns:
    bool: True if an update is needed, False otherwise.
    """
    # Get the stored and current shortcut counts
    stored_count = get_local_shortcuts_count()
    current_count = get_total_shortcuts_count()

    # Determine if the local count matches the current count in the database
    if stored_count == current_count:
        return False
    return True


def log_update(processed_shortcuts):
    """
    Log the update status and processed shortcuts to a JSON file.

    Parameters:
    status (str): The status of the update (e.g., "completed", "cancelled", "failed").
    processed_shortcuts (int): The number of shortcuts processed during the update.
    """
    # Create a log entry with the update status and processed shortcuts
    log_entry = {
        "processed_shortcuts": processed_shortcuts,  # Subtract 1 to account for the final increment
    }
    try:
        # Write log entry to the file, overriding existing content
        with open(UPDATE_LOG_PATH, 'w') as log_file:
            json.dump(log_entry, log_file, indent=4)
        logger.error("Update log saved to %s", UPDATE_LOG_PATH)
    except Exception as e:
        logger.error("Failed to write update log: %s", e)

def load_latest_version():
    """Load the latest version number from a local file."""
    version_file = "data/latest_version.txt"
    try:
        with open(version_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0"
    except IOError as e:
        logger.error("Error reading %s: %s", version_file, e)
        return "1.0.0"

def check_for_application_updates(current_version):
    """
    Check for application updates by comparing the current version with the latest version.

    Args:
        current_version (str): The current version of the application.

    Returns:
        bool: True if an update is available, False otherwise.
    """
    # Fetch the latest version number from the repository
    try:
        url = "https://raw.githubusercontent.com/rob1010/Hotkey-Helper/main/latest_version.txt"
        response = requests.get(url)
        latest_version = response.text.strip()
        if latest_version > current_version:
            print(f"New version available: {latest_version}\n and current version: {current_version}")
            return True
        return False
    except Exception:
        logger.error("Couldn't check for updates.")
        return False
