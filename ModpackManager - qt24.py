import subprocess, math, os, random, re, shutil, requests, webbrowser, zipfile, stat, json, git, time, platform
from datetime import datetime
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtCore import QUrl, Qt, QTimer, QProcess, QThread, pyqtSignal, QPoint
from PyQt6.QtWidgets import QFrame, QProgressDialog, QHBoxLayout, QFileDialog, QMessageBox, QApplication, QCheckBox, QLineEdit, QDialog, QLabel, QPushButton, QComboBox, QGridLayout, QWidget, QVBoxLayout, QSpinBox
from git import Repo, GitCommandError
os.environ['GIT_PYTHON_REFRESH'] = 'quiet'

############################################################
# Detect OS and set default settings
############################################################

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
        "auto_install_after_download": False,
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
        "auto_install_after_download": False,
    }

# File paths for settings and installation exclusions
SETTINGS_FILE = "user_settings.json"
INSTALL_FILE = "excluded_mods.json" 

DATE = "2024/12/21"
ITERATION = "24"
VERSION = "1.5.5"

def set_git_buffer_size():
    try:
        # Increase the buffer size globally
        subprocess.run(['git', 'config', '--global', 'http.postBuffer', '524288000'], check=True)
        print("Git buffer size set to 500MB")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set Git buffer size: {e}")

# Call this function before performing Git operations
set_git_buffer_size()

############################################################
# Worker class for downloading/updating modpack in the background
############################################################

url = "https://raw.githubusercontent.com/Dimserene/ModpackManager/main/information.json"

def fetch_modpack_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()       # Parse JSON data
        return data
    except requests.RequestException as e:
        print(f"Failed to fetch data: {e}")
        return None

modpack_data = fetch_modpack_data(url)

class ModpackDownloadWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)  # Signal to update progress (optional)

    def __init__(self, clone_url, repo_name, force_update=False):
        super().__init__()
        self.clone_url = clone_url
        self.repo_name = repo_name
        self.force_update = force_update
        self.process = None  # Store the QProcess instance

    def run(self):
        try:
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
                # Clone the repository using Git
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)  # Merge stdout and stderr
                git_command = ["git", "clone", "--recurse-submodules", "--remote-submodules", self.clone_url, self.repo_name]
                
                # Connect QProcess signals for dynamic error capturing
                self.process.finished.connect(self.git_finished)
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

class ModpackUpdateWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)  # Optional progress signal if a progress bar is desired

    def __init__(self, repo_path):
        super().__init__()
        self.repo_path = repo_path

    def run(self):
        try:
            # Check if the repo path exists and is a valid Git repository
            if not os.path.exists(self.repo_path) or not os.path.isdir(self.repo_path):
                self.finished.emit(False, f"Invalid repository path: {self.repo_path}")
                return

            # Initialize the Git repository
            repo = Repo(self.repo_path)

            # Perform git pull and update the submodules
            print("Pulling latest changes...")
            repo.remotes.origin.pull()

            # Count total submodules for progress tracking
            total_submodules = len(repo.submodules)
            for idx, submodule in enumerate(repo.submodules):
                try:
                    print(f"Updating submodule: {submodule.name} ({idx + 1}/{total_submodules})")
                    submodule.update(init=True, recursive=True)

                    # Emit progress update (optional)
                    progress_percent = int(((idx + 1) / total_submodules) * 100)
                    self.progress.emit(progress_percent)
                except GitCommandError as submodule_error:
                    self.finished.emit(False, f"Failed to update submodule '{submodule.name}': {str(submodule_error)}")
                    return

            # Emit success signal if everything was updated
            self.finished.emit(True, "Modpack updated successfully.")
        except GitCommandError as e:
            self.finished.emit(False, f"Failed to update modpack: {str(e)}")
        except Exception as e:
            self.finished.emit(False, f"An unexpected error occurred: {str(e)}")

class MultiModpackWorker(QThread):
    progress = pyqtSignal(int)
    status_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # Signal with two arguments (success, message)

    def __init__(self, modpack_names, operation, main_window):
        super().__init__()
        self.modpack_names = modpack_names
        self.operation = operation  # 'download' or 'update'
        self.main_window = main_window

    def run(self):
        try:
            for index, modpack_name in enumerate(self.modpack_names):
                # Check for cancellation
                if self.isInterruptionRequested():
                    self.status_message.emit("Operation cancelled.")
                    self.finished.emit(False, "Operation cancelled by the user.")
                    return

                # Fetch the modpack URL
                clone_url = self.get_modpack_url(modpack_name)
                if not clone_url:
                    self.status_message.emit(f"URL not found for {modpack_name}. Skipping.")
                    self.progress.emit(index + 1)
                    continue

                # Determine the repository name
                repo_name = self.get_repo_name(clone_url, modpack_name)
                repo_path = os.path.join(os.getcwd(), repo_name)

                try:
                    if self.operation == 'download':
                        # Handle the download operation
                        self.handle_download(clone_url, repo_name, modpack_name, repo_path)
                    elif self.operation == 'update':
                        # Handle the update operation
                        self.handle_update(modpack_name, repo_path)
                    else:
                        self.status_message.emit(f"Invalid operation for {modpack_name}.")
                except Exception as e:
                    error_message = f"Error processing {modpack_name}: {e}"
                    print(error_message)
                    self.status_message.emit(error_message)

                # Update progress
                self.progress.emit(int(((index + 1) / len(self.modpack_names)) * 100))

            # Emit success when all modpacks are processed without interruption
            self.finished.emit(True, "All modpacks processed successfully.")
        except Exception as e:
            self.finished.emit(False, f"An unexpected error occurred: {str(e)}")

    def get_modpack_url(self, modpack_name):
        """Retrieve the URL for the specified modpack."""
        modpack_info = self.main_window.get_modpack_info(modpack_name)
        return modpack_info['url'] if modpack_info else ""

    def get_repo_name(self, clone_url, modpack_name):
        """Determine the name of the repository based on the clone URL or modpack name."""
        if clone_url.endswith('.git'):
            return clone_url.split('/')[-1].replace('.git', '')
        return modpack_name.replace(' ', '_')

    def handle_download(self, clone_url, repo_name, modpack_name, repo_path):
        """Handle the download operation for a modpack."""
        # Check for cancellation before downloading
        if self.isInterruptionRequested():
            self.status_message.emit(f"Operation cancelled while processing {modpack_name}.")
            self.finished.emit(False, "Operation cancelled by the user.")
            return

        # If the modpack exists, remove it before re-downloading
        if os.path.isdir(repo_path):
            self.status_message.emit(f"Removing existing {modpack_name}...")
            shutil.rmtree(repo_path, onerror=readonly_handler)

        # Download the modpack
        self.status_message.emit(f"Downloading {modpack_name}...")
        self.download_modpack(clone_url, repo_name)

    def handle_update(self, modpack_name, repo_path):
        """Handle the update operation for a modpack."""
        if os.path.isdir(repo_path):
            self.status_message.emit(f"Updating {modpack_name}...")
            self.update_modpack(repo_path)
        else:
            self.status_message.emit(f"Modpack {modpack_name} not found. Cannot update.")
            self.finished.emit(False, f"Modpack {modpack_name} not found. Cannot update.")

    def download_modpack(self, clone_url, repo_name):
        """Download a modpack from a given URL, including submodules if applicable."""
        try:
            if clone_url.endswith('.git'):
                # Clone the repository with submodules
                self.status_message.emit(f"Cloning repository: {repo_name}...")
                repo = git.Repo.clone_from(clone_url, repo_name, recursive=True)

                # Emit status message for each submodule during the download
                if repo.submodules:
                    total_submodules = len(repo.submodules)
                    for idx, submodule in enumerate(repo.submodules):
                        self.status_message.emit(f"Downloading submodule: {submodule.name} ({idx + 1}/{total_submodules})")
                        submodule.update(init=True, recursive=True)

                        # Emit progress for submodules (optional)
                        progress_percent = int(((idx + 1) / total_submodules) * 100)
                        self.progress.emit(progress_percent)

                print(f"Downloaded {repo_name} with submodules.")
                self.status_message.emit(f"Downloaded {repo_name} with all submodules.")
            else:
                # Handle direct downloads
                self.download_direct_modpack(clone_url, repo_name)
        except Exception as e:
            error_message = f"Failed to download {repo_name}: {e}"
            print(error_message)
            self.status_message.emit(error_message)
            self.finished.emit(False, error_message)

    def download_direct_modpack(self, clone_url, repo_name):
        """Handle direct download of a modpack if it's not a Git repository."""
        try:
            response = requests.get(clone_url, stream=True)
            response.raise_for_status()
            zip_file_path = os.path.join(os.getcwd(), f"{repo_name}.zip")

            with open(zip_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.isInterruptionRequested():
                        self.status_message.emit(f"Operation cancelled while downloading {repo_name}.")
                        self.finished.emit(False, "Operation cancelled by the user.")
                        return
                    f.write(chunk)

            # Unzip the file
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(repo_name)
            os.remove(zip_file_path)
            self.status_message.emit(f"Downloaded and extracted {repo_name}")
            print(f"Downloaded and extracted {repo_name}")
        except Exception as e:
            error_message = f"Failed to download {repo_name}: {e}"
            print(error_message)
            self.status_message.emit(error_message)
            self.finished.emit(False, error_message)

    def update_modpack(self, repo_path):
        """Update an existing modpack."""
        try:
            # Check if the repo path exists and is a valid Git repository
            if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
                self.finished.emit(False, f"Invalid repository path: {repo_path}")
                return

            # Initialize the Git repository
            repo = Repo(repo_path)

            # Perform git pull to get the latest changes
            print("Pulling latest changes...")
            self.status_message.emit("Pulling latest changes...")
            repo.remotes.origin.pull()

            # Count total submodules for progress tracking
            total_submodules = len(repo.submodules)
            for idx, submodule in enumerate(repo.submodules):
                try:
                    submodule_name = submodule.name
                    print(f"Updating submodule: {submodule_name} ({idx + 1}/{total_submodules})")
                    self.status_message.emit(f"Updating submodule: {submodule_name} ({idx + 1}/{total_submodules})")

                    # Update submodule (init if needed, update recursively)
                    submodule.update(init=True, recursive=True)

                    # Emit progress update (optional)
                    progress_percent = int(((idx + 1) / total_submodules) * 100)
                    self.progress.emit(progress_percent)
                except GitCommandError as submodule_error:
                    error_message = f"Failed to update submodule '{submodule_name}': {str(submodule_error)}"
                    print(error_message)
                    self.status_message.emit(error_message)
                    self.finished.emit(False, error_message)
                    return

            # Emit success signal if everything was updated
            self.finished.emit(True, "Modpack updated successfully.")
        except GitCommandError as e:
            self.finished.emit(False, f"Failed to update modpack: {str(e)}")
        except Exception as e:
            self.finished.emit(False, f"An unexpected error occurred: {str(e)}")


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

        # Flags to track whether the popups are open
        self.settings_popup_open = False
        self.revert_popup_open = False
        self.install_popup_open = False

        # Initialize custom_install_path as None
        self.custom_install_path = None

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

        self.create_widgets()
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
        # Fetch the latest version and download URL from modpack_data
        latest_version = self.modpack_data.get('latest_version')
        download_url = self.modpack_data.get('download_url')
        changelog = self.modpack_data.get('changelog')

        # Compare with the current version
        if VERSION != latest_version:
            # An update is available
            self.prompt_update(latest_version, download_url, changelog)

    def prompt_update(self, latest_version, download_url, changelog):
        # Display the update prompt with "Ok" and "Cancel" buttons
        reply = QMessageBox.question(
            self,
            "Update Available",
            f"A new version ({latest_version}) is available.\nChangelog:\n{changelog}\n\nWould you like to download it from the official website?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        # Open the download URL only if the user clicked "Ok"
        if reply == QMessageBox.StandardButton.Ok:
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
        layout.addWidget(self.refresh_button, 3, 2, 1, 2)
        self.refresh_button.clicked.connect(self.update_installed_info)
        self.refresh_button.setToolTip("Refresh currently installed modpack information")

        # Modpack selection dropdown
        self.modpack_label = QLabel("Select Modpack:", self)
        self.modpack_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.modpack_label, 4, 0, 1, 1)

        # Assuming self.settings["default_modpack"] exists and contains the default modpack name
        modpack_names = self.get_modpack_names()

        self.modpack_var = QComboBox(self)
        self.modpack_var.setEditable(True)
        self.modpack_var.addItems(modpack_names)

        # Descriptions
        self.description_label = QLabel("", self)
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label, 5, 0, 1, 6)

        self.modpack_var.currentIndexChanged.connect(self.update_modpack_description)

        # Download button
        self.download_button = QPushButton("Download", self)
        self.download_button.setStyleSheet("font: 12pt 'Helvetica';")
        layout.addWidget(self.download_button, 6, 0, 1, 2)
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

        layout.addWidget(self.modpack_var, 4, 1, 1, 5)

        # Quick Update button
        self.update_button = QPushButton("Quick Update", self)
        self.update_button.setStyleSheet("font: 12pt 'Helvetica';")
        layout.addWidget(self.update_button, 6, 2, 1, 2)
        self.update_button.clicked.connect(self.update_modpack)
        self.update_button.setToolTip("Quickly update downloaded modpacks (can be malfunctioned)")

        # Multi-Download/Update button
        self.multi_download_button = QPushButton("Multi Mode", self)
        self.multi_download_button.setStyleSheet("font: 12pt 'Helvetica';")
        layout.addWidget(self.multi_download_button, 6, 4, 1, 2)
        self.multi_download_button.clicked.connect(self.open_multi_modpack_popup)
        self.multi_download_button.setToolTip("Download or update multiple modpacks at once")

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

        # Time Travel button
        self.revert_button = QPushButton("Time Travel", self)
        self.revert_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.revert_button, 8, 0, 1, 2)
        self.revert_button.clicked.connect(self.open_revert_popup)
        self.revert_button.setToolTip("Revert the modpack to a certain historical version")

        # Verify Integrity button
        self.verify_button = QPushButton("Verify Integrity", self)
        self.verify_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.verify_button, 8, 2, 1, 2)  # Adjust grid position as needed
        self.verify_button.clicked.connect(self.verify_modpack_integrity)
        self.verify_button.setToolTip("Check modpack for missing or incomplete files")

        # Auto backup button
        self.backup_button = QPushButton("Backup Save", self)
        self.backup_button.setStyleSheet("font: 10pt 'Helvetica';")
        layout.addWidget(self.backup_button, 8, 4, 1, 2)
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
        self.mod_list_button = QPushButton("Mod List", self)
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

        Date = DATE
        Iteration = ITERATION
        Version = VERSION

        # Modpack Manager Info
        self.info = QLabel(f"Build: {Date}, Iteration: {Iteration}, Version: Release {Version}", self)
        self.info.setStyleSheet("font: 8pt 'Helvetica';")
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

############################################################
# Multi Mode
############################################################

    def open_multi_modpack_popup(self):
        # Create a new popup window
        popup = QDialog(self)
        popup.setWindowTitle("Multi Modpack Download/Update")

        # Create a layout for the popup
        layout = QVBoxLayout(popup)

        # Instruction label
        label = QLabel("Select modpacks to download or update:", popup)
        layout.addWidget(label)

        # List of modpacks with checkboxes
        self.modpack_checkboxes = []
        modpack_names = self.get_modpack_names()
        for modpack_name in modpack_names:
            checkbox = QCheckBox(modpack_name, popup)
            self.modpack_checkboxes.append(checkbox)
            layout.addWidget(checkbox)

        # Add buttons for operations
        button_layout = QHBoxLayout()
        download_button = QPushButton("Download", popup)
        update_button = QPushButton("Update", popup)
        cancel_button = QPushButton("Cancel", popup)
        button_layout.addWidget(download_button)
        button_layout.addWidget(update_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Connect buttons to their respective functions
        download_button.clicked.connect(lambda: self.start_multi_modpack_operation(popup, operation='download'))
        update_button.clicked.connect(lambda: self.start_multi_modpack_operation(popup, operation='update'))
        cancel_button.clicked.connect(popup.close)

        # Show the popup
        popup.exec()


    def start_multi_modpack_operation(self, popup, operation):
        # Get the list of selected modpacks
        selected_modpacks = [checkbox.text() for checkbox in self.modpack_checkboxes if checkbox.isChecked()]

        if not selected_modpacks:
            QMessageBox.warning(self, "No Modpacks Selected", "Please select at least one modpack.")
            return

        if operation not in ['download', 'update']:
            QMessageBox.warning(self, "Invalid Operation", "Invalid operation selected.")
            return

        # Identify existing modpacks
        existing_modpacks = self.get_existing_modpacks(selected_modpacks)

        # If there are existing modpacks and operation is 'download', warn the user
        if operation == 'download' and existing_modpacks:
            modpacks_str = "\n".join(existing_modpacks)
            reply = QMessageBox.question(
                self,
                "Confirm Re-download",
                f"The following modpacks are already downloaded and will be re-downloaded:\n\n{modpacks_str}\n\nDo you want to proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                # User chose not to proceed
                return

        # Close the popup
        popup.close()

        # Show a progress dialog
        operation_capitalized = operation.capitalize()
        self.progress_dialog = QProgressDialog(f"{operation_capitalized}ing Modpacks...", "Cancel", 0, len(selected_modpacks), self)
        self.progress_dialog.setWindowTitle("Progress")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        # Start the operation in a separate thread
        self.multi_modpack_worker = MultiModpackWorker(selected_modpacks, operation, self)
        self.multi_modpack_worker.progress.connect(self.progress_dialog.setValue)
        self.multi_modpack_worker.status_message.connect(self.progress_dialog.setLabelText)
        self.multi_modpack_worker.finished.connect(self.on_multi_modpack_operation_finished)
        self.multi_modpack_worker.start()

        # If the user cancels, stop the worker
        self.progress_dialog.canceled.connect(self.multi_modpack_worker.requestInterruption)

    def on_multi_modpack_operation_finished(self):
        self.progress_dialog.close()
        QMessageBox.information(self, "Operation Complete", "Selected modpacks have been processed.")

    def get_existing_modpacks(self, selected_modpacks):
        existing_modpacks = []
        for modpack_name in selected_modpacks:
            modpack_info = self.get_modpack_info(modpack_name)
            if modpack_info:
                clone_url = modpack_info['url']
                if clone_url.endswith('.git'):
                    repo_name = clone_url.split('/')[-1].replace('.git', '')
                else:
                    repo_name = modpack_name.replace(' ', '_')
                repo_path = os.path.join(os.getcwd(), repo_name)
                if os.path.isdir(repo_path):
                    existing_modpacks.append(modpack_name)
        return existing_modpacks


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

        # List all .exe files in the game directory and strip ".exe"
        exe_files = self.get_exe_files(self.settings["game_directory"])

        # Create a layout for the popup window
        layout = QGridLayout(popup)

        # Game Directory
        self.game_directory_label = QLabel("Game Directory:", popup)
        layout.addWidget(self.game_directory_label, 0, 0, 1, 2)

        game_dir_entry = QLineEdit(popup)
        game_dir_entry.setText(self.settings["game_directory"])
        game_dir_entry.setReadOnly(True)
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
        mods_dir_entry.setReadOnly(True)
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
        if not os.path.exists(SETTINGS_FILE):
            # If no settings file exists, create it with default settings
            with open(SETTINGS_FILE, "w") as f:
                json.dump(DEFAULT_SETTINGS, f, indent=4)
            return DEFAULT_SETTINGS.copy()
        else:
            # Load existing settings from the file
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)

    # Function to save settings to the JSON file
    def save_settings(self, popup=None, game_directory=None, mods_directory=None, profile_name=None, default_modpack=None, backup_interval=None, skip_mod_selection=None, auto_install_after_download=None):
        try:
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
            if skip_mod_selection is not None:
                self.settings["skip_mod_selection"] = skip_mod_selection
            if auto_install_after_download is not None:
                self.settings["auto_install_after_download"] = auto_install_after_download
            
            # Write the settings to the JSON file
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)

        except Exception as e:
            # Display an error message if the save operation fails
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to save settings: {str(e)}")
            msg_box.exec()


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
        try:
            # Check if the directory exists, if not create it
            if not os.path.exists(path):
                os.makedirs(path)  # Create the directory and all intermediate directories if needed
                
                # Show information message
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Info")
                msg_box.setText(f"Directory did not exist, created: {path}")
                msg_box.exec()

            # Open the directory after ensuring it exists
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            
        except Exception as e:
            # Display an error message if unable to open the directory
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to open or create directory: {e}")
            msg_box.exec()

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
    def get_exe_files(self, directory):
        try:
            exe_files = [f[:-4] for f in os.listdir(directory) if f.endswith(".exe")]
            return exe_files
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
        self.settings = self.load_settings()
        self.game_dir = self.settings.get("game_directory")
        self.profile_name = self.settings.get("profile_name")        

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
        repos = {
            "Full Pack": ("Dimserene", "Dimserenes-Modpack"),
            "Fine-tuned": ("Dimserene", "Fine-tuned-Pack"),
            "Vanilla+": ("Dimserene", "Vanilla-Plus-Pack"),
            "Insane Pack": ("Dimserene", "Insane-Pack"),
            "Cruel Pack": ("Dimserene", "Cruel-Pack"),
            "Manager": ("Dimserene", "ModpackManager")
        }
        commit_messages = {}
        for repo_name, (owner, name) in repos.items():
            commit_message = self.get_latest_commit_message(owner, name)
            commit_messages[repo_name] = commit_message
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
        try:
            modpack_name = self.modpack_var.currentText()
            if not clone_url:
                clone_url = self.get_modpack_url(modpack_name)

            # Special case for Coonie's Modpack
            if modpack_name == "Coonie's Modpack":
                coonies_modpack_path = os.path.join(os.getcwd(), "Coonies-Modpack")
                
                # Check if "Coonies-Modpack" folder is already present
                if os.path.isdir(coonies_modpack_path):
                    # Prompt user whether to overwrite the existing folder or skip download
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Question)
                    msg_box.setWindowTitle("Confirm update/redownload")
                    msg_box.setText("Coonie's Modpack is already downloaded. Update/Redownload?")
                    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    response = msg_box.exec()

                    if response == QMessageBox.StandardButton.No:
                        return  # Exit early, as the user chose not to overwrite

                # Show a progress dialog while downloading and unzipping
                self.show_progress_dialog(main_window, modpack_name)

                # Download and unzip the Coonie's Modpack
                self.download_and_unzip_coonies_modpack()

                # Close the progress dialog
                self.progress_dialog.close()
                return  # Exit early, as we don't want to continue with the regular flow

            # Regular modpack download flow for other modpacks
            if not clone_url:
                clone_url = self.get_modpack_url(modpack_name)

            if not clone_url:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("Modpack URL not found. Please ensure you selected a valid modpack.")
                msg_box.exec()
                return

            repo_name = clone_url.split('/')[-1].replace('.git', '')

            # Prompt force download if the repository directory already exists
            force_update = False
            if os.path.isdir(repo_name):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setWindowTitle("Confirm update/redownload")
                msg_box.setText(f"{repo_name} is already downloaded. Update/Redownload?")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)

                # Show the message box and capture the response
                force_update = msg_box.exec() == QMessageBox.StandardButton.Yes
                if not force_update:
                    return

            # Show the progress dialog
            self.show_progress_dialog(main_window, modpack_name)

            # Create the worker for downloading modpack
            self.worker = ModpackDownloadWorker(clone_url, repo_name, force_update)
            self.worker.finished.connect(self.on_download_finished)

            # Start the worker (background task)
            self.worker.start()

        except Exception as e:
            # Ensure the progress dialog is closed on error
            if self.progress_dialog:
                self.progress_dialog.close()

            # Handle unexpected errors
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"An unexpected error occurred: {str(e)}")
            msg_box.exec()
            print(f"Unexpected error during download: {e}")

    def on_download_finished(self, success, message):
        # Close the progress dialog
        self.progress_dialog.close()

        # Show the result message (success or failure)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information if success else QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Download Status" if success else "Error")
        msg_box.setText(message)
        msg_box.exec()

        # Check the setting and install modpack if needed
        if success and self.settings.get("auto_install_after_download", False):
            self.install_modpack()

    def show_progress_dialog(self, main_window, modpack_name):
        """Show the progress dialog with modpack name."""
        self.progress_dialog = QProgressDialog("", None, 0, 0)  # Pass None to remove the cancel button
        self.progress_dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # No title bar
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # Modal
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)

        # Apply custom QSS (Qt Style Sheets) for border and text styling
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                border: 3px solid #555;  /* Add a border */
                background-color: #ffffff;  /* Background color */
            }
            QLabel {
                font-size: 24px;  /* Larger text */
                font-weight: bold;  /* Bold text */
                color: #333;  /* Text color */
                background-color: transparent;
            }
        """)

        # Create a custom QLabel for the message with the modpack name
        label = QLabel(f"Downloading {modpack_name}...")  # Show the name of the modpack
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

        # Show the progress dialog immediately (no delay)
        self.progress_dialog.show()

        # Center the progress dialog relative to the main window
        if isinstance(main_window, QWidget):  # Ensure main_window is a valid QWidget
            parent_geometry = main_window.geometry()  # Get the main window's geometry
            dialog_geometry = self.progress_dialog.frameGeometry()  # Get the dialog's geometry
            dialog_geometry.moveCenter(parent_geometry.center())  # Center the progress dialog to the main window
            self.progress_dialog.move(dialog_geometry.topLeft())  # Move to the new position

        QApplication.processEvents()  # Ensure the UI is responsive

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
        modpack_name = self.modpack_var.currentText()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)
        selected_modpack = self.modpack_var.currentText()

        # Check if the selected modpack is "Coonie's Modpack"
        if selected_modpack == "Coonie's Modpack":
            # Show a popup message and prevent closing the window
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Incompatible Modpack")
            msg_box.setText("This function is not compatible with Coonie's Modpack! Please use Download/Update instead.")
            msg_box.exec()

        # Check if the repository exists
        if not os.path.isdir(repo_path):
            QMessageBox.critical(self, "Error", "Repository not found. Attempting to clone it.")
            self.download_modpack(main_window=self, clone_url=clone_url)  # Attempt to download the modpack if it's not found
            return

        # Create and display the progress dialog for updating
        self.progress_dialog = QProgressDialog("", None, 0, 0)  # Pass None to remove the cancel button
        self.progress_dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # No always-on-top flag
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # Modal
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)

        # Apply custom QSS (Qt Style Sheets) for border and text styling
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                border: 3px solid #555;  /* Add a border */
                background-color: #ffffff;  /* Background color */
            }
            QLabel {
                font-size: 24px;  /* Larger text */
                font-weight: bold;  /* Bold text */
                color: #333;  /* Text color */
                background-color: transparent;
            }
        """)

        # Create a custom QLabel for the message with the modpack name
        label = QLabel(f"Updating {modpack_name}...")  # Show the name of the modpack
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

        # Show the progress dialog immediately (no delay)
        self.progress_dialog.show()

        # Center the progress dialog relative to the parent popup
        if isinstance(self, QWidget):  # Ensure self is a valid QWidget
            parent_geometry = self.geometry()  # Get the parent window's geometry
            dialog_geometry = self.progress_dialog.frameGeometry()  # Get the dialog's geometry
            dialog_geometry.moveCenter(parent_geometry.center())  # Center the progress dialog to the parent
            self.progress_dialog.move(dialog_geometry.topLeft())  # Move to the new position

        QApplication.processEvents()  # Ensure the UI is responsive

        # Create the worker for updating the modpack
        self.worker = ModpackUpdateWorker(repo_path)
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

        # Check the setting and install modpack if needed
        if success and self.settings.get("auto_install_after_download", False):
            self.install_modpack()


    def install_modpack(self):
        self.settings = self.load_settings()
        skip_mod_selection = self.settings.get("skip_mod_selection", False)
        modpack_name = self.modpack_var.currentText()
        modpack_info = self.get_modpack_info(modpack_name)
        if not modpack_info:
            QMessageBox.critical(self, "Error", "Modpack information not found.")
            return

        # Handle special cases based on URL type
        if modpack_info['url'].endswith('.git'):
            repo_name = modpack_info['url'].split('/')[-1].replace('.git', '')
        else:
            repo_name = modpack_name.replace(' ', '_')

        repo_path = os.path.join(os.getcwd(), repo_name)
        mods_src = os.path.join(repo_path, 'Mods')
        install_path = self.mods_dir
        mod_list = self.get_mod_list(mods_src)

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
                self.popup_mod_selection(mod_list)

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
        
    def popup_mod_selection(self, mod_list):
        # Prevent opening multiple install popups
        if self.install_popup_open:
            return

        # Mark the install popup as open
        self.install_popup_open = True

        # Create a popup window for mod selection
        popup = QDialog(self)
        popup.setWindowTitle("Mod Selection")

        # Create a grid layout for the popup
        layout = QGridLayout(popup)

        # Instruction label with "DO NOT" in red
        label = QLabel('<span style="font-size: 16pt; font-family: Helvetica;">Select the mods you <span style="color: red;">DO NOT</span> want to install:</span>', popup)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, 0, 0, 1, -1)  # Span the label across all columns

        # List of locked mods that cannot be deselected
        locked_mods = ["ModpackUtil", "Steamodded"]

        # Define mod dependencies: {'mod_that_depends': ['required_mod1', 'required_mod2', ...]}
        dependencies = {
            "Cryptid": ["Talisman"],
            "ModpackDecks": ["SDM_0-s-Stuff"],
            "Jestobiology": ["Fusion-Jokers"],
            "Vultbines_Joker": ["Fusion-Jokers"],
            "Tsunami": ["Fusion-Jokers"],
            "AntonosStakes": ["Talisman"],
            "Bmjokers": ["Bmwallet"],
            "Oiiman-s-Additions": ["Cryptid", "Talisman"],
            # Add more dependencies as needed
        }

        # Exclude "ModpackUtil" and "Steamodded" from mod selection
        filtered_mod_list = [mod for mod in mod_list if mod not in locked_mods]

        # Create a list of checkboxes for each mod
        mod_vars = []
        mods_per_column = 20  # Number of mods per column

        for index, mod in enumerate(filtered_mod_list):
            var = QCheckBox(mod, popup)
            var.setChecked(mod in self.excluded_mods)
            mod_vars.append((mod, var))

            # Calculate row and column position
            row = (index % mods_per_column) + 1  # Row position
            column = index // mods_per_column  # Column position

            # Connect the checkbox state change event to handle dependencies
            var.stateChanged.connect(lambda state, mod=mod, var=var: self.handle_dependencies(mod, var, mod_vars, dependencies))

            # Add the checkbox to the layout
            layout.addWidget(var, row, column)

        # Function to clear all selections
        def clear_all():
            for _, var in mod_vars:
                var.setChecked(False)

        # Function to reverse the selections
        def reverse_select():
            for _, var in mod_vars:
                var.blockSignals(True)  # Temporarily block signals to avoid triggering stateChanged handlers
                var.setChecked(not var.isChecked())
                var.blockSignals(False)  # Re-enable signals after changing the state

        # Function to randomly select mods and apply dependencies
        def feel_lucky():
            for _, var in mod_vars:
                var.blockSignals(True)  # Temporarily block signals to avoid triggering stateChanged handlers
                var.setChecked(random.choice([True, False]))  # Randomly check/uncheck the mod
                var.blockSignals(False)  # Re-enable signals after changing the state
            
            # Ensure dependencies are respected after random selection
            for mod, var in mod_vars:
                if var.isChecked():
                    self.handle_dependencies(mod, var, mod_vars, dependencies)

        # Create the buttons
        clear_button = QPushButton("Clear All", popup)
        clear_button.clicked.connect(clear_all)

        reverse_button = QPushButton("Reverse Select", popup)
        reverse_button.clicked.connect(reverse_select)

        feel_lucky_button = QPushButton("I Feel Lucky", popup)
        feel_lucky_button.clicked.connect(feel_lucky)

        save_button = QPushButton("Save && Install", popup)
        save_button.clicked.connect(lambda: self.save_and_install(mod_vars, popup))

        # Create a container widget for the buttons and a horizontal layout for centering
        button_container = QWidget(popup)
        button_layout = QHBoxLayout(button_container)

        # Add buttons to the container's layout
        button_layout.addWidget(clear_button)
        button_layout.addWidget(reverse_button)
        button_layout.addWidget(feel_lucky_button)  # Add "I Feel Lucky" button
        button_layout.addWidget(save_button)

        # Align the buttons to the center of the row
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add the container widget to the grid layout, spanning all columns
        layout.addWidget(button_container, mods_per_column + 1, 0, 1, -1)

        # Create the "Backup Mods Folder" checkbox
        self.backup_checkbox = QCheckBox("Backup Mods Folder", popup)
        self.backup_checkbox.setChecked(self.settings.get("backup_mods", False))  # Set based on saved settings

        # Create the "Remove Mods Folder" checkbox
        self.remove_checkbox = QCheckBox("Remove Mods Folder", popup)
        self.remove_checkbox.setChecked(self.settings.get("remove_mods", True))  # Set based on saved settings or default

        # Create a layout for the checkboxes
        checkbox_container = QWidget(popup)
        checkbox_layout = QHBoxLayout(checkbox_container)

        # Add both checkboxes to the layout
        checkbox_layout.addWidget(self.backup_checkbox)
        checkbox_layout.addWidget(self.remove_checkbox)

        # Align the checkboxes to the center
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add the container widget with the checkboxes to the layout, spanning all columns
        layout.addWidget(checkbox_container, mods_per_column + 2, 0, 1, -1)

        # Close event handler to reset the flag when the window is closed
        def settings_on_close():
            self.install_popup_open = False
            popup.close()

        # Connect the close event to the handler
        popup.finished.connect(settings_on_close)

        # Show the dialog as modal
        popup.exec()

    def handle_dependencies(self, mod, var, mod_vars, dependencies):
        """Handle mod dependencies when a checkbox is clicked (checked = excluded)."""
        
        def exclude_dependent_mods(required_mod):
            """Helper function to exclude dependent mods when a required mod is excluded."""
            for dependent_mod, required_mods in dependencies.items():
                if required_mod in required_mods:
                    for mod_name, mod_var in mod_vars:
                        if mod_name == dependent_mod and not mod_var.isChecked():
                            # Exclude dependent mod
                            mod_var.blockSignals(True)  # Temporarily block signals
                            mod_var.setChecked(True)
                            mod_var.blockSignals(False)
                            # Recursively exclude mods that depend on this mod
                            exclude_dependent_mods(dependent_mod)

        def unexclude_required_mods(dependent_mod):
            """Helper function to unexclude required mods when a dependent mod is unexcluded."""
            if dependent_mod in dependencies:
                required_mods = dependencies[dependent_mod]
                for required_mod in required_mods:
                    for mod_name, mod_var in mod_vars:
                        if mod_name == required_mod and mod_var.isChecked():
                            # Unexclude the required mod
                            mod_var.blockSignals(True)  # Temporarily block signals
                            mod_var.setChecked(False)
                            mod_var.blockSignals(False)
                            # Recursively unexclude mods that depend on this required mod
                            unexclude_required_mods(required_mod)

        # Main logic when mod checkbox state changes
        if var.isChecked():  # Exclude mod
            exclude_dependent_mods(mod)
        else:  # Unexclude mod
            unexclude_required_mods(mod)

    def save_preferences(self, mod_vars):
        # Let the user pick mods they DON'T want to install
        self.excluded_mods = [mod for mod, var in mod_vars if var.isChecked()]

        # Save user preferences to a file
        with open(INSTALL_FILE, "w") as f:
            for mod in self.excluded_mods:
                f.write(mod + "\n")

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Preferences Saved")
        msg_box.setText(f"Excluded mods saved: {self.excluded_mods}")
        msg_box.exec()
        print(f"Excluded mods: {self.excluded_mods}")  # Debugging

    def read_preferences(self):
        # If the preferences file doesn't exist, create an empty one
        if not os.path.exists(INSTALL_FILE):
            with open(INSTALL_FILE, "w") as f:
                f.write("")  # Create an empty file
            return []  # Return an empty list of excluded mods
        else:
            with open(INSTALL_FILE, "r") as f:
                return [line.strip() for line in f.readlines()]

    def install_mods(self, popup):
        modpack_name = self.modpack_var.currentText()

        # Handle special case for "Coonie's Modpack"
        if modpack_name == "Coonie's Modpack":
            repo_path = os.path.join(os.getcwd(), "Coonies-Modpack")
        else:
            clone_url = self.get_modpack_url(modpack_name)
            repo_name = clone_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(os.getcwd(), repo_name)

        mods_src = os.path.join(repo_path, 'Mods')

        # Check if the Mods directory exists and warn the user
        if os.path.isdir(self.mods_dir):

            # Determine if the user has opted to backup mods
            backup_mods = self.settings.get("backup_mods", False)
            if hasattr(self, 'backup_checkbox'):  # Use the checkbox from the popup_mod_selection dialog if present
                backup_mods = self.backup_checkbox.isChecked()

            if backup_mods:
                # Create backup of the current Mods folder
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                backup_folder = os.path.join(os.path.dirname(self.mods_dir), f"Mods-backup-{timestamp}")
                try:
                    shutil.move(self.mods_dir, backup_folder)
                except Exception as e:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Critical)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText(f"Failed to backup Mods folder. Error: {e}")
                    msg_box.exec()
                    return

            # Determine if the user has opted to remove mods
            remove_mods = self.settings.get("remove_mods", False)
            if hasattr(self, 'remove_checkbox'):  # Use the checkbox from the popup_mod_selection dialog if present
                remove_mods = self.remove_checkbox.isChecked()

            if remove_mods:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("The current 'Mods' folder will be erased. Do you want to proceed?")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                response = msg_box.exec()

                if response == QMessageBox.StandardButton.No:
                    return  # User canceled the installation
                
                # Remove the existing Mods folder
                try:
                    shutil.rmtree(self.mods_dir, ignore_errors=True)
                except Exception as e:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Critical)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText(f"Failed to remove Mods folder. Error: {e}")
                    msg_box.exec()
                    return

        # Ensure the install directory exists
        if not os.path.exists(self.mods_dir):
            os.makedirs(self.mods_dir)

        # Install mods that are not in the excluded_mods list
        for mod in self.get_mod_list(mods_src):
            if mod not in self.excluded_mods:
                source_mod_path = os.path.join(mods_src, mod)
                destination_mod_path = os.path.join(self.mods_dir, mod)

                # Copy the mod folder to the installation directory
                try:
                    if os.path.exists(destination_mod_path):
                        shutil.rmtree(destination_mod_path)  # Remove old version of the mod if it exists
                    shutil.copytree(source_mod_path, destination_mod_path)
                except Exception as e:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Critical)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText(f"Failed to install mod: {mod}. Error: {e}")
                    msg_box.exec()
                    return

        # Close the installation popup if it exists
        if popup:
            self.install_popup_open = False
            popup.close()

        # Show installation success message
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Install Status")
        msg_box.setText("Successfully installed modpack.")
        msg_box.exec()

        
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
        for dirpath, dirnames, filenames in os.walk(root_folder):
            if self.is_empty_or_git_only(dirpath):
                empty_or_git_only_folders.append(os.path.basename(dirpath))  # Append folder name, not full path
        return empty_or_git_only_folders

    # Verification function for a specific modpack folder
    def verify_modpack_folder(self, modpack_folder):
        print(f"Verifying modpack folder: {modpack_folder}")
        self.list_empty_or_git_only_folders(modpack_folder)

    # Function to verify the integrity of the 'Mods' folder of the currently selected modpack
    def verify_modpack_integrity(self):
        modpack_name = self.modpack_var.currentText()  # Get the name of the selected modpack

        # Handle special case for Coonie's Modpack
        if modpack_name == "Coonie's Modpack":
            repo_name = "Coonies-Modpack"
        else:
            clone_url = self.get_modpack_url(modpack_name)
            repo_name = clone_url.split('/')[-1].replace('.git', '')

        modpack_folder = os.path.join(os.getcwd(), repo_name, 'Mods')  # Check inside the 'Mods' folder

        if not os.path.isdir(modpack_folder):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Mods Folder Not Found")
            msg_box.setText(f"The 'Mods' folder for {modpack_name} is not found.")
            msg_box.exec()
            return

        # Call the verification function to get the list of empty or .git-only folders
        empty_or_git_only_folders = self.list_empty_or_git_only_folders(modpack_folder)

        # Show the result in a message box
        if empty_or_git_only_folders:
            folder_list = "\n".join(empty_or_git_only_folders)
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Verification Result")
            msg_box.setText(f"The following mods are not downloaded correctly. Please attempt reclone:\n\n{folder_list}")
            msg_box.exec()
        else:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Verification Complete")
            msg_box.setText(f"All folders in the 'Mods' folder for {modpack_name} are properly populated.")
            msg_box.exec()

    def check_versions(self):
        try:
            install_path = self.mods_dir
            mods_path = os.path.join(install_path, 'ModpackUtil')

            # Define file paths
            current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
            modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')
            current_pack_file = os.path.join(mods_path, 'CurrentPack.txt')  # For Coonie's modpack

            # Load current version
            current_version = self.read_file_content(current_version_file)

            # Determine pack name
            pack_name = self.read_file_content(current_pack_file) or self.extract_pack_name(modpack_util_file)

            # Fetch commit messages
            commit_messages = self.fetch_commit_messages()
            coonies_version_info = self.get_latest_coonies_tag()

            # Prepare version information
            version_info = ""
            update_message = ""
            for repo_name, commit_message in commit_messages.items():
                version_info += f"{repo_name}:\t{commit_message}\n"
                # Check if an update is needed
                if pack_name == repo_name and current_version and commit_message != current_version:
                    update_message = "Update available!"

            # Prepare installed information
            installed_info = f"\nInstalled modpack: {pack_name}\nInstalled version: {current_version}" if pack_name else "\nNo modpack installed or ModpackUtil mod removed."

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

        game_path = os.path.join(self.game_dir, "balatro.exe")

        # Verify existence of balatro.exe or prompt user to select the directory
        if not os.path.exists(game_path):
            warning_box = QMessageBox()
            warning_box.setIcon(QMessageBox.Icon.Warning)
            warning_box.setWindowTitle("Warning")
            warning_box.setText("Game executable not found in the default directory. Please specify it in settings.")
            warning_box.exec()
            return

        # Download and installation process
        url = "https://github.com/ethangreen-dev/lovely-injector/releases/latest/download/lovely-x86_64-pc-windows-msvc.zip"
        zip_file_path = os.path.join(self.game_dir, "lovely-injector.zip")
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(zip_file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extract("version.dll", self.game_dir)
            
            os.remove(zip_file_path)  # Clean up the zip file after extraction

            success_box = QMessageBox()
            success_box.setIcon(QMessageBox.Icon.Information)
            success_box.setWindowTitle("Install Status")
            success_box.setText("Lovely Injector installed successfully.")
            success_box.exec()

        except requests.RequestException as e:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.setWindowTitle("Error")
            error_box.setText(f"Failed to download Lovely Injector: {e}")
            error_box.exec()
            
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
        
        except zipfile.BadZipFile as e:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.setWindowTitle("Error")
            error_box.setText(f"Failed to unzip the downloaded file: {e}")
            error_box.exec()
        
        except Exception as e:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.setWindowTitle("Error")
            error_box.setText(f"An unexpected error occurred during installation: {str(e)}")
            error_box.exec()

    def open_discord(self, event=None):
        # Check if the user has already joined the official Discord
        webbrowser.open("https://discord.com/invite/balatro")
        webbrowser.open("https://discord.com/channels/1116389027176787968/1255696773599592458")

    def open_mod_list(self, event=None): 
        webbrowser.open("https://docs.google.com/spreadsheets/d/1L2wPG5mNI-ZBSW_ta__L9EcfAw-arKrXXVD-43eU4og")

############################################################
# Misc functions
############################################################

def readonly_handler(func, path, exc_info):
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
                    
        QCheckBox::indicator {
            width: 15px;  /* Size of the checkbox */
            height: 15px;  /* Size of the checkbox */
            border: 2px solid black;  /* Black outline for checkbox */
            background-color: #ffffff;  /* White background for checkbox */
        }
                    
        QCheckBox::indicator:checked {
            background-color: #000000;  /* Black background when checked */
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