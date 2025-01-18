import tarfile, io, subprocess, math, os, random, re, shutil, requests, webbrowser, zipfile, stat, json, git, time, platform
from datetime import datetime
from PyQt6.QtGui import QColor, QPixmap, QDesktopServices
from PyQt6.QtCore import QUrl, Qt, QTimer, QProcess, QThread, pyqtSignal, QPoint
from PyQt6.QtWidgets import QSplashScreen, QInputDialog, QMenu, QSplitter, QListWidgetItem, QScrollArea, QFrame, QProgressDialog, QHBoxLayout, QFileDialog, QMessageBox, QApplication, QCheckBox, QLineEdit, QDialog, QLabel, QPushButton, QComboBox, QGridLayout, QWidget, QVBoxLayout, QSpinBox
from git import Repo, GitCommandError
from packaging.version import Version
import pandas as pd


############################################################
# Detect OS and set default settings
############################################################

DATE = "2025/01/18"
ITERATION = "29"
VERSION = Version("1.8.0")  # Current version of the Modpack Manager

system_platform = platform.system()

if system_platform == "Windows":
    DEFAULT_SETTINGS = {
        "game_directory": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro",
        "profile_name": "Balatro",
        "mods_directory": "%AppData%\\Balatro\\Mods",
        "default_modpack": "Dimserenes-Modpack",
        "backup_interval": 60,
        "backup_mods": False,
        "remove_mods": True,
        "skip_mod_selection": False,
        "auto_install": False,
    }
elif system_platform == "Linux":
    DEFAULT_SETTINGS = {
        "game_directory": "/home/$USER/.steam/steam/steamapps/common/Balatro",
        "profile_name": "Balatro",
        "mods_directory": "/home/$USER/.steam/steam/steamapps/compatdata/2379780/pfx/drive_c/users/steamuser/AppData/Roaming/Balatro/Mods",
        "default_modpack": "Dimserenes-Modpack",
        "backup_interval": 60,
        "backup_mods": False,
        "remove_mods": True,
        "skip_mod_selection": False,
        "auto_install": False,
    }
elif system_platform == "Darwin":
    DEFAULT_SETTINGS = {
        "game_directory": "~/Library/Application Support/Steam/steamapps/common/Balatro/",
        "profile_name": "Balatro",
        "mods_directory": "~/Library/Application Support/Balatro/Mods",
        "default_modpack": "Dimserenes-Modpack",
        "backup_interval": 60,
        "backup_mods": False,
        "remove_mods": True,
        "skip_mod_selection": False,
        "auto_install": False,
    }

# File paths for settings and installation exclusions
# Determine the correct settings folder based on the operating system
if platform.system() == "Windows":
    SETTINGS_FOLDER = os.path.abspath(os.path.expandvars(r"%AppData%\Balatro\ManagerSettings"))
elif platform.system() == "Darwin":  # macOS
    SETTINGS_FOLDER = os.path.abspath(os.path.expanduser("~/Library/Application Support/Balatro/ManagerSettings"))
else:  # Assume Linux or other Unix-like OS
    SETTINGS_FOLDER = os.path.abspath(os.path.expanduser("~/.balatro/ManagerSettings"))
    
SETTINGS_FILE = os.path.join(SETTINGS_FOLDER, "user_settings.json")
INSTALL_FILE = os.path.join(SETTINGS_FOLDER, "excluded_mods.json")
FAVORITES_FILE = os.path.join(SETTINGS_FOLDER, "favorites.json")
PRESETS_FILE = os.path.join(SETTINGS_FOLDER, "modpack_presets.json")
CACHE_FILE = os.path.join(SETTINGS_FOLDER, "modpack_cache.json")
CSV_CACHE_FILE = os.path.join(SETTINGS_FOLDER, "cached_data.csv")

LOGO_URL = "https://raw.githubusercontent.com/Dimserene/Dimserenes-Modpack/refs/heads/main/NewFullPackLogo%20New%20Year.png"
LOGO_PATH =  os.path.join(SETTINGS_FOLDER, "logoNewYear.png")  # File name to save the downloaded logo

MODPACKS_FOLDER = os.path.join(os.getcwd(), "Modpacks")  # Folder to store downloaded modpacks

# Ensure the Mods folder and required files exist
def ensure_settings_folder_exists():
    if not os.path.exists(SETTINGS_FOLDER):
        os.makedirs(SETTINGS_FOLDER)
        print(f"Created Mods folder at: {SETTINGS_FOLDER}")

    # Create default JSON files if they don't exist
    for file_path, default_content in [
        (SETTINGS_FILE, DEFAULT_SETTINGS),
        (INSTALL_FILE, []),
        (FAVORITES_FILE, [])
    ]:
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                json.dump(default_content, f, indent=4)
            print(f"Created file: {file_path}")

ensure_settings_folder_exists()

def set_git_buffer_size():
    try:
        # Increase the buffer size globally
        subprocess.run(['git', 'config', '--global', 'http.postBuffer', '524288000'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to set Git buffer size: {e}")

# Call this function before performing Git operations
set_git_buffer_size()

def cache_modpack_data(data):
    """Cache modpack data to a local JSON file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print("Modpack data cached successfully.")
    except Exception as e:
        print(f"Failed to cache modpack data: {e}")

def load_cached_modpack_data():
    """Load cached modpack data, with a check for availability."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                print("Cached modpack data loaded.")
                return json.load(f)
        else:
            print("No cached modpack data found.")
    except Exception as e:
        print(f"Failed to load cached modpack data: {e}")
    return {}

def download_logo(url, save_path):
    """Download the logo from the given URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"Logo downloaded successfully: {save_path}")
    except requests.RequestException as e:
        print(f"Failed to download logo: {e}")
        exit(1)

def remove_debug_folders(mods_directory):
    """
    Check for folders other than 'Steamodded' that contain 'tk_debug_window.py'
    and remove them.
    """
    for folder in os.listdir(mods_directory):
        folder_path = os.path.join(mods_directory, folder)
        if folder != "Steamodded" and os.path.isdir(folder_path):
            debug_file_path = os.path.join(folder_path, "tk_debug_window.py")
            if os.path.isfile(debug_file_path):
                print(f"Removing folder: {folder_path}")
                shutil.rmtree(folder_path)

def is_online(test_url="https://www.google.com", parent=None):
    """Check if the system is connected to the internet."""
    try:
        response = requests.get(test_url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        if parent:
            QMessageBox.warning(parent, "Offline Mode", "Unable to fetch modpack data. Using cached data if available.")
        return False

############################################################
# Worker class for downloading/updating modpack in the background
############################################################

url = "https://raw.githubusercontent.com/Dimserene/ModpackManager/main/information.json"

def fetch_modpack_data(url):
    """Fetch modpack data, with fallback to offline cache if offline."""
    if is_online():
        print("Online: Fetching modpack data...")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise exception for HTTP errors
            data = response.json()       # Parse JSON data
            cache_modpack_data(data)     # Cache the data for offline use
            return data
        except requests.RequestException as e:
            print(f"Failed to fetch data: {e}")
    else:
        print("Offline: Using cached modpack data.")

    # Fallback to cached data if offline
    return load_cached_modpack_data()

modpack_data = fetch_modpack_data(url)

def fetch_dependencies(url):
    """
    Fetch dependencies from the `information.json` file.
    Args:
        url (str): URL of the `information.json` file.
        parent (QWidget or None): Optional parent for QMessageBox.
    Returns:
        dict: Dictionary of dependencies from the JSON file.
    """
    if is_online():
        print(f"Fetching dependencies from {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Cache the dependencies locally
            cache_modpack_data(data)
            print("Dependencies fetched successfully:", data.get("dependencies", {}))
            return data.get("dependencies", {})
        except requests.RequestException as e:
            print(f"Failed to fetch dependencies: {e}")
    else:
        print("Offline: Using cached dependency data.")
    
    # Load cached data as fallback
    cached_data = load_cached_modpack_data()
    return cached_data.get("dependencies", {}) if cached_data else {}
    
dependencies = fetch_dependencies(url)

# URL to the public Google Sheet (export as CSV format)
sheet_url = "https://docs.google.com/spreadsheets/d/1L2wPG5mNI-ZBSW_ta__L9EcfAw-arKrXXVD-43eU4og/export?format=csv&gid=510782711"

# Download and load CSV data
import io

def fetch_csv_data(url, parent=None):
    """
    Fetch CSV data with fallback to offline mode and caching.
    Args:
        url (str): URL of the CSV file.
        parent (QWidget or None): Optional parent for QMessageBox.
    Returns:
        pd.DataFrame or None: Pandas DataFrame with CSV data, or None on failure.
    """
    if is_online():
        print(f"Fetching CSV data from {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            csv_data = response.text
            
            # Save the CSV data to cache
            with open(CSV_CACHE_FILE, "w", encoding="utf-8") as cache_file:
                cache_file.write(csv_data)
            print("CSV data cached successfully.")

            # Load the data into a DataFrame
            return pd.read_csv(io.StringIO(csv_data))

        except requests.RequestException as e:
            print(f"Error fetching CSV data: {e}")
            if parent:
                QMessageBox.warning(parent, "Offline Mode", "Failed to fetch CSV data. Using cached data if available.")
    else:
        print("Offline: Cannot fetch CSV data without an internet connection.")
        if parent:
            QMessageBox.information(parent, "Offline Mode", "No internet connection detected. Using cached CSV data.")

    # Fallback to cached CSV data
    return load_cached_csv_data()

def load_cached_csv_data():
    """
    Load cached CSV data from the local file.
    Returns:
        pd.DataFrame or None: Cached CSV data as a DataFrame, or None if not available.
    """
    try:
        if os.path.exists(CSV_CACHE_FILE):
            print("Loading cached CSV data...")
            return pd.read_csv(CSV_CACHE_FILE)
        else:
            print("No cached CSV data found.")
    except Exception as e:
        print(f"Failed to load cached CSV data: {e}")
    return None

# Process data to extract genres and tags
def process_genres_tags(data):
    if 'Genre' not in data.columns or 'Tags' not in data.columns:
        raise KeyError("Required columns 'Genre' and 'Tags' not found in the data.")

    genres = data['Genre'].unique()
    genre_tags = {}
    for genre in genres:
        tags = data[data['Genre'] == genre]['Tags'].dropna().astype(str).unique().tolist()
        genre_tags[genre] = tags
    return genre_tags

# Populate genres and tags in a QListWidget
def populate_genres_tags(list_widget, genre_tags):
    for genre, tags in genre_tags.items():
        # Add genre as a parent item
        genre_item = QListWidgetItem(f"Genre: {genre}")
        genre_item.setFlags(genre_item.flags())  # Non-editable
        list_widget.addItem(genre_item)

        # Add tags as child items
        for tag in tags:
            tag_item = QListWidgetItem(f"  - Tag: {tag}")
            tag_item.setFlags(tag_item.flags())  # Non-editable
            list_widget.addItem(tag_item)

# Map mods to their metadata (Genre, Tags, and Description)
def map_mods_to_metadata(data):
    metadata = {}
    for _, row in data.iterrows():
        folder_name = row['Folder Name']  # Folder Name
        genre = row.get('Genre', "Unknown")  # Genre
        tags = row.get('Tags', "")  # Tags
        description = row.get('Description', "No description available.")  # Description
        page_link = row.get('Page Link', "")  # Page Link
        discord_link = row.get('Discord Link', "")  # Discord Link

        # Add data to metadata dictionary
        metadata[folder_name] = {
            "Genre": genre if pd.notna(genre) else "Unknown",
            "Tags": [tag.strip() for tag in tags.split(',')] if pd.notna(tags) else [],
            "Description": description.strip() if pd.notna(description) else "No description available.",
            "Page Link": page_link.strip() if pd.notna(page_link) else "",
            "Discord Link": discord_link.strip() if pd.notna(discord_link) else ""

        }
    return metadata

class ModpackDownloadWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)  # Signal to update progress (optional)

    def __init__(self, clone_url, repo_name, branch_name, force_update=False):
        super().__init__()
        self.clone_url = clone_url
        self.repo_name = os.path.join(os.getcwd(), "Modpacks", repo_name)
        self.branch_name = branch_name
        self.force_update = force_update
        self.process = None  # Store the QProcess instance

    def run(self):
        try:
            # Ensure the Modpacks folder exists
            os.makedirs(os.path.dirname(self.repo_name), exist_ok=True)

            # Check if the repository folder already exists
            if os.path.exists(self.repo_name):
                if self.force_update:
                    # Delete the existing folder if force_update is True
                    try:
                        shutil.rmtree(self.repo_name, onerror=readonly_handler)
                        print(f"Deleted existing folder: {self.repo_name}")
                    except Exception as e:
                        self.finished.emit(False, f"Failed to delete existing folder: {str(e)}")
                        return
                else:
                    # If not forcing update, emit failure message
                    self.finished.emit(False, f"Modpack folder '{self.repo_name}' already exists. Enable force update to overwrite.")
                    return

            if self.clone_url.endswith('.git'):
                # Clone the repository using the selected branch
                git_command = ["git", "clone", "--branch", self.branch_name, "--recurse-submodules", "--remote-submodules", self.clone_url, self.repo_name]
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
                
                # Connect QProcess signals for dynamic output handling
                self.process.finished.connect(self.git_finished)
                self.process.readyReadStandardOutput.connect(self.read_git_output)
                self.process.start(git_command[0], git_command[1:])
                self.process.waitForFinished(-1)
            else:
                # Download the file (this part will still emit the success message)
                response = requests.get(self.clone_url, stream=True)
                if response.status_code != 200:
                    self.finished.emit(False, f"File download failed: HTTP status {response.status_code}.")
                    return

                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                local_file_path = os.path.join(os.getcwd(), self.repo_name + '.zip')

                with open(local_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            # Emit progress signal if you have a connected GUI progress bar
                            if total_size > 0:
                                progress_percent = int((downloaded_size / total_size) * 100)
                                self.progress.emit(progress_percent)

                # Verify the file size after download
                if downloaded_size != total_size:
                    self.finished.emit(False, "File download failed: Incomplete file.")
                    return

                # Unzip if necessary
                if zipfile.is_zipfile(local_file_path):
                    try:
                        with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
                            zip_ref.extractall(self.repo_name)
                        os.remove(local_file_path)
                    except zipfile.BadZipFile:
                        self.finished.emit(False, "File download failed: Corrupt ZIP file.")
                        return

                # If file download succeeds, emit success
                self.finished.emit(True, f"Successfully downloaded {self.repo_name}.")

        except Exception as e:
            self.finished.emit(False, f"An unexpected error occurred: {str(e)}")

    def read_git_output(self):
        """Capture real-time output from the Git process."""
        output = bytes(self.process.readAllStandardOutput()).decode('utf-8')
        print(output)  # Optionally, update your GUI log or console with this output

    def git_finished(self):
        """Callback for handling the QProcess finish signal for Git operations."""
        # Capture standard output and error messages
        output = self.process.readAllStandardOutput().data().decode('utf-8').strip()
        error_msg = self.process.readAllStandardError().data().decode('utf-8').strip()

        # Check for actual error conditions
        if self.process.exitCode() == 0 and self.process.error() == QProcess.ProcessError.UnknownError:
            # Success case: Repository should exist
            if os.path.exists(self.repo_name) and os.listdir(self.repo_name):
                self.finished.emit(True, f"Successfully cloned {self.repo_name}.")
            else:
                # Handle unexpected case where the repo doesn't exist after a 'successful' clone
                self.finished.emit(False, f"Git clone succeeded but the folder {self.repo_name} is empty.")
        else:
            # Error case: Provide more detailed output
            error_detail = error_msg if error_msg else (output if output else "An unknown error occurred.")
            self.finished.emit(False, f"Git clone failed: {error_detail}")

        self.process.readyReadStandardOutput.connect(self.capture_stdout)
        self.process.readyReadStandardError.connect(self.capture_stderr)

    def capture_stdout(self):
        output = self.process.readAllStandardOutput().data().decode('utf-8').strip()
        print(f"Standard Output: {output}")

    def capture_stderr(self):
        error_msg = self.process.readAllStandardError().data().decode('utf-8').strip()
        print(f"Standard Error: {error_msg}")

def update_submodules(repo):
    """
    Update submodules of a given repository, handling additions and removals.

    Args:
        repo (Repo): The GitPython Repo object representing the repository.
    """
    try:
        print("Synchronizing submodules...")
        repo.git.submodule('sync')  # Sync submodule URLs

        print("Initializing new submodules...")
        repo.git.submodule('init')  # Initialize new submodules

        print("Updating submodules recursively...")
        repo.git.submodule('update', '--recursive', '--remote')  # Update submodules

        submodules_path = os.path.join(repo.working_tree_dir, '.gitmodules')
        if not os.path.exists(submodules_path):
            print(".gitmodules file not found. Skipping stale submodule cleanup.")
            return

        print("Cleaning up stale submodules...")
        # Deinit stale submodules
        repo.git.submodule('deinit', '--all', '--force')

        # Remove cached and stale submodules
        repo.git.rm('--cached', '-r', '--ignore-unmatch', submodules_path)
        stale_paths = [
            os.path.join(repo.working_tree_dir, submodule.path) for submodule in repo.submodules
        ]
        for path in stale_paths:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)

        print("Re-initializing submodules...")
        repo.git.submodule('init')
        repo.git.submodule('update', '--recursive', '--remote')

        print("Submodules updated successfully.")
    except GitCommandError as e:
        print(f"Git command error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during submodule update: {e}")
        raise

class ModpackUpdateWorker(QThread):
    finished = pyqtSignal(bool, str)  # Signal to indicate task completion with success status and message
    progress = pyqtSignal(str)       # Signal to report progress to the GUI

    def __init__(self, repo_url, repo_name, branch_name, parent_folder):
        super().__init__()
        self.repo_url = repo_url
        self.repo_name = repo_name
        self.branch_name = branch_name
        self.repo_path = os.path.join(parent_folder, self.repo_name)

    def run(self):
        try:
            if not os.path.exists(self.repo_path) or not os.path.isdir(self.repo_path):
                self.finished.emit(False, f"Invalid repository path: {self.repo_path}")
                return

            repo = Repo(self.repo_path)

            # Handle uncommitted changes
            try:
                if repo.is_dirty(untracked_files=True):
                    self.progress.emit("Uncommitted changes detected. Resetting and cleaning repository...")
                    repo.git.reset('--hard')  # Discard local changes
                    repo.git.clean('-fd')     # Remove untracked files and directories
            except GitCommandError as e:
                self.finished.emit(False, f"Error resetting repository: {str(e)}")
                return

            # Pull the latest changes
            self.progress.emit("Pulling latest changes...")
            try:
                repo.remotes.origin.pull()
            except GitCommandError as e:
                self.finished.emit(False, f"Error pulling latest changes: {str(e)}")
                return

            # Update submodules
            self.progress.emit("Updating submodules...")
            try:
                self.update_submodules(repo)
            except GitCommandError as e:
                self.finished.emit(False, f"Error updating submodules: {str(e)}")
                return

            self.finished.emit(True, "Modpack and submodules updated successfully.")
        except GitCommandError as e:
            self.finished.emit(False, f"Git error: {str(e)}")
        except Exception as e:
            self.finished.emit(False, f"Unexpected error: {str(e)}")

    def update_submodules(self, repo):
        """Update all submodules recursively."""
        repo.git.submodule('update', '--init', '--recursive')
        self.progress.emit("Submodules updated.")

############################################################
# Tutorial class
############################################################

class TutorialPopup(QDialog):
    """Floating, titleless popup to display tutorial instructions."""
    def __init__(self, step_text, related_widget, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window  # Store the main window for use in positioning
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)  # Modal
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout()

        # QLabel to display the tutorial text
        self.label = QLabel(step_text)
        
        # Custom stylesheet for the tutorial text
        self.label.setStyleSheet("""
            QLabel {
                background-color: lightyellow;
                color: #333333;
                font-size: 10pt;
                padding: 10px;
                border: 2px solid #0087eb;
                border-radius: 10px;
            }
        """)
        
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Adjust the popup's position near the related widget
        self.adjust_popup_position(related_widget)

    def adjust_popup_position(self, related_widget):
        """Position the popup near the related widget and ensure it stays within the main window's bounds."""
        main_window_geometry = self.main_window.geometry()  # Get the main window size and position
        widget_pos = related_widget.mapToGlobal(QPoint(0, related_widget.height()))  # Get widget position
        self.adjustSize()  # Adjust popup size before positioning

        popup_x = widget_pos.x()
        popup_y = widget_pos.y()

        # Ensure the popup stays within the main window bounds
        popup_width = self.width()
        popup_height = self.height()
        main_window_right = main_window_geometry.x() + main_window_geometry.width()
        main_window_left = main_window_geometry.x()
        main_window_top = main_window_geometry.y()
        main_window_bottom = main_window_geometry.y() + main_window_geometry.height()

        # Correct if the popup goes off the right side of the main window
        if popup_x + popup_width > main_window_right:
            popup_x = main_window_right - popup_width - 10  # Adjust to fit within the right side

        # Correct if the popup goes off the left side of the main window
        if popup_x < main_window_left:
            popup_x = main_window_left + 10  # Add margin to the left

        # Correct if the popup goes off the bottom of the main window
        if popup_y + popup_height > main_window_bottom:
            popup_y = widget_pos.y() - popup_height - related_widget.height()

        # Correct if the popup goes off the top of the main window
        if popup_y < main_window_top:
            popup_y = main_window_top + 10  # Add margin to the top

        # Finally, move the popup to the adjusted position
        self.move(popup_x, popup_y)

############################################################
# Main Program
############################################################

class ModpackManagerApp(QWidget):  # or QMainWindow
    
    def __init__(self, *args, **kwargs):
        super(ModpackManagerApp, self).__init__(*args, **kwargs)
        self.setWindowTitle("Dimserene's Modpack Manager")

        download_logo(LOGO_URL, LOGO_PATH)

        # Load the splash screen
        splash_pixmap = QPixmap(LOGO_PATH).scaled(
            400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.splash = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint)
        self.splash.showMessage(
            "Loading Modpack Manager...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white,
        )
        self.splash.show()

        # Flags to track whether the popups are open
        self.settings_popup_open = False
        self.revert_popup_open = False
        self.install_popup_open = False

        # Initialize custom_install_path as None
        self.custom_install_path = None

        # Initialize metadata as an attribute
        self.metadata = {}

        # Fetch modpack data with offline support
        self.modpack_data = fetch_modpack_data("https://raw.githubusercontent.com/Dimserene/ModpackManager/main/information.json")
        if not self.modpack_data:
            QMessageBox.critical(self, "Error", "Failed to load modpack data. Please check your internet connection.")
            self.modpack_data = {"modpack_categories": []}  # Use empty data as a fallback

        self.branch_data = {}        # Dictionary to store branches for each modpack

        # Load favorite mods
        self.favorite_mods = set()  # Initialize favorites
        self.load_favorites()  # Load favorites on startup

        # Load and process the CSV data
        data = fetch_csv_data(sheet_url)  # Replace with your CSV-fetching logic
        if data is not None:
            self.metadata = map_mods_to_metadata(data)  # Create metadata mapping
        else:
            QMessageBox.critical(self, "Error", "Failed to load metadata. Ensure the CSV is accessible.")

        # Load settings (either default or user preferences)
        self.settings = self.load_settings()
        self.game_dir = self.settings.get("game_directory")
        self.profile_name = self.settings.get("profile_name")
        self.mods_dir = os.path.expandvars(self.settings.get("mods_directory"))
        self.selected_modpack = self.settings.get("game_directory")
        self.excluded_mods = self.read_preferences()

        # Declare default versions
        self.old_version = ""
        self.version_hash = ""

        # Fetch modpack data
        self.modpack_data = modpack_data  # Assign the global modpack_data to an instance variable

        # Proceed only if data is available
        if not self.modpack_data:
            QMessageBox.critical(self, "Error", "Failed to load modpack data. Please check your internet connection.")
            return
        self.splash.finish(self)
        self.create_widgets()
        
        self.initialize_branches()   # List all branches on startup
        self.update_branch_dropdown()
        self.update_installed_info()  # Initial update
        self.check_for_updates()

        # Backup interval in seconds (user set, example: 300 seconds -> 5 minutes)
        self.backup_interval = 60  # Default backup interval
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.perform_backup)
        self.backup_timer.stop()
        
        # Load backup interval from settings (if exists)
        self.backup_interval = self.settings.get("backup_interval", 60)

        # Create a reference to the worker thread
        self.worker = None

        self.tutorial_popup = None  # To track the active tutorial popup
        self.current_step = 0  # To track the current tutorial step
        self.tutorial_steps = [
            ("Welcome to the Modpack Manager! Let's get started.", self),
            ("↑ Use this dropdown to select the modpack.", self.modpack_var),
            ("↑ Click Download/Update button to download or update the selected modpack.", self.download_button),
            ("↑ Use Install button to copy the mod files.", self.install_button),
            ("↑ Then click PLAY button to start the game.", self.play_button),
            ("That's it! You are now ready to use the Modpack Manager.", self)
        ]
    
    def closeEvent(self, event):
        # Save the selected modpack when the window is closed
        selected_modpack = self.modpack_var.currentText()
        self.settings["default_modpack"] = selected_modpack

        # Save settings without showing a popup
        self.save_settings(default_modpack=selected_modpack)

        # Call the default closeEvent to continue closing the window
        super(ModpackManagerApp, self).closeEvent(event)

    def check_for_updates(self):
        """
        Check if an update is available for the manager.
        """
        latest_version_str = self.modpack_data.get("latest_version", None)
        if not latest_version_str:
            QMessageBox.warning(self, "Update Check", "Could not fetch the latest version information.")
            return

        try:
            latest_version = Version(latest_version_str)
        except ValueError:
            QMessageBox.warning(self, "Update Check", f"Invalid version format: {latest_version_str}")
            return

        if VERSION < latest_version:
            # Close the splash screen if it's still open
            if hasattr(self, "splash") and self.splash.isVisible():
                self.splash.finish(self)
            self.prompt_update(latest_version_str, self.modpack_data.get("download_url"), self.modpack_data.get("changelog"))

    def prompt_update(self, latest_version, download_url, changelog):
        """Prompt the user to update if a new version is available."""
        response = QMessageBox.question(
            self,
            "New Version Available",
            f"A new version ({latest_version}) of the modpack is available.\n\nChangelog:\n{changelog}\n\nDo you want to download it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        # Open the download URL only if the user clicked "Ok"
        if response == QMessageBox.StandardButton.Ok:
            webbrowser.open(download_url)
                
    def apply_modpack_styles(self, modpack_name):
        """Apply styles to UI elements based on the selected modpack"""
        if modpack_name == "Coonie's Modpack":
            self.apply_coonies_play_button_style()  # Purple for Coonie's Modpack
        elif modpack_name == "Elbe's Modpack":
            self.apply_elbes_play_button_style()  # Dark Blue for Elbe's Modpack
        else:
            self.apply_default_play_button_style()  # Green for other modpacks

############################################################
# Foundation of root window
############################################################

    def get_modpack_names(self):
        modpack_names = []
        if self.modpack_data:
            for category in self.modpack_data.get('modpack_categories', []):
                for modpack in category.get('modpacks', []):
                    modpack_names.append(modpack['name'])
        return modpack_names

    def create_widgets(self):
        layout = QGridLayout()

        # Title label
        self.title_label = QLabel("☷☷☷Dimserene's Modpack Manager☷☷☷", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font: 16pt 'Helvetica';")
        layout.addWidget(self.title_label, 0, 0, 1, 6, alignment=Qt.AlignmentFlag.AlignCenter)

        # Initialize variables for breathing effect
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_color)
        self.timer.start(150)  # Adjust the interval for smoother or slower color changes

        self.breathing_phase = 0

        # PLAY button
        self.play_button = QPushButton("PLAY", self)

        layout.addWidget(self.play_button, 1, 0, 1, 6)
        self.play_button.clicked.connect(self.play_game)

        # Installed modpack info
        self.installed_info_label = QLabel("", self)
        self.installed_info_label.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.installed_info_label, 2, 0, 1, 6)

        # Refresh button
        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.setStyleSheet("font: 10pt 'Helvetica';")
        self.refresh_button.setToolTip("Refresh currently installed modpack information")
        self.refresh_button.clicked.connect(self.update_installed_info)

        # Add the refresh button to the layout and center it
        layout.addWidget(self.refresh_button, 3, 0, 1, 6, alignment=Qt.AlignmentFlag.AlignCenter)

        # Modpack selection dropdown
        self.modpack_label = QLabel("Select Modpack:", self)
        self.modpack_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.modpack_label, 4, 0, 1, 1)

        # Assuming self.settings["default_modpack"] exists and contains the default modpack name
        modpack_names = self.get_modpack_names()

        self.modpack_var = QComboBox(self)
        self.modpack_var.addItems(modpack_names)
        layout.addWidget(self.modpack_var, 4, 1, 1, 3)

        self.branch_var = QComboBox(self)
        layout.addWidget(self.branch_var, 4, 4, 1, 2)

        # Connect modpack change to update branches
        self.modpack_var.currentIndexChanged.connect(self.update_branch_dropdown)

        # Descriptions
        self.description_label = QLabel("", self)
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label, 5, 0, 1, 6)

        self.modpack_var.currentIndexChanged.connect(self.update_modpack_description)

        # Download button
        self.download_button = QPushButton("Download", self)
        self.download_button.setStyleSheet("font: 12pt 'Helvetica';")
        layout.addWidget(self.download_button, 6, 0, 1, 3)
        self.download_button.clicked.connect(lambda: self.download_modpack(main_window=self))
        self.download_button.setToolTip("Download (clone) selected modpack to the same directory as manager")

        # Assuming modpack_names is a list of available modpack names
        default_modpack = self.settings.get("default_modpack", "Dimserenes-Modpack")  # Get default modpack

        if default_modpack in modpack_names:
            index = self.modpack_var.findText(default_modpack)
            self.modpack_var.setCurrentIndex(index)
        else:
            self.modpack_var.setEditText(default_modpack)

        # Apply corresponding styles based on the selected modpack
        self.apply_modpack_styles(default_modpack)


        # **Update the description label for the initial selected modpack**
        self.update_modpack_description()

        # Connect the currentIndexChanged signal to the modpack change handler
        self.modpack_var.currentIndexChanged.connect(self.on_modpack_changed)

        # Quick Update button
        self.update_button = QPushButton("Quick Update", self)
        self.update_button.setStyleSheet("font: 12pt 'Helvetica';")
        layout.addWidget(self.update_button, 6, 3, 1, 3)
        self.update_button.clicked.connect(self.update_modpack)
        self.update_button.setToolTip("Quickly update downloaded modpacks (can be malfunctioned)")

        # # Multi-Download/Update button
        # self.multi_download_button = QPushButton("Multi Mode", self)
        # self.multi_download_button.setStyleSheet("font: 12pt 'Helvetica';")
        # layout.addWidget(self.multi_download_button, 6, 4, 1, 2)
        # self.multi_download_button.clicked.connect(self.open_multi_modpack_popup)
        # self.multi_download_button.setToolTip("Download or update multiple modpacks at once")

        # Install button
        self.install_button = QPushButton("Install (Copy)", self)
        self.install_button.setStyleSheet("font: 12pt 'Helvetica';")
        layout.addWidget(self.install_button, 7, 0, 1, 3)
        self.install_button.clicked.connect(self.install_modpack)
        self.install_button.setToolTip("Copy (install) Mods content")

        # Uninstall button
        self.uninstall_button = QPushButton("Uninstall (Remove)", self)
        self.uninstall_button.setStyleSheet("font: 12pt 'Helvetica';")
        layout.addWidget(self.uninstall_button, 7, 3, 1, 3)
        self.uninstall_button.clicked.connect(self.uninstall_modpack)
        self.uninstall_button.setToolTip("Delete Mods folder and its contents")

        # # Time Travel button
        # self.revert_button = QPushButton("Time Travel", self)
        # self.revert_button.setStyleSheet("font: 10pt 'Helvetica';")
        # layout.addWidget(self.revert_button, 8, 0, 1, 2)
        # self.revert_button.clicked.connect(self.open_revert_popup)
        # self.revert_button.setToolTip("Revert the modpack to a certain historical version")

        # Verify Integrity button
        self.verify_button = QPushButton("Verify Integrity", self)
        self.verify_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.verify_button, 8, 0, 1, 3)  # Adjust grid position as needed
        self.verify_button.clicked.connect(self.verify_modpack_integrity)
        self.verify_button.setToolTip("Check modpack for missing or incomplete files")

        # Auto backup button
        self.backup_button = QPushButton("Backup Save", self)
        self.backup_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.backup_button, 8, 3, 1, 3)
        self.backup_button.clicked.connect(self.auto_backup_popup)
        self.backup_button.setToolTip("Automatically backup saves in set duration")

        # Check Versions button
        self.check_versions_button = QPushButton("Check Versions", self)
        self.check_versions_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.check_versions_button, 9, 0, 1, 3)
        self.check_versions_button.clicked.connect(self.check_versions)
        self.check_versions_button.setToolTip("Check latest version for all modpacks")

        # Install Lovely button
        self.install_lovely_button = QPushButton("Install/Update lovely", self)
        self.install_lovely_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.install_lovely_button, 9, 3, 1, 3)
        self.install_lovely_button.clicked.connect(self.install_lovely_injector)
        self.install_lovely_button.setToolTip("Install/update lovely injector")

        # Mod List button
        self.mod_list_button = QPushButton("Mod List / Feedback", self)
        self.mod_list_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.mod_list_button, 10, 0, 1, 2)
        self.mod_list_button.clicked.connect(self.open_mod_list)
        self.mod_list_button.setToolTip("Open mod list in web browser")

        # Settings button
        self.open_settings_button = QPushButton("Settings", self)
        self.open_settings_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.open_settings_button, 10, 2, 1, 2)
        self.open_settings_button.clicked.connect(self.open_settings_popup)
        self.open_settings_button.setToolTip("Settings")

        # Discord button
        self.discord_button = QPushButton("Join Discord", self)
        self.discord_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.discord_button, 10, 4, 1, 2)
        self.discord_button.clicked.connect(self.open_discord)
        self.discord_button.setToolTip("Open Discord server in web browser")

        # QLabel acting as a clickable link
        self.tutorial_link = QLabel(self)
        self.tutorial_link.setText('<a href="#">Start Tutorial</a>')  # Set HTML for clickable text
        self.tutorial_link.setOpenExternalLinks(False)  # Disable default behavior of opening URLs
        self.tutorial_link.linkActivated.connect(self.start_tutorial)  # Connect to the tutorial method
        self.tutorial_link.setStyleSheet("""
            QLabel {
                color: #0087eb;  /* Blue link color */
                font-size: 8pt;
                text-decoration: underline;  /* Underline the text to make it look like a link */
            }
            QLabel:hover {
                color: #005ea0;  /* Change color on hover */
            }
        """)
        layout.addWidget(self.tutorial_link, 11, 0, 1, 2)

        latest_version_str = self.modpack_data.get("latest_version", None)

        # Validate and compare versions
        if latest_version_str:
            try:
                latest_version = Version(latest_version_str)
                if VERSION > latest_version:
                    version_style = "color: red;"  # Local version is greater
                else:
                    version_style = "color: black;"  # Default style
            except ValueError:
                version_style = "color: orange;"  # Invalid version format
        else:
            version_style = "color: gray;"  # No version fetched

        self.info = QLabel(f"Build: {DATE}, Iteration: {ITERATION}, Version: Release {VERSION}", self)
        self.info.setStyleSheet(f"font: 8pt 'Helvetica'; {version_style}")
        layout.addWidget(self.info, 11, 0, 1, 6, alignment=Qt.AlignmentFlag.AlignRight)

        # Apply the grid layout to the window
        self.setLayout(layout)

    # Function to handle modpack change
    def on_modpack_changed(self):
        selected_modpack = self.modpack_var.currentText()

        if selected_modpack == "Coonies-Modpack":
            self.apply_coonies_play_button_style()
        elif selected_modpack == "elbes-Modpack":
            self.apply_elbes_play_button_style()
        else:
            self.apply_default_play_button_style()

        # Update the settings with the new default modpack
        self.settings["default_modpack"] = selected_modpack

    def update_color(self):
        # Calculate the breathing effect (sinusoidal pattern)
        self.breathing_phase += 0.005  # 10x slower change
        intensity = (math.sin(self.breathing_phase) + 1) / 2  # Value between 0 and 1

        # Create a dimmer rainbow color effect based on phase, starting from black
        red = int(63 * intensity * (math.sin(self.breathing_phase) + 1))  # Dimmer colors (0-127)
        green = int(63 * intensity * (math.sin(self.breathing_phase + 2 * math.pi / 3) + 1))
        blue = int(63 * intensity * (math.sin(self.breathing_phase + 4 * math.pi / 3) + 1))

        color = QColor(red, green, blue)
        color_hex = color.name()

        # Update label's color without changing font size
        self.title_label.setStyleSheet(
            f"font: 16pt 'Helvetica'; "
            f"color: {color_hex};"
        )
            
    def get_repo_url(self, modpack_name):
        """Returns the Git URL for the selected modpack."""
        return self.modpack_data.get(modpack_name, {}).get("url", "")

    def initialize_branches(self):
        """Lists all branches for each modpack and stores them."""
        for category in self.modpack_data.get("modpack_categories", []):
            for modpack in category.get("modpacks", []):
                modpack_name = modpack["name"]
                self.branch_data[modpack_name] = self.list_branches(modpack_name)

        print("Branch data initialized:")
        for modpack, branches in self.branch_data.items():
            print(f"{modpack}: {branches}")

    def list_branches(self, modpack_name):
        """Lists all branches of a given modpack from the JSON data."""
        for category in self.modpack_data.get("modpack_categories", []):
            for modpack in category.get("modpacks", []):
                if modpack["name"] == modpack_name:
                    # Return defined branches or default to ["main"]
                    return modpack.get("branches", ["main"])
        return []

    def update_branch_dropdown(self):
        """Update branch dropdown based on the selected modpack."""
        selected_modpack = self.modpack_var.currentText()
        branches = self.branch_data.get(selected_modpack, [])

        if branches:
            self.branch_var.clear()
            self.branch_var.addItems(branches)
            self.branch_var.setVisible(True)
        else:
            self.branch_var.clear()
            self.branch_var.setVisible(False)
            QMessageBox.information(self, "Info", f"No branches available for {selected_modpack}.")

############################################################
# Foundation of tutorial
############################################################

    def start_tutorial(self):
        """Starts the tutorial from step 0."""
        self.current_step = 0
        self.show_tutorial_step()

    def show_tutorial_step(self):
        """Shows the current tutorial step with a floating popup."""
        if self.current_step >= len(self.tutorial_steps):
            # Tutorial completed, close the popup and reset
            if self.tutorial_popup:
                self.tutorial_popup.close()
                self.tutorial_popup = None  # Clear the popup
            self.current_step = 0  # Reset tutorial steps
            return

        step_text, widget = self.tutorial_steps[self.current_step]

        # Close the previous popup if it exists
        if self.tutorial_popup:
            self.tutorial_popup.close()

        # Create a new popup and show it
        self.tutorial_popup = TutorialPopup(step_text, widget, self)
        self.tutorial_popup.show()

        # Move to the next step after 5 seconds
        self.current_step += 1
        QApplication.processEvents()
        QTimer.singleShot(5000, self.show_tutorial_step)

    def next_tutorial_step(self):
        """Moves to the next step in the tutorial."""
        self.current_step += 1
        self.show_tutorial_step()
    
    def complete_tutorial(self):
        """Force complete the tutorial and close the popup."""
        if self.tutorial_popup:
            self.tutorial_popup.close()
        self.current_step = len(self.tutorial_steps)  # Set current step to the end

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Tutorial Complete")
        msg_box.setText("You have completed the tutorial!")
        msg_box.exec()

############################################################
# Foundation of settings popup
############################################################

    def open_settings_popup(self):
        # Reload settings whenever the settings popup appears
        self.settings = self.load_settings()

        # Prevent opening multiple settings popups
        if self.settings_popup_open:
            return

        # Mark the settings popup as open
        self.settings_popup_open = True

        # Create a new popup window
        popup = QDialog(self)
        popup.setWindowTitle("Settings")

        # Adjust default game directory based on OS
        default_game_dir = self.settings["game_directory"]
        if platform.system() == "Darwin":  # macOS
            default_game_dir = os.path.abspath(os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Balatro/"))
        elif platform.system() == "Windows":
            default_game_dir = self.settings["game_directory"]

        # List all .exe files in the game directory and strip ".exe"
        exe_files = self.get_exe_files(default_game_dir, macos=True)

        # Create a layout for the popup window
        layout = QGridLayout(popup)

        # Game Directory
        self.game_directory_label = QLabel("Game Directory:", popup)
        layout.addWidget(self.game_directory_label, 0, 0, 1, 2)

        game_dir_entry = QLineEdit(popup)
        game_dir_entry.setText(self.settings["game_directory"])
        layout.addWidget(game_dir_entry, 1, 0, 1, 2)

        self.browse_game_directory_button = QPushButton("Browse", popup)
        self.browse_game_directory_button.clicked.connect(lambda: self.browse_directory(game_dir_entry, True))
        layout.addWidget(self.browse_game_directory_button, 2, 0)

        self.open_game_directory_button = QPushButton("Open", popup)
        self.open_game_directory_button.clicked.connect(lambda: self.open_directory(game_dir_entry.text()))
        layout.addWidget(self.open_game_directory_button, 2, 1)

        # Mods Directory
        self.mods_directory_label = QLabel("Mods Directory:", popup)
        layout.addWidget(self.mods_directory_label, 3, 0, 1, 2)

        mods_dir_entry = QLineEdit(popup)
        mods_dir_entry.setText(os.path.expandvars(self.settings["mods_directory"]))
        layout.addWidget(mods_dir_entry, 4, 0, 1, 2)

        self.open_mods_directory_button = QPushButton("Open", popup)
        self.open_mods_directory_button.clicked.connect(lambda: self.open_directory(mods_dir_entry.text()))
        layout.addWidget(self.open_mods_directory_button, 5, 1)

        # Profile Name Label and Dropdown Menu
        self.profile_name_label = QLabel("Profile Name (Game Executive Name):", popup)
        layout.addWidget(self.profile_name_label, 6, 0, 1, 2)

        profile_name_var = QComboBox(popup)
        profile_name_var.addItems(exe_files)
        profile_name_var.setEditable(True)  # Allow the user to type their own value
        profile_name_var.setCurrentText(self.settings.get("profile_name", exe_files[0] if exe_files else "Balatro"))
        layout.addWidget(profile_name_var, 7, 0, 1, 2)

        self.profile_name_set_button = QPushButton("Set/Create", popup)
        self.profile_name_set_button.clicked.connect(lambda: self.set_profile_name(profile_name_var.currentText(), mods_dir_entry))
        layout.addWidget(self.profile_name_set_button, 8, 1)

        # # Add a checkbox for skipping mod selection screen
        # self.skip_mod_selection_checkbox = QCheckBox("Skip Mod Selection Screen (Install All Mods)", popup)
        # self.skip_mod_selection_checkbox.setChecked(self.settings.get("skip_mod_selection", False))
        # layout.addWidget(self.skip_mod_selection_checkbox, 9, 0, 1, 2)

        # # Add a checkbox for auto-install after download
        # self.auto_install_checkbox = QCheckBox("Install Modpack After Download/Update", popup)
        # self.auto_install_checkbox.setChecked(self.settings.get("auto_install_after_download", False))
        # layout.addWidget(self.auto_install_checkbox, 10, 0, 1, 2)

        # Reset to Default Button
        self.default_button = QPushButton("Reset to Default", popup)
        self.default_button.clicked.connect(lambda: self.reset_to_default(game_dir_entry, mods_dir_entry, profile_name_var))
        layout.addWidget(self.default_button, 16, 0, 1, 2)

        # Save and Cancel Buttons
        self.save_settings_button = QPushButton("Save", popup)
        self.save_settings_button.clicked.connect(lambda: self.save_settings(popup, game_dir_entry.text(), mods_dir_entry.text(), profile_name_var.currentText(), self.modpack_var.currentText(), self.backup_interval))
        layout.addWidget(self.save_settings_button, 17, 0)

        self.cancel_settings_button = QPushButton("Exit", popup)
        self.cancel_settings_button.clicked.connect(lambda: popup.close())

        layout.addWidget(self.cancel_settings_button, 17, 1)

        # Set the fixed width of the popup
        popup.setFixedWidth(400)

        # Close event handler to reset the flag when the window is closed
        def settings_on_close():
            self.settings_popup_open = False
            popup.close()

        # Connect the close event to the handler
        popup.finished.connect(settings_on_close)

        # Show the dialog as modal
        popup.exec()

       
############################################################
# Read and load user preferences
############################################################

    # Function to load settings from the JSON file
    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return DEFAULT_SETTINGS.copy()

    # Function to save settings to the JSON file
    def save_settings(self, popup=None, game_directory=None, mods_directory=None, profile_name=None, default_modpack=None, backup_interval=None):
        # Save the settings to the settings dictionary if provided
        if game_directory is not None:
            self.settings["game_directory"] = game_directory
        if profile_name is not None:
            self.settings["profile_name"] = profile_name
        if mods_directory is not None:
            self.settings["mods_directory"] = mods_directory
        if default_modpack is not None:
            self.settings["default_modpack"] = default_modpack
        if backup_interval is not None:
            self.settings["backup_interval"] = backup_interval

        # Write the settings to the JSON file
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
        finally:
            if popup:
                popup.close()

    # Function to reset settings to defaults
    def reset_to_default(self, game_dir_entry, mods_dir_entry, profile_name_var):
        self.settings = DEFAULT_SETTINGS.copy()
        
        # Reset game directory
        game_dir_entry.setReadOnly(False)
        game_dir_entry.setText(self.settings["game_directory"])
        game_dir_entry.setReadOnly(True)

        # Reset mods directory
        mods_dir_entry.setReadOnly(False)
        mods_dir_entry.setText(os.path.expandvars(self.settings["mods_directory"]))
        mods_dir_entry.setReadOnly(True)

        # Reset profile name in the combobox
        profile_name_var.setCurrentText(self.settings["profile_name"])

    # Function to browse and update the directory
    def browse_directory(self, entry_widget, readonly):
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder_selected:
            # Temporarily make the entry writable
            if readonly:
                entry_widget.setReadOnly(False)

            # Update the entry with the selected folder path
            entry_widget.setText(folder_selected)

            # If it was readonly before, set it back to readonly
            if readonly:
                entry_widget.setReadOnly(True)


    # Function to open the directory in file explorer
    def open_directory(self, path):
        """
        Opens the specified directory in the file explorer.
        Supports macOS, Windows, and Linux.
        """
        # Expand and normalize the directory path
        expanded_path = os.path.abspath(os.path.expanduser(path))
        print(f"Expanded Path: {expanded_path}")
        try:
            # Check if the directory exists, if not create it
            if not os.path.exists(expanded_path):
                os.makedirs(expanded_path)  # Create the directory and all intermediate directories if needed
                
                # Show information message
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Info")
                msg_box.setText(f"Directory did not exist, created: {expanded_path}")
                msg_box.exec()

            # Platform-specific commands to open the directory
            if platform.system() == "Darwin":  # macOS
                print(f"Attempting to open directory on macOS: {expanded_path}")
                subprocess.run(["open", expanded_path], check=True)
            elif platform.system() == "Windows":
                print(f"Attempting to open directory on Windows: {expanded_path}")
                os.startfile(expanded_path)  # Windows uses os.startfile
            elif platform.system() == "Linux":
                print(f"Attempting to open directory on Linux: {expanded_path}")
                subprocess.run(["xdg-open", expanded_path], check=True)
            else:
                QMessageBox.critical(None, "Error", "Unsupported operating system.")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to open directory:\n{expanded_path}\nError: {e}")

    def set_profile_name(self, profile_name, mods_dir_entry):
        # Construct the new mods directory path based on profile name
        if profile_name:
            new_mods_dir = os.path.expandvars(f"%AppData%\\{profile_name}\\Mods")
            self.settings["mods_directory"] = new_mods_dir  # Update the settings
            self.mods_dir = new_mods_dir

            # Update the mods_dir_entry to show the new directory
            mods_dir_entry.setReadOnly(False)  # Temporarily make it writable
            mods_dir_entry.setText(new_mods_dir)  # Insert the new directory
            mods_dir_entry.setReadOnly(True)  # Set back to readonly

            # Construct the source and destination paths
            source_exe = os.path.join(self.game_dir, "balatro.exe")
            destination_exe = os.path.join(self.game_dir, f"{profile_name}.exe")

            # Check if balatro.exe exists, otherwise prompt the user to choose a file
            if not os.path.exists(source_exe):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("File Not Found")
                msg_box.setText("balatro.exe not found in the game directory. Please choose an executable file to copy.")
                msg_box.exec()

                # Prompt the user to select an executable file
                chosen_file, _ = QFileDialog.getOpenFileName(None, "Select Executable", "", "Executable Files (*.exe)")

                if not chosen_file:  # If the user cancels the file selection
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Information)
                    msg_box.setWindowTitle("Operation Cancelled")
                    msg_box.setText("No executable file selected. Profile creation aborted.")
                    msg_box.exec()
                    return  # Abort the operation if no file is selected

                # Set the source_exe to the chosen file
                source_exe = chosen_file

            # Try copying the executable file to the new profile name
            try:
                shutil.copy2(source_exe, destination_exe)
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Success")
                msg_box.setText(f"Profile executable {profile_name}.exe created successfully!")
                msg_box.exec()

            except Exception as e:
                # Display an error message if something goes wrong during the file copy process
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Failed to create {profile_name}.exe: {str(e)}")
                msg_box.exec()


    # Function to get .exe files and strip the extension
    def get_exe_files(self, directory, macos=False):
        try:
            if macos:
                return [f for f in os.listdir(directory) if f.endswith(".app")]
            return [f for f in os.listdir(directory) if f.endswith(".exe")]
        except FileNotFoundError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Directory not found: {directory}")
            msg_box.exec()
            return []

############################################################
# Foundation of time travel popup
############################################################

    def open_revert_popup(self):
        selected_modpack = self.modpack_var.currentText()

        # Check if the selected modpack is "Coonie's Modpack"
        if selected_modpack == "Coonie's Modpack":
            # Show a popup message and prevent closing the window
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Incompatible Modpack")
            msg_box.setText("This function is not compatible with Coonie's Modpack!")
            msg_box.exec()
            return []

        # Prevent opening multiple time travel popups
        if self.revert_popup_open:
            return

        # Mark the time travel popup as open
        self.revert_popup_open = True

        # Create a new popup window
        popup = QDialog(self)
        popup.setWindowTitle("Time Machine")

        # Create a layout for the popup window
        layout = QGridLayout(popup)

        # Label for selecting the version
        self.old_version_label = QLabel("Select version to time travel:", popup)
        layout.addWidget(self.old_version_label, 0, 0, 1, 2)

        # Fetch all available versions (commit messages)
        commit_versions = self.get_all_commit_versions()

        # Dropdown menu to select version
        self.version_var = QComboBox(popup)
        self.version_var.addItems(commit_versions)
        layout.addWidget(self.version_var, 1, 0, 1, 2)

        if commit_versions:
            self.version_var.setCurrentIndex(0)  # Set the default selection to the first version

        # Submit Button to find the commit hash
        submit_button = QPushButton("Submit", popup)
        submit_button.clicked.connect(self.submit_version)
        layout.addWidget(submit_button, 2, 0, 1, 2)

        # Result Label for Commit Hash
        self.hash_title_label = QLabel("Hash:", popup)
        self.hash_title_label.setStyleSheet("color: gray;")
        layout.addWidget(self.hash_title_label, 3, 0, 1, 1)

        self.version_hash_label = QLabel("", popup)
        self.version_hash_label.setStyleSheet("color: gray;")
        layout.addWidget(self.version_hash_label, 4, 0, 1, 2)

        # Button to Revert to Current
        self.current_button = QPushButton("Revert to Current", popup)
        self.current_button.clicked.connect(self.switch_back_to_main)
        layout.addWidget(self.current_button, 5, 0, 1, 1)
        
        # Button to Revert to Commit
        self.time_travel_button = QPushButton("Time Travel", popup)
        self.time_travel_button.setEnabled(False)  # Initially disabled
        self.time_travel_button.clicked.connect(self.revert_version)
        layout.addWidget(self.time_travel_button, 5, 1, 1, 1)

        # Close event handler to reset the flag when the window is closed
        def revert_on_close():
            self.revert_popup_open = False
            popup.close()

        # Connect the close event to the handler
        popup.finished.connect(revert_on_close)

        # Set the fixed width of the popup
        popup.setFixedWidth(400)

        # Show the dialog as modal
        popup.exec()


############################################################
# Time travel functions
############################################################

    def get_all_commit_versions(self, limit_to_commit=None):
        modpack_name = self.modpack_var.currentText()
        repo_path = os.path.join(os.getcwd(), modpack_name)
        commit_versions = []

        try:
            # Initialize the repository
            repo = git.Repo(repo_path)

            # Get the first line of each commit message
            for commit in repo.iter_commits():
                commit_first_line = commit.message.split("\n", 1)[0]
                commit_versions.append(commit_first_line)

                # If limit_to_commit is provided, stop fetching commits once we hit this commit
                if limit_to_commit and (commit.hexsha == limit_to_commit or commit_first_line == limit_to_commit):
                    break

            return commit_versions
        
        except git.exc.InvalidGitRepositoryError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Invalid Git repository.")
            msg_box.exec()
            return []
        
        except Exception as e:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to fetch commit versions: {str(e)}")
            msg_box.exec()
            return []

    def submit_version(self):
        # Store user input version in self.old_version
        self.old_version = self.version_var.currentText()

        # Fetch the commit hash based on user input
        self.find_commit(self.old_version)

    def find_commit(self, old_version):
        modpack_name = self.modpack_var.currentText()
        repo_path = os.path.join(os.getcwd(), modpack_name)

        if not os.path.exists(repo_path):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("The modpack not found. Please download first.")
            msg_box.exec()
            return

        # Fetch the commit hash by the version message
        commit_hash = self.find_commit_hash_by_message(old_version)

        # If commit hash found, update the label and enable the time travel button
        if commit_hash:
            if commit_hash.startswith("Error"):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText(commit_hash)
                msg_box.exec()
            else:
                self.version_hash_label.setText(f"{commit_hash}")
                self.version_hash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.time_travel_button.setEnabled(True)  # Enable the time travel button

        else:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Not Found")
            msg_box.setText(f"No commit found with version: {old_version}")
            msg_box.exec()

    def find_commit_hash_by_message(self, commit_message):
        modpack_name = self.modpack_var.currentText()
        repo_path = os.path.join(os.getcwd(), modpack_name)
        
        try:
            # Initialize the repository
            repo = git.Repo(repo_path)

            # Iterate through the commits and search for the commit message
            for commit in repo.iter_commits():
                # Git allows multiline commit messages, so we'll compare only the first line
                commit_first_line = commit.message.split("\n", 1)[0]
                if re.fullmatch(commit_message, commit_first_line):
                    return commit.hexsha

            return None
        except git.exc.InvalidGitRepositoryError:
            return "Error: Invalid Git repository."
        except Exception as e:
            return f"Error: {str(e)}"

    def revert_version(self):
        modpack_name = self.modpack_var.currentText()
        repo_path = os.path.join(os.getcwd(), modpack_name)
        old_version = self.version_var.currentText()

        # Get the correct commit hash from the version_hash_label
        commit_hash = self.version_hash_label.text()

        try:
            repo = git.Repo(repo_path)

            # Perform git switch --detach to detach HEAD
            repo.git.switch('--detach')

            # Perform the git reset --hard <hash>
            repo.git.reset('--hard', commit_hash)

            # Show success message
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Success")
            msg_box.setText(f"Time traveled to version: {old_version}, please install again.")
            msg_box.exec()

        except Exception as e:
            # Show error message
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to time travel: {str(e)}")
            msg_box.exec()

    def switch_back_to_main(self):
        modpack_name = self.modpack_var.currentText()
        repo_path = os.path.join(os.getcwd(), modpack_name)

        try:
            repo = git.Repo(repo_path)
            
            # Perform git switch main to switch back to the main branch
            repo.git.switch('main')

            # Show success message
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Success")
            msg_box.setText("Travelled back to current.")
            msg_box.exec()

        except Exception as e:
            # Show error message
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to travel back to current: {str(e)}")
            msg_box.exec()

############################################################
# Foundation of Backup popup and functions
############################################################

    def auto_backup_popup(self):

        # Create a new popup window
        popup = QDialog(self)
        popup.setWindowTitle("Auto Backup Settings")

        # Create the layout for the popup
        layout = QVBoxLayout(popup)

        # Add a label for interval setting
        label = QLabel("Set the interval (in seconds) for automatic backups:", popup)
        layout.addWidget(label)

        # Add a spinbox for selecting the interval (in seconds)
        interval_spinbox = QSpinBox(popup)
        interval_spinbox.setMinimum(5)  # Minimum interval is 5 seconds
        interval_spinbox.setMaximum(600)  # Maximum interval is 600 seconds (10 minutes)
        interval_spinbox.setValue(self.backup_interval)  # Display current value in seconds
        layout.addWidget(interval_spinbox)

        # Add preset buttons for predefined intervals
        preset_buttons_layout = QHBoxLayout()
        preset_intervals = [5, 10, 30, 60, 120, 300, 600]

        for interval in preset_intervals:
            label = f"{interval} sec" if interval < 60 else f"{interval // 60} min"
            preset_button = QPushButton(label, popup)
            preset_button.clicked.connect(lambda _, i=interval: interval_spinbox.setValue(i))
            preset_buttons_layout.addWidget(preset_button)

        layout.addLayout(preset_buttons_layout)

        # Add Horizontal Line (Separator)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setLineWidth(2)
        layout.addWidget(line)

        # Add a label for interval setting
        label = QLabel("Choose which backup file to restore:", popup)
        layout.addWidget(label)

        # Backup dropdown with load button
        backup_dropdown_layout = QHBoxLayout()
        self.backup_dropdown = QComboBox(popup)  # Now an instance attribute
        self.update_backup_dropdown(self.backup_dropdown)  # Populate the dropdown with existing backups
        backup_dropdown_layout.addWidget(self.backup_dropdown)

        # Add a Load button to refresh the dropdown
        load_button = QPushButton("Load", popup)
        load_button.clicked.connect(lambda: self.update_backup_dropdown(self.backup_dropdown))
        backup_dropdown_layout.addWidget(load_button)

        layout.addLayout(backup_dropdown_layout)

        # Restore, delete all, and open folder buttons
        button_layout = QHBoxLayout()
        restore_button = QPushButton("Restore Backup", popup)
        delete_all_button = QPushButton("Delete All", popup)
        open_folder_button = QPushButton("Open Folder", popup)
        button_layout.addWidget(restore_button)
        button_layout.addWidget(delete_all_button)
        button_layout.addWidget(open_folder_button)
        layout.addLayout(button_layout)

        # Start, stop, and cancel buttons
        action_buttons_layout = QHBoxLayout()
        start_button = QPushButton("Start", popup)
        stop_button = QPushButton("Stop", popup)
        cancel_button = QPushButton("Cancel", popup)
        action_buttons_layout.addWidget(start_button)
        action_buttons_layout.addWidget(stop_button)
        action_buttons_layout.addWidget(cancel_button)
        layout.addLayout(action_buttons_layout)

        # Connect buttons to their respective functions
        start_button.clicked.connect(lambda: self.start_auto_backup(interval_spinbox.value(), popup))
        stop_button.clicked.connect(lambda: self.stop_auto_backup(popup))
        cancel_button.clicked.connect(popup.close)
        restore_button.clicked.connect(lambda: self.restore_backup(self.backup_dropdown.currentText()))  # Access backup_dropdown as instance attribute
        delete_all_button.clicked.connect(self.delete_all_backups)
        open_folder_button.clicked.connect(self.open_backup_folder)

        popup.exec()

    def start_auto_backup(self, interval, parent_widget):
        """Start the automatic backup with user-defined intervals"""
        self.backup_interval = interval
        if not self.backup_timer.isActive():
            print(f"Starting auto backup every {interval} seconds.")  # Debugging info
            self.backup_timer.start(interval * 1000)  # Convert to milliseconds
            # Notify user of backup start
            QMessageBox.information(parent_widget, "Auto Backup", f"Auto backup started. Interval: {interval} seconds.")
        else:
            print("Backup timer is already active.")  # Debugging info

    def stop_auto_backup(self, parent_widget):
        """Stop the automatic backup"""
        if self.backup_timer.isActive():
            print("Stopping auto backup.")  # Debugging info
            self.backup_timer.stop()
            # Notify user of backup stop
            QMessageBox.information(parent_widget, "Auto Backup", "Auto backup stopped.")
        else:
            print("Backup timer was not active.")  # Debugging info
            QMessageBox.information(parent_widget, "Auto Backup", "Backup timer was not active.")


    def perform_backup(self):
        """Perform the backup task"""
        try:
            # Define paths
            save_file_path = os.path.expandvars("%AppData%\\Balatro\\1\\save.jkr")
            backup_dir = os.path.expandvars("%AppData%\\Balatro\\1\\autosave")

            # Ensure the backup directory exists
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            # Create a timestamped backup file name
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_file_name = f"save-{timestamp}.jkr"
            backup_file_path = os.path.join(backup_dir, backup_file_name)

            # Perform the file copy
            shutil.copy2(save_file_path, backup_file_path)
            print(f"Backup successful: {backup_file_path}")  # Debugging info

        except Exception as e:
            print(f"Backup failed: {str(e)}")  # Debugging info

    def update_backup_dropdown(self, dropdown):
        """Update the dropdown with the list of backups"""
        backup_dir = os.path.expandvars("%AppData%\\Balatro\\1\\autosave")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        backup_files = sorted([f for f in os.listdir(backup_dir) if f.endswith(".jkr")])

        dropdown.clear()
        for backup in backup_files:
            dropdown.addItem(backup)

    def restore_backup(self, backup_file):
        """Backup the current save and restore the selected backup"""
        try:
            # Define paths
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            save_file_path = os.path.expandvars("%AppData%\\Balatro\\1\\save.jkr")
            backup_dir = os.path.expandvars("%AppData%\\Balatro\\1\\autosave")
            backup_file_path = os.path.join(backup_dir, backup_file)

            # Backup current save.jkr as save.jkr.bk (if exist, suffix number)
            backup_save_path = os.path.join(backup_dir, f"save-{timestamp}-bk.jkr")
            counter = 1
            while os.path.exists(backup_save_path):
                backup_save_path = os.path.join(backup_dir, f"save-{timestamp}-bk-{counter}.jkr")
                counter += 1

            shutil.copy2(save_file_path, backup_save_path)
            print(f"Current save backed up as: {backup_save_path}")

            # Restore the selected backup
            shutil.copy2(backup_file_path, save_file_path)
            print(f"Backup {backup_file} restored to save.jkr")

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Restore Complete")
            msg_box.setText(f"Backup {backup_file} restored successfully.")
            msg_box.exec()

        except Exception as e:
            print(f"Restore failed: {str(e)}")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Restore Failed")
            msg_box.setText(f"Failed to restore backup: {str(e)}")
            msg_box.exec()

    def delete_all_backups(self):
        """Delete all backup saves with a confirmation prompt."""
        try:
            # Prompt the user for confirmation
            reply = QMessageBox.question(self, "Confirm Deletion", 
                                        "Are you sure you want to delete all backup saves?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            # Check if the user clicked 'Yes'
            if reply == QMessageBox.StandardButton.Yes:
                backup_dir = os.path.expandvars("%AppData%\\Balatro\\1\\autosave")

                for backup_file in os.listdir(backup_dir):
                    file_path = os.path.join(backup_dir, backup_file)
                    if os.path.isfile(file_path) and backup_file.endswith(".jkr"):
                        os.remove(file_path)

                print("All backups deleted.")
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Delete All")
                msg_box.setText("All backups deleted successfully.")
                msg_box.exec()

                # Update the dropdown after deletion
                self.update_backup_dropdown(self.backup_dropdown)

            else:
                print("Deletion canceled.")
        
        except Exception as e:
            print(f"Failed to delete backups: {str(e)}")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Delete Failed")
            msg_box.setText(f"Failed to delete backups: {str(e)}")
            msg_box.exec()

    def open_backup_folder(self):
        """Open the folder containing the backups"""
        backup_dir = os.path.expandvars("%AppData%\\Balatro\\1\\autosave")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        webbrowser.open(backup_dir)

############################################################
# Top functions (Play, installed info, refresh)
############################################################

    def play_game(self):
        # Check if Lovely Injector is installed
        if not self.check_lovely_injector_installed():
            QMessageBox.warning(
                self, 
                "Cannot Launch Game", 
                "Lovely Injector is required to play the modded game. Launch aborted."
            )
            return

        self.settings = self.load_settings()
        self.game_dir = self.settings.get("game_directory")
        self.profile_name = self.settings.get("profile_name")        
        self.mods_path = os.path.expandvars(self.settings.get("mods_directory"))
        remove_debug_folders(self.mods_path)

        # Detect the operating system
        system_platform = platform.system()

        if system_platform == "Windows":
            # Construct the path to the game executable
            game_executable = os.path.join(self.game_dir, f"{self.profile_name}.exe")

            try:
                # Check if the executable exists
                if os.path.exists(game_executable):
                    print(f"Launching {game_executable}")
                    # Use QProcess to launch the game in a non-blocking way
                    self.process = QProcess(self)
                    self.process.start(game_executable)
                else:
                    raise FileNotFoundError(f"Game executable not found: {game_executable}")
            except Exception as e:
                # Display an error message if something goes wrong
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Failed to launch game: {e}")
                msg_box.exec()

        elif system_platform == "Linux":
            try:
                # Use Steam to launch the game via its app ID
                steam_command = "steam://rungameid/2379780"
                print(f"Launching game via Steam: {steam_command}")
                self.process = QProcess(self)
                self.process.start("xdg-open", [steam_command])  # xdg-open is used to open URLs on Linux
            except Exception as e:
                # Display an error message if something goes wrong
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Failed to launch game via Steam: {e}")
                msg_box.exec()

        elif system_platform == "Darwin":  # macOS
            try:
                # Use Steam to launch the game via its app ID
                steam_command = "steam://rungameid/2379780"
                print(f"Launching game via Steam on macOS: {steam_command}")
                self.process = QProcess(self)
                self.process.start("open", [steam_command])  # 'open' is the macOS equivalent to xdg-open
            except Exception as e:
                # Display an error message if something goes wrong
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Failed to launch game via Steam on macOS: {e}")
                msg_box.exec()

        else:
            # Unsupported platform
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Unsupported Platform")
            msg_box.setText("Your operating system is not supported for launching the game.")
            msg_box.exec()


    def apply_coonies_play_button_style(self):
        """ Apply Coonie's Modpack play button color (Purple) """
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #5e00bd;  /* Purple for Coonie's Modpack */
                color: white;
                border-radius: 8px;
                padding: 10px;
                font: 30pt 'Helvetica';
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background-color: #4700a3;  /* Darker Purple on hover */
                border: 2px solid #34006b;  /* Dark Purple border on hover */
            }
            QPushButton:pressed {
                background-color: #34006b;  /* Even darker Purple on press */
                padding-top: 12px;
                padding-bottom: 8px;
            }
        """)

    def apply_elbes_play_button_style(self):
        """ Apply Elbe's Modpack play button color (Dark Blue) """
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #003366;  /* Dark Blue for Elbe's Modpack */
                color: white;
                border-radius: 8px;
                padding: 10px;
                font: 30pt 'Helvetica';
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background-color: #002a5c;  /* Darker Blue on hover */
                border: 2px solid #001f45;  /* Dark Blue border on hover */
            }
            QPushButton:pressed {
                background-color: #001f45;  /* Even darker Blue on press */
                padding-top: 12px;
                padding-bottom: 8px;
            }
        """)

    def apply_default_play_button_style(self):
        """ Apply default play button color (Green) """
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #00D600;  /* Green for default */
                color: white;
                border-radius: 8px;
                padding: 10px;
                font: 30pt 'Helvetica';
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background-color: #00C400;  /* Darker Green on hover */
                border: 2px solid #00A800;  /* Dark Green border on hover */
            }
            QPushButton:pressed {
                background-color: #008c00;  /* Even darker Green on press */
                padding-top: 12px;
                padding-bottom: 8px;
            }
        """)

    def get_latest_commit_message(self, repo_owner, repo_name):
        try:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            commits = response.json()
            if commits:
                latest_commit = commits[0]
                commit_message = latest_commit['commit']['message']
                return commit_message
            else:
                return "No commits found."
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return "Failed to fetch commits."

    def fetch_commit_messages(self):
        # Dynamically fetch repositories from the "Dimserene" category in modpack_data
        repos = {}
        if self.modpack_data:
            for category in self.modpack_data.get("modpack_categories", []):
                if category.get("category") == "Dimserene":
                    for modpack in category.get("modpacks", []):
                        name = modpack.get("name")
                        url = modpack.get("url")
                        if name and url:
                            # Extract owner and repo name from URL
                            match = re.match(r"https://github\.com/([^/]+)/([^/.]+)", url)
                            if match:
                                owner, repo_name = match.groups()
                                repos[name] = (owner, repo_name)

        # Fetch the latest commit messages for each repository
        commit_messages = {}
        for repo_name, (owner, repo) in repos.items():
            commit_message = self.get_latest_commit_message(owner, repo)
            # Adjust tabulation based on the length of the repo_name
            tabs = "\t\t" if len(repo_name) < 12 else "\t"
            commit_messages[repo_name] = f"{tabs}{commit_message}"

        return commit_messages

    def get_version_info(self):
        # Paths for version and modpack name files
        mods_path = os.path.join(os.path.expandvars(self.mods_dir), "ModpackUtil")
        current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
        modpack_name_file = os.path.join(mods_path, 'ModpackName.txt')
        modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')

        current_version, pack_name = None, ""

        # Load the current version if available
        if os.path.exists(current_version_file):
            current_version = self.read_file_content(current_version_file)

        # Attempt to load the modpack name from ModpackName.txt
        if os.path.exists(modpack_name_file):
            pack_name = self.read_file_content(modpack_name_file)
        else:
            # Fallback to extracting from ModpackUtil.lua if ModpackName.txt is missing
            pack_name = self.extract_pack_name(modpack_util_file)
        
        return current_version, pack_name

    def update_installed_info(self):
        # Load user settings once
        self.settings = self.load_settings()

        # Paths for version and modpack name files
        install_path = os.path.expandvars(self.settings["mods_directory"])
        mods_path = os.path.join(install_path, 'ModpackUtil')
        current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
        modpack_name_file = os.path.join(mods_path, 'ModpackName.txt')
        modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')

        # Attempt to read the current version
        current_version = self.read_file_content(current_version_file)

        # Attempt to read the modpack name from ModpackName.txt, or fallback to ModpackUtil.lua
        pack_name = self.read_file_content(modpack_name_file) or self.extract_pack_name(modpack_util_file)

        # Update installed info label with pack name and version
        info_text = f"Installed pack: {pack_name} ({current_version})" if pack_name else "No modpack installed or ModpackUtil mod removed."
        self.installed_info_label.setText(info_text)
        self.installed_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def read_file_content(self, file_path):
        """Helper to read content from a file."""
        try:
            with open(file_path, 'r') as file:
                return file.read().strip()
        except IOError as e:
            print(f"IOError reading {file_path}: {e}")
            return None

    def extract_pack_name(self, lua_file_path):
        """Helper to extract the pack name from ModpackUtil.lua."""
        try:
            with open(lua_file_path, 'r') as file:
                for line in file:
                    if line.startswith('--- VERSION:'):
                        return line.split(':')[1].strip()
        except IOError as e:
            print(f"IOError reading {lua_file_path}: {e}")
        return None

    def update_modpack_description(self):
        selected_modpack = self.modpack_var.currentText()
        modpack_info = self.get_modpack_info(selected_modpack)
        if modpack_info:
            self.description_label.setText(modpack_info['description'])
        else:
            self.description_label.setText("Description not available.")

############################################################
# Middle functions (Download, install, update, uninstall)
############################################################

    def get_modpack_info(self, modpack_name):
        if self.modpack_data:
            for category in self.modpack_data.get('modpack_categories', []):
                for modpack in category.get('modpacks', []):
                    if modpack['name'] == modpack_name:
                        return modpack
        return None

    def get_modpack_url(self, modpack_name):
        modpack_info = self.get_modpack_info(modpack_name)
        if modpack_info:
            return modpack_info['url']
        else:
            return ""

    def prompt_for_installation(self):
        modpack_name = self.modpack_var.currentText()
        modpack_url = self.get_modpack_url(modpack_name)
        if modpack_url:
            self.download_modpack(main_window=self, clone_url=modpack_url)
        else:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Invalid modpack selected.")
            msg_box.exec()

    def download_modpack(self, main_window=None, clone_url=None):
        """Download the selected modpack with a prompt for overwriting."""
        modpack_name = self.modpack_var.currentText()
        selected_branch = self.branch_var.currentText()
        repo_url = clone_url or self.get_modpack_url(modpack_name)

        if not repo_url:
            QMessageBox.critical(self, "Error", "Invalid modpack URL.")
            return

        # Define the full path for the repository
        folder_name = f"{modpack_name}-{selected_branch}" if selected_branch != "main" else modpack_name
        repo_path = os.path.join(os.getcwd(), "Modpacks", folder_name)

        # Check if the folder already exists
        if os.path.exists(repo_path):
            response = QMessageBox.question(
                self,
                "Overwrite Existing Modpack",
                f"The folder '{folder_name}' already exists. Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if response == QMessageBox.StandardButton.No:
                return  # Exit early if the user does not want to overwrite

            # If Yes, delete the existing folder
            try:
                shutil.rmtree(repo_path, onerror=readonly_handler)  # Remove the folder and its contents
                print(f"Deleted existing folder: {repo_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete existing folder: {str(e)}")
                return

        # Ensure the Modpacks folder exists
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)

        # Create and display the progress dialog for updating
        self.progress_dialog = QProgressDialog("", None, 0, 0)  # Pass None to remove the cancel button
        self.progress_dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # No title bar
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # Modal
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                border: 3px solid #555;
                background-color: #ffffff;
            }
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                background-color: transparent;
            }
        """)

        # Create a custom QLabel for the message with the modpack name
        label = QLabel(f"Downloading {modpack_name}({selected_branch})...")  # Show the name of the modpack
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align the text
        label.setStyleSheet("""
            QLabel {
                background-color: transparent;
            }
        """)

        # Create a layout for the dialog and add the label
        layout = QVBoxLayout(self.progress_dialog)
        layout.addWidget(label)

        self.progress_dialog.setLayout(layout)
        self.progress_dialog.show()

        # Center the progress dialog relative to the parent window
        if isinstance(self, QWidget):
            parent_geometry = self.geometry()
            dialog_geometry = self.progress_dialog.frameGeometry()
            dialog_geometry.moveCenter(parent_geometry.center())
            self.progress_dialog.move(dialog_geometry.topLeft())

        QApplication.processEvents()

        self.worker = ModpackDownloadWorker(repo_url, folder_name, selected_branch, force_update=True)
        self.worker.finished.connect(self.on_download_finished)

        # Start the worker thread
        self.worker.start()

    def on_download_finished(self, success, message):
        # Close the progress dialog
        self.progress_dialog.close()

        # Show the result message (success or failure)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information if success else QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Download Status" if success else "Error")
        msg_box.setText(message)
        msg_box.exec()

        # If successful, verify the integrity of the downloaded modpack
        if success:
            self.verify_modpack_integrity()

        # Check the setting and install modpack if needed
        if success and self.settings.get("auto_install_after_download", False):
            self.install_modpack()

    def get_latest_tag_message(self):
        """Fetch the latest tag message from the Coonie's Modpack GitHub repository."""
        try:
            api_url = "https://api.github.com/repos/GayCoonie/Coonies-Mod-Pack/tags"
            response = requests.get(api_url)
            if response.status_code == 200:
                tags = response.json()
                if tags:
                    # Return the latest tag's message
                    latest_tag = tags[0]
                    return f"{latest_tag['name']}"
                else:
                    return "No tags found in the repository."
            else:
                raise Exception(f"GitHub API request failed with status code {response.status_code}")
        except Exception as e:
            print(f"Error fetching latest tag message: {e}")
            return "Error fetching the latest version."

    def update_modpack(self):
        """Update the selected modpack with branch support."""
        modpack_name = self.modpack_var.currentText()
        repo_url = self.get_modpack_url(modpack_name)
        selected_branch = self.branch_var.currentText()

        # Ensure consistent use of the Modpacks folder
        parent_folder = os.path.join(os.getcwd(), "Modpacks")
        os.makedirs(parent_folder, exist_ok=True)  # Ensure the parent folder exists

        # Correctly construct the repository name with branch
        if selected_branch != "main":
            repo_name = f"{modpack_name}-{selected_branch}"
        else:
            repo_name = modpack_name

        # Construct the full path to the repository
        repo_path = os.path.join(parent_folder, repo_name)

        # Debugging (optional): Print constructed paths
        print(f"Modpack Name: {modpack_name}")
        print(f"Branch Name: {selected_branch}")
        print(f"Repo Name: {repo_name}")
        print(f"Repo Path: {repo_path}")

        # Check if the selected modpack is "Coonie's Modpack"
        if modpack_name == "Coonie's Modpack":
            QMessageBox.warning(
                self,
                "Incompatible Modpack",
                "This function is not compatible with Coonie's Modpack! Please use Download/Update instead."
            )
            return

        # Check if the repository exists in the Modpacks folder
        if not os.path.isdir(repo_path):
            QMessageBox.critical(
                self,
                "Error",
                f"Repository not found in Modpacks folder. Attempting to clone it at {repo_path}."
            )
            self.download_modpack(main_window=self, clone_url=repo_url)
            return

        # Create and display the progress dialog for updating
        self.progress_dialog = QProgressDialog("", None, 0, 0)  # Pass None to remove the cancel button
        self.progress_dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # No title bar
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # Modal
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                border: 3px solid #555;
                background-color: #ffffff;
            }
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                background-color: transparent;
            }
        """)

        # Create a custom QLabel for the message with the modpack name
        label = QLabel(f"Updating {modpack_name}({selected_branch})...")  # Show the name of the modpack
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align the text
        label.setStyleSheet("""
            QLabel {
                background-color: transparent;
            }
        """)

        # Create a layout for the dialog and add the label
        layout = QVBoxLayout(self.progress_dialog)
        layout.addWidget(label)

        self.progress_dialog.setLayout(layout)
        self.progress_dialog.show()

        # Center the progress dialog relative to the parent window
        if isinstance(self, QWidget):
            parent_geometry = self.geometry()
            dialog_geometry = self.progress_dialog.frameGeometry()
            dialog_geometry.moveCenter(parent_geometry.center())
            self.progress_dialog.move(dialog_geometry.topLeft())

        QApplication.processEvents()

        # Create the worker for updating the modpack
        self.worker = ModpackUpdateWorker(repo_url, repo_name, selected_branch, parent_folder)
        self.worker.finished.connect(self.on_update_finished)

        # Start the worker (background task)
        self.worker.start()

    def on_update_finished(self, success, message):
        # Close the progress dialog
        self.progress_dialog.close()

        # Show the result message (success or failure)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information if success else QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Update Status" if success else "Error")
        msg_box.setText(message)
        msg_box.exec()

        # If successful, verify the integrity of the downloaded modpack
        if success:
            self.verify_modpack_integrity()

        # Check the setting and install modpack if needed
        if success and self.settings.get("auto_install_after_download", False):
            self.install_modpack()


    def install_modpack(self):
        self.settings = self.load_settings()
        skip_mod_selection = self.settings.get("skip_mod_selection", False)
        modpack_name = self.modpack_var.currentText()
        selected_branch = self.branch_var.currentText()
        modpack_info = self.get_modpack_info(modpack_name)

        if not modpack_info:
            QMessageBox.critical(self, "Error", "Modpack information not found.")
            return

        # Handle repository name and path
        repo_name = f"{modpack_name}-{selected_branch}" if selected_branch != "main" else modpack_name
        repo_path = os.path.join(os.getcwd(), "Modpacks", repo_name)
        mods_src = os.path.join(repo_path, "Mods")
        install_path = self.mods_dir
        mod_list = self.get_mod_list(mods_src)

        # Handle special cases based on URL type
        if modpack_info['url'].endswith('.git'):
            repo_name = modpack_info['url'].split('/')[-1].replace('.git', '')
        else:
            repo_name = modpack_name.replace(' ', '_')

        try:
            # Check if the repository directory exists
            if not os.path.isdir(repo_path):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Modpack {repo_path} does not exist. Please download first.")
                msg_box.exec()
                return

            # Check if the Mods folder exists in the repository
            if not os.path.isdir(mods_src):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Mods folder not found in the repository: {mods_src}. Please force download and try again.")
                msg_box.exec()
                return

            # Check if the install path exists and create it if necessary
            if not os.path.exists(install_path):
                os.makedirs(install_path)

            if skip_mod_selection:
                # Install all mods without showing the mod selection popup
                self.excluded_mods = []  # No mods are excluded
                self.install_mods(None)  # Pass None as we don't have a popup
            else:
                # Show mod selection popup
                self.popup_mod_selection(mod_list, dependencies)

        except Exception as e:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"An unexpected error occurred during installation: {str(e)}")
            msg_box.exec()

    def get_mod_list(self, mods_src):
        try:
            return sorted([f for f in os.listdir(mods_src) if os.path.isdir(os.path.join(mods_src, f))], key=lambda s: s.lower())
        except FileNotFoundError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Mods folder not found.")
            msg_box.exec()
            return []
        
    def popup_mod_selection(self, mod_list, dependencies):

        # Add mods to the middle panel
        always_installed = {"Steamodded", "ModpackUtil"}  # Mods that are always installed and not displayed

        if self.install_popup_open:
            return

        self.install_popup_open = True

        # Ensure metadata is available
        if not self.metadata:
            QMessageBox.critical(self, "Error", "Metadata for mods is not loaded. Please check your internet connection.")
            return

        # Create a popup window for mod selection
        popup = QDialog(self)
        popup.setWindowTitle("Mod Selection")

        # Create a QSplitter to divide left (filters) and middle (mods) panels
        splitter = QSplitter(popup)
        splitter.setOrientation(Qt.Orientation.Horizontal)

        # Extract unique genres and tags from metadata
        genres = sorted(set(info['Genre'] for info in self.metadata.values()))
        tags = sorted({tag for info in self.metadata.values() for tag in info['Tags']})

        # Left panel (Filters)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_scroll_area = QScrollArea(popup)
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setWidget(left_panel)

        # Search bar
        search_bar = QLineEdit(popup)
        search_bar.setPlaceholderText("Search mods...")
        left_layout.addWidget(search_bar)

        # Favorite mods filter
        favorite_filter_checkbox = QCheckBox("Show favorites", popup)
        left_layout.addWidget(favorite_filter_checkbox)

        # Genre filter section
        genre_label = QLabel("Genres", popup)
        genre_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(genre_label)

        genre_checkboxes = []
        for genre in genres:
            genre_checkbox = QCheckBox(genre, popup)
            left_layout.addWidget(genre_checkbox)
            genre_checkboxes.append(genre_checkbox)

        # Tags filter section
        tags_label = QLabel("Tags (WIP)", popup)
        tags_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(tags_label)

        tag_checkboxes = []
        for tag in tags:
            tag_checkbox = QCheckBox(tag, popup)
            left_layout.addWidget(tag_checkbox)
            tag_checkboxes.append(tag_checkbox)

        # Spacer to fill the remaining space
        left_layout.addStretch()

        # Middle panel (Scrollable mod list)
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)

        middle_scroll_area = QScrollArea(popup)
        middle_scroll_area.setWidgetResizable(True)

        mod_container = QWidget()
        mod_layout = QVBoxLayout(mod_container)
        mod_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align mods to the top of the container

        middle_scroll_area.setWidget(mod_container)
        middle_layout.addWidget(middle_scroll_area)

        def add_context_menu(mod_row_container, mod, metadata):
            """Add a right-click context menu to the mod row."""
            def open_discord():
                discord_url = metadata.get(mod, {}).get("Discord Link", None)
                if discord_url:
                    webbrowser.open(discord_url)
                else:
                    QMessageBox.information(mod_row_container, "Info", "Discord link not available for this mod.")

            def open_mod_page():
                mod_page_url = metadata.get(mod, {}).get("Page Link", None)
                if mod_page_url:
                    webbrowser.open(mod_page_url)
                else:
                    QMessageBox.information(mod_row_container, "Info", "Mod page link not available for this mod.")

            # Add context menu to mod row
            def show_context_menu(event):
                if event.button() == Qt.MouseButton.RightButton:
                    context_menu = QMenu(mod_row_container)
                    discord_action = context_menu.addAction("Visit Discord Channel")
                    github_action = context_menu.addAction("Visit Mod Page")

                    # Connect actions to their respective functions
                    discord_action.triggered.connect(open_discord)
                    github_action.triggered.connect(open_mod_page)

                    # Show the menu at the cursor's position
                    context_menu.exec(event.globalPosition().toPoint())

            mod_row_container.mousePressEvent = show_context_menu

        mod_vars = []  # Clear any existing data

        def toggle_favorite(label, mod):
            """Toggle favorite state for the given mod."""
            if mod in self.favorite_mods:
                self.favorite_mods.remove(mod)
                label.setText("☆")  # Empty star
            else:
                self.favorite_mods.add(mod)
                label.setText("★")  # Solid star
            
            self.save_favorites()  # Save favorites whenever they are toggled
            filter_mods()  # Reapply the filter to reflect changes immediately

        for mod in mod_list:
            if mod in always_installed:
                continue  # Skip mods in the excluded list

            mod_row_container = QWidget(mod_container)
            mod_row_layout = QHBoxLayout(mod_row_container)
            mod_row_layout.setContentsMargins(0, 0, 0, 0)
            mod_row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            mod_checkbox = QCheckBox(mod, popup)
            mod_checkbox.setChecked(mod not in self.excluded_mods)  # Default to checked

            # Add a star label for favorite mods
            star_label = QLabel("★" if mod in self.favorite_mods else "☆", popup)
            star_label.setStyleSheet("font-size: 20px; color: black;")
            star_label.setCursor(Qt.CursorShape.PointingHandCursor)  # Clickable star
            star_label.mousePressEvent = lambda _, mod=mod, label=star_label: toggle_favorite(label, mod)

            # Attach the context menu to the mod row container
            add_context_menu(mod_row_container, mod, self.metadata)

            # Retrieve metadata for the mod
            mod_metadata = self.metadata.get(mod, {})
            genre = mod_metadata.get("Genre", "Unknown")
            tags = ", ".join(mod_metadata.get("Tags", []))
            description = mod_metadata.get("Description", "No description available.")
            
            # Combine metadata into a tooltip text
            tooltip_text = f"<b>Genre:</b> {genre}<br><b>Tags:</b> {tags}<br><b>Description:</b> {description}"
            
            # Set the tooltip for the checkbox
            mod_checkbox.setToolTip(tooltip_text)

            # Append all elements to mod_vars
            mod_vars.append((mod_row_container, mod, mod_checkbox, star_label))

            # Add widgets to the layout
            mod_row_layout.addWidget(star_label)
            mod_row_layout.addWidget(mod_checkbox)
            mod_layout.addWidget(mod_row_container)

            # Connect state change event for dependency handling
            mod_checkbox.stateChanged.connect(
                lambda _, mod_name=mod, mod_var=mod_checkbox: self.handle_dependencies(mod_name, mod_var, mod_vars, dependencies)
            )

        # Add a right panel for presets
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_label = QLabel("Modpack Presets", popup)
        right_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(right_label)

        # List of presets
        self.presets_dropdown = QComboBox(popup)
        self.update_presets_dropdown()  # Populate the dropdown
        right_layout.addWidget(self.presets_dropdown)

        # Buttons to manage presets
        save_preset_button = QPushButton("Save Preset", popup)
        save_preset_button.clicked.connect(lambda: self.save_preset(mod_vars))
        right_layout.addWidget(save_preset_button)

        load_preset_button = QPushButton("Load Preset", popup)
        load_preset_button.clicked.connect(lambda: self.load_preset(mod_vars))
        right_layout.addWidget(load_preset_button)

        delete_preset_button = QPushButton("Delete Preset", popup)
        delete_preset_button.clicked.connect(self.delete_preset)
        right_layout.addWidget(delete_preset_button)

        # Spacer to align elements at the top
        right_layout.addStretch()

        # Add panels to splitter
        splitter.addWidget(left_scroll_area)
        splitter.addWidget(middle_scroll_area)
        splitter.addWidget(right_panel)

        # Set fixed width for left panel
        splitter.setSizes([800, 1000, 400])

        # Layout for popup
        main_layout = QVBoxLayout(popup)
        main_layout.addWidget(splitter)

        # Integrate the "Show favorites" filter
        def filter_mods():
            query = search_bar.text().lower()
            selected_genres = {checkbox.text() for checkbox in genre_checkboxes if checkbox.isChecked()}
            selected_tags = {checkbox.text() for checkbox in tag_checkboxes if checkbox.isChecked()}
            show_only_favorites = favorite_filter_checkbox.isChecked()

            for mod_row_container, mod, _, _ in mod_vars:
                mod_metadata = self.metadata.get(mod, {})
                mod_genre = mod_metadata.get("Genre", "Unknown")
                mod_tags = set(mod_metadata.get("Tags", []))
                matches_query = query in mod.lower()
                matches_genre = not selected_genres or mod_genre in selected_genres
                matches_tags = not selected_tags or bool(selected_tags.intersection(mod_tags))
                is_favorite = mod in self.favorite_mods  # Use self.favorite_mods directly

                # Determine visibility
                should_show = matches_query and matches_genre and matches_tags
                if show_only_favorites:
                    should_show = should_show and is_favorite

                mod_row_container.setVisible(should_show)

        # Connect the "Show favorites" checkbox to the filter function
        favorite_filter_checkbox.stateChanged.connect(filter_mods)
        search_bar.textChanged.connect(filter_mods)
        for checkbox in genre_checkboxes + tag_checkboxes:
            checkbox.stateChanged.connect(filter_mods)

        # Buttons for actions
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        clear_button = QPushButton("Clear All", popup)
        reverse_button = QPushButton("Reverse Select", popup)
        feel_lucky_button = QPushButton("I Feel Lucky", popup)
        save_button = QPushButton("Save & Install", popup)

        clear_button.clicked.connect(lambda: [checkbox.setChecked(False) for _, _, checkbox, _ in mod_vars])
        reverse_button.clicked.connect(lambda: self.reverse_select_with_dependencies(mod_vars, dependencies))
        feel_lucky_button.clicked.connect(lambda: [checkbox.setChecked(random.choice([True, False])) for _, _, checkbox, _ in mod_vars])
        save_button.clicked.connect(lambda: self.save_and_install([(mod, checkbox) for _, mod, checkbox, _ in mod_vars], popup))

        button_layout.addWidget(clear_button)
        button_layout.addWidget(reverse_button)
        button_layout.addWidget(feel_lucky_button)
        button_layout.addWidget(save_button)
        main_layout.addWidget(button_container)

        # Add checkboxes for Backup and Remove Mods
        checkbox_container = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_container)

        # Create the "Backup Mods Folder" and "Remove Mods Folder" checkboxes
        self.backup_checkbox = QCheckBox("Backup Mods Folder", popup)
        self.remove_checkbox = QCheckBox("Remove Mods Folder", popup)

        self.backup_checkbox.setChecked(self.settings.get("backup_mods", False))
        self.remove_checkbox.setChecked(self.settings.get("remove_mods", True))

        checkbox_layout.addWidget(self.backup_checkbox)
        checkbox_layout.addWidget(self.remove_checkbox)
        main_layout.addWidget(checkbox_container)

        # Close event handler to reset the flag when the window is closed
        def on_close():
            self.install_popup_open = False
            popup.close()

        popup.finished.connect(on_close)
        popup.exec()

    def handle_dependencies(self, mod, var, mod_vars, dependencies):
        """
        Handle mod dependencies when a checkbox state changes.
        Args:
            mod (str): The mod whose state changed.
            var (QCheckBox): The checkbox associated with the mod.
            mod_vars (list): List of (mod_row_container, mod_name, QCheckBox, star_label).
            dependencies (dict): Dependency mapping of mods.
        """
        mod_dict = {mod_name: (mod_var, mod_row_container) for mod_row_container, mod_name, mod_var, _ in mod_vars}

        def include_required_mods(dependent_mod):
            required_mods = dependencies.get(dependent_mod, [])
            for required_mod in required_mods:
                required_var, required_container = mod_dict.get(required_mod, (None, None))
                if required_var and not required_var.isChecked() and required_container.isVisible():
                    required_var.blockSignals(True)
                    required_var.setChecked(True)
                    required_var.blockSignals(False)
                    include_required_mods(required_mod)

        def exclude_dependent_mods(required_mod):
            for dependent_mod, required_mods in dependencies.items():
                if required_mod in required_mods:
                    dependent_var, dependent_container = mod_dict.get(dependent_mod, (None, None))
                    if dependent_var and dependent_var.isChecked() and dependent_container.isVisible():
                        dependent_var.blockSignals(True)
                        dependent_var.setChecked(False)
                        dependent_var.blockSignals(False)
                        exclude_dependent_mods(dependent_mod)

        if var.isChecked():  # Include the mod
            include_required_mods(mod)
        else:  # Exclude the mod
            exclude_dependent_mods(mod)

    def reverse_select_with_dependencies(self, mod_vars, dependencies):
        """
        Reverse the checked state of visible mods and process dependencies afterward.
        Args:
            mod_vars (list): List of (mod_row_container, mod_name, QCheckBox, star_label).
            dependencies (dict): Dependency mapping of mods.
        """
        # Step 1: Flip the checked state of all visible mods
        for mod_row_container, mod_name, checkbox, _ in mod_vars:
            if mod_row_container.isVisible():
                checkbox.blockSignals(True)  # Prevent triggering dependency logic during the flip
                checkbox.setChecked(not checkbox.isChecked())
                checkbox.blockSignals(False)

        # Step 2: Process dependencies for all visible mods based on their new state
        for mod_row_container, mod_name, checkbox, _ in mod_vars:
            if mod_row_container.isVisible():
                self.handle_dependencies(mod_name, checkbox, mod_vars, dependencies)

    def save_preferences(self, mod_vars):
        # Collect mods that are unchecked (excluded from installation)
        excluded_mods = [mod for mod, var in mod_vars if not var.isChecked()]
        try:
            with open(INSTALL_FILE, "w") as f:
                json.dump(excluded_mods, f, indent=4)
            print(f"Excluded mods saved successfully: {excluded_mods}")
        except Exception as e:
            print(f"Failed to save excluded mods: {e}")

    def read_preferences(self):
        try:
            with open(INSTALL_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    # Load favorites from the file
    def load_favorites(self):
        """Load favorite mods from a JSON file."""
        favorites_file = "favorites.json"  # Path to favorites file
        try:
            if os.path.exists(favorites_file):
                with open(favorites_file, "r") as f:
                    self.favorite_mods = set(json.load(f))  # Load favorites into a set
            else:
                self.favorite_mods = set()  # Initialize as an empty set if the file doesn't exist
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading favorites: {e}")
            self.favorite_mods = set()  # Default to empty set on failure

    # Save favorites to the file
    def save_favorites(self):
        """Save favorite mods to a JSON file."""
        favorites_file = "favorites.json"  # Path to favorites file
        try:
            with open(favorites_file, "w") as f:
                json.dump(list(self.favorite_mods), f, indent=4)  # Save favorites as a list
        except IOError as e:
            print(f"Error saving favorites: {e}")

    def reset_favorites_file(self):
        """Reset the favorites file if corrupted."""
        try:
            with open(FAVORITES_FILE, "w") as f:
                json.dump([], f)  # Reset to an empty list
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset favorite mods file. Error: {e}")

    def save_preset(self, mod_vars):
        """Save the current mod selection as a preset."""
        preset_name, ok = QInputDialog.getText(self, "Save Preset", "Enter a name for this preset:")
        if not ok or not preset_name.strip():
            return

        # Save selected mods as a preset
        selected_mods = [mod for _, mod, checkbox, _ in mod_vars if checkbox.isChecked()]
        presets = self.load_presets()
        presets[preset_name] = selected_mods
        self.write_presets(presets)

        QMessageBox.information(self, "Preset Saved", f"Preset '{preset_name}' saved successfully.")
        self.update_presets_dropdown()

    def load_preset(self, mod_vars):
        """Load the selected preset and apply it to the mod selection."""
        preset_name = self.presets_dropdown.currentText()
        if not preset_name:
            QMessageBox.warning(self, "Load Preset", "No preset selected.")
            return

        presets = self.load_presets()
        selected_mods = presets.get(preset_name, [])
        if not selected_mods:
            QMessageBox.warning(self, "Load Preset", f"Preset '{preset_name}' is empty or invalid.")
            return

        for _, mod, checkbox, _ in mod_vars:
            checkbox.setChecked(mod in selected_mods)

    def delete_preset(self):
        """Delete the selected preset."""
        preset_name = self.presets_dropdown.currentText()
        if not preset_name:
            QMessageBox.warning(self, "Delete Preset", "No preset selected.")
            return

        presets = self.load_presets()
        if preset_name in presets:
            del presets[preset_name]
            self.write_presets(presets)
            QMessageBox.information(self, "Preset Deleted", f"Preset '{preset_name}' deleted successfully.")
            self.update_presets_dropdown()

    def load_presets(self):
        """Load presets from the JSON file."""
        try:
            with open("presets.json", "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def write_presets(self, presets):
        """Write presets to the JSON file."""
        with open("presets.json", "w") as file:
            json.dump(presets, file, indent=4)

    def update_presets_dropdown(self):
        """Update the presets dropdown with the available presets."""
        presets = self.load_presets()
        self.presets_dropdown.clear()
        self.presets_dropdown.addItems(presets.keys())

    def install_mods(self, popup):
        """
        Install mods with a progress bar showing the current mod being copied.
        Args:
            popup (QDialog): The mod selection popup (optional).
        """
        # Read excluded mods
        excluded_mods = self.read_preferences()
        modpack_name = self.modpack_var.currentText()
        selected_branch = self.branch_var.currentText()


        # Handle special case for "Coonie's Modpack"
        if modpack_name == "Coonie's Modpack":
            repo_path = os.path.join(os.getcwd(), "Coonies-Modpack")
        else:
            repo_name = f"{modpack_name}-{selected_branch}" if selected_branch != "main" else modpack_name
            repo_path = os.path.join(os.getcwd(),"Modpacks", repo_name)

        mods_src = os.path.join(repo_path, 'Mods')

        # Check if the Mods directory exists and warn the user
        if os.path.isdir(self.mods_dir):
            # Backup existing mods folder if enabled
            backup_mods = self.settings.get("backup_mods", False)
            if hasattr(self, 'backup_checkbox'):  # Use checkbox if available
                backup_mods = self.backup_checkbox.isChecked()

            if backup_mods:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                backup_folder = os.path.join(os.path.dirname(self.mods_dir), f"Mods-backup-{timestamp}")
                try:
                    shutil.move(self.mods_dir, backup_folder)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to backup Mods folder. Error: {e}")
                    return

            # Remove existing mods folder if enabled
            remove_mods = self.settings.get("remove_mods", False)
            if hasattr(self, 'remove_checkbox'):  # Use checkbox if available
                remove_mods = self.remove_checkbox.isChecked()

            if remove_mods:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("The current 'Mods' folder will be erased. Do you want to proceed?")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                response = msg_box.exec()
                if response == QMessageBox.StandardButton.No:
                    return
                try:
                    shutil.rmtree(self.mods_dir, ignore_errors=True)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to remove Mods folder. Error: {e}")
                    return

        # Ensure the install directory exists
        if not os.path.exists(self.mods_dir):
            os.makedirs(self.mods_dir)

        # Create a progress dialog
        progress_dialog = QProgressDialog("Installing mods...", "Cancel", 0, 100, self)
        progress_dialog.setWindowTitle("Installation Progress")
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)

        # Always install "Steamodded" and "ModpackUtil"
        mandatory_mods = {"Steamodded", "ModpackUtil"}
        all_mods = mandatory_mods.union(set(os.listdir(mods_src)))
        filtered_mods = [mod for mod in all_mods if mod not in excluded_mods or mod in mandatory_mods]

        try:
            # Iterate through mods and copy them
            total_mods = len(filtered_mods)
            for index, mod in enumerate(filtered_mods, start=1):
                source_mod_path = os.path.join(mods_src, mod)
                destination_mod_path = os.path.join(self.mods_dir, mod)

                # Update progress dialog
                progress_percentage = int((index / total_mods) * 100)
                progress_dialog.setValue(progress_percentage)
                progress_dialog.setLabelText(f"Copying mod: {mod} ({index}/{total_mods})")
                QApplication.processEvents()  # Keep the UI responsive

                # Handle user cancellation
                if progress_dialog.wasCanceled():
                    QMessageBox.warning(self, "Installation Canceled", "The installation process was canceled.")
                    return

                # Perform the copy operation
                if os.path.exists(destination_mod_path):
                    shutil.rmtree(destination_mod_path)
                shutil.copytree(source_mod_path, destination_mod_path)

            # Close the progress dialog
            progress_dialog.close()

            # Show installation success message
            QMessageBox.information(self, "Install Status", "Successfully installed modpack.")

        except Exception as e:
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"An error occurred during installation: {e}")

        finally:
            self.mods_path = os.path.expandvars(self.settings.get("mods_directory"))
            remove_debug_folders(self.mods_path)

            # Ensure the installation popup is closed
            if popup:
                self.install_popup_open = False
                popup.close()

    def save_and_install(self, mod_vars, popup):
        self.save_preferences(mod_vars)
        self.excluded_mods = self.read_preferences()
        self.install_mods(popup)
        
    def uninstall_modpack(self):
        self.settings = self.load_settings()
        install_path = self.mods_dir

        # Confirm the uninstallation
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle("Confirm Uninstallation")
        msg_box.setText("Are you sure you want to uninstall the modpack? This action cannot be undone.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        # Show the confirmation dialog and proceed if Yes is clicked
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(install_path):
                    shutil.rmtree(install_path, onerror=readonly_handler)

                    # Show success message
                    success_box = QMessageBox()
                    success_box.setIcon(QMessageBox.Icon.Information)
                    success_box.setWindowTitle("Uninstall Status")
                    success_box.setText("Modpack uninstalled successfully.")
                    success_box.exec()
                else:
                    # Show warning message
                    warning_box = QMessageBox()
                    warning_box.setIcon(QMessageBox.Icon.Warning)
                    warning_box.setWindowTitle("Uninstall Status")
                    warning_box.setText("No modpack found to uninstall.")
                    warning_box.exec()
            except Exception as e:
                # Show error message
                error_box = QMessageBox()
                error_box.setIcon(QMessageBox.Icon.Critical)
                error_box.setWindowTitle("Error")
                error_box.setText(f"An error occurred during uninstallation: {str(e)}")
                error_box.exec()

############################################################
# Bottom functions (Check versions, lovely, browser links)
############################################################

    # Function to check if a folder is empty or contains only a '.git' directory
    def is_empty_or_git_only(self, folder_path):
        try:
            # Get list of files/folders in the current directory, excluding hidden files
            items = [item for item in os.listdir(folder_path) if not item.startswith('.')]
            if len(items) == 0:
                return True  # Folder is empty
            if len(items) == 1 and items[0] == '.git':
                return True  # Folder contains only .git
            return False
        except Exception as e:
            print(f"Error while processing {folder_path}: {str(e)}")
            return False

    # Function to list all empty or git-only folders
    def list_empty_or_git_only_folders(self, root_folder):
        empty_or_git_only_folders = []
        for dirpath, _, _ in os.walk(root_folder):
            if self.is_empty_or_git_only(dirpath):
                empty_or_git_only_folders.append(os.path.basename(dirpath))  # Append folder name, not full path
        return empty_or_git_only_folders

    # Verification function for a specific modpack folder
    def verify_modpack_folder(self, modpack_folder):
        print(f"Verifying modpack folder: {modpack_folder}")
        self.list_empty_or_git_only_folders(modpack_folder)

    # Function to verify the integrity of the 'Mods' folder of the currently selected modpack
    def verify_modpack_integrity(self):
        """Verify the integrity of the selected modpack."""
        modpack_name = self.modpack_var.currentText()  # Get the name of the selected modpack

        # Handle special case for Coonie's Modpack
        if modpack_name == "Coonie's Modpack":
            repo_name = "Coonies-Modpack"
        else:
            clone_url = self.get_modpack_url(modpack_name)
            if not clone_url:
                QMessageBox.critical(self, "Error", f"URL not found for modpack '{modpack_name}'.")
                return
            repo_name = clone_url.split('/')[-1].replace('.git', '')

        # Ensure the folder is inside the 'Modpacks' directory
        modpack_folder = os.path.join(os.getcwd(), "Modpacks", repo_name, "Mods")

        if not os.path.isdir(modpack_folder):
            QMessageBox.warning(
                self,
                "Mods Folder Not Found",
                f"The 'Mods' folder for {modpack_name} was not found in '{modpack_folder}'.",
            )
            return

        # Call the verification function to get the list of empty or .git-only folders
        empty_or_git_only_folders = self.list_empty_or_git_only_folders(modpack_folder)

        # Show the result in a message box
        if empty_or_git_only_folders:
            folder_list = "\n".join(empty_or_git_only_folders)
            QMessageBox.information(
                self,
                "Verification Result",
                f"The following mods are not downloaded correctly. Please attempt reclone:\n\n{folder_list}",
            )
        else:
            QMessageBox.information(
                self,
                "Verification Complete",
                f"All folders in the 'Mods' folder for {modpack_name} are properly populated.",
            )

    def check_versions(self):
        try:
            # Fetch commit messages
            commit_messages = self.fetch_commit_messages()
            coonies_version_info = self.get_latest_coonies_tag()

            # Prepare version information
            version_info = ""
            for repo_name, commit_message in commit_messages.items():
                version_info += f"{repo_name}:\t{commit_message}\n"

            # Display version and update information
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Version Information")
            msg_box.setText(f"{version_info}\nCoonie's:\t{coonies_version_info}")
            msg_box.exec()

        except Exception as e:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"An error occurred while checking versions: {str(e)}")
            msg_box.exec()

    def read_file_content(self, file_path):
        """Helper function to read file content and handle IOErrors."""
        try:
            with open(file_path, 'r') as file:
                return file.read().strip()
        except IOError as e:
            print(f"IOError reading {file_path}: {e}")
            return None

    def extract_pack_name(self, lua_file_path):
        """Helper to extract the pack name from ModpackUtil.lua."""
        try:
            with open(lua_file_path, 'r') as file:
                for line in file:
                    if line.startswith('--- VERSION:'):
                        return line.split(':')[1].strip()
        except IOError as e:
            print(f"IOError reading {lua_file_path}: {e}")
        return None

    def get_latest_coonies_tag(self):
        """Fetch the latest tag name from the Coonie's Modpack GitHub repository."""
        try:
            api_url = "https://api.github.com/repos/GayCoonie/Coonies-Mod-Pack/tags"
            response = requests.get(api_url)
            if response.status_code == 200:
                tags = response.json()
                if tags:
                    # Return the latest tag's name
                    return tags[0]['name']
                else:
                    return "No tags found"
            else:
                raise Exception(f"GitHub API request failed with status code {response.status_code}")
        except Exception as e:
            print(f"Error fetching latest tag for Coonie's Modpack: {e}")
            return "Unknown"

    def install_lovely_injector(self):
        # Prompt user to confirm the installation
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle("Install Lovely Injector")
        msg_box.setText("This installation requires disabling antivirus software temporarily and whitelisting the Balatro game directory. Proceed?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg_box.exec() != QMessageBox.StandardButton.Yes:
            return

        # Determine platform and download URL
        system = platform.system()
        arch = platform.machine()

        if system == "Darwin":  # macOS
            if arch == "arm64":
                url = "https://github.com/ethangreen-dev/lovely-injector/releases/latest/download/lovely-aarch64-apple-darwin.tar.gz"
            elif arch == "x86_64":
                url = "https://github.com/ethangreen-dev/lovely-injector/releases/latest/download/lovely-x86_64-apple-darwin.tar.gz"
            else:
                QMessageBox.critical(None, "Error", "Unsupported macOS architecture.")
                return
            archive_name = "lovely-injector.tar.gz"
            extracted_files = ["liblovely.dylib", "run_lovely.sh"]
        else:
            url = "https://github.com/ethangreen-dev/lovely-injector/releases/latest/download/lovely-x86_64-pc-windows-msvc.zip"
            archive_name = "lovely-injector.zip"
            extracted_files = ["version.dll"]

        # Expand and normalize the game directory path
        game_dir = os.path.abspath(os.path.expanduser(self.game_dir))
        archive_path = os.path.join(game_dir, archive_name)

        # Verify existence of the game executable
        game_exe = "Balatro.app" if system == "Darwin" else "balatro.exe"
        game_path = os.path.join(game_dir, game_exe)
        if not os.path.exists(game_path):
            warning_box = QMessageBox()
            warning_box.setIcon(QMessageBox.Icon.Warning)
            warning_box.setWindowTitle("Warning")
            warning_box.setText("Game executable not found in the default directory. Please specify it in settings.")
            warning_box.exec()
            return

        # Download and extract the archive
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(archive_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            if archive_name.endswith(".zip"):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(game_dir)
            elif archive_name.endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(game_dir)

            # Verify extracted files
            missing_files = [f for f in extracted_files if not os.path.exists(os.path.join(game_dir, f))]
            if missing_files:
                raise FileNotFoundError(f"Missing files after extraction: {', '.join(missing_files)}")

            os.remove(archive_path)  # Clean up

            success_box = QMessageBox()
            success_box.setIcon(QMessageBox.Icon.Information)
            success_box.setWindowTitle("Install Status")
            success_box.setText("Lovely Injector installed successfully.")
            success_box.exec()

        except requests.RequestException as e:
            QMessageBox.critical(None, "Error", f"Failed to download Lovely Injector: {e}")
            if os.path.exists(archive_path):
                os.remove(archive_path)
        except (zipfile.BadZipFile, tarfile.TarError) as e:
            QMessageBox.critical(None, "Error", f"Failed to extract the archive: {e}")
            if os.path.exists(archive_path):
                os.remove(archive_path)
        except Exception as e:
            QMessageBox.critical(None, "Error", f"An unexpected error occurred during installation: {str(e)}")

    def check_lovely_injector_installed(self):
        """Check if Lovely Injector is installed and prompt the user to install if not."""
        system = platform.system()

        # Expand and normalize the game directory path
        game_dir = os.path.abspath(os.path.expanduser(self.game_dir))

        if system == "Windows":
            lovely_path = os.path.join(game_dir, "version.dll")
        elif system == "Darwin":  # macOS
            lovely_path = os.path.join(game_dir, "liblovely.dylib")

        if not os.path.exists(lovely_path):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle("Lovely Injector Not Found")
            msg_box.setText(
                "Lovely Injector is not installed. It is required for the game to function properly.\n"
                "Would you like to install it now?"
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

            if msg_box.exec() == QMessageBox.StandardButton.Yes:
                self.install_lovely_injector()
                # Re-check if installation was successful
                if os.path.exists(lovely_path):
                    return True
                else:
                    QMessageBox.critical(
                        None,
                        "Error",
                        "Lovely Injector installation failed. Please try again or check your settings.",
                    )
                    return False
            else:
                return False  # User declined to install Lovely Injector

        return True  # Lovely Injector is installed


    def open_discord(self):
        # Check if the user has already joined the official Discord
        webbrowser.open("https://discord.com/invite/balatro")
        webbrowser.open("https://discord.com/channels/1116389027176787968/1255696773599592458")

    def open_mod_list(self): 
        webbrowser.open("https://docs.google.com/spreadsheets/d/1L2wPG5mNI-ZBSW_ta__L9EcfAw-arKrXXVD-43eU4og")

############################################################
# Misc functions
############################################################

def readonly_handler(func, path, _):
    # Remove read-only attribute and retry
    os.chmod(path, stat.S_IWRITE)
    func(path)

def center_window(window, width, height):
    # Get the screen width and height
    screen_geometry = window.screenGeometry()
    screen_width = screen_geometry.width()
    screen_height = screen_geometry.height()

    # Calculate the position for the window to be centered
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    # Set the geometry of the window
    window.setGeometry(int(x), int(y), width, height)
    
if __name__ == "__main__":

    app = QApplication([])  # Initialize the QApplication

    root = ModpackManagerApp()  # No need to pass 'root', since the window is handled by PyQt itself

    # Set global stylesheet to apply a 1pt gray border to all QPushButtons
    app.setStyleSheet("""
        QWidget {
            background-color: #f3f3f3;  /* Set background color */
            color: #000000;  /* Set text color */
        }
                    
        QMainWindow, QDialog, QWidget {
            background-color: #f3f3f3;  /* Force window background to white */
        }
                    
        QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QSpinBox {
            color: #000000;  /* Force text color to black */
        }
                    
        QPushButton {
            border: 1px solid gray;
            border-radius: 5px;
            padding-top: 8px;   /* Equivalent to ipady */
            padding-bottom: 8px; /* Equivalent to ipady */
            padding-left: 5px;  /* Equivalent to ipadx */
            padding-right: 5px; /* Equivalent to ipadx */
            background-color: #f3f3f3;  /* Default background color */
        }
                    
        QPushButton:hover {
            background-color: #dadada;  /* Hover color */
        }
                    
        QPushButton:pressed {
            background-color: #aaaaaa;  /* Press color */
        }
                    
        QPushButton:disabled {
            background-color: #e0e0e0;  /* Disabled background color */
            color: #a0a0a0;  /* Disabled text color */
            border: 1px solid #cccccc;  /* Disabled border color */
        }
                    
        QSpinBox {
            padding: 10px;  /* Set padding for spinbox */
            border: 1px solid gray;  /* Dropdown border */
        }
                    
        QComboBox {
            padding: 10px 10px;  /* Padding inside the dropdown */
            background-color: #f3f3f3;  /* Default background color */
            border: 1px solid gray;  /* Dropdown border */
        }
                    
        QComboBox QLineEdit {
            padding: 20px;  /* Padding inside the editable field */
            background-color: #f3f3f3;  /* Background color for editable field */
            border: none;  /* Remove the border for the internal QLineEdit */
        }
                    
        QLineEdit {
            background-color: #f3f3f3;  /* Background for input fields */
            border: 1px solid gray;
            border-radius: 5px;
            padding-left: 10px;
            padding-right: 10px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
                    
        QCheckBox {
            background-color: transparent;  /* Transparent background for checkboxes */
        }
                    
    """)

    # Center the window
    screen_geometry = app.primaryScreen().availableGeometry()
    window_width = root.sizeHint().width()
    window_height = root.sizeHint().height()

    # Calculate position for the window to be centered
    position_x = (screen_geometry.width() - window_width) // 2
    position_y = (screen_geometry.height() - window_height) // 2

    # Set the window size and position
    root.setGeometry(position_x, position_y, window_width, window_height)

    root.show()  # Show the main window
    app.exec()   # Execute the application's event loop