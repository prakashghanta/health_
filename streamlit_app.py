import streamlit as st
import os
import sys
import logging
import zipfile
import requests
import subprocess
import shutil
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LifeCheck.Launcher")

# Config - GitHub Release URL or Google Drive file ID
# If using GitHub Releases:
GITHUB_RELEASE_URL = "https://github.com/prakashghanta/health_/releases/download/V1.0/Archive.zip"
# If using Google Drive:
FILE_ID = "1nmgbgX8unUmGaDzphUSWCw_kLoQHk68P"
USE_GITHUB = False  # Set to True to use GitHub Releases, False to use Google Drive

APP_FOLDER = "lifecheck"
MAIN_FILE = "main.py"

# List of required packages
REQUIRED_PACKAGES = [
    "matplotlib",
    "numpy",
    "pandas",
    # Add any other packages that might be needed by LifeCheck
]

def install_dependencies():
    """Install required dependencies"""
    try:
        st.info("Checking and installing required dependencies...")
        
        for package in REQUIRED_PACKAGES:
            st.info(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            st.success(f"Successfully installed {package}")
        
        return True
    except Exception as e:
        st.error(f"Failed to install dependencies: {e}")
        return False

def download_from_github(url, output_path):
    """Download file directly from GitHub Releases"""
    try:
        st.info(f"Downloading from GitHub: {url}")
        
        # Use a session for better connection handling
        session = requests.Session()
        
        # Make sure we get a proper user agent to avoid being blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Get the file with streaming enabled
        response = session.get(url, headers=headers, stream=True)
        
        # Check if request was successful
        if response.status_code != 200:
            st.error(f"Download failed with status code: {response.status_code}")
            return False
            
        # Setup progress display
        total_size = int(response.headers.get('content-length', 0))
        progress_bar = None
        
        if total_size > 0:
            progress_bar = st.progress(0)
            st.info(f"File size: {total_size / (1024*1024):.2f} MB")
        
        # Download the file with progress updates
        downloaded = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_bar and total_size > 0:
                        progress_bar.progress(min(downloaded / total_size, 1.0))
        
        file_size = os.path.getsize(output_path)
        st.info(f"Downloaded file size: {file_size} bytes")
        
        # Verify if it's a valid ZIP file
        if file_size > 0:
            with open(output_path, 'rb') as f:
                header = f.read(4)
                if not header.startswith(b'PK\x03\x04'):
                    st.error("Downloaded file is not a valid ZIP archive")
                    with open(output_path, 'r', errors='ignore') as f2:
                        content_preview = f2.read(200)
                    st.error(f"File content preview: {content_preview}")
                    return False
            return True
        else:
            st.error("Downloaded file is empty")
            return False
    except Exception as e:
        st.error(f"Error downloading: {e}")
        return False

def extract_zip(zip_path, extract_to="./"):
    """Extract zip file to the specified directory"""
    try:
        if not os.path.exists(zip_path):
            st.error(f"Zip file does not exist: {zip_path}")
            return False
            
        file_size = os.path.getsize(zip_path)
        st.info(f"Zip file size: {file_size} bytes")
        
        if file_size == 0:
            st.error("Zip file is empty (0 bytes)")
            return False
        
        st.info("Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_to)
        st.success("Extraction complete")
        
        # Check if extraction created the expected app folder
        if os.path.exists(APP_FOLDER):
            num_files = len([f for f in os.listdir(APP_FOLDER) if os.path.isfile(os.path.join(APP_FOLDER, f))])
            st.info(f"Extracted {num_files} files in {APP_FOLDER} directory")
            return True
        else:
            # If the zip contains a folder with all contents, try to handle that
            extracted_contents = os.listdir(".")
            for item in extracted_contents:
                if os.path.isdir(item) and item != APP_FOLDER:
                    # Check if this directory contains the expected files
                    if os.path.exists(os.path.join(item, MAIN_FILE)):
                        st.info(f"Found main.py in {item} directory, renaming to {APP_FOLDER}")
                        # If APP_FOLDER already exists as empty dir, remove it
                        if os.path.exists(APP_FOLDER) and not os.listdir(APP_FOLDER):
                            os.rmdir(APP_FOLDER)
                        # Rename the directory to the expected APP_FOLDER
                        os.rename(item, APP_FOLDER)
                        return True
            
            st.error(f"Extraction did not create the expected {APP_FOLDER} directory")
            return False
            
    except zipfile.BadZipFile as e:
        st.error(f"Bad zip file: {e}")
        return False
    except Exception as e:
        st.error(f"Error extracting: {e}")
        return False

# Define page config here - will be used only if files don't exist yet
PAGE_CONFIG = {
    "page_title": "LifeCheck - Health Assistant",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

def main():
    # Check if the app folder exists
    if not os.path.exists(APP_FOLDER) or not os.path.exists(os.path.join(APP_FOLDER, MAIN_FILE)):
        # Only set page config if we're showing the download page
        st.set_page_config(**PAGE_CONFIG)
        
        st.title("LifeCheck - Health Assistant")
        st.warning("LifeCheck files not found.")
        
        # Check if archive.zip is already present (manually downloaded)
        temp_zip = "archive.zip"
        if os.path.exists(temp_zip):
            st.info("Found existing archive.zip file. Extracting...")
            # Extract the zip file
            success = extract_zip(temp_zip)
            
            if not success:
                st.error("Failed to extract the zip file. It might be corrupted.")
                return
                
            st.success("LifeCheck files extracted successfully!")
            st.info("Starting LifeCheck app...")
            st.rerun()
        else:
            st.info("Please download the archive.zip file and place it in this directory.")
            st.info("Alternatively, click the button below to attempt downloading it automatically.")
            
            if st.button("Download and Install LifeCheck"):
                # Create temporary zip file path
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
                
                success = False
                
                # Download the zip file
                if USE_GITHUB:
                    success = download_from_github(GITHUB_RELEASE_URL, temp_zip)
                else:
                    st.error("Auto-download from Google Drive is not reliable. Please download the file manually.")
                    st.info(f"Download URL: https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing")
                    return
                
                if not success:
                    st.error("Failed to download the zip file.")
                    return
                    
                # Extract the zip file
                success = extract_zip(temp_zip)
                
                # Clean up the temp zip file
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
                    
                if not success:
                    st.error("Failed to set up LifeCheck. Please try again.")
                    return
                    
                st.success("LifeCheck files downloaded and extracted successfully!")
                st.info("Starting LifeCheck app...")
                st.rerun()
                
            return
    
    # Install required dependencies before running the app
    if not install_dependencies():
        st.error("Failed to install required dependencies. Cannot run LifeCheck.")
        return
    
    # Now that we have the files and dependencies, import and run the main app
    try:
        # Add the lifecheck directory to the Python path
        if APP_FOLDER not in sys.path:
            sys.path.insert(0, APP_FOLDER)
        
        # Import the main module
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", os.path.join(APP_FOLDER, MAIN_FILE))
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        # Run the main function
        main_module.main()
    except Exception as e:
        # If we got an error, we need to set the page config for our error page
        if "set_page_config" in str(e):
            st.warning("LifeCheck is running! Please refresh the page.")
            st.stop()
        else:
            # For other errors, show an error page
            st.set_page_config(**PAGE_CONFIG)
            st.title("LifeCheck - Health Assistant")
            st.error(f"Error running LifeCheck: {e}")
            logger.error(f"Error running app: {e}")
            
            # Suggest possible fixes
            if "No module named" in str(e):
                missing_module = str(e).split("No module named ")[1].strip("'")
                st.info(f"The error is due to a missing Python module: {missing_module}")
                st.info(f"Try installing it manually using: pip install {missing_module}")
                
                if st.button(f"Install {missing_module} now"):
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", missing_module])
                        st.success(f"Successfully installed {missing_module}")
                        st.info("Restarting application...")
                        st.rerun()
                    except Exception as install_error:
                        st.error(f"Failed to install {missing_module}: {install_error}")

if __name__ == "__main__":
    main()
