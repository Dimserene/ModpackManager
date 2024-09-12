#!/bin/bash

# Default directories
GAME_DIR="$HOME/.steam/steam/steamapps/common/Balatro"
GAME_DIR2="/run/media/deck/STEAM/steamapps/common/Balatro"

MODS_DIR="$HOME/.steam/steam/steamapps/compatdata/2379780/pfx/drive_c/users/steamuser/AppData/Roaming/Balatro"
MODPACK_DOWNLOAD_DIR="$HOME/Downloads/Modpack/$REPO_NAME"

# Lovely Injector
LOVELY_DOWNLOAD_URL="https://github.com/ethangreen-dev/lovely-injector/releases/latest/download/lovely-x86_64-pc-windows-msvc.zip"
LOVELY_ZIP_FILE="$HOME/Downloads/lovely-injector.zip"
LOVELY_TEMP_DIR="$HOME/Downloads/LovelyInjectorTemp"

# Modpack URLs and names
DIMSERENE_MODPACK_URL="https://github.com/Dimserene/Dimserenes-Modpack"
FINE_TUNED_MODPACK_URL="https://github.com/Dimserene/Fine-tuned-Pack"
VANILLA_PLUS_MODPACK_URL="https://github.com/Dimserene/Vanilla-Plus-Pack"
INSANE_MODPACK_URL="https://github.com/Dimserene/Insane-Pack"
CRUEL_MODPACK_URL="https://github.com/Dimserene/Cruel-Pack"

REPO_NAME=""
DIMSERENE_MODPACK_NAME="Full"
FINE_TUNED_MODPACK_NAME="Fine-tuned"
VANILLA_PLUS_MODPACK_NAME="Vanilla+"
INSANE_MODPACK_NAME="Insane"
CRUEL_MODPACK_NAME="Cruel"

# Function to display menu options
display_menu() {
  echo "=== Dimserene's Modpack Manager ==="
  echo "1. Download/Update Modpack"
  echo "2. Install Modpack"
  echo "3. Uninstall Modpack"
  echo "4. Install Lovely Injector"
  echo "5. Exit"
  echo ""
  }

# Function to get the latest commit hash (version) from a GitHub repository
get_latest_version() {
  local repo_url=$1
  git ls-remote "$repo_url" HEAD | awk '{print $1}'
}

# Function to read the local installed version from CurrentVersion.txt
get_installed_version() {
  local version_file="$MODS_DIR/Mods/ModpackUtil/CurrentVersion.txt"
  if [ -f "$version_file" ]; then
    cat "$version_file"
  else
    echo "No CurrentVersion.txt found"
  fi
}

# Function to read the local installed pack name from ModpackUtil.lua
get_installed_pack_name() {
  local modpack_util="$MODS_DIR/Mods/ModpackUtil/ModpackUtil.lua"
  
  if [ -f "$modpack_util" ]; then
    grep "^--- VERSION:" "$modpack_util" | awk '{print $3}'
  else
    echo "No ModpackUtil.lua found"
  fi
}

# Function to match the installed modpack with the remote counterpart and compare versions
check_versions() {
  echo "Checking versions..."
  # Get the installed modpack name and version
  local installed_pack_name
  installed_pack_name=$(get_installed_pack_name)
  local installed_version
  installed_version=$(get_installed_version)

  # Initialize variables for comparison
  local latest_version=""
  local modpack_url=""

  # Match installed modpack with the correct remote repository
  case $installed_pack_name in
    "Dimserene's Modpack")
      modpack_url=$DIMSERENE_MODPACK_URL
      latest_version=$(get_latest_version "$modpack_url")
      ;;
    "Fine-tuned Pack")
      modpack_url=$FINE_TUNED_MODPACK_URL
      latest_version=$(get_latest_version "$modpack_url")
      ;;
    "Vanilla+ Pack")
      modpack_url=$VANILLA_PLUS_MODPACK_URL
      latest_version=$(get_latest_version "$modpack_url")
      ;;
    *)
      echo "Installed modpack not recognized. No update check can be performed."
      return 1
      ;;
  esac

  # Compare versions and notify the user if an update is available
  
    echo "=== Installed Modpack Information ==="
    echo "Installed Pack Name: $installed_pack_name"
    echo "Installed Version: $installed_version"
    echo "Latest Version: $latest_version"
    echo ""
    if [ "$installed_version" != "$latest_version" ]; then
      echo "Update available: $latest_version!"
    else
      echo "You have the latest version of $installed_pack_name."
  fi
}

# Function to download a modpack
download_modpack() {
  choose_modpack
  if [ $? -ne 0 ]; then
    return
  fi
  if [ -d "$MODPACK_DOWNLOAD_DIR/$REPO_NAME" ]; then
    echo "Modpack directory already exists. Removing the old one."
    rm -rf "$MODPACK_DOWNLOAD_DIR/$REPO_NAME"
  fi
  echo "Cloning modpack $REPO_NAME from $MODPACK_URL..."
  git clone --recurse-submodules --remote-submodules "$MODPACK_URL" "$MODPACK_DOWNLOAD_DIR/$REPO_NAME"
  if [ $? -eq 0 ]; then
    echo "$REPO_NAME downloaded successfully to $MODPACK_DOWNLOAD_DIR/$REPO_NAME."
  else
    echo "Failed to download $REPO_NAME."
  fi
}

# Function to install a modpack
install_modpack() {
  choose_modpack
  if [ $? -ne 0 ]; then
    return
  fi
  echo "Installing $REPO_NAME..."
  if [ ! -d "$MODS_DIR" ]; then
    echo "Mods directory does not exist. Creating it..."
    mkdir -p "$MODS_DIR"
  fi
  if [ -d "$MODPACK_DOWNLOAD_DIR/$REPO_NAME/Mods" ]; then
    cp -r "$MODPACK_DOWNLOAD_DIR/$REPO_NAME/Mods/"* "$MODS_DIR"
    if [ $? -eq 0 ]; then
      echo "$REPO_NAME installed successfully to $MODS_DIR."
    else
      echo "Failed to install $REPO_NAME."
    fi
  else
    echo "No Mods directory found in the downloaded modpack. Please check the download."
  fi
}

# Function to uninstall a modpack
uninstall_modpack() {
  echo "Uninstalling modpack..."
  if [ -d "$MODS_DIR/Mods" ]; then
    rm -rf "$MODS_DIR/Mods/*"
    if [ $? -eq 0 ]; then
      echo "Modpack uninstalled successfully."
    else
      echo "Failed to uninstall modpack."
    fi
  else
    echo "Mods directory does not exist. Nothing to uninstall."
  fi
}

# Function to install Lovely Injector mod
install_lovely() {
  echo "Installing Lovely Injector..."
  # Ensure game directory exists
  if [ ! -d "$GAME_DIR" ]; then
    echo "Game directory does not exist: $GAME_DIR"
    $GAME_DIR=$GAME_DIR2
    if [ ! -d "$GAME_DIR" ]; then
      echo "Game directory does not exist: $GAME_DIR"
      # Prompt user input here
      return 1
    fi
  fi

  # Download the Lovely Injector zip file
  echo "Downloading Lovely Injector from $LOVELY_DOWNLOAD_URL..."
  wget -O "$LOVELY_ZIP_FILE" "$LOVELY_DOWNLOAD_URL"
  if [ $? -ne 0 ]; then
    echo "Failed to download Lovely Injector."
    return 1
  fi

  # Create a temporary directory for extraction
  mkdir -p "$LOVELY_TEMP_DIR"

  # Unzip the file to the temporary directory
  echo "Extracting Lovely Injector..."
  unzip -o "$LOVELY_ZIP_FILE" -d "$LOVELY_TEMP_DIR"
  if [ $? -ne 0 ]; then
    echo "Failed to extract Lovely Injector."
    return 1
  fi

  # Move the extracted files to the game directory
  echo "Installing Lovely Injector to the game directory..."
  cp -r "$LOVELY_TEMP_DIR/"* "$GAME_DIR"
  if [ $? -eq 0 ]; then
    echo "Lovely Injector installed successfully to $GAME_DIR."
  else
    echo "Failed to install Lovely Injector."
  fi

  # Clean up temporary files
  rm -rf "$LOVELY_TEMP_DIR" "$LOVELY_ZIP_FILE"
}

# Function to choose modpack, returning both name and URL
choose_modpack() {
  echo "Choose a modpack to download or install:"
  echo "1. Dimserene's Modpack"
  echo "2. Fine-tuned Pack"
  echo "3. Vanilla+ Pack"
  echo ""
  read -r MODPACK_CHOICE
  case $MODPACK_CHOICE in
    1)
      echo "You chose Dimserene's Modpack."
      MODPACK_NAME=$DIMSERENE_MODPACK_NAME
      MODPACK_URL=$DIMSERENE_MODPACK_URL
      REPO_NAME="Dimserenes-Modpack"
      ;;
    2)
      echo "You chose Fine-tuned Pack."
      MODPACK_NAME=$FINE_TUNED_MODPACK_NAME
      MODPACK_URL=$FINE_TUNED_MODPACK_URL
      REPO_NAME="Fine-tuned-Pack"
      ;;
    3)
      echo "You chose Vanilla+ Pack."
      MODPACK_NAME=$VANILLA_PLUS_MODPACK_NAME
      MODPACK_URL=$VANILLA_PLUS_MODPACK_URL
      REPO_NAME="Vanilla-Plus-Pack"
      ;;
    *)
      echo "Invalid choice. Please select a valid modpack."
      return 1
      ;;
  esac
  return 0
}

# Main script loop
while true; do
  display_menu
  echo "Choose an option:"
  read -r OPTION
  case $OPTION in
    1)
      download_modpack
      ;;
    2)
      install_modpack
      ;;
    3)
      uninstall_modpack
      ;;
    4)
      install_lovely
      ;;
    5)
      echo "Exiting..."
      break
      ;;
    *)
      echo "Invalid option. Please try again."
      ;;
  esac
done
