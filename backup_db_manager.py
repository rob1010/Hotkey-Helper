import json
import difflib
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Define local storage path for shortcut data file
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "local_shortcut_db.json")
UPDATE_LOG_PATH = "update_log.json"  # Path to store last sync timestamp

def find_best_match(app_map, window_title, verbose=False):
    """
    Finds the best match for an application based on the active window title.

    Parameters:
    app_map (dict): Dictionary of application names and their details.
    window_title (str): The title of the active window.
    verbose (bool): If True, prints debugging output. Default is True.

    Returns:
    tuple: (Standardized application name, version) or (None, None) if no match is found.
    """
    version = "latest"  # Default version if not specified

    # Extract the last part of the window title after " - " for better matching
    if " - " in window_title:
        window_title = window_title.split(" - ")[-1].strip()

    window_title_lower = window_title.lower()

    if verbose:
        print(f"Searching for match for window title: '{window_title}'")

    # Attempt exact match based on phrases in the window title
    for app_name, app_info in app_map.items():
        if app_name.lower() in window_title_lower:
            if verbose:
                print(f"Exact match found: '{app_name}'")
            return app_info.get("name", app_name), app_info.get("version", version)

    # If no exact match, use difflib to find the closest partial match
    close_matches = difflib.get_close_matches(window_title_lower, app_map.keys(), n=1, cutoff=0.5)
    if close_matches:
        best_match = close_matches[0]
        if verbose:
            print(f"Best close match found: '{best_match}'")
        return app_map[best_match].get("name", best_match), app_map[best_match].get("version", version)

    if verbose:
        print(f"No matching application found for window title: '{window_title}' with app map keys: {list(app_map.keys())}")
    return None, None

def load_local_shortcuts(window_title):
    """
    Loads shortcuts from local storage based on the active window title.

    Parameters:
    window_title (str): The title of the active window.

    Returns:
    dict: Dictionary of shortcuts for the application in the window title.
    """
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"Local shortcut file not found: {LOCAL_DB_PATH}")
        return {}

    # Load the local shortcuts data
    with open(LOCAL_DB_PATH, "r") as f:
        shortcut_data = json.load(f)

    # Use find_best_match to identify the best application match
    app_name, _ = find_best_match(shortcut_data, window_title)

    if app_name:
        # If a match is found, return the corresponding shortcuts
        print(f"Shortcuts found for application: '{app_name}'")
        return shortcut_data.get(app_name, {})
    
    # No match found
    print(f"No shortcuts found for the window title: '{window_title}'")
    return {}

class FirestoreDataFetcher:
    def __init__(self, credentials_path):
        """
        Initializes the FirestoreDataFetcher with a Firestore client using Firebase Admin SDK.

        Args:
            credentials_path: Path to the Firebase credentials JSON file.
        """
        # Initialize Firebase Admin SDK with credentials file
        cred = credentials.Certificate(credentials_path)
        try:
            firebase_admin.initialize_app(cred)
            print("Firebase successfully initialized.")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")

        # Define Firestore client for database interactions
        self.db = firestore.client()

    def fetch_data_recursively(self, ref, current_depth=0, max_depth=5):
        """
        Fetches data from Firestore reference recursively up to a specified depth.
        
        Args:
            ref: Firestore reference (could be a collection or document reference).
            current_depth: Current depth of recursion.
            max_depth: Maximum depth allowed for recursion.
        
        Returns:
            A dictionary representing the fetched data.
        """
        if current_depth > max_depth:
            return {}  # Stop recursion if max depth is reached

        all_data = {}
        try:
            if isinstance(ref, firestore.CollectionReference):
                # If the reference is a collection, iterate over its documents
                print(f"Attempting to get documents from collection: {ref.id}")
                documents = ref.stream()
                for doc in documents:
                    if not doc.exists:
                        print(f"Document {doc.id} does not exist or is empty.")
                    else:
                        print(f"Fetching data for document: {doc.id}, exists: {doc.exists}")
                        all_data[doc.id] = self.fetch_data_recursively(doc.reference, current_depth + 1, max_depth)
            elif isinstance(ref, firestore.DocumentReference):
                # If the reference is a document, get its data and any subcollections
                doc = ref.get()
                if doc.exists:
                    doc_data = doc.to_dict() or {}
                    doc_data["id"] = doc.id  # Ensure each document has its ID
                    print(f"Fetched document data: {doc_data}")
                    subcollections = list(ref.collections())
                    for subcollection in subcollections:
                        print(f"Fetching subcollection: {subcollection.id} for document: {doc.id}")
                        subcollection_data = self.fetch_data_recursively(subcollection, current_depth + 1, max_depth)
                        if subcollection_data:
                            doc_data[subcollection.id] = subcollection_data
                    all_data = doc_data
                else:
                    print(f"Document {ref.id} does not exist.")
        except Exception as e:
            print(f"Error fetching data from Firestore reference {ref.id if hasattr(ref, 'id') else 'unknown'}: {e}")

        return all_data

    def fetch_data(self):
        """
        Fetches data from the 'hotkeys' collection.
        Saves the fetched data to a local JSON file.

        Returns:
            A dictionary representing the fetched data.
        """
        all_data = {}

        try:
            # Start recursion from the top-level 'hotkeys' collection
            hotkeys_collection = self.db.collection('hotkeys')
            all_data = self.fetch_data_recursively(hotkeys_collection)
        except Exception as e:
            print("Error fetching data from Firestore.")
            print(f"Error: {e}")

        # Save the fetched data to a local file
        print(f"Final data to be saved: {all_data}")
        with open(LOCAL_DB_PATH, 'w') as f:
            json.dump(all_data, f, indent=4)

        return all_data

    def list_top_level_collections(self):
        """
        Lists all top-level collections in Firestore to verify if the 'hotkeys' collection exists.
        """
        try:
            collections = list(self.db.collections())
            print("Top-level collections:")
            for collection in collections:
                print(f" - {collection.id}")
        except Exception as e:
            print(f"Error listing top-level collections: {e}")

    def run(self):
        """
        Runs the process of fetching data from Firestore and saving it locally.
        
        This method retrieves all data from the 'hotkeys' collection
        and saves the data into a local file for later use.
        """
        # List all top-level collections to verify if 'hotkeys' exists
        self.list_top_level_collections()
        
        # Fetch data from the entire 'hotkeys' collection
        fetched_data = self.fetch_data()
        print("All data fetched and saved from 'hotkeys' collection.")



    # Functions to handle last sync time
    def get_last_sync_time():
        pass
