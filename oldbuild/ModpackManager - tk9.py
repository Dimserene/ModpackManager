import tkinter as tk
from tkinter import simpledialog, ttk, messagebox, filedialog
import os
import subprocess
import platform
import shutil
import requests
import webbrowser
import zipfile
os.environ["GIT_PYTHON_REFRESH"] = "quiet"
from git import Repo, GitCommandError


class ModpackManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dimserene's Modpack Manager")

        # Initialize custom_install_path as None
        self.custom_install_path = None

        # Declare default directories
        self.game_dir = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro"
        self.mods_dir = os.path.join(os.getenv('APPDATA'), "Balatro", "Mods")

        self.create_widgets()
        self.update_installed_info()  # Initial update

    def create_widgets(self):
        
        root.grid_columnconfigure((0,1,2,3), weight=1, uniform="column")
        
        # Title label
        self.title_label = tk.Label(self.root, text="☷☷☷☷Dimserene's Modpack Manager☷☷☷☷", font=('Helvetica', 16))
        self.title_label.grid(pady=10, row=0, column=0, columnspan=4)

        # PLAY button
        self.play_button = tk.Button(self.root, text="PLAY", command=self.play_game, font=('Helvetica', 30), height=0, width=10, background='#0087eb')
        self.play_button.grid(padx=5, pady=5, row=1, column=0, columnspan=4)

        # Installed modpack info
        self.installed_info_label = tk.Label(self.root, text="", font=('Helvetica', 12))
        self.installed_info_label.grid(padx=5, pady=5, ipady=5, row=2, column=0, columnspan=4)

        # Refresh button
        self.refresh_button = tk.Button(self.root, text="Refresh", command=self.update_installed_info)
        self.refresh_button.grid(padx=5, pady=5, row=3, column=0, columnspan=4)

        # Modpack selection dropdown
        self.modpack_label = tk.Label(self.root, text="Select Modpack:")
        self.modpack_label.grid(padx=5, ipady=5, row=4, column=0, columnspan=4)

        self.modpack_var = tk.StringVar()
        self.modpack_dropdown = ttk.Combobox(self.root, textvariable=self.modpack_var)
        self.modpack_dropdown['values'] = [
            "Dimserenes-Modpack",
            "Fine-tuned-Pack",
            "Vanilla-Plus-Pack"
        ]
        self.modpack_dropdown.grid(padx=5, ipady=5, row=5, column=0, columnspan=4)
        self.modpack_dropdown.current(0)

        # Create buttons
        self.download_button = tk.Button(self.root, text="Download", command=self.download_modpack, font=('Helvetica', 16))
        self.download_button.grid(padx=10, pady=5, ipady=5, row=6, column=0, columnspan=2, sticky="WE")

        self.install_button = tk.Button(self.root, text="Install (Copy)", command=self.install_modpack, font=('Helvetica', 16))
        self.install_button.grid(padx=10, pady=5, ipady=5, row=6, column=2, columnspan=2, sticky="WE")

        self.update_button = tk.Button(self.root, text="Update", command=self.update_modpack, font=('Helvetica', 16))
        self.update_button.grid(padx=10, pady=5, ipady=5, row=7, column=0, columnspan=2, sticky="WE")

        self.uninstall_button = tk.Button(self.root, text="Uninstall", command=self.uninstall_modpack, font=('Helvetica', 16))
        self.uninstall_button.grid(padx=10, pady=5, ipady=5, row=7, column=2, columnspan=2, sticky="WE")

        self.check_versions_button = tk.Button(self.root, text="Check Versions", command=self.check_versions, font=('Helvetica', 12))
        self.check_versions_button.grid(padx=10, pady=5, ipady=5, row=8, column=0, columnspan=2, sticky="WE")

        self.install_lovely_button = tk.Button(self.root, text="Install lovely", command=self.install_lovely_injector, font=('Helvetica', 12))
        self.install_lovely_button.grid(padx=10, pady=5, ipady=5, row=8, column=2, columnspan=2, sticky="WE")

        self.open_settings_button = tk.Button(self.root, text="Settings", command=self.open_settings_popup, font=('Helvetica', 12))
        self.open_settings_button.grid(padx=10, pady=5, ipady=5, row=9, column=0, columnspan=2, sticky="WE")

        self.mod_list_button = tk.Button(self.root, text="Mod List", command=self.open_mod_list, font=('Helvetica', 12))
        self.mod_list_button.grid(padx=10, pady=5, ipady=5, row=9, column=2, columnspan=1, sticky="WE")

        self.discord_button = tk.Button(self.root, text="Join Discord", command=self.open_discord, font=('Helvetica', 12))
        self.discord_button.grid(padx=10, pady=5, ipady=5, row=9, column=3, columnspan=1, sticky="WE")

        # Modpack Manager Info
        self.info = tk.Label(self.root, text="Build: 2024/08/17, Iteration: 9th, Version: Release 0.5.0", font=('Helvetica', 8))
        self.info.grid(row=10,column=0, columnspan=4, sticky="E")

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
        game_dir_entry.grid(column=0, row=1, columnspan= 2, pady=5)
        game_dir_entry.insert(0, self.game_dir)
        
        self.browse_game_directory_button = tk.Button(popup, text="Browse", command=lambda: self.browse_directory(game_dir_entry))
        self.browse_game_directory_button.grid(column=0, row=2, columnspan= 1, padx=5, pady=5)

        self.open_game_directory_button = tk.Button(popup, text="Open", command=lambda: self.open_directory(self.game_dir))
        self.open_game_directory_button.grid(column=1, row=2, columnspan= 1, padx=5, pady=5)

        # Mods Directory
        self.mods_directory_button = tk.Label(popup, text="Mods Directory:")
        self.mods_directory_button.grid(column=0, row=3, columnspan= 2, pady=5)
        mods_dir_entry = tk.Entry(popup, width=50)
        mods_dir_entry.grid(column=0, row=4, columnspan= 2, pady=5)
        mods_dir_entry.insert(0, self.mods_dir)
        
        self.browse_mods_directory_button = tk.Button(popup, text="Browse", command=lambda: self.browse_directory(mods_dir_entry))
        self.browse_mods_directory_button.grid(column=0, row=5, columnspan= 1, padx=5, pady=5)

        self.open_mods_directory_button = tk.Button(popup, text="Open", command=lambda: self.open_directory(self.mods_dir))
        self.open_mods_directory_button.grid(column=1, row=5, columnspan= 1, padx=5, pady=5)

        # Reset to Default Button
        self.default_button = tk.Button(popup, text="Reset to Default", command=lambda: self.reset_to_default(game_dir_entry, mods_dir_entry, default_game_dir, default_mods_dir))
        self.default_button.grid(column=0, row=6, columnspan= 2, pady=5)

        # Save and Cancel Buttons
        self.save_settings_button = tk.Button(popup, text="Save", command=lambda: self.save_settings(popup, game_dir_entry.get(), mods_dir_entry.get()))
        self.save_settings_button.grid(column=0, row=7, padx=20, pady=20)
        self.cancel_settings_button = tk.Button(popup, text="Cancel", command=popup.destroy)
        self.cancel_settings_button.grid(column=1, row=7, padx=20, pady=20)

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

    def save_settings(self, popup, game_dir, mods_dir):
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

        if self.game_dir:
            game_path = os.path.join(self.game_dir, "Balatro.exe")
        else:
            game_path = r"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro\\Balatro.exe"
            
        if not os.path.exists(game_path):
            result = tk.filedialog.askopenfilename(
                title="Select Balatro Executable",
                filetypes=[("Executable Files", "*.exe")]
            )
            if result:
                game_path = result
            else:
                messagebox.showwarning("File Not Found", "No valid executable selected.")
                return

        try:
            os.startfile(game_path)
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

            # Check if the repository directory already exists
            if os.path.isdir(repo_name):
                messagebox.showinfo("Download Status", f"{repo_name} is already downloaded.")
                return

            # Attempt to clone the repository
            Repo.clone_from(clone_url, repo_name, multi_options=["--recurse-submodules", "--remote-submodules"])
            messagebox.showinfo("Download Status", f"Downloaded {repo_name} successfully.")

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
                messagebox.showerror("Error", f"Repository directory {repo_path} does not exist.")
                return

            # Check if the Mods folder exists in the repository
            if not os.path.isdir(mods_src):
                messagebox.showerror("Error", f"Mods folder not found in the repository: {mods_src}.")
                return

            # Check if the install path exists and create it if necessary
            if not os.path.exists(install_path):
                os.makedirs(install_path)

            # Remove the existing Mods folder if it exists
            if os.path.isdir(install_path):
                shutil.rmtree(install_path, ignore_errors=True)

            # Copy the Mods folder to the install path
            shutil.copytree(mods_src, install_path)
            messagebox.showinfo("Install Status", "Modpack installed successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during installation: {str(e)}")

    def update_modpack(self):
        modpack_name = self.modpack_var.get()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)

        # Get local version (not used in this updated function)
        _, pack_name = self.get_version_info()

        # Check if the repository exists
        if not os.path.isdir(repo_path):
            messagebox.showerror("Error", "Repository not found. Attempting to clone it.")
            self.download_modpack(clone_url)  # Attempt to download the modpack if it's not found
            return

        # Update the modpack
        try:
            repo = Repo(repo_path)

            # Perform git pull and submodule update
            repo.remotes.origin.pull()
            for submodule in repo.submodules:
                submodule.update(init=True, recursive=True)

            # Update the Mods folder
            mods_src = os.path.join(repo_path, 'Mods')
            install_path = self.get_install_path()

            if os.path.exists(install_path):
                shutil.rmtree(install_path, ignore_errors=True)
            shutil.copytree(mods_src, install_path)

            messagebox.showinfo("Update Status", "Modpack updated successfully.")
        except GitCommandError as e:
            messagebox.showerror("Error", f"Failed to update modpack: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

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

def center_window(window, width, height):
    # Get the screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Calculate the position for the window to be centered
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    # Set the geometry of the window
    window.geometry(f'{width}x{height}+{int(x)}+{int(y)}')
    
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