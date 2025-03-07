import os
import time
import json
import shutil
import logging
import requests
import firebase_admin

from firebase_admin import credentials, firestore

# Get a logger for this module
logger = logging.getLogger(__name__)

# Define local storage paths for shortcut data and update log files
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "data/shortcut_db.json")
UPDATE_LOG_PATH = os.path.join(os.path.dirname(__file__), "data/update_log.json")  # Converted to relative path
TEMP_DB_PATH = os.path.join(os.path.dirname(__file__), "data/temp_shortcut_db.json")

# Relative path for Firebase credentials
CRED_PATH = os.path.join(os.path.dirname(__file__), "data/hotkey-helper-firebase-adminsdk-qhk5p-a146688617.json")

# Cache settings for Firestore reads
CACHE_DURATION = 30  # Cache duration in seconds, adjust as needed for development.

cache = {
    "total_shortcuts": None,
    "last_updated": 0
}

# Initialize Firebase using relative path for the credentials
try:
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    logger.info(f"Error initializing Firebase: {e}")
    db = None

def load_latest_version():
    version_file = "data/latest_version.txt"
    try:
        with open(version_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0"  # Default if file is missing
    except IOError as e:
        logger.error(f"Error reading {version_file}: {e}")
        return "1.0.0"
    
def check_for_updates(current_version):
    try:
        url = "https://raw.githubusercontent.com/yourusername/yourrepo/main/latest_version.txt"
        response = requests.get(url)
        latest_version = response.text.strip()
        if latest_version > current_version:
            return True
        else:
            return False
    except Exception:
        logger.error("Couldn’t check for updates.")
        
# Function to get the total number of shortcuts
def get_total_shortcuts():
    """
    Get the total number of shortcuts from Firestore.

    Returns:
    int: The total number of shortcuts, or local database count,
    if an error occurs so it would not start the update.
    """
    if db is None:
        return get_local_shortcuts()

    current_time = time.time()

    # Use cached value if it's recent enough.
    if cache["total_shortcuts"] is not None and (current_time - cache["last_updated"]) < CACHE_DURATION:
        return cache["total_shortcuts"]

    try:
        # Fetching the data from Firestore
        counter_ref = db.collection('hotkeys_metadata').document('counters')
        counter_doc = counter_ref.get()
        
        # If the document exists, retrieve the number of total shortcuts.
        if counter_doc.exists:
            total_shortcuts = counter_doc.to_dict().get('total_shortcuts', 0)
            # Update the cache with the new value.
            cache["total_shortcuts"] = total_shortcuts
            cache["last_updated"] = current_time
            return total_shortcuts
        else:
            return 0
    except Exception as e:
        logger.error(f"Error fetching counter document: {e}")
        return 0

# Function to get the stored count of shortcuts from a local file
def get_local_shortcuts():
    """
    Get the total number of shortcuts from the local update log file.

    Returns:
    int: The number of local shortcuts, or 0 if an error occurs.
    """
    try:
        # Check if the file exists before trying to open it
        if not os.path.exists(UPDATE_LOG_PATH):
            return 0

        # Open and read the local update log file
        try:
            with open(UPDATE_LOG_PATH, 'r') as update_log_file:
                update_log = json.load(update_log_file)
        except Exception as e:
            # Handle the case where the JSON file is not properly formatted
            logger.error("Error reading update log file: Invalid JSON format.")
        
        # Retrieve the stored count, defaulting to 0 if the key is missing
        stored_count = update_log.get('processed_shortcuts', 0)
        return stored_count
    
    except Exception as e:
        # Handle the case where the JSON file is not properly formatted
        logger.error("Error reading update log file: Invalid JSON format.")
        return 0
    except Exception as e:
        # General error handler for any other unforeseen issues
        logger.error(f"Unexpected error reading update log file: {e}")
        return 0

# Function to determine if an update is needed
def check_for_db_updates():
    """
    Check if a database update is needed by comparing local and remote shortcut counts.

    Returns:
    bool: True if an update is needed, False otherwise.
    """
    stored_count = get_local_shortcuts()
    current_count = get_total_shortcuts()

    # Determine if the local count matches the current count in the database
    if stored_count == current_count:
        return False
    else:
        return True
    
def get_all_documents_recursive(collection_ref):
    """
    Recursively fetch all documents and subcollections from a Firestore collection.

    Parameters:
    collection_ref (CollectionReference): A reference to the Firestore collection.

    Returns:
    dict: A dictionary containing document data and subcollections.
    """
    data = {}
    try:
        docs = collection_ref.stream()
        for doc in docs:
            sub_data = {}
            subcollections = doc.reference.collections()
            for subcollection in subcollections:
                sub_data[subcollection.id] = get_all_documents_recursive(subcollection)
            # Unified format: Application name as the collection, shortcut name as the document
            data[doc.id] = {
                "fields": doc.to_dict(),
                "subcollections": sub_data
            }
    except Exception as e:
        logger.error(f"Error fetching documents in collection {collection_ref.id}: {e}")
    return data

def download_all_collections(callback=None, cancel=None):
    """
    Download all Firestore collections, updating local storage with the latest data.

    Parameters:
    callback (callable, optional): A function to call with progress updates.
    cancel (callable, optional): A function to call to determine if the process should be canceled.

    Returns:
    bool: True if the download completed successfully, False if it was canceled or an error occurred.
    """
    try:
        # Copy existing data from local to temp if it exists
        if os.path.exists(LOCAL_DB_PATH):
            shutil.copy(LOCAL_DB_PATH, TEMP_DB_PATH)
            with open(TEMP_DB_PATH, 'r') as temp_json_file:
                all_data = json.load(temp_json_file)
        else:
            all_data = {}

        collections = db.collections()
        total_shortcuts = get_total_shortcuts()
        processed_shortcuts = 0

        # Start the download process, updating only new or changed data
        for collection in collections:
            # Check if a cancellation request has been made
            if cancel and cancel():
                log_update("cancelled", processed_shortcuts)
                return False  # Indicate that the process was canceled

            collection_data = get_all_documents_recursive(collection)

            # Adjusting structure to match JS format
            if collection.id not in all_data or all_data[collection.id] != collection_data:
                all_data[collection.id] = collection_data

            # Update the progress for each document retrieved
            for document in collection_data:
                processed_shortcuts += 1
                if callback:
                    progress = (processed_shortcuts / total_shortcuts) * 100
                    callback(progress)

                # Check for cancellation during processing of each document
                if cancel and cancel():
                    log_update("cancelled", processed_shortcuts)
                    return False

        # Write updated data to the temporary JSON file
        with open(TEMP_DB_PATH, 'w') as temp_json_file:
            json.dump(all_data, temp_json_file, indent=4)

        # Move the temporary file to the final location
        shutil.move(TEMP_DB_PATH, LOCAL_DB_PATH)
        log_update("completed", processed_shortcuts)
        return True
    except Exception as e:
        logger.error(f"Error while downloading Firestore data: {e}")
        log_update("failed", processed_shortcuts)
        return False

def log_update(status, processed_shortcuts):
    """
    Log the update status and processed shortcuts to a JSON file.

    Parameters:
    status (str): The status of the update (e.g., "completed", "cancelled", "failed").
    processed_shortcuts (int): The number of shortcuts processed during the update.
    """
    log_entry = {
        "status": status,
        "processed_shortcuts": processed_shortcuts - 1,  # Subtract 1 to account for the final increment
    }
    try:
        # Write log entry to the file, overriding existing content
        with open(UPDATE_LOG_PATH, 'w') as log_file:
            json.dump(log_entry, log_file, indent=4)
        logger.error(f"Update log saved to {UPDATE_LOG_PATH}")
    except Exception as e:
        logger.error(f"Failed to write update log: {e}")
