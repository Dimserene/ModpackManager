import os, sys, re, shutil, requests, webbrowser, zipfile, stat, json, git, time, platform, subprocess
from datetime import datetime
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from threading import Thread
from git import Repo, GitCommandError

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
        "backup_interval": 60
    }
elif system_platform == "Linux":
    DEFAULT_SETTINGS = {
        "game_directory": "/home/$USER/.steam/steam/steamapps/common/Balatro",
        "profile_name": "Balatro",
        "mods_directory": "/home/$USER/.steam/steam/steamapps/compatdata/2379780/pfx/drive_c/users/steamuser/AppData/Roaming/Balatro/Mods",
        "default_modpack": "Dimserenes-Modpack",
        "backup_interval": 60
    }

# File paths for settings and installation exclusions
SETTINGS_FILE = "user_settings.json"
INSTALL_FILE = "excluded_mods.json" 

DATE = "2024/09/24"
ITERATION = "22"
VERSION = "1.4.2"

############################################################
# Worker class for downloading/updating modpack in the background
############################################################

class ModpackDownloadWorker(Thread):
    def __init__(self, clone_url, repo_name, force_update=False):
        super().__init__()
        self.clone_url = clone_url
        self.repo_name = repo_name
        self.force_update = force_update

    def run(self):
        try:
            if os.path.isdir(self.repo_name) and self.force_update:
                shutil.rmtree(self.repo_name)
            os.system(f"git clone --recurse-submodules {self.clone_url} {self.repo_name}")
        except Exception as e:
            pass

class ModpackUpdateWorker(Thread):
    def __init__(self, repo_path):
        super().__init__()
        self.repo_path = repo_path

    def run(self):
        try:
            repo = Repo(self.repo_path)
            repo.remotes.origin.pull()
            for submodule in repo.submodules:
                submodule.update(init=True, recursive=True)
        except GitCommandError:
            pass

class CooniesDownloadWorker(Thread):
    def __init__(self, url, local_zip_path, unzip_folder, progress_popup):
        super().__init__()
        self.url = url
        self.local_zip_path = local_zip_path
        self.unzip_folder = unzip_folder
        self.progress_popup = progress_popup

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            with open(self.local_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress_percent = int(downloaded_size * 100 / total_size)
                        Clock.schedule_once(lambda dt: self.progress_popup.progress_bar.set_value(progress_percent))
            with zipfile.ZipFile(self.local_zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.unzip_folder)
            os.remove(self.local_zip_path)
        except Exception:
            pass

############################################################
# Tutorial class
############################################################

class TutorialPopup(Popup):
    """Floating, titleless popup to display tutorial instructions."""
    def __init__(self, step_text, related_widget, main_window, **kwargs):
        super().__init__(**kwargs)
        self.main_window = main_window  # Store the main window for use in positioning
        self.title = ""  # No title for the popup
        self.size_hint = (None, None)  # Custom size
        self.auto_dismiss = False  # The popup will not dismiss unless instructed
        self.background = ""  # Make background transparent

        # Create a layout and set the text for the tutorial
        layout = BoxLayout(orientation='vertical')
        self.label = Label(
            text=step_text,
            size_hint=(None, None),
            halign="center",
            valign="middle",
            padding=(10, 10),
            size=(300, 100)
        )
        
        # Custom style for the tutorial popup
        self.label.canvas.before.clear()
        with self.label.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(1, 1, 0.8, 1)  # lightyellow background color
            self.rect = Rectangle(size=self.label.size, pos=self.label.pos)
        
        # Update rectangle size when the label size changes
        self.label.bind(size=self._update_rect, pos=self._update_rect)
        
        layout.add_widget(self.label)
        self.content = layout

        # Set size and position
        self.adjust_popup_position(related_widget)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def adjust_popup_position(self, related_widget):
        """Position the popup near the related widget and ensure it stays within the main window's bounds."""
        widget_pos = related_widget.to_window(related_widget.x, related_widget.y)  # Get widget position
        widget_width, widget_height = related_widget.size

        # Set default popup position below the related widget
        popup_x = widget_pos[0]
        popup_y = widget_pos[1] - self.height

        # Ensure the popup stays within the window bounds
        if popup_x + self.width > Window.width:
            popup_x = Window.width - self.width - 10  # Adjust to fit within the right side
        if popup_x < 0:
            popup_x = 10  # Add margin to the left
        if popup_y + self.height > Window.height:
            popup_y = widget_pos[1] - self.height - widget_height
        if popup_y < 0:
            popup_y = 10  # Add margin to the top

        # Finally, position the popup
        self.pos = (popup_x, popup_y)

############################################################
# Main Program
############################################################

class ModpackManagerApp(BoxLayout):
    def __init__(self, **kwargs):
        super(ModpackManagerApp, self).__init__(orientation='vertical', **kwargs)
        
        self.settings_popup_open = False
        self.revert_popup_open = False
        self.install_popup_open = False
        self.custom_install_path = None
        
        # Load settings
        self.settings = self.load_settings()
        self.game_dir = self.settings.get("game_directory", "")
        self.profile_name = self.settings.get("profile_name", "")
        self.mods_dir = os.path.expandvars(self.settings.get("mods_directory", ""))
        self.excluded_mods = self.read_preferences()

        self.old_version = ""
        self.version_hash = ""

        # Create widgets and set up the app
        self.create_widgets()
        self.update_installed_info()

        # Backup interval
        self.backup_interval = self.settings.get("backup_interval", 60)
        self.backup_timer = Clock.schedule_interval(self.perform_backup, self.backup_interval)
        
        # Worker and tutorial popup placeholders
        self.worker = None
        self.tutorial_popup = None
        self.current_step = 0
        self.tutorial_steps = [
            ("Welcome to the Modpack Manager! Let's get started.", self),
            ("↑ Use this dropdown to select the modpack.", None),
            ("↑ Click Download/Update button to download or update the selected modpack.", None),
            ("↑ Use Install button to copy the mod files.", None),
            ("↑ Then click PLAY button to start the game.", None),
            ("That's it! You are now ready to use the Modpack Manager.", self)
        ]

    def closeEvent(self):
        # Save the selected modpack when closing
        selected_modpack = self.modpack_spinner.text
        self.settings["default_modpack"] = selected_modpack
        self.save_settings()
        Clock.unschedule(self.backup_timer)

    def show_git_error(self, message):
        """Display a user-friendly error message if Git is not installed."""
        popup = Popup(
            title="Git Not Found",
            content=Label(text=f"{message}\n\nPlease install Git and reboot your device.\n\n"
                               "Visit https://git-scm.com/downloads for installation instructions."),
            size_hint=(0.7, 0.7)
        )
        popup.open()


############################################################
# Foundation of root window
############################################################

class ModpackManagerApp(GridLayout):
    def create_widgets(self):
        self.cols = 6

        # Title label
        self.title_label = Label(text="☷☷☷☷Dimserene's Modpack Manager☷☷☷☷", font_size='16pt', halign='center')
        self.add_widget(self.title_label)

        # PLAY button
        self.play_button = Button(text="PLAY", font_size='30pt', background_color=(0, 0.53, 0.92, 1))
        self.play_button.bind(on_release=self.play_game)
        self.add_widget(self.play_button)

        # Installed modpack info
        self.installed_info_label = Label(text="", font_size='12pt')
        self.add_widget(self.installed_info_label)

        # Refresh button
        self.refresh_button = Button(text="Refresh", on_release=self.update_installed_info)
        self.refresh_button.tooltip_text = "Refresh currently installed modpack information"
        self.add_widget(self.refresh_button)

        # Modpack selection dropdown
        self.modpack_spinner = Spinner(
            text=self.settings.get("default_modpack", "Dimserene's Modpack"),
            values=["Dimserene's Modpack", "Coonie's Modpack", "Fine-tuned Pack", "Vanilla+ Pack", "Insane Pack", "Cruel Pack"]
        )
        self.modpack_spinner.bind(text=self.on_modpack_changed)
        self.add_widget(Label(text="Select Modpack:"))
        self.add_widget(self.modpack_spinner)

        # Download button
        self.download_button = Button(text="Download / Update", font_size='16pt')
        self.download_button.bind(on_release=lambda *args: self.download_modpack(main_window=self))
        self.download_button.tooltip_text = "Download (clone) selected modpack to the same directory as manager"
        self.add_widget(self.download_button)

        # Quick Update button
        self.update_button = Button(text="Quick Update", font_size='16pt')
        self.update_button.bind(on_release=self.update_modpack)
        self.add_widget(self.update_button)

        # Install button
        self.install_button = Button(text="Install (Copy)", font_size='16pt')
        self.install_button.bind(on_release=self.install_modpack)
        self.add_widget(self.install_button)

        # Uninstall button
        self.uninstall_button = Button(text="Uninstall (Remove)", font_size='16pt')
        self.uninstall_button.bind(on_release=self.uninstall_modpack)
        self.add_widget(self.uninstall_button)

        # Time Travel button
        self.revert_button = Button(text="Time Travel", font_size='12pt')
        self.revert_button.bind(on_release=self.open_revert_popup)
        self.add_widget(self.revert_button)

        # Auto Backup button
        self.backup_button = Button(text="Backup Save", font_size='12pt')
        self.backup_button.bind(on_release=self.auto_backup_popup)
        self.add_widget(self.backup_button)

        # Check Versions button
        self.check_versions_button = Button(text="Check Versions", font_size='12pt')
        self.check_versions_button.bind(on_release=self.check_versions)
        self.add_widget(self.check_versions_button)

        # Install Lovely button
        self.install_lovely_button = Button(text="Install/Update lovely", font_size='12pt')
        self.install_lovely_button.bind(on_release=self.install_lovely_injector)
        self.add_widget(self.install_lovely_button)

        # Mod List button
        self.mod_list_button = Button(text="Mod List", font_size='12pt')
        self.mod_list_button.bind(on_release=self.open_mod_list)
        self.add_widget(self.mod_list_button)

        # Settings button
        self.open_settings_button = Button(text="Settings", font_size='12pt')
        self.open_settings_button.bind(on_release=self.open_settings_popup)
        self.add_widget(self.open_settings_button)

        # Discord button
        self.discord_button = Button(text="Join Discord", font_size='12pt')
        self.discord_button.bind(on_release=self.open_discord)
        self.add_widget(self.discord_button)

        # Create clickable link using a Label and handling touch event
        self.tutorial_link = Label(
            text='[ref=tutorial]Start Tutorial[/ref]',
            markup=True,  # Enable markup for links
            font_size='10pt',
            color=(0, 0.53, 0.92, 1)
        )
        self.tutorial_link.bind(on_ref_press=self.start_tutorial)  # Bind the click to the tutorial method
        self.add_widget(self.tutorial_link)

        # Modpack Manager Info (build info)
        self.info = Label(
            text=f"Build: {DATE}, Iteration: {ITERATION}, Version: Release {VERSION}",
            font_size='8pt', halign='right'
        )
        self.add_widget(self.info)

    def on_modpack_changed(self, spinner, text):
        """Function to handle modpack change."""
        self.settings["default_modpack"] = text

    # Function to display a popup with a message
    def show_popup(self, title, message, popup_type):
        layout = BoxLayout(orientation='vertical', padding=10)
        label = Label(text=message, size_hint_y=None, height=50)
        layout.add_widget(label)
        close_button = Button(text="Close", size_hint_y=None, height=40)
        layout.add_widget(close_button)

        popup = Popup(title=title, content=layout, size_hint=(0.6, 0.4))

        close_button.bind(on_release=popup.dismiss)
        popup.open()

    def show_confirmation_popup(self, title, message, callback):
        """Display a confirmation popup with Yes and No buttons."""
        layout = BoxLayout(orientation='vertical', padding=10)
        label = Label(text=message, size_hint_y=None, height=50)
        layout.add_widget(label)

        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)

        yes_button = Button(text="Yes")
        no_button = Button(text="No")

        button_layout.add_widget(yes_button)
        button_layout.add_widget(no_button)

        layout.add_widget(button_layout)

        popup = Popup(title=title, content=layout, size_hint=(0.6, 0.4), auto_dismiss=False)

        # Bind the "Yes" and "No" buttons to callback functions
        yes_button.bind(on_release=lambda instance: self.on_confirmation_response(popup, True, callback))
        no_button.bind(on_release=lambda instance: self.on_confirmation_response(popup, False, callback))

        popup.open()

    def on_confirmation_response(self, popup, confirmed, callback):
        """Handle the user's response from the confirmation popup."""
        popup.dismiss()  # Close the popup
        callback(confirmed)  # Call the provided callback with the user's response

    def confirmation_callback(self, confirmed):
        """The callback that handles the user's response."""
        if not confirmed:
            return  # User chose "No", exit early
        else:
            # Proceed with update/redownload logic
            print("Proceed with update/redownload")


############################################################
# Foundation of tutorial
############################################################

    def start_tutorial(self):
        """Starts the tutorial from step 0."""
        self.current_step = 0
        self.show_tutorial_step()

    def show_tutorial_step(self, *args):
        """Shows the current tutorial step with a floating popup."""
        if self.current_step >= len(self.tutorial_steps):
            # Tutorial completed, close the popup and reset
            if self.tutorial_popup:
                self.tutorial_popup.dismiss()
                self.tutorial_popup = None  # Clear the popup
            self.current_step = 0  # Reset tutorial steps
            return

        step_text, widget = self.tutorial_steps[self.current_step]

        # Close the previous popup if it exists
        if self.tutorial_popup:
            self.tutorial_popup.dismiss()

        # Create a new popup and show it
        content = Label(text=step_text)
        self.tutorial_popup = Popup(title="Tutorial", content=content, size_hint=(0.6, 0.4))
        self.tutorial_popup.open()

        # Move to the next step after 5 seconds
        self.current_step += 1
        Clock.schedule_once(self.show_tutorial_step, 5)

    def next_tutorial_step(self):
        """Moves to the next step in the tutorial."""
        self.current_step += 1
        self.show_tutorial_step()

    def complete_tutorial(self):
        """Force complete the tutorial and close the popup."""
        if self.tutorial_popup:
            self.tutorial_popup.dismiss()
        self.current_step = len(self.tutorial_steps)  # Set current step to the end

        # Show a completion message
        complete_popup = Popup(title="Tutorial Complete", content=Label(text="You have completed the tutorial!"), size_hint=(0.6, 0.4))
        complete_popup.open()

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
        popup = Popup(title="Settings", size_hint=(0.8, 0.8), auto_dismiss=False)

        # Create a layout for the popup window
        layout = GridLayout(cols=2, spacing=10, padding=10)

        # Game Directory
        layout.add_widget(Label(text="Game Directory:"))
        game_dir_entry = TextInput(text=self.settings["game_directory"], readonly=True)
        layout.add_widget(game_dir_entry)

        browse_game_directory_button = Button(text="Browse")
        browse_game_directory_button.bind(on_release=lambda x: self.browse_directory(game_dir_entry, True))
        layout.add_widget(browse_game_directory_button)

        open_game_directory_button = Button(text="Open")
        open_game_directory_button.bind(on_release=lambda x: self.open_directory(game_dir_entry.text))
        layout.add_widget(open_game_directory_button)

        # Mods Directory
        layout.add_widget(Label(text="Mods Directory:"))
        mods_dir_entry = TextInput(text=os.path.expandvars(self.settings["mods_directory"]), readonly=True)
        layout.add_widget(mods_dir_entry)

        open_mods_directory_button = Button(text="Open")
        open_mods_directory_button.bind(on_release=lambda x: self.open_directory(mods_dir_entry.text))
        layout.add_widget(open_mods_directory_button)

        # Profile Name Label and Dropdown Menu
        layout.add_widget(Label(text="Profile Name (Game Executive Name):"))
        exe_files = self.get_exe_files(self.settings["game_directory"])

        profile_name_spinner = Spinner(
            text=self.settings.get("profile_name", exe_files[0] if exe_files else "Balatro"),
            values=exe_files
        )
        layout.add_widget(profile_name_spinner)

        profile_name_set_button = Button(text="Set/Create")
        profile_name_set_button.bind(on_release=lambda x: self.set_profile_name(profile_name_spinner.text, mods_dir_entry))
        layout.add_widget(profile_name_set_button)

        # Reset to Default Button
        default_button = Button(text="Reset to Default")
        default_button.bind(on_release=lambda x: self.reset_to_default(game_dir_entry, mods_dir_entry, profile_name_spinner))
        layout.add_widget(default_button)

        # Save and Cancel Buttons
        save_settings_button = Button(text="Save")
        save_settings_button.bind(on_release=lambda x: self.save_settings(
            popup,
            game_dir_entry.text,
            mods_dir_entry.text,
            profile_name_spinner.text,
            self.modpack_var.text,
            self.backup_interval
        ))
        layout.add_widget(save_settings_button)

        cancel_settings_button = Button(text="Exit")
        cancel_settings_button.bind(on_release=lambda x: popup.dismiss())
        layout.add_widget(cancel_settings_button)

        # Set the layout for the popup content
        popup.content = layout

        # Close event handler to reset the flag when the window is closed
        def on_popup_close():
            self.settings_popup_open = False

        popup.bind(on_dismiss=lambda x: on_popup_close())

        # Open the popup
        popup.open()

       
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
    def save_settings(self, popup=None, game_directory=None, mods_directory=None, profile_name=None, default_modpack=None, backup_interval=None):
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

            # Write the settings to the JSON file
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)

            # Close the settings popup after saving
            if popup:
                popup.dismiss()

        except Exception as e:
            # Display an error message if the save operation fails
            self.show_popup(f"Failed to save settings: {str(e)}")

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
    def browse_directory(self, entry_widget: TextInput, readonly: bool):
        # Create a file chooser popup to select a directory
        filechooser_popup = Popup(title="Select Directory", size_hint=(0.9, 0.9))

        filechooser = FileChooserIconView(path=os.getcwd(), dirselect=True)  # Allow only directory selection
        filechooser.bind(on_submit=lambda instance, selection, touch: self.on_directory_selected(instance, selection, entry_widget, filechooser_popup, readonly))

        layout = BoxLayout(orientation='vertical')
        layout.add_widget(filechooser)
        close_button = Button(text="Close", size_hint_y=None, height=40)
        close_button.bind(on_release=filechooser_popup.dismiss)
        layout.add_widget(close_button)

        filechooser_popup.content = layout
        filechooser_popup.open()

    def on_directory_selected(self, filechooser, selection, entry_widget, popup, readonly):
        """Update the directory path in the TextInput widget."""
        if selection:
            folder_selected = selection[0]

            # Temporarily make the entry writable
            if readonly:
                entry_widget.readonly = False

            # Update the entry with the selected folder path
            entry_widget.text = folder_selected

            # If it was readonly before, set it back to readonly
            if readonly:
                entry_widget.readonly = True

            popup.dismiss()

    # Function to open the directory in file explorer
    def open_directory(self, path):
        try:
            # Check if the directory exists, if not create it
            if not os.path.exists(path):
                os.makedirs(path)  # Create the directory and all intermediate directories if needed
                self.show_popup("Info", f"Directory did not exist, created: {path}", "information")

            # Open the directory using the operating system's file explorer
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS or Linux
                os.system(f'xdg-open "{path}"')

        except Exception as e:
            self.show_popup("Error", f"Failed to open or create directory: {e}", "error")

    # Function to set the profile name and copy the executable
    def set_profile_name(self, profile_name, mods_dir_entry: TextInput):
        if profile_name:
            new_mods_dir = os.path.expandvars(f"%AppData%\\{profile_name}\\Mods")
            self.settings["mods_directory"] = new_mods_dir  # Update the settings
            self.mods_dir = new_mods_dir

            # Update the mods_dir_entry to show the new directory
            mods_dir_entry.readonly = False
            mods_dir_entry.text = new_mods_dir
            mods_dir_entry.readonly = True

            source_exe = os.path.join(self.game_dir, "balatro.exe")
            destination_exe = os.path.join(self.game_dir, f"{profile_name}.exe")

            if not os.path.exists(source_exe):
                self.show_popup("File Not Found", "balatro.exe not found in the game directory. Please choose an executable file to copy.", "warning")

                # Use Kivy's file chooser to select an executable file
                filechooser_popup = Popup(title="Select Executable", size_hint=(0.9, 0.9))
                filechooser = FileChooserIconView(filters=['*.exe'])
                filechooser.bind(on_submit=lambda instance, selection, touch: self.on_exe_selected(instance, selection, filechooser_popup, profile_name, mods_dir_entry))

                layout = BoxLayout(orientation='vertical')
                layout.add_widget(filechooser)
                close_button = Button(text="Close", size_hint_y=None, height=40)
                close_button.bind(on_release=filechooser_popup.dismiss)
                layout.add_widget(close_button)

                filechooser_popup.content = layout
                filechooser_popup.open()

            else:
                self.copy_exe_file(source_exe, destination_exe)

    def on_exe_selected(self, filechooser, selection, popup, profile_name, mods_dir_entry):
        """Callback when an executable file is selected."""
        if selection:
            source_exe = selection[0]
            destination_exe = os.path.join(self.game_dir, f"{profile_name}.exe")
            self.copy_exe_file(source_exe, destination_exe)

        popup.dismiss()

    def copy_exe_file(self, source_exe, destination_exe):
        """Copies the executable file to the new profile name."""
        try:
            shutil.copy2(source_exe, destination_exe)
            self.show_popup("Success", f"Profile executable {os.path.basename(destination_exe)} created successfully!", "information")
        except Exception as e:
            self.show_popup("Error", f"Failed to create {os.path.basename(destination_exe)}: {str(e)}", "error")

    # Function to get .exe files and strip the extension
    def get_exe_files(self, directory):
        try:
            exe_files = [f[:-4] for f in os.listdir(directory) if f.endswith(".exe")]
            return exe_files
        except FileNotFoundError:
            self.show_popup("Error", f"Directory not found: {directory}", "error")
            return []

############################################################
# Foundation of time travel popup
############################################################

    def open_revert_popup(self):
        selected_modpack = self.modpack_var.text

        # Check if the selected modpack is "Coonie's Modpack"
        if selected_modpack == "Coonie's Modpack":
            # Show a popup message and prevent proceeding
            self.show_popup("Incompatible Modpack", "This function is not compatible with Coonie's Modpack!", "warning")
            return

        # Prevent opening multiple time travel popups
        if self.revert_popup_open:
            return

        # Mark the time travel popup as open
        self.revert_popup_open = True

        # Create the layout for the popup
        layout = GridLayout(cols=2, padding=10, spacing=10)

        # Label for selecting the version
        layout.add_widget(Label(text="Select version to time travel:"))

        # Fetch all available versions (commit messages)
        commit_versions = self.get_all_commit_versions()

        # Dropdown menu to select version
        self.version_var = Spinner(
            text=commit_versions[0] if commit_versions else "",
            values=commit_versions
        )
        layout.add_widget(self.version_var)

        # Submit Button to find the commit hash
        submit_button = Button(text="Submit")
        submit_button.bind(on_release=self.submit_version)
        layout.add_widget(submit_button)

        # Result Label for Commit Hash
        layout.add_widget(Label(text="Hash:", color=[0.5, 0.5, 0.5, 1]))  # Gray text color
        self.version_hash_label = Label(text="", color=[0.5, 0.5, 0.5, 1])
        layout.add_widget(self.version_hash_label)

        # Button to Revert to Current
        current_button = Button(text="Revert to Current")
        current_button.bind(on_release=self.switch_back_to_main)
        layout.add_widget(current_button)

        # Button to Revert to Commit
        self.time_travel_button = Button(text="Time Travel", disabled=True)  # Initially disabled
        self.time_travel_button.bind(on_release=self.revert_version)
        layout.add_widget(self.time_travel_button)

        # Create a popup for the time travel dialog
        popup = Popup(title="Time Machine", content=layout, size_hint=(0.6, 0.6), auto_dismiss=False)

        # Close event handler to reset the flag when the window is closed
        def revert_on_close(instance):
            self.revert_popup_open = False
            popup.dismiss()

        # Close button
        close_button = Button(text="Close", size_hint=(1, 0.2))
        close_button.bind(on_release=revert_on_close)
        layout.add_widget(close_button)

        # Open the popup
        popup.open()

    # Function to display popups for warnings or errors
    def show_popup(self, title, message, popup_type):
        """Displays a popup with a message."""
        layout = BoxLayout(orientation='vertical', padding=10)
        label = Label(text=message)
        close_button = Button(text="Close", size_hint_y=None, height=40)
        layout.add_widget(label)
        layout.add_widget(close_button)

        popup = Popup(title=title, content=layout, size_hint=(0.6, 0.4))
        close_button.bind(on_release=popup.dismiss)

        popup.open()


############################################################
# Time travel functions
############################################################

    def get_all_commit_versions(self, limit_to_commit=None):
        modpack_name = self.modpack_var.text
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
            self.show_popup("Error", "Invalid Git repository.", "critical")
            return []
        
        except Exception as e:
            self.show_popup("Error", f"Failed to fetch commit versions: {str(e)}", "critical")
            return []

    def submit_version(self):
        # Store user input version in self.old_version
        self.old_version = self.version_var.text

        # Fetch the commit hash based on user input
        self.find_commit(self.old_version)

    def find_commit(self, old_version):
        modpack_name = self.modpack_var.text
        repo_path = os.path.join(os.getcwd(), modpack_name)

        if not os.path.exists(repo_path):
            self.show_popup("Error", "The modpack not found. Please download first.", "critical")
            return

        # Fetch the commit hash by the version message
        commit_hash = self.find_commit_hash_by_message(old_version)

        # If commit hash found, update the label and enable the time travel button
        if commit_hash:
            if commit_hash.startswith("Error"):
                self.show_popup("Error", commit_hash, "critical")
            else:
                self.version_hash_label.text = f"{commit_hash}"
                self.time_travel_button.disabled = False  # Enable the time travel button

        else:
            self.show_popup("Not Found", f"No commit found with version: {old_version}", "information")

    def find_commit_hash_by_message(self, commit_message):
        modpack_name = self.modpack_var.text
        repo_path = os.path.join(os.getcwd(), modpack_name)
        
        try:
            # Initialize the repository
            repo = git.Repo(repo_path)

            # Iterate through the commits and search for the commit message
            for commit in repo.iter_commits():
                commit_first_line = commit.message.split("\n", 1)[0]
                if re.fullmatch(commit_message, commit_first_line):
                    return commit.hexsha

            return None
        except git.exc.InvalidGitRepositoryError:
            return "Error: Invalid Git repository."
        except Exception as e:
            return f"Error: {str(e)}"

    def revert_version(self):
        modpack_name = self.modpack_var.text
        repo_path = os.path.join(os.getcwd(), modpack_name)
        old_version = self.version_var.text

        # Get the correct commit hash from the version_hash_label
        commit_hash = self.version_hash_label.text

        try:
            repo = git.Repo(repo_path)

            # Perform git switch --detach to detach HEAD
            repo.git.switch('--detach')

            # Perform the git reset --hard <hash>
            repo.git.reset('--hard', commit_hash)

            # Show success message
            self.show_popup("Success", f"Time traveled to version: {old_version}, please install again.", "information")

        except Exception as e:
            self.show_popup("Error", f"Failed to time travel: {str(e)}", "critical")

    def switch_back_to_main(self):
        modpack_name = self.modpack_var.text
        repo_path = os.path.join(os.getcwd(), modpack_name)

        try:
            repo = git.Repo(repo_path)
            
            # Perform git switch main to switch back to the main branch
            repo.git.switch('main')

            # Show success message
            self.show_popup("Success", "Travelled back to current.", "information")

        except Exception as e:
            self.show_popup("Error", f"Failed to travel back to current: {str(e)}", "critical")

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
                    # Use subprocess to launch the game in a non-blocking way
                    subprocess.Popen([game_executable], shell=True)
                else:
                    raise FileNotFoundError(f"Game executable not found: {game_executable}")
            except Exception as e:
                # Display an error message if something goes wrong
                self.show_popup("Error", f"Failed to launch game: {str(e)}", "critical")

        elif system_platform == "Linux":
            try:
                # Use Steam to launch the game via its app ID
                steam_command = "steam://rungameid/2379780"
                print(f"Launching game via Steam: {steam_command}")
                subprocess.Popen(["xdg-open", steam_command])
            except Exception as e:
                # Display an error message if something goes wrong
                self.show_popup("Error", f"Failed to launch game via Steam: {str(e)}", "critical")


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
        mods_path = os.path.join(os.path.expandvars(self.mods_dir), "ModpackUtil")
        
        current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
        modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')

        current_version = None

        self.settings = self.load_settings()

        if os.path.exists(current_version_file):
            try:
                with open(current_version_file, 'r') as file:
                    current_version = file.read().strip()
            except IOError as e:
                print(f"IOError reading CurrentVersion.txt: {e}")

        pack_name = ""
        if os.path.exists(modpack_util_file):
            try:
                with open(modpack_util_file, 'r') as file:
                    for line in file:
                        if line.startswith('--- VERSION:'):
                            pack_name = line.split(':')[1].strip()
                            break
            except IOError as e:
                print(f"IOError reading ModpackUtil.lua: {e}")
        else:
            pack_name = None
        
        return current_version, pack_name
    
    def update_installed_info(self):
        self.settings = self.load_settings()

        install_path = os.path.expandvars(self.settings["mods_directory"])
        mods_path = os.path.join(install_path, 'ModpackUtil')

        current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
        current_pack_file = os.path.join(mods_path, 'CurrentPack.txt')  # New file to check
        modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')

        current_version = None
        pack_name = None

        try:
            # First check if CurrentVersion.txt exists and read the version
            if os.path.exists(current_version_file):
                try:
                    with open(current_version_file, 'r') as file:
                        current_version = file.read().strip()
                except IOError as e:
                    print(f"IOError reading CurrentVersion.txt: {e}")

            # Check if CurrentPack.txt exists and use its content as pack_name
            if os.path.exists(current_pack_file):
                try:
                    with open(current_pack_file, 'r') as file:
                        pack_name = file.read().strip()
                except IOError as e:
                    print(f"IOError reading CurrentPack.txt: {e}")
            else:
                # Fallback to checking ModpackUtil.lua if CurrentPack.txt does not exist
                if os.path.exists(modpack_util_file):
                    try:
                        with open(modpack_util_file, 'r') as file:
                            for line in file:
                                if line.startswith('--- VERSION:'):
                                    pack_name = line.split(':')[1].strip()
                                    break
                    except IOError as e:
                        print(f"IOError reading ModpackUtil.lua: {e}")

            # Update the installed info label with the pack name and version
            if pack_name:
                self.installed_info_label.text = f"Installed pack: {pack_name} ({current_version})"
            else:
                self.installed_info_label.text = "No modpack installed or ModpackUtil mod removed."

            # Center the label's text
            self.installed_info_label.halign = 'center'
            self.installed_info_label.valign = 'middle'
            self.installed_info_label.texture_update()  # Make sure the alignment takes effect

        except Exception as e:
            self.show_popup("Error", f"An error occurred while updating installed info: {str(e)}", "critical")

############################################################
# Middle functions (Download, install, update, uninstall)
############################################################

    def get_modpack_url(self, modpack_name):
        urls = {
            "Dimserene's Modpack": "https://github.com/Dimserene/Dimserenes-Modpack.git",
            "Fine-tuned Pack": "https://github.com/Dimserene/Fine-tuned-Pack.git",
            "Vanilla+ Pack": "https://github.com/Dimserene/Vanilla-Plus-Pack.git",
            "Insane Pack": "https://github.com/Dimserene/Insane-Pack.git",
            "Cruel Pack": "https://github.com/Dimserene/Cruel-Pack.git"
        }
        return urls.get(modpack_name, "")

    def prompt_for_installation(self):
        modpack_name = self.modpack_var.currentText()
        modpack_url = self.get_modpack_url(modpack_name)
        if modpack_url:
            self.download_modpack(main_window=self, clone_url=modpack_url)
        else:
            self.show_popup("Error", "Invalid modpack selected.", "critical")

    def download_modpack(self, main_window=None, clone_url=None):
        try:
            modpack_name = self.modpack_var.currentText()  # Get the name of the selected modpack

            # Special case for Coonie's Modpack
            if modpack_name == "Coonie's Modpack":
                coonies_modpack_path = os.path.join(os.getcwd(), "Coonies-Modpack")
                
                # Check if "Coonies-Modpack" folder is already present
                if os.path.isdir(coonies_modpack_path):
                    # Prompt user whether to overwrite the existing folder or skip download
                    self.show_confirmation_popup("Confirm update/redownload", "Coonie's Modpack is already downloaded. Update/Redownload?", self.confirmation_callback)

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
                self.show_popup("Error", "Modpack URL not found. Please ensure you selected a valid modpack.", "critical")
                return

            repo_name = clone_url.split('/')[-1].replace('.git', '')

            # Prompt force download if the repository directory already exists
            force_update = False
            if os.path.isdir(repo_name):
                self.show_confirmation_popup(repo_name, self.confirmation_callback)

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
            self.show_popup("Error", f"An unexpected error occurred: {str(e)}", "error")

    def show_progress_dialog(self, main_window, modpack_name):
        """Show a progress popup with modpack name."""

        # Create a vertical layout for the popup
        layout = BoxLayout(orientation='vertical', padding=10)

        # Add a label to display the modpack name
        label = Label(text=f"Downloading {modpack_name}...", size_hint_y=None, height=50)
        layout.add_widget(label)

        # Add a progress bar
        self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=30)
        layout.add_widget(self.progress_bar)

        # Create the popup
        self.progress_popup = Popup(title="", content=layout, size_hint=(0.7, 0.3), auto_dismiss=False)
        
        # Open the popup
        self.progress_popup.open()

        # You can use a clock or threading to update the progress bar during the download process
        # For example, simulate progress (you will replace this with your actual logic)
        Clock.schedule_interval(self.update_progress_bar, 0.1)

    def update_progress_bar(self, dt):
        """Update the progress bar."""
        if self.progress_bar.value >= 100:
            # When progress is complete, close the popup
            self.progress_popup.dismiss()
            return False  # Stop the Clock schedule
        else:
            # Increment the progress bar (this would be based on your actual download progress)
            self.progress_bar.value += 5
            return True  # Continue updating

    def close_progress_dialog(self):
        """Close the progress dialog."""
        if self.progress_popup:
            self.progress_popup.dismiss()

    def download_and_unzip_coonies_modpack(self):
        """Download and unzip Coonie's Modpack with progress tracking."""
        try:
            url = "https://github.com/GayCoonie/Coonies-Mod-Pack/releases/latest/download/Mods.zip"
            local_zip_path = os.path.join(os.getcwd(), "Mods.zip")
            unzip_folder = os.path.join(os.getcwd(), "Coonies-Modpack")

            # Ensure the folder exists
            if not os.path.exists(unzip_folder):
                os.makedirs(unzip_folder)

            # Create and configure the progress popup
            layout = BoxLayout(orientation='vertical', padding=10)
            self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=30)
            layout.add_widget(Label(text="Downloading Coonie's Modpack..."))
            layout.add_widget(self.progress_bar)

            self.progress_popup = Popup(title="Download Progress", content=layout, size_hint=(0.7, 0.3), auto_dismiss=False)
            self.progress_popup.open()

            # Start the download in a background thread
            Clock.schedule_once(lambda dt: self.download_worker(url, local_zip_path, unzip_folder), 0.1)

        except Exception as e:
            self.show_popup("Error", f"An error occurred while setting up the download: {str(e)}", "error")

    def download_worker(self, url, local_zip_path, unzip_folder):
        """Download the modpack and update the progress."""
        try:
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(local_zip_path, 'wb') as f:
                for data in response.iter_content(chunk_size=4096):
                    if data:
                        f.write(data)
                        downloaded_size += len(data)
                        progress = int(downloaded_size * 100 / total_size)
                        self.progress_bar.value = progress
                        Clock.usleep(10000)  # Ensure the UI updates smoothly

            # Unzip the file after download
            with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                zip_ref.extractall(unzip_folder)

            # Call the download finished handler
            self.on_coonies_download_finished(True, "Download and extraction complete.")
        
        except Exception as e:
            self.on_coonies_download_finished(False, f"Download failed: {str(e)}")

    def on_coonies_download_finished(self, success, message):
        """Handle the download finished event."""
        # Close the progress popup
        self.progress_popup.dismiss()

        # Show result popup
        if success:
            self.show_popup("Success", message, "info")

            # Optionally, create CurrentVersion.txt and CurrentPack.txt files
            modpack_util_path = os.path.join(os.getcwd(), "Coonies-Modpack", 'Mods', 'ModpackUtil')
            if not os.path.exists(modpack_util_path):
                os.makedirs(modpack_util_path)

            # Write to CurrentVersion.txt and CurrentPack.txt
            current_version_path = os.path.join(modpack_util_path, 'CurrentVersion.txt')
            with open(current_version_path, 'w') as version_file:
                version_file.write(self.get_latest_tag_message())

            current_pack_path = os.path.join(modpack_util_path, 'CurrentPack.txt')
            with open(current_pack_path, 'w') as pack_file:
                pack_file.write("Coonie's Modpack")

        else:
            self.show_popup("Error", message, "error")


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

    def on_download_finished(self, success, message):
        """Handle the completion of the download."""
        # Close the progress dialog
        if self.progress_popup:
            self.progress_popup.dismiss()

        # Show the result message (success or failure)
        popup_title = "Download Status" if success else "Error"
        popup_type = "info" if success else "error"

        # Show the result using a popup
        self.show_popup(popup_title, message, popup_type)

    def update_modpack(self):
        modpack_name = self.modpack_var.text  # Use the Kivy Spinner or TextInput for modpack selection
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)
        selected_modpack = self.modpack_var.text

        # Check if the selected modpack is "Coonie's Modpack"
        if selected_modpack == "Coonie's Modpack":
            self.show_popup("Incompatible Modpack", "This function is not compatible with Coonie's Modpack! Please use Download/Update instead.", "warning")
            return

        # Check if the repository exists
        if not os.path.isdir(repo_path):
            self.show_popup("Error", "Repository not found. Attempting to clone it.", "error")
            self.download_modpack(main_window=self, clone_url=clone_url)  # Attempt to download the modpack if it's not found
            return

        # Create and configure the progress popup
        layout = BoxLayout(orientation='vertical', padding=10)
        label = Label(text=f"Updating {modpack_name}...", size_hint_y=None, height=50)
        layout.add_widget(label)

        self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=30)
        layout.add_widget(self.progress_bar)

        self.progress_popup = Popup(title="Updating Modpack", content=layout, size_hint=(0.7, 0.3), auto_dismiss=False)
        self.progress_popup.open()

        # Start the update process using a background worker
        Clock.schedule_once(lambda dt: self.start_update_worker(repo_path), 0.1)

    def start_update_worker(self, repo_path):
        """Start the modpack update worker."""
        # Create the worker for updating the modpack (you can replace this with actual background work)
        try:
            # Simulate the update (you will replace this with the actual update logic)
            self.simulate_progress()
            self.on_update_finished(True, "Modpack updated successfully.")
        except Exception as e:
            self.on_update_finished(False, f"Failed to update modpack: {str(e)}")

    def simulate_progress(self):
        """Simulate progress bar updates (replace this with actual logic)."""
        for i in range(0, 101, 10):
            self.progress_bar.value = i
            Clock.usleep(100000)  # Simulate work being done (replace with actual download or update logic)

    def on_update_finished(self, success, message):
        """Handle the completion of the update process."""
        # Close the progress popup
        if self.progress_popup:
            self.progress_popup.dismiss()

        # Show the result message (success or failure)
        popup_title = "Update Status" if success else "Error"
        popup_type = "info" if success else "error"
        self.show_popup(popup_title, message, popup_type)

    def install_modpack(self):
        self.settings = self.load_settings()
        modpack_name = self.modpack_var.text  # Assuming Kivy Spinner/TextInput for mod selection

        # Special case for Coonie's Modpack
        if modpack_name == "Coonie's Modpack":
            repo_name = "Coonies-Modpack"
            repo_path = os.path.join(os.getcwd(), repo_name)
            mods_src = os.path.join(repo_path, 'Mods')
        else:
            # Handle regular modpacks
            clone_url = self.get_modpack_url(modpack_name)
            repo_name = clone_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(os.getcwd(), repo_name)
            mods_src = os.path.join(repo_path, 'Mods')

        install_path = self.mods_dir
        mod_list = self.get_mod_list(mods_src)

        try:
            # Check if the repository directory exists
            if not os.path.isdir(repo_path):
                self.show_popup("Error", f"Modpack {repo_path} does not exist. Please download first.", "error")
                return

            # Check if the Mods folder exists in the repository
            if not os.path.isdir(mods_src):
                self.show_popup("Error", f"Mods folder not found in the repository: {mods_src}. Please force download and try again.", "error")
                return

            # Check if the install path exists and create it if necessary
            if not os.path.exists(install_path):
                os.makedirs(install_path)

            # Pop up mod selection window for user to choose mods
            self.popup_mod_selection(mod_list)

        except Exception as e:
            self.show_popup("Error", f"An unexpected error occurred during installation: {str(e)}", "error")

    def get_mod_list(self, mods_src):
        try:
            return [f for f in os.listdir(mods_src) if os.path.isdir(os.path.join(mods_src, f))]
        except FileNotFoundError:
            self.show_popup("Error", "Mods folder not found.", "error")
            return []

    def popup_mod_selection(self, mod_list):
        # Prevent opening multiple install popups
        if self.install_popup_open:
            return

        # Mark the install popup as open
        self.install_popup_open = True

        # Create a grid layout for mod selection
        layout = GridLayout(cols=1, padding=10, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Create a scrollable area for mod selection
        scroll_view = ScrollView(size_hint=(1, None), size=(self.width, 400))
        scroll_view.add_widget(layout)

        # Instruction label
        label = Label(text='[color=ff3333]Select the mods you DO NOT want to install:[/color]', markup=True, size_hint_y=None, height=50)
        layout.add_widget(label)

        # Locked mods that cannot be deselected
        locked_mods = ["ModpackUtil", "Steamodded"]
        filtered_mod_list = [mod for mod in mod_list if mod not in locked_mods]

        # Mod selection checkboxes
        mod_vars = []
        for mod in filtered_mod_list:
            box_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            checkbox = CheckBox()
            label = Label(text=mod)
            checkbox.active = mod in self.excluded_mods  # Assuming self.excluded_mods holds mods to exclude
            mod_vars.append((mod, checkbox))

            box_layout.add_widget(checkbox)
            box_layout.add_widget(label)
            layout.add_widget(box_layout)

        # Buttons for "Clear All", "Reverse Select", and "Save & Install"
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, padding=10, spacing=10)

        clear_button = Button(text="Clear All", on_press=lambda instance: self.clear_mod_selection(mod_vars))
        reverse_button = Button(text="Reverse Select", on_press=lambda instance: self.reverse_mod_selection(mod_vars))
        save_button = Button(text="Save & Install", on_press=lambda instance: self.save_and_install(mod_vars))

        button_layout.add_widget(clear_button)
        button_layout.add_widget(reverse_button)
        button_layout.add_widget(save_button)

        # Backup checkbox
        backup_checkbox = CheckBox(active=self.settings.get("backup_mods", False))
        backup_label = Label(text="Backup Mods Folder")
        backup_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        backup_layout.add_widget(backup_checkbox)
        backup_layout.add_widget(backup_label)

        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        main_layout.add_widget(scroll_view)
        main_layout.add_widget(backup_layout)
        main_layout.add_widget(button_layout)

        # Create the popup
        popup = Popup(title="Mod Selection", content=main_layout, size_hint=(0.8, 0.8), auto_dismiss=False)

        # Close event handler
        def close_popup(instance):
            self.install_popup_open = False
            popup.dismiss()

        # Bind close button to dismiss popup
        save_button.bind(on_release=close_popup)
        popup.open()

    def clear_mod_selection(self, mod_vars):
        """Clear all mod selections."""
        for mod, checkbox in mod_vars:
            checkbox.active = False

    def reverse_mod_selection(self, mod_vars):
        """Reverse mod selections."""
        for mod, checkbox in mod_vars:
            checkbox.active = not checkbox.active

    def handle_dependencies(self, mod, var, mod_vars, dependencies):
        """Handle mod dependencies when a checkbox is clicked (checked = excluded)."""
        
        # Case 1: If a required mod (A) is excluded, ensure all dependent mods (B) are excluded
        if var.isChecked():
            for dependent_mod, required_mods in dependencies.items():
                if mod in required_mods:  # If the current mod is a required mod for any dependent mod
                    for mod_name, mod_var in mod_vars:
                        if mod_name == dependent_mod and not mod_var.isChecked():
                            # Exclude the dependent mod if the required mod is excluded
                            mod_var.setChecked(True)

        # Case 2: If a dependent mod (B) is unexcluded (unchecked), unexclude the required mod (A)
        if not var.isChecked() and mod in dependencies:
            required_mods = dependencies[mod]
            for required_mod in required_mods:
                for mod_name, mod_var in mod_vars:
                    if mod_name == required_mod and mod_var.isChecked():
                        # Unexclude the required mod if the dependent mod is unexcluded
                        mod_var.setChecked(False)

    def save_preferences(self, mod_vars):
        # Let the user pick mods they DON'T want to install
        self.excluded_mods = [mod for mod, var in mod_vars if var.isChecked()]

        # Save user preferences to a file
        with open(INSTALL_FILE, "w") as f:
            for mod in self.excluded_mods:
                f.write(mod + "\n")

        self.show_popup("Preferences Saved", "Excluded mods saved", "info")

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
            self.show_popup(
                "Warning",
                "The current 'Mods' folder will be erased. Do you want to proceed?",
                self.on_confirmation_response
            )

            if response == QMessageBox.StandardButton.No:
                return  # User canceled the installation

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

            # Remove the existing Mods folder
            shutil.rmtree(self.mods_dir, ignore_errors=True)

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

        # Close the installation popup
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

    def check_versions(self):
        try:
            install_path = self.mods_dir
            mods_path = os.path.join(install_path, 'ModpackUtil')

            current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
            modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')
            current_pack_file = os.path.join(mods_path, 'CurrentPack.txt')  # For Coonie's modpack

            current_version = None
            if os.path.exists(current_version_file):
                try:
                    with open(current_version_file, 'r') as file:
                        current_version = file.read().strip()
                except IOError as e:
                    print(f"IOError reading CurrentVersion.txt: {e}")

            pack_name = ""
            # Check if CurrentPack.txt exists for Coonie's modpack
            if os.path.exists(current_pack_file):
                try:
                    with open(current_pack_file, 'r') as file:
                        pack_name = file.read().strip()
                except IOError as e:
                    print(f"IOError reading CurrentPack.txt: {e}")
            elif os.path.exists(modpack_util_file):
                # Check ModpackUtil.lua for version information
                try:
                    with open(modpack_util_file, 'r') as file:
                        for line in file:
                            if line.startswith('--- VERSION:'):
                                pack_name = line.split(':')[1].strip()
                                break
                except IOError as e:
                    print(f"IOError reading ModpackUtil.lua: {e}")
            else:
                pack_name = None

            commit_messages = self.fetch_commit_messages()

            version_info = ""
            coonies_version_info = self.get_latest_coonies_tag()
            installed_info = ""
            update_message = ""

            for repo_name, commit_message in commit_messages.items():
                version_info += f"{repo_name}:\t{commit_message}\n"

                if pack_name == repo_name:
                    if current_version and commit_message != current_version:
                        update_message = "Update available!"
            
            if pack_name:
                installed_info = f"\nInstalled modpack: {pack_name}\nInstalled version: {current_version}"
            else:
                installed_info = "\nNo modpack installed or ModpackUtil mod removed."

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Version Information")
            msg_box.setText(f"{version_info}\nCoonie's:\t{coonies_version_info}\n{installed_info}\n\n{update_message}")
            msg_box.exec()

        except Exception as e:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"An error occurred while checking versions: {str(e)}")
            msg_box.exec()


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
            padding-top: 10px;   /* Equivalent to ipady */
            padding-bottom: 10px; /* Equivalent to ipady */
            padding-left: 10px;  /* Equivalent to ipadx */
            padding-right: 10px; /* Equivalent to ipadx */
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


