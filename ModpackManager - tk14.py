import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import re
import shutil
import requests
import webbrowser
import subprocess
import zipfile
import stat
import json
from idlelib.tooltip import Hovertip
import git
from git import GitCommandError, Repo

############################################################

# Default settings

############################################################

DEFAULT_SETTINGS = {
    "game_directory": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro",
    "profile_name": "Balatro",
    "mods_directory": "%AppData%\\Balatro\\Mods",
}

# File path for settings

SETTINGS_FILE = "user_settings.json"
INSTALL_FILE = "excluded_mods.json"

############################################################

# Initialize Program

############################################################

class ModpackManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dimserene's Modpack Manager")

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
        self.excluded_mods = self.read_preferences()

        # Declare default versions
        self.old_version = ""
        self.version_hash = ""

        self.create_widgets()
        self.update_installed_info()  # Initial update

############################################################

# Foundation of root window

############################################################

    def create_widgets(self):
        
        root.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="column")
        
        # Title label
        self.title_label = tk.Label(self.root, text="☷☷☷☷Dimserene's Modpack Manager☷☷☷☷", font=('Helvetica', 16))
        self.title_label.grid(pady=10, row=0, column=0, columnspan=6)

        # PLAY button
        self.play_button = tk.Button(self.root, text="PLAY", command=self.play_game, font=('Helvetica', 30), height=0, width=10, background='#0087eb')
        self.play_button.grid(padx=5, pady=5, row=1, column=0, columnspan=6)
        Hovertip(self.play_button, "Play Balatro modded now")

        # Installed modpack info
        self.installed_info_label = tk.Label(self.root, text="", font=('Helvetica', 12))
        self.installed_info_label.grid(padx=5, pady=5, ipady=5, row=2, column=0, columnspan=6)

        # Refresh button
        self.refresh_button = tk.Button(self.root, text="Refresh", command=self.update_installed_info)
        self.refresh_button.grid(padx=5, pady=5, row=3, column=0, columnspan=6)
        Hovertip(self.refresh_button, "Refresh currently installed modpack information")

        # Modpack selection dropdown
        self.modpack_label = tk.Label(self.root, text="Select Modpack:")
        self.modpack_label.grid(padx=5, ipady=5, row=4, column=0, columnspan=6)

        self.modpack_var = tk.StringVar()
        self.modpack_dropdown = ttk.Combobox(self.root, textvariable=self.modpack_var)
        self.modpack_dropdown['values'] = [
            "Dimserenes-Modpack",
            "Fine-tuned-Pack",
            "Vanilla-Plus-Pack"
        ]
        self.modpack_dropdown.grid(padx=5, ipady=5, row=5, column=0, columnspan=6)
        self.modpack_dropdown.current(0)

        # Create Download button
        self.download_button = tk.Button(self.root, text="Download (Clone)", command=self.download_modpack, font=('Helvetica', 16))
        self.download_button.grid(padx=10, pady=5, ipady=5, row=6, column=0, columnspan=3, sticky="WE")
        Hovertip(self.download_button, "Download (clone) selected modpack to the same directory as manager")

        # Create Install button
        self.install_button = tk.Button(self.root, text="Install (Copy)", command=self.install_modpack, font=('Helvetica', 16))
        self.install_button.grid(padx=10, pady=5, ipady=5, row=6, column=3, columnspan=3, sticky="WE")
        Hovertip(self.install_button, "Copy (install) Mods content")

        # Create Update button
        self.update_button = tk.Button(self.root, text="Update (Reclone)", command=self.update_modpack, font=('Helvetica', 16))
        self.update_button.grid(padx=10, pady=5, ipady=5, row=7, column=0, columnspan=3, sticky="WE")
        Hovertip(self.update_button, "Force reclone selected modpack")

        # Create Uninstall button
        self.uninstall_button = tk.Button(self.root, text="Uninstall (Remove)", command=self.uninstall_modpack, font=('Helvetica', 16))
        self.uninstall_button.grid(padx=10, pady=5, ipady=5, row=7, column=3, columnspan=3, sticky="WE")
        Hovertip(self.uninstall_button, "Delete Mods folder and its contents")

        # Create Check Versions button
        self.check_versions_button = tk.Button(self.root, text="Check Versions", command=self.check_versions, font=('Helvetica', 12))
        self.check_versions_button.grid(padx=10, pady=5, ipady=5, row=8, column=0, columnspan=2, sticky="WE")
        Hovertip(self.check_versions_button, "Check latest version for all modpacks")

        # Create Install Lovely button
        self.install_lovely_button = tk.Button(self.root, text="Install lovely", command=self.install_lovely_injector, font=('Helvetica', 12))
        self.install_lovely_button.grid(padx=10, pady=5, ipady=5, row=8, column=2, columnspan=2, sticky="WE")
        Hovertip(self.install_lovely_button, "Install/update lovely injector")

        # Create Time Travel button
        self.revert_button = tk.Button(self.root, text="Time Travel", command=self.open_revert_popup, font=('Helvetica', 12))
        self.revert_button.grid(padx=10, pady=5, ipady=5, row=8, column=4, columnspan=2, sticky="WE")
        Hovertip(self.revert_button, "Revert the modpack to a certain historical version")

        # Create Mod List button
        self.mod_list_button = tk.Button(self.root, text="Mod List", command=self.open_mod_list, font=('Helvetica', 12))
        self.mod_list_button.grid(padx=10, pady=5, ipady=5, row=9, column=0, columnspan=2, sticky="WE")
        Hovertip(self.mod_list_button, "Open mod list in web browser")

        # Create Settings button
        self.open_settings_button = tk.Button(self.root, text="Settings", command=self.open_settings_popup, font=('Helvetica', 12))
        self.open_settings_button.grid(padx=10, pady=5, ipady=5, row=9, column=2, columnspan=2, sticky="WE")
        Hovertip(self.open_settings_button, "Settings")

        # Create Discord button
        self.discord_button = tk.Button(self.root, text="Join Discord", command=self.open_discord, font=('Helvetica', 12))
        self.discord_button.grid(padx=10, pady=5, ipady=5, row=9, column=4, columnspan=2, sticky="WE")
        Hovertip(self.discord_button, "Open Discord server in web browser")

        # Modpack Manager Info
        self.info = tk.Label(self.root, text="Build: 2024/08/20, Iteration: 14th, Version: Release 1.1.1", font=('Helvetica', 8))
        self.info.grid(row=10,column=0, columnspan=6, sticky="E")


############################################################

# Foundation of settings popup

############################################################

    def open_settings_popup(self):

        # Reload settings whenever setting popup appears
        self.settings = self.load_settings()

        # Prevent opening multiple settings popups
        if self.settings_popup_open:
            return
        
        # Mark the settings popup as open
        self.settings_popup_open = True

        # Create a new popup window
        popup = tk.Toplevel(self.root)
        popup.title("Settings")

        # Make the popup modal and grab focus
        popup.grab_set()
        popup.focus()

        # List all .exe files in the game directory and strip ".exe"
        exe_files = self.get_exe_files(self.settings["game_directory"])

        # Create a StringVar to hold the selected profile name
        profile_name_var = tk.StringVar(popup)
        if exe_files:
            profile_name_var.set(exe_files[0])  # Set default selection to first executable found

        # Game Directory
        self.game_directory_label = tk.Label(popup, text="Game Directory:")
        self.game_directory_label.grid(column=0, row=0, columnspan= 2, pady=5)
        game_dir_entry = tk.Entry(popup, width=50)
        game_dir_entry.grid(column=0, row=1, columnspan= 2, pady=5, padx=5)
        game_dir_entry.insert(0, self.settings["game_directory"])
        
        game_dir_entry.config(state="readonly")

        self.browse_game_directory_button = tk.Button(popup, text="Browse", command=lambda: self.browse_directory(game_dir_entry, True))
        self.browse_game_directory_button.grid(column=0, row=2, columnspan= 1, padx=20, pady=5, sticky="WE")

        self.open_game_directory_button = tk.Button(popup, text="Open", command=lambda: self.open_directory(game_dir_entry.get()))
        self.open_game_directory_button.grid(column=1, row=2, columnspan= 1, padx=20, pady=5, sticky="WE")

        # Mods Directory
        self.mods_directory_label = tk.Label(popup, text="Mods Directory:")
        self.mods_directory_label.grid(column=0, row=3, columnspan= 2, pady=5)
        mods_dir_entry = tk.Entry(popup, width=50)
        mods_dir_entry.grid(column=0, row=4, columnspan= 2, pady=5, padx=5)
        mods_dir_entry.insert(0, os.path.expandvars(self.settings["mods_directory"]))

        mods_dir_entry.config(state="readonly")

        self.open_mods_directory_button = tk.Button(popup, text="Open", command=lambda: self.open_directory(mods_dir_entry.get()))
        self.open_mods_directory_button.grid(column=1, row=5, columnspan= 1, padx=20, pady=5, sticky="WE")

        # Profile Name Label and Dropdown Menu
        self.profile_name_label = tk.Label(popup, text="Profile Name (Game Executive Name):")
        self.profile_name_label.grid(column=0, row=6, columnspan=2, pady=5)
        
        # Create a StringVar to hold the selected profile name
        profile_name_var = tk.StringVar(popup)
        if exe_files:
            profile_name_var.set(self.settings["profile_name"])  # Set default selection to first executable found
        else:
            profile_name_var.set("Balatro")

        profile_name_dropdown = ttk.Combobox(popup, textvariable=profile_name_var, values=exe_files)
        profile_name_dropdown.grid(column=0, row=7, columnspan=2, pady=5, padx=5)

        self.profile_name_set_button = tk.Button(popup, text="Set", command=lambda: self.set_profile_name(profile_name_var.get(), mods_dir_entry))
        self.profile_name_set_button.grid(column=1, row=8, columnspan= 2, padx=20, pady=5, sticky="WE")

        # Reset to Default Button
        self.default_button = tk.Button(popup, text="Reset to Default", command=lambda: self.reset_to_default(game_dir_entry, mods_dir_entry, profile_name_var))
        self.default_button.grid(column=0, row=9, columnspan= 2, pady=5)

        # Save and Cancel Buttons
        self.save_settings_button = tk.Button(popup, text="Save", command=lambda: self.save_settings(popup, game_dir_entry.get(), mods_dir_entry.get(), profile_name_var.get()))
        self.save_settings_button.grid(column=0, row=10, padx=20, pady=20, sticky="WE")
        self.cancel_settings_button = tk.Button(popup, text="Cancel", command=lambda: self.close_settings_popup(popup))
        self.cancel_settings_button.grid(column=1, row=10, padx=20, pady=20, sticky="WE")

        # Close event handler to reset the flag when the window is closed
        def settings_on_close():
            self.settings_popup_open = False
            popup.destroy()

        # When the popup is closed, reset the flag
        popup.protocol("WM_DELETE_WINDOW", settings_on_close)

    def close_settings_popup(self, popup):
        self.settings_popup_open = False
        popup.destroy()
       
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
    def save_settings(self, popup, game_directory, mods_directory, profile_name):
        try:
            # Save the settings to the settings dictionary
            self.settings["game_directory"] = game_directory
            self.settings["profile_name"] = profile_name
            self.settings["mods_directory"] = mods_directory

            # Write the settings to the JSON file
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)

            # Show a confirmation message
            messagebox.showinfo("Settings", "Settings have been saved successfully.")
            
            # Reload the settings after saving
            self.settings = self.load_settings()

            # Close the popup
            self.settings_popup_open = False
            popup.destroy()

        except Exception as e:
            # Display an error message if the save operation fails
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    # Function to reset settings to defaults
    def reset_to_default(self, game_dir_entry, mods_dir_entry, profile_name_var):
        self.settings = DEFAULT_SETTINGS.copy()
        game_dir_entry.config(state="normal")
        game_dir_entry.delete(0, tk.END)
        game_dir_entry.insert(0, self.settings["game_directory"])
        game_dir_entry.config(state="readonly")

        mods_dir_entry.config(state="normal")
        mods_dir_entry.delete(0, tk.END)
        mods_dir_entry.insert(0, os.path.expandvars(self.settings["mods_directory"]))
        mods_dir_entry.config(state="readonly")

        # Reset profile name
        profile_name_var.set(self.settings["profile_name"])  # Use set() to reset the profile name

    # Function to browse and update the directory
    def browse_directory(self, entry_widget, readonly):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            # Temporarily make the entry writable
            if readonly:
                entry_widget.config(state="normal")

            # Update the entry with the selected folder path
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder_selected)

            # If it was readonly before, set it back to readonly
            if readonly:
                entry_widget.config(state="readonly")

    # Function to open the directory in file explorer
    def open_directory(self, path):
        try:
            # Check if the directory exists, if not create it
            if not os.path.exists(path):
                os.makedirs(path)  # Create the directory and all intermediate directories if needed
                messagebox.showinfo("Info", f"Directory did not exist, created: {path}")
            
            # Open the directory after ensuring it exists
            os.startfile(path)
        except Exception as e:
            # Display an error message if unable to open the directory
            messagebox.showerror("Error", f"Failed to open or create directory: {e}")

    # Function to set profile name
    def set_profile_name(self, profile_name, mods_dir_entry):
        # Construct the new mods directory path based on profile name
        if profile_name:
            new_mods_dir = os.path.expandvars(f"%AppData%\\{profile_name}\\Mods")
            self.settings["mods_directory"] = new_mods_dir  # Update the settings
            self.mods_dir = new_mods_dir

            # Update the mods_dir_entry to show the new directory
            mods_dir_entry.config(state="normal")  # Temporarily make it writable
            mods_dir_entry.delete(0, tk.END)  # Clear current content
            mods_dir_entry.insert(0, new_mods_dir)  # Insert the new directory
            mods_dir_entry.config(state="readonly")  # Set back to readonly

    # Function to get .exe files and strip the extension
    def get_exe_files(self, directory):
        try:
            exe_files = [f[:-4] for f in os.listdir(directory) if f.endswith(".exe")]
            return exe_files
        except FileNotFoundError:
            messagebox.showerror("Error", f"Directory not found: {directory}")
            return []

############################################################

# Foundation of time travel popup

############################################################

    def open_revert_popup(self):

        # Prevent opening multiple time travel popups
        if self.revert_popup_open:
            return
        
        # Mark the time travel popup as open
        self.revert_popup_open = True

        # Create a new popup window
        popup = tk.Toplevel(self.root)
        popup.title("Time Machine")

        # Make the popup modal and grab focus
        popup.grab_set()
        popup.focus()

        # Label for selecting the version
        self.old_version_label = tk.Label(popup, text="Select version to time travel:")
        self.old_version_label.grid(column=0, row=0, columnspan=2, pady=5)

        # Fetch all available versions (commit messages)
        commit_versions = self.get_all_commit_versions()

        # Dropdown menu to select version
        self.version_var = tk.StringVar()
        self.version_dropdown = ttk.Combobox(popup, textvariable=self.version_var, values=commit_versions, width=50)
        self.version_dropdown.grid(column=0, row=1, columnspan=2, pady=5, padx=5)

        if commit_versions:
            self.version_dropdown.current(0)  # Set the default selection to the first version

        # Submit Button to find the commit hash
        submit_button = tk.Button(popup, text="Submit", command=self.submit_version)
        submit_button.grid(column=0, row=2, columnspan= 2, pady=5)

        # Result Label for Commit Hash
        self.hash_title_label = tk.Label(popup, text="Hash:", fg="gray")
        self.hash_title_label.grid(column=0, row=3, columnspan=1, pady=5, sticky="W")
        self.version_hash_label = tk.Label(popup, text="", fg="gray")
        self.version_hash_label.grid(column=0, row=3, columnspan= 2, pady=5)

        # Reset Button to Revert to Commit
        self.time_travel_button = tk.Button(popup, text="Time Travel", command=self.revert_version, state=tk.DISABLED)
        self.time_travel_button.grid(column=0, row=4, columnspan= 2, pady=5)

        # Close event handler to reset the flag when the window is closed
        def revert_on_close():
            self.revert_popup_open = False
            popup.destroy()

        # When the popup is closed, reset the flag
        popup.protocol("WM_DELETE_WINDOW", revert_on_close)

############################################################

# Time travel functions

############################################################

    def get_all_commit_versions(self, limit_to_commit=None):
        modpack_name = self.modpack_var.get()
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
            messagebox.showerror("Error", "Invalid Git repository.")
            return []
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch commit versions: {str(e)}")
            return []

    def submit_version(self):
        # Store user input version in self.old_version
        self.old_version = self.version_var.get()

        # Fetch the commit hash based on user input
        self.find_commit(self.old_version)

    def find_commit(self, old_version):
        modpack_name = self.modpack_var.get()
        repo_path = os.path.join(os.getcwd(), modpack_name)

        if not os.path.exists(repo_path):
            messagebox.showerror("Error", "The modpack not found. Please download first.")
            return

        # Fetch the commit hash by the version message
        commit_hash = self.find_commit_hash_by_message(old_version)

        # If commit hash found, update the label and enable the time travel button
        if commit_hash:
            if commit_hash.startswith("Error"):
                messagebox.showerror("Error", commit_hash)
            else:
                self.version_hash_label.config(text=f"{commit_hash}")
                self.time_travel_button.config(state=tk.NORMAL)  # Enable the time travel button
        else:
            messagebox.showinfo("Not Found", f"No commit found with version: {old_version}")

    def find_commit_hash_by_message(self, commit_message):
        modpack_name = self.modpack_var.get()
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
        modpack_name = self.modpack_var.get()
        repo_path = os.path.join(os.getcwd(), modpack_name)
        old_version = self.version_var.get()

        # Get the correct commit hash from the version_hash_label
        commit_hash = self.version_hash_label.cget("text")

        try:
            repo = git.Repo(repo_path)
            # Perform the git reset --hard <hash>
            repo.git.reset('--hard', commit_hash)
            messagebox.showinfo("Success", f"Time traveled to version: {old_version}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to time travel: {str(e)}")

############################################################

# Top functions (Play, installed info, refresh)

############################################################

    def play_game(self):
        self.settings = self.load_settings()
        self.game_dir = self.settings.get("game_directory")
        self.profile_name = self.settings.get("profile_name")        

        # Debugging: Print the settings loaded
        print(f"Game Directory: {self.game_dir}")
        print(f"Profile Name: {self.profile_name}")

        # Construct the path to the game executable
        game_executable = os.path.join(self.game_dir, f"{self.profile_name}.exe")

        # Debugging: Print the constructed path to ensure it's correct
        print(f"Game Executable Path: {game_executable}")

        try:
            # Check if the executable exists
            if os.path.exists(game_executable):
                print(f"Launching {game_executable}")
                # Launch the game executable
                subprocess.run([game_executable], check=True)
            else:
                raise FileNotFoundError(f"Game executable not found: {game_executable}")
        except Exception as e:
            # Display an error message if something goes wrong
            messagebox.showerror("Error", f"Failed to launch game: {e}")

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
            "Full(Extreme)": ("Dimserene", "Dimserenes-Modpack"),
            "Fine-tuned": ("Dimserene", "Fine-tuned-Pack"),
            "Vanilla+": ("Dimserene", "Vanilla-Plus-Pack")
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

        install_path = self.settings["mods_directory"]
        mods_path = os.path.join(install_path, 'ModpackUtil')

        current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
        modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')

        current_version = None

        try:
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

            if pack_name:
                self.installed_info_label.config(text=f"Installed pack: {pack_name} ({current_version})")
            else:
                self.installed_info_label.config(text="No modpack installed or ModpackUtil mod removed.")
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while updating installed info: {str(e)}")

############################################################

# Middle functions (Download, install, update, uninstall)

############################################################

    def get_modpack_url(self, modpack_name):
        urls = {
            "Dimserenes-Modpack": "https://github.com/Dimserene/Dimserenes-Modpack.git",
            "Fine-tuned-Pack": "https://github.com/Dimserene/Fine-tuned-Pack.git",
            "Vanilla-Plus-Pack": "https://github.com/Dimserene/Vanilla-Plus-Pack.git"
        }
        return urls.get(modpack_name, "")

    def prompt_for_installation(self):
        modpack_name = self.modpack_var.get()
        modpack_url = self.get_modpack_url(modpack_name)
        if modpack_url:
            self.download_modpack(modpack_url)
        else:
            messagebox.showerror("Error", "Invalid modpack selected.")

    def download_modpack(self, clone_url=None):
        try:
            # Get the clone URL
            if not clone_url:
                modpack_name = self.modpack_var.get()
                clone_url = self.get_modpack_url(modpack_name)

            # Ensure a valid URL is retrieved
            if not clone_url:
                messagebox.showerror("Error", "Modpack URL not found. Please ensure you selected a valid modpack.")
                return

            repo_name = clone_url.split('/')[-1].replace('.git', '')

            # Prompt force download if the repository directory already exists
            if os.path.isdir(repo_name):
                proceed = messagebox.askyesno("Confirm download", f"{repo_name} is already downloaded. Download anyway?")
                try:
                    if proceed:
                        shutil.rmtree(repo_name, onexc=readonly_handler)
                    else:
                        messagebox.showwarning("Download Status", "Aborted.")
                        return
                except Exception as e:
                        messagebox.showerror("Error", f"An error occurred during download: {str(e)}")

            # Attempt to clone the repository
            Repo.clone_from(clone_url, repo_name, multi_options=["--recurse-submodules", "--remote-submodules"])
            messagebox.showinfo("Download Status", f"Successfully downloaded {repo_name}.")

        except GitCommandError as e:
            messagebox.showerror("Error", f"Failed to download modpack: {str(e)}")
            print(f"GitCommandError during download: {e}")

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
            print(f"Unexpected error during download: {e}")

    def install_modpack(self):

        self.settings = self.load_settings()

        modpack_name = self.modpack_var.get()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)
        mods_src = os.path.join(repo_path, 'Mods')
        install_path = self.mods_dir
        mod_list = self.get_mod_list(mods_src)

        try:
            # Check if the repository directory exists
            if not os.path.isdir(repo_path):
                messagebox.showerror("Error", f"Modpack {repo_path} does not exist. Please download first.")
                return

            # Check if the Mods folder exists in the repository
            if not os.path.isdir(mods_src):
                messagebox.showerror("Error", f"Mods folder not found in the repository: {mods_src}. Please force download and try again.")
                return

            # Check if the install path exists and create it if necessary
            if not os.path.exists(install_path):
                os.makedirs(install_path)

            # Remove the existing Mods folder if it exists
            if os.path.isdir(install_path):
                shutil.rmtree(install_path, ignore_errors=True)

            # Pop up mod selection window
            self.popup_mod_selection(mod_list)

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during installation: {str(e)}")

    def get_mod_list(self, mods_src):
        try:
            return [f for f in os.listdir(mods_src) if os.path.isdir(os.path.join(mods_src, f))]
        except FileNotFoundError:
            messagebox.showerror("Error", "Mods folder not found.")
            return []
        
    def popup_mod_selection(self, mod_list):

        # Prevent opening multiple settings popups
        if self.install_popup_open:
            return
        
        # Mark the install popup as open
        self.install_popup_open = True

        # Create a popup window for mod selection
        popup = tk.Toplevel(self.root)
        popup.title("Mod Selection")

        # Make the popup modal and grab focus
        popup.grab_set()
        popup.focus()

        # Create a list of checkboxes for each mod
        mod_vars = []
        mods_per_column = 15  # Number of mods per column
        num_columns = (len(mod_list) + mods_per_column - 1) // mods_per_column  # Calculate number of columns needed

        # Instruction label
        label = tk.Label(popup, text="Select the mods you DO NOT want to install:")
        label.grid(row=0, column=0, columnspan=num_columns, pady=10)

        # List of locked mods that cannot be deselected
        locked_mods = ["ModpackUtil", "Steamodded"]

        for index, mod in enumerate(mod_list):
            var = tk.BooleanVar(value=mod in self.excluded_mods)
            mod_vars.append((mod, var))

            # Calculate row and column position
            row = (index % mods_per_column) + 1  # Row position
            column = index // mods_per_column  # Column position

            # Check if the mod is locked and disable its checkbox if it is
            if mod in locked_mods:
                checkbutton = tk.Checkbutton(popup, text=mod, variable=var, state="disabled")
                var.set(False)  # Ensure the locked mods are always selected (not excluded)
            else:
                checkbutton = tk.Checkbutton(popup, text=mod, variable=var)
            
            checkbutton.grid(row=row, column=column, sticky="w")

        # Function to clear all selections
        def clear_all():
            for mod, var in mod_vars:
                if mod not in locked_mods:  # Only clear mods that are not locked
                    var.set(False)

        # Function to reverse the selections
        def reverse_select():
            for mod, var in mod_vars:
                if mod not in locked_mods:  # Only reverse mods that are not locked
                    var.set(not var.get())

        # Add "Clear All" button
        clear_button = tk.Button(popup, text="Clear All", command=clear_all)
        clear_button.grid(row=mods_per_column + 1, column=0, pady=10)

        # Add "Reverse Select" button
        reverse_button = tk.Button(popup, text="Reverse Select", command=reverse_select)
        reverse_button.grid(row=mods_per_column + 1, column=1, pady=10)

        # Save and install button (place below the checkboxes)
        save_button = tk.Button(popup, text="Save & Install", command=lambda: self.save_and_install(mod_vars, popup))
        save_button.grid(row=mods_per_column + 1, column=2, pady=10)

        # Close event handler to reset the flag when the window is closed
        def settings_on_close():
            self.install_popup_open = False
            popup.destroy()

        # When the popup is closed, reset the flag
        popup.protocol("WM_DELETE_WINDOW", settings_on_close)


    def save_preferences(self, mod_vars):
        # 3. Let the user pick mods they DON'T want to install
        self.excluded_mods = [mod for mod, var in mod_vars if var.get()]

        # Save user preferences to a file
        with open(INSTALL_FILE, "w") as f:
            for mod in self.excluded_mods:
                f.write(mod + "\n")

        messagebox.showinfo("Preferences Saved", f"Excluded mods saved: {self.excluded_mods}")
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
        modpack_name = self.modpack_var.get()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)
        mods_src = os.path.join(repo_path, 'Mods')
        install_path = self.mods_dir
        
        # Ensure install directory exists
        if not os.path.exists(self.mods_dir):
            os.makedirs(self.mods_dir)

        # 5. Install mods that are not in the excluded_mods list
        for mod in self.get_mod_list(mods_src):
            if mod not in self.excluded_mods:
                source_mod_path = os.path.join(mods_src, mod)
                destination_mod_path = os.path.join(install_path, mod)
                
                # Copy the mod folder to the installation directory
                try:
                    if os.path.exists(destination_mod_path):
                        shutil.rmtree(destination_mod_path)  # Remove old version of the mod if it exists
                    shutil.copytree(source_mod_path, destination_mod_path)
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to install mod: {mod}. Error: {e}")
                    return
                
        popup.destroy()        
        messagebox.showinfo("Install Status", "Successfully installed modpack.")
        
    def save_and_install(self, mod_vars, popup):
        self.save_preferences(mod_vars)
        self.excluded_mods = self.read_preferences()
        self.install_mods(popup)


    def update_modpack(self):

        self.settings = self.load_settings()

        modpack_name = self.modpack_var.get()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)
        mods_src = os.path.join(repo_path, 'Mods')
        install_path = self.mods_dir

        # Confirm the uninstallation
        if messagebox.askyesno("Confirm Update", "This will perform a clean reclone which will wipe both downloaded and currently installed modpacks. Proceed?"):
            try:
                # Check modpack downloaded
                if not os.path.isdir(repo_path):
                    messagebox.showerror("Error", "Modpack not found. Please download modpack first.")
                    return

                # Delete if the repository directory already exists
                if os.path.isdir(repo_path):
                    shutil.rmtree(repo_path, onexc=readonly_handler)

                # Get the clone URL
                if not clone_url:
                    modpack_name = self.modpack_var.get()
                    clone_url = self.get_modpack_url(modpack_name)

                # Ensure a valid URL is retrieved
                if not clone_url:
                    messagebox.showerror("Error", "Modpack URL not found. Please ensure you selected a valid modpack.")
                    return

                # Attempt to clone the repository
                Repo.clone_from(clone_url, repo_name, multi_options=["--recurse-submodules", "--remote-submodules"])

                if os.path.exists(install_path):
                    shutil.rmtree(install_path, ignore_errors=True)

                shutil.copytree(mods_src, install_path)
                messagebox.showinfo("Update Status", "Successfully updated modpack.")

            except GitCommandError as e:
                messagebox.showerror("Error", f"Failed to update modpack: {str(e)}, Please try again.")
                print(f"GitCommandError during download: {e}")

            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}, Please try again.")
                print(f"Unexpected error during download: {e}")
        
    def uninstall_modpack(self):

        self.settings = self.load_settings()

        install_path = self.mods_dir

        # Confirm the uninstallation
        if messagebox.askyesno("Confirm Uninstallation", "Are you sure you want to uninstall the modpack? This action cannot be undone."):
            try:
                if os.path.exists(install_path):
                    shutil.rmtree(install_path)
                    messagebox.showinfo("Uninstall Status", "Modpack uninstalled successfully.")
                else:
                    messagebox.showwarning("Uninstall Status", "No modpack found to uninstall.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during uninstallation: {str(e)}")

############################################################

# Bottom functions (Check versions, lovely, browser links)

############################################################

    def check_versions(self):
        try:
            install_path = self.mods_dir
            mods_path = os.path.join(install_path, 'ModpackUtil')

            current_version_file = os.path.join(mods_path, 'CurrentVersion.txt')
            modpack_util_file = os.path.join(mods_path, 'ModpackUtil.lua')

            current_version = None
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

            commit_messages = self.fetch_commit_messages()

            version_info = ""
            update_message = ""

            for repo_name, commit_message in commit_messages.items():
                version_info += f"{repo_name}: {commit_message}\n"

                if pack_name == repo_name:
                    if current_version and commit_message != current_version:
                        update_message = "Update available!"
            
            if pack_name:
                version_info += f"\nInstalled modpack: {pack_name}\nInstalled version: {current_version}"
            else:
                version_info += "\nNo modpack installed or ModpackUtil mod removed."

            if update_message:
                messagebox.showinfo("Version Information", f"{version_info}\n\n{update_message}")
            else:
                messagebox.showinfo("Version Information", version_info)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while checking versions: {str(e)}")

    def install_lovely_injector(self):
        # Prompt user to confirm the installation
        proceed = messagebox.askyesno("Install Lovely Injector",
                                      "This installation requires disabling antivirus software temporarily"
                                      "and whitelisting the Balatro game directory. Proceed?")
        if not proceed:
            messagebox.showinfo("Installation Aborted", "Lovely Injector installation was aborted by the user.")
            return

        game_path = os.path.join(self.game_dir, "balatro.exe")

        # Verify existence of balatro.exe or prompt user to select the directory
        if not os.path.exists(game_path):
            messagebox.showwarning("Warning", "Game executive not found in default directory. Please specify it in settings.")
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
            messagebox.showinfo("Install Status", "Lovely Injector installed successfully.")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to download Lovely Injector: {e}")
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
        except zipfile.BadZipFile as e:
            messagebox.showerror("Error", f"Failed to unzip the downloaded file: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during installation: {str(e)}")

    def open_discord(self, event=None):
        webbrowser.open("https://discord.com/channels/1116389027176787968/1255696773599592458")

    def open_mod_list(self, event=None): 
        webbrowser.open("https://docs.google.com/spreadsheets/d/1L2wPG5mNI-ZBSW_ta__L9EcfAw-arKrXXVD-43eU4og")

############################################################

# Misc functions

############################################################

def readonly_handler(func, path, execinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def center_window(window, width, height):

    window.update_idletasks()  # Ensures window dimensions are calculated

    # Get the screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Calculate the position for the window to be centered
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    # Set the geometry of the window
    window.geometry(f'{width}x{height}+{x}+{y}')
    
if __name__ == "__main__":
    root = tk.Tk()
    app = ModpackManagerApp(root)

    # Update the window size to ensure widgets are packed before centering
    root.update_idletasks()

    # Get the screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Get the window width and height
    window_width = root.winfo_width()
    window_height = root.winfo_height()

    # Calculate the position x, y coordinates
    position_x = (screen_width // 2) - (window_width // 2)
    position_y = (screen_height // 2) - (window_height // 2)

    # Set the position of the window to the calculated coordinates
    root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    root.mainloop()