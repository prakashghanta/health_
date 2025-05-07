import streamlit as st
import os
import sys
import logging
import zipfile
import subprocess
import shutil
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LifeCheck.Launcher")

# Config - Google Drive file ID and URL
FILE_ID = "1-enPexyyciKarb3Xb_6fo53lQ3_L8skm"
FILE_URL = f"https://drive.google.com/uc?id={FILE_ID}"
APP_FOLDER = "lifecheck"
MAIN_FILE = "main.py"

def install_gdown():
    """Install gdown package if not already installed"""
    try:
        import gdown
        st.success("gdown already installed")
        return True
    except ImportError:
        st.info("Installing gdown package...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
            st.success("gdown installed successfully")
            return True
        except Exception as e:
            st.error(f"Failed to install gdown: {e}")
            return False

def download_with_gdown(url, output_path):
    """Download file from Google Drive using gdown"""
    try:
        import gdown
        st.info(f"Downloading from Google Drive: {url}")
        st.info(f"This may take a while for large files...")
        
        # Try downloading with gdown
        output = gdown.download(url, output_path, quiet=False)
        
        if output:
            file_size = os.path.getsize(output_path)
            st.info(f"Downloaded file size: {file_size} bytes")
            return True
        else:
            st.error("Download failed")
            return False
    except Exception as e:
        st.error(f"Error downloading with gdown: {e}")
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
    # We don't set the page config here anymore - we'll wait to see if we need to
    
    # Check if the app folder exists
    if not os.path.exists(APP_FOLDER) or not os.path.exists(os.path.join(APP_FOLDER, MAIN_FILE)):
        # Only set page config if we're showing the download page
        st.set_page_config(**PAGE_CONFIG)
        
        st.title("LifeCheck - Health Assistant")
        st.warning("LifeCheck files not found. Downloading...")
        
        # Install gdown if needed
        if not install_gdown():
            st.error("Failed to install required dependencies.")
            return
        
        # Create temporary zip file path
        temp_zip = "archive.zip"
        
        # Remove existing file if it exists
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        
        # Download the zip file from Google Drive
        success = download_with_gdown(FILE_URL, temp_zip)
        
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
            
        st.success("LifeCheck files downloaded successfully!")
        st.info("Starting LifeCheck app...")
        st.rerun()
    
    # Now that we have the files, import and run the main app
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

if __name__ == "__main__":
    main()
