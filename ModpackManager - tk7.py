import tkinter as tk
from tkinter import simpledialog, ttk, messagebox, filedialog
from PIL import Image, ImageTk
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

        self.create_widgets()
        self.update_installed_info()  # Initial update

    def create_widgets(self):
        
        root.grid_columnconfigure((0,1), weight=1, uniform="column")
        
        # Title label
        self.title_label = tk.Label(self.root, text="Dimserene's Modpack Manager", font=('Helvetica', 16))
        self.title_label.grid(pady=10, padx=100, row=0, column=0, columnspan=2)

        # PLAY button
        self.play_button = tk.Button(self.root, text="PLAY", command=self.play_game, font=('Helvetica', 30), height=0, width=10, background='#0087eb')
        self.play_button.grid(padx=5, pady=5, row=1, column=0, columnspan=2)

        # Installed modpack info
        self.installed_info_label = tk.Label(self.root, text="", font=('Helvetica', 12))
        self.installed_info_label.grid(padx=5, pady=5, ipady=5, row=2, column=0, columnspan=2)

        # Refresh button
        self.refresh_button = tk.Button(self.root, text="Refresh", command=self.update_installed_info)
        self.refresh_button.grid(padx=5, pady=5, row=3, column=0, columnspan=2)

        # Modpack selection dropdown
        self.modpack_label = tk.Label(self.root, text="Select Modpack:")
        self.modpack_label.grid(padx=5, pady=5, ipady=5, row=4, column=0, columnspan=1, sticky="E")

        self.modpack_var = tk.StringVar()
        self.modpack_dropdown = ttk.Combobox(self.root, textvariable=self.modpack_var)
        self.modpack_dropdown['values'] = [
            "Dimserenes-Modpack",
            "Fine-tuned-Pack",
            "Vanilla-Plus-Pack"
        ]
        self.modpack_dropdown.grid(padx=5, pady=5, ipady=5, row=4, column=1, columnspan=1, sticky="W")
        self.modpack_dropdown.current(0)

        # Create buttons
        self.download_button = tk.Button(self.root, text="Download", command=self.download_modpack, font=('Helvetica', 16))
        self.download_button.grid(padx=10, pady=5, ipady=5, row=5, column=0, columnspan=1, sticky="WE")

        self.install_button = tk.Button(self.root, text="Install (Copy)", command=self.install_modpack, font=('Helvetica', 16))
        self.install_button.grid(padx=10, pady=5, ipady=5, row=5, column=1, columnspan=1, sticky="WE")

        self.update_button = tk.Button(self.root, text="Update", command=self.update_modpack, font=('Helvetica', 16))
        self.update_button.grid(padx=10, pady=5, ipady=5, row=6, column=0, columnspan=2, sticky="WE")

        self.check_versions_button = tk.Button(self.root, text="Check Versions", command=self.check_versions)
        self.check_versions_button.grid(padx=10, pady=5, ipady=5, row=7, column=0, columnspan=1, sticky="WE")

        self.open_install_directory_button = tk.Button(self.root, text="Open Install Directory", command=self.open_install_directory)
        self.open_install_directory_button.grid(padx=10, pady=5, ipady=5, row=7, column=1, columnspan=1, sticky="WE")

        self.install_lovely_button = tk.Button(self.root, text="Install lovely", command=self.install_lovely_injector)
        self.install_lovely_button.grid(padx=10, pady=5, ipady=5, row=8, column=0, columnspan=1, sticky="WE")

        # Settings button
        self.settings_button = tk.Button(self.root, text="Settings", command=self.open_settings_popup)
        self.settings_button.grid(padx=10, pady=5, ipady=5, row=8, column=1, columnspan=1, sticky="WE")

    def play_game(self):
        if platform.system() == "Windows":
            game_path = r"C:\Program Files (x86)\Steam\steamapps\common\Balatro\Balatro.exe"
        else:
            game_path = os.path.expanduser("~/.steam/steam/steamapps/common/Balatro/Balatro.exe")

        if not os.path.exists(game_path):
            result = tk.filedialog.askopenfilename(
                title="Select Balatro Executable",
                filetypes=[("Executable Files", "*.exe") if platform.system() == "Windows" else ("Binary Files", "*")]
            )
            if result:
                game_path = result
            else:
                messagebox.showwarning("File Not Found", "No valid executable selected.")
                return

        try:
            if platform.system() == "Windows":
                os.startfile(game_path)
            else:
                subprocess.Popen([game_path])
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch the game: {e}")

    def open_settings_popup(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")

        # Display current path
        current_path_label = tk.Label(settings_window, text="Current Install Path:")
        current_path_label.grid(pady=5)
        self.path_display = tk.Label(settings_window, text=self.get_install_path())
        self.path_display.grid(pady=5)

        # Browse button
        browse_button = tk.Button(settings_window, text="Browse", command=self.browse_for_path)
        browse_button.grid(pady=5)

        # Default button
        default_button = tk.Button(settings_window, text="Default", command=self.reset_to_default_path)
        default_button.grid(pady=5)

        # Save button
        save_button = tk.Button(settings_window, text="Save", command=settings_window.destroy)
        save_button.grid(pady=5)

    def browse_for_path(self):
        new_path = tk.filedialog.askdirectory(title="Select Install Path")
        if new_path:
            self.custom_install_path = new_path
            self.path_display.config(text=new_path)

    def save_settings(self):
        settings_window = self.root.nametowidget('.!toplevel')
        settings_window.destroy()
        self.update_installed_info()  # Update the display after saving settings

    def browse_install_path(self):
        new_path = filedialog.askdirectory(initialdir=self.install_path, title="Select Install Path")
        if new_path:
            self.install_path = new_path
            self.path_display.config(text=self.install_path)

    def reset_to_default_path(self):
        self.custom_install_path = None
        self.path_display.config(text=self.get_install_path())

    def get_install_path(self):
        if self.custom_install_path:
            return self.custom_install_path
        if platform.system() == "Windows":
            return os.path.expandvars(r'%AppData%\Balatro\Mods')
        else:
            return os.path.expanduser('/home/$USER/.steam/steam/steamapps/compatdata/2379780/pfx/drive_c/users/steamuser/AppData/Roaming/Balatro/Mods/')

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
        if platform.system() == "Windows":
            mods_path = os.path.expandvars(r'%AppData%\Balatro\Mods\ModpackUtil')
        else:
            mods_path = os.path.expanduser('/home/$USER/.steam/steam/steamapps/compatdata/2379780/pfx/drive_c/users/steamuser/AppData/Roaming/Balatro/Mods/ModpackUtil/')

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

    def compare_versions(self, local_version, remote_version):
        if local_version == remote_version:
            return "Your modpack is up-to-date."
        else:
            return f"Update available: Remote version is {remote_version}, but your local version is {local_version}."

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
        if not clone_url:
            modpack_name = self.modpack_var.get()
            clone_url = self.get_modpack_url(modpack_name)
        
        if clone_url:
            repo_name = clone_url.split('/')[-1].replace('.git', '')
            
            # Check if the repository directory already exists
            if os.path.isdir(repo_name):
                messagebox.showinfo("Download Status", f"{repo_name} is already downloaded.")
                return
            
            try:
                Repo.clone_from(clone_url, repo_name, multi_options=["--recurse-submodules", "--remote-submodules"])
                messagebox.showinfo("Download Status", f"Downloaded {repo_name} successfully.")
            except GitCommandError as e:
                messagebox.showerror("Error", f"Failed to download modpack: {str(e)}")
                print(f"Error during download: {e}")

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


    def open_install_directory(self):
        install_path = self.get_install_path()
        
        # Check if the directory exists, and create it if it does not
        if not os.path.exists(install_path):
            try:
                os.makedirs(install_path)
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred while creating the directory: {str(e)}")
                return
        
        # Open the directory
        try:
            if platform.system() == "Windows":
                os.startfile(install_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", install_path])
            else:
                subprocess.run(["xdg-open", install_path])
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while opening the install directory: {str(e)}")



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
        
        messagebox.showwarning("Warning", "Please disable antivirus and whitelist Balatro game directory to proceed.")
        
        # Determine the default game directory based on the OS
        if platform.system() == "Windows":
            default_game_directory = r"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro"
        else:
            default_game_directory = os.path.expanduser("~/.steam/steam/steamapps/common/Balatro")

        # Check if balatro.exe exists in the default directory
        balatro_exe_path = os.path.join(default_game_directory, "balatro.exe")

        if not os.path.exists(balatro_exe_path):
            # If not found, prompt the user to select the game directory
            messagebox.showwarning("Game Not Found", "Balatro.exe not found in the default directory. Please select the game directory.")
            selected_directory = filedialog.askdirectory(title="Select Balatro Game Directory")
            
            if not selected_directory:
                messagebox.showerror("No Directory Selected", "No directory was selected. Lovely Injector installation aborted.")
                return
            
            # Save the selected directory for future use
            self.custom_install_path = selected_directory
            game_directory = selected_directory
            balatro_exe_path = os.path.join(game_directory, "balatro.exe")
        else:
            game_directory = default_game_directory
        
        # Verify if balatro.exe exists in the chosen directory
        if not os.path.exists(balatro_exe_path):
            messagebox.showerror("Error", "Balatro.exe not found in the selected directory. Lovely Injector installation aborted.")
            return
        
        # Download the lovely-injector zip file
        url = "https://github.com/ethangreen-dev/lovely-injector/releases/latest/download/lovely-x86_64-pc-windows-msvc.zip"
        zip_file_path = os.path.join(game_directory, "lovely-injector.zip")
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(zip_file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            messagebox.showinfo("Download Status", "Download completed successfully.")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to download Lovely Injector: {e}")
            return
        
        # Extract the version.dll from the zip file
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extract("version.dll", game_directory)
            os.remove(zip_file_path)  # Clean up the zip file after extraction
            messagebox.showinfo("Install Status", "Lovely Injector installed successfully.")
        except zipfile.BadZipFile as e:
            messagebox.showerror("Error", f"Failed to unzip the downloaded file: {e}")
        except IOError as e:
            messagebox.showerror("Error", f"Error during file extraction: {e}")

def open_discord():
    webbrowser.open("https://discord.com/channels/1116389027176787968/1255696773599592458")

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

    discord_link = tk.Label(root, text="discord", fg="blue", cursor="hand2")
    discord_link.grid(padx=5, pady=5, row=10, column=0, columnspan=2)
    discord_link.bind("<Button-1>", lambda e: open_discord())

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