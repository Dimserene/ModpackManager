import tkinter as tk
from tkinter import simpledialog, ttk, messagebox, filedialog
import os
import re
import shutil
import requests
import webbrowser
import zipfile
import stat
from idlelib.tooltip import Hovertip
os.environ["GIT_PYTHON_REFRESH"] = "quiet"
import git
from git import GitCommandError, Repo


class ModpackManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dimserene's Modpack Manager")

        # Initialize custom_install_path as None
        self.custom_install_path = None

        # Declare default directories
        self.game_dir = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro"
        self.mods_dir = os.path.join(os.getenv('APPDATA'), "Balatro", "Mods")
        self.old_version = ""
        self.version_hash = ""

        self.create_widgets()
        self.update_installed_info()  # Initial update

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

        # Create buttons
        self.download_button = tk.Button(self.root, text="Download (Clone)", command=self.download_modpack, font=('Helvetica', 16))
        self.download_button.grid(padx=10, pady=5, ipady=5, row=6, column=0, columnspan=3, sticky="WE")
        Hovertip(self.download_button, "Download (clone) selected modpack to the same directory as manager")

        self.install_button = tk.Button(self.root, text="Install (Copy)", command=self.install_modpack, font=('Helvetica', 16))
        self.install_button.grid(padx=10, pady=5, ipady=5, row=6, column=3, columnspan=3, sticky="WE")
        Hovertip(self.install_button, "Copy (install) Mods content")

        self.update_button = tk.Button(self.root, text="Update (Reclone)", command=self.update_modpack, font=('Helvetica', 16))
        self.update_button.grid(padx=10, pady=5, ipady=5, row=7, column=0, columnspan=3, sticky="WE")
        Hovertip(self.update_button, "Force reclone selected modpack")

        self.uninstall_button = tk.Button(self.root, text="Uninstall (Remove)", command=self.uninstall_modpack, font=('Helvetica', 16))
        self.uninstall_button.grid(padx=10, pady=5, ipady=5, row=7, column=3, columnspan=3, sticky="WE")
        Hovertip(self.uninstall_button, "Delete Mods folder and its contents")

        self.check_versions_button = tk.Button(self.root, text="Check Versions", command=self.check_versions, font=('Helvetica', 12))
        self.check_versions_button.grid(padx=10, pady=5, ipady=5, row=8, column=0, columnspan=2, sticky="WE")
        Hovertip(self.check_versions_button, "Check latest version for all modpacks")

        self.install_lovely_button = tk.Button(self.root, text="Install lovely", command=self.install_lovely_injector, font=('Helvetica', 12))
        self.install_lovely_button.grid(padx=10, pady=5, ipady=5, row=8, column=2, columnspan=2, sticky="WE")
        Hovertip(self.install_lovely_button, "Install/update lovely injector")

        self.revert_button = tk.Button(self.root, text="Time Travel", command=self.open_revert_popup, font=('Helvetica', 12))
        self.revert_button.grid(padx=10, pady=5, ipady=5, row=8, column=4, columnspan=2, sticky="WE")
        Hovertip(self.revert_button, "Revert the modpack to a certain historical version")

        self.mod_list_button = tk.Button(self.root, text="Mod List", command=self.open_mod_list, font=('Helvetica', 12))
        self.mod_list_button.grid(padx=10, pady=5, ipady=5, row=9, column=0, columnspan=2, sticky="WE")
        Hovertip(self.mod_list_button, "Open mod list in web browser")

        self.open_settings_button = tk.Button(self.root, text="Settings", command=self.open_settings_popup, font=('Helvetica', 12))
        self.open_settings_button.grid(padx=10, pady=5, ipady=5, row=9, column=2, columnspan=2, sticky="WE")
        Hovertip(self.open_settings_button, "Settings")

        self.discord_button = tk.Button(self.root, text="Join Discord", command=self.open_discord, font=('Helvetica', 12))
        self.discord_button.grid(padx=10, pady=5, ipady=5, row=9, column=4, columnspan=2, sticky="WE")
        Hovertip(self.discord_button, "Open Discord server in web browser")

        # Modpack Manager Info
        self.info = tk.Label(self.root, text="Build: 2024/08/19, Iteration: 12th, Version: Release 0.6.0", font=('Helvetica', 8))
        self.info.grid(row=10,column=0, columnspan=6, sticky="E")

    def open_settings_popup(self):
        # Create a new popup window
        popup = tk.Toplevel(self.root)
        popup.title("Settings")

        # Default values for reset functionality
        default_game_dir = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro"
        default_mods_dir = os.path.join(os.getenv('APPDATA'), "Balatro", "Mods") # Game Directory

        # Game Directory
        self.game_directory_label = tk.Label(popup, text="Game Directory:")
        self.game_directory_label.grid(column=0, row=0, columnspan= 2, pady=5)
        game_dir_entry = tk.Entry(popup, width=50)
        game_dir_entry.grid(column=0, row=1, columnspan= 2, pady=5, padx=5)
        game_dir_entry.insert(0, self.game_dir)
        
        self.browse_game_directory_button = tk.Button(popup, text="Browse", command=lambda: self.browse_directory(game_dir_entry))
        self.browse_game_directory_button.grid(column=0, row=2, columnspan= 1, padx=20, pady=5, sticky="WE")

        self.open_game_directory_button = tk.Button(popup, text="Open", command=lambda: self.open_directory(self.game_dir))
        self.open_game_directory_button.grid(column=1, row=2, columnspan= 1, padx=20, pady=5, sticky="WE")

        # Mods Directory
        self.mods_directory_button = tk.Label(popup, text="Mods Directory:")
        self.mods_directory_button.grid(column=0, row=3, columnspan= 2, pady=5)
        mods_dir_entry = tk.Entry(popup, width=50)
        mods_dir_entry.grid(column=0, row=4, columnspan= 2, pady=5, padx=5)
        mods_dir_entry.insert(0, self.mods_dir)
        
        self.browse_mods_directory_button = tk.Button(popup, text="Browse", command=lambda: self.browse_directory(mods_dir_entry))
        self.browse_mods_directory_button.grid(column=0, row=5, columnspan= 1, padx=20, pady=5, sticky="WE")

        self.open_mods_directory_button = tk.Button(popup, text="Open", command=lambda: self.open_directory(self.mods_dir))
        self.open_mods_directory_button.grid(column=1, row=5, columnspan= 1, padx=20, pady=5, sticky="WE")

        # Reset to Default Button
        self.default_button = tk.Button(popup, text="Reset to Default", command=lambda: self.reset_to_default(game_dir_entry, mods_dir_entry, default_game_dir, default_mods_dir))
        self.default_button.grid(column=0, row=6, columnspan= 2, pady=5)

        # Save and Cancel Buttons
        self.save_settings_button = tk.Button(popup, text="Save", command=lambda: self.save_settings(popup, game_dir_entry.get(), mods_dir_entry.get()))
        self.save_settings_button.grid(column=0, row=7, padx=20, pady=20, sticky="WE")
        self.cancel_settings_button = tk.Button(popup, text="Cancel", command=popup.destroy)
        self.cancel_settings_button.grid(column=1, row=7, padx=20, pady=20, sticky="WE")

        # Call the center_window function to center the popup dynamically
        self.center_window(popup)

    def browse_directory(self, entry):
        selected_dir = filedialog.askdirectory(initialdir=entry.get())
        if selected_dir:
            entry.delete(0, tk.END)
            entry.insert(0, selected_dir)

    def reset_to_default(self, game_dir_entry, mods_dir_entry, default_game_dir, default_mods_dir):
        game_dir_entry.delete(0, tk.END)
        game_dir_entry.insert(0, default_game_dir)

        mods_dir_entry.delete(0, tk.END)
        mods_dir_entry.insert(0, default_mods_dir)

    def save_settings(self, game_dir, mods_dir):
        self.game_dir = game_dir
        self.mods_dir = mods_dir
        messagebox.showinfo("Settings Saved", "The directories have been updated.")

    def open_directory(self, path):
        
        # Check if the directory exists, and create it if it does not
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred while creating the directory: {str(e)}")
                return
        
        # Open the directory
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while opening the install directory: {str(e)}")
       

    def play_game(self):

        # Declare variables
        steam_url = f"steam://run/2379780"

        try:
            webbrowser.open(steam_url)
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch the game: {e}")
        

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
        mods_path = os.path.expandvars(r'%AppData%\\Balatro\\Mods\\ModpackUtil')
        
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
        
        return current_version, pack_name

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
        modpack_name = self.modpack_var.get()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)
        mods_src = os.path.join(repo_path, 'Mods')
        install_path = self.get_install_path()

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

            # Copy the Mods folder to the install path
            shutil.copytree(mods_src, install_path)
            messagebox.showinfo("Install Status", "Successfully installed modpack.")

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during installation: {str(e)}")

    def update_modpack(self):
        modpack_name = self.modpack_var.get()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)
        mods_src = os.path.join(repo_path, 'Mods')
        install_path = self.get_install_path()

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

    def get_install_path(self):
        if self.mods_dir:
            return self.mods_dir
        else:
            return os.path.expandvars(r'%AppData%\\Balatro\\Mods')
        
    def update_installed_info(self):
        try:
            install_path = self.get_install_path()
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

            if pack_name:
                self.installed_info_label.config(text=f"Installed pack: {pack_name} ({current_version})")
            else:
                self.installed_info_label.config(text="No modpack installed or ModpackUtil mod removed.")
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while updating installed info: {str(e)}")

    def uninstall_modpack(self):
        install_path = self.get_install_path()

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
        
    def check_versions(self):
        try:
            install_path = self.get_install_path()
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
                                      "This installation requires disabling antivirus software temporarily "
                                      "and whitelisting the Balatro game directory. Proceed?")
        if not proceed:
            messagebox.showinfo("Installation Aborted", "Lovely Injector installation was aborted by the user.")
            return

        default_game_directory = r"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro"

        game_directory = default_game_directory
        game_path = os.path.join(game_directory, "balatro.exe")

        # Verify existence of balatro.exe or prompt user to select the directory
        if not os.path.exists(game_path):
            game_directory = filedialog.askdirectory(title="Select Balatro Game Directory", initialdir=os.path.dirname(default_game_directory))
            if not game_directory:
                messagebox.showerror("Installation Aborted", "No game directory was selected.")
                return
            game_path = os.path.join(game_directory, "balatro.exe")
            if not os.path.exists(game_path):
                messagebox.showerror("Error", "Balatro.exe not found in the selected directory.")
                return

        # Download and installation process
        url = "https://github.com/ethangreen-dev/lovely-injector/releases/latest/download/lovely-x86_64-pc-windows-msvc.zip"
        zip_file_path = os.path.join(game_directory, "lovely-injector.zip")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(zip_file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extract("version.dll", game_directory)
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

    def open_revert_popup(self):
        # Create a new popup window
        popup = tk.Toplevel(self.root)
        popup.title("Time Machine")

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

        # Call the center_window function to center the popup dynamically
        self.center_window(popup)

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