import tkinter as tk
from tkinter import simpledialog, ttk, messagebox
import os
import platform
import shutil
import requests
from git import Repo, GitCommandError

class ModpackManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dimserene's Modpack Manager")

        self.create_widgets()
        self.update_installed_info()  # Initial update

    def create_widgets(self):
        # Title label
        self.title_label = tk.Label(self.root, text="Dimserene's Modpack Manager", font=('Helvetica', 16))
        self.title_label.pack(pady=10)

        # Installed modpack info
        self.installed_info_label = tk.Label(self.root, text="", font=('Helvetica', 12))
        self.installed_info_label.pack(pady=5)

        # Refresh button
        self.refresh_button = tk.Button(self.root, text="Refresh", command=self.update_installed_info)
        self.refresh_button.pack(pady=5)

        # Modpack selection dropdown
        self.modpack_label = tk.Label(self.root, text="Select Modpack:")
        self.modpack_label.pack(pady=5)

        self.modpack_var = tk.StringVar()
        self.modpack_dropdown = ttk.Combobox(self.root, textvariable=self.modpack_var)
        self.modpack_dropdown['values'] = [
            "Dimserenes-Modpack",
            "Fine-tuned-Pack",
            "Vanilla-Plus-Pack"
        ]
        self.modpack_dropdown.pack(pady=5)
        self.modpack_dropdown.current(0)

        # Create buttons
        self.check_versions_button = tk.Button(self.root, text="Check Versions", command=self.check_versions)
        self.check_versions_button.pack(pady=5)

        self.download_button = tk.Button(self.root, text="Download", command=self.download_modpack)
        self.download_button.pack(pady=5)

        self.install_button = tk.Button(self.root, text="Install (Copy)", command=self.install_modpack)
        self.install_button.pack(pady=5)

        self.update_button = tk.Button(self.root, text="Update", command=self.update_modpack)
        self.update_button.pack(pady=5)

        self.open_mods_folder_button = tk.Button(self.root, text="Open Mods Folder", command=self.open_mods_folder)
        self.open_mods_folder_button.pack(pady=5)

    def get_latest_commit_message(self, repo_owner, repo_name):
        try:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
            headers = {
                "Authorization": "token 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"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
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
            "Dimserenes-Modpack": ("Dimserene", "Dimserenes-Modpack"),
            "Fine-tuned-Pack": ("Dimserene", "Fine-tuned-Pack"),
            "Vanilla-Plus-Pack": ("Dimserene", "Vanilla-Plus-Pack")
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
        if os.path.isdir(repo_name):
            mods_src = os.path.join(repo_name, 'Mods')
            install_path = self.get_install_path()
            if os.path.exists(mods_src):
                if os.path.exists(install_path):
                    shutil.rmtree(install_path, ignore_errors=True)
                shutil.copytree(mods_src, install_path)
                messagebox.showinfo("Install Status", "Modpack installed successfully.")
            else:
                messagebox.showerror("Error", "Mods folder not found in the downloaded repository.")
        else:
            messagebox.showerror("Error", "Downloaded repository not found.")

    def prompt_for_update(self, current_version, remote_version, repo_name):
        choice = simpledialog.askstring("Update Available", f"Modpack update available.\nDo you want to update the current modpack? (y/n):")
        if choice and choice.lower() == 'y':
            self.update_modpack()
        elif choice and choice.lower() == 'n':
            messagebox.showinfo("Update Status", "Update process aborted.")
        else:
            messagebox.showinfo("Update Status", "Invalid choice. Update process aborted.")

    def update_modpack(self):
        modpack_name = self.modpack_var.get()
        clone_url = self.get_modpack_url(modpack_name)
        repo_name = clone_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(os.getcwd(), repo_name)

        # Get local version and fetch remote version
        current_version, pack_name = self.get_version_info()
        commit_messages = self.fetch_commit_messages()
        remote_version = commit_messages.get(pack_name, "Unknown")

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

    def check_versions(self):
        try:
            # Get local version and pack name
            current_version, local_pack_name = self.get_version_info()

            # Fetch remote versions for all modpacks
            commit_messages = self.fetch_commit_messages()

            # Prepare version information display
            version_info = ""
            update_message = ""

            for pack_name, commit_message in commit_messages.items():
                version_info += f"{pack_name}: {commit_message}\n"

                # Compare versions for the local pack
                if local_pack_name == pack_name:
                    if current_version and commit_message != current_version:
                        update_message = "Update available!"
            
            if local_pack_name:
                version_info += f"\nInstalled modpack: {local_pack_name}\nInstalled version: {current_version}"
            else:
                version_info += "\nNo modpack installed or ModpackUtil mod removed."

            # Display version information
            if update_message:
                messagebox.showinfo("Version Information", f"{version_info}\n\n{update_message}")
            else:
                messagebox.showinfo("Version Information", version_info)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while checking versions: {str(e)}")

    def open_mods_folder(self):
        install_path = self.get_install_path()
        
        # Check if the Mods folder exists
        if not os.path.exists(install_path):
            # Create the Mods folder if it does not exist
            try:
                os.makedirs(install_path)
                messagebox.showinfo("Folder Created", "Mods folder was created successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create Mods folder: {str(e)}")
                return

        # Open the Mods folder
        try:
            if platform.system() == "Windows":
                os.startfile(install_path)
            elif platform.system() == "Linux":
                os.system(f'xdg-open "{install_path}"')
            else:
                messagebox.showerror("Error", "Unsupported operating system.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Mods folder: {str(e)}")


    def get_install_path(self):
        if platform.system() == "Windows":
            return os.path.expandvars(r'%AppData%\Balatro\Mods')
        else:
            return os.path.expanduser('/home/$USER/.steam/steam/steamapps/compatdata/2379780/pfx/drive_c/users/steamuser/AppData/Roaming/Balatro/Mods/')

    def update_installed_info(self):
        current_version, pack_name = self.get_version_info()
        if pack_name:
            self.installed_info_label.config(text=f"Installed pack: {pack_name} ({current_version})")
        else:
            self.installed_info_label.config(text="No modpack installed or ModpackUtil mod removed.")

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)
    window.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

if __name__ == "__main__":
    root = tk.Tk()
    app = ModpackManagerApp(root)
    # Set the size of the window and center it
    window_width = 400
    window_height = 400
    center_window(root, window_width, window_height)
    root.mainloop()
