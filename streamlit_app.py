import streamlit as st
import os
import sys
import logging
import zipfile
import shutil
import requests
from pathlib import Path

# Quick setup for logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LifeCheck.Launcher")

# Google Drive stuff
FILE_ID = "1XtvofSB1_ia_RtpXBjuUP-arMD1KClnK"
FILE_URL = f"https://drive.google.com/uc?id={FILE_ID}"
APP_FOLDER = "lifecheck"
MAIN_FILE = "main.py"

def install_gdown():
    """Installs gdown package using pip"""
    try:
        st.info("Installing gdown package...")
        import subprocess
        # Use subprocess to install gdown
        result = subprocess.run([sys.executable, "-m", "pip", "install", "gdown"], 
                               capture_output=True, text=True, check=True)
        st.success("Successfully installed gdown")
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to install gdown: {e}")
        st.error(f"Error details: {e.stderr}")
        return False
    except Exception as e:
        st.error(f"Error installing gdown: {e}")
        return False

def download_from_drive(file_id, destination):
    """Downloads a file from Google Drive using direct API without gdown"""
    try:
        # Use a download URL that doesn't require confirmation for most files
        url = f"https://drive.google.com/uc?id={file_id}&export=download"
        
        st.info(f"Downloading from Google Drive...")
        
        # First request to get cookies and confirm token
        session = requests.Session()
        response = session.get(url, stream=True)
        
        # Check if we got HTML (means we need confirmation for large file)
        if 'text/html' in response.headers.get('Content-Type', ''):
            st.info("Large file detected, handling confirmation...")
            
            # Try to extract the confirm token
            for chunk in response.iter_content(chunk_size=4096):
                if b'confirm=' in chunk:
                    confirm_token = chunk.decode().split('confirm=')[1].split('&')[0]
                    # Construct URL with confirmation token
                    url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm={confirm_token}"
                    break
            
            # Get the actual file with confirmation
            response = session.get(url, stream=True)
        
        # Save the file
        total_size = 0
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)
        
        st.info(f"Downloaded {total_size} bytes")
        return os.path.exists(destination) and os.path.getsize(destination) > 0
        
    except Exception as e:
        st.error(f"Error downloading: {e}")
        return False

def extract_zip(zip_path, extract_to="./"):
    """Unzips everything to the right place"""
    try:
        if not os.path.exists(zip_path):
            st.error(f"Zip file doesn't exist: {zip_path}")
            return False
            
        file_size = os.path.getsize(zip_path)
        st.info(f"Zip file size: {file_size} bytes")
        
        if file_size == 0:
            st.error("Zip file is empty! That's not gonna work...")
            return False
        
        st.info("Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_to)
        st.success("Extraction complete")
        
        # Make sure our app folder is there
        if os.path.exists(APP_FOLDER):
            num_files = len([f for f in os.listdir(APP_FOLDER) if os.path.isfile(os.path.join(APP_FOLDER, f))])
            st.info(f"Extracted {num_files} files in {APP_FOLDER} directory")
            return True
        else:
            # Sometimes the zip has a different folder name than what we expect
            extracted_contents = os.listdir(".")
            for item in extracted_contents:
                if os.path.isdir(item) and item != APP_FOLDER:
                    # See if this folder has what we need
                    if os.path.exists(os.path.join(item, MAIN_FILE)):
                        st.info(f"Found main.py in {item} folder, renaming to {APP_FOLDER}")
                        # Get rid of empty folder if it exists
                        if os.path.exists(APP_FOLDER) and not os.listdir(APP_FOLDER):
                            os.rmdir(APP_FOLDER)
                        # Rename to what we need
                        os.rename(item, APP_FOLDER)
                        return True
            
            st.error(f"Can't find the {APP_FOLDER} folder after extraction")
            return False
            
    except zipfile.BadZipFile as e:
        st.error(f"Bad zip file: {e}")
        return False
    except Exception as e:
        st.error(f"Something went wrong during extraction: {e}")
        return False

# Page settings for when we need to show our own UI
PAGE_CONFIG = {
    "page_title": "LifeCheck - Health Assistant",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

def main():
    # We'll wait to set up the page until we know what we're doing
    
    # Check if our app is ready to go
    if not os.path.exists(APP_FOLDER) or not os.path.exists(os.path.join(APP_FOLDER, MAIN_FILE)):
        # We need to download stuff, so let's set up our page
        st.set_page_config(**PAGE_CONFIG)
        
        st.title("LifeCheck - Health Assistant")
        st.warning("LifeCheck files not found. Downloading...")
        
        # Where we'll save the zip temporarily
        temp_zip = "archive.zip"
        
        # Clean up any old files
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        
        # Get the zip from Google Drive
        success = download_from_drive(FILE_ID, temp_zip)
        
        if not success:
            st.error("Couldn't download the zip file. Check your internet connection?")
            return
            
        # Unzip everything
        success = extract_zip(temp_zip)
        
        # Clean up after ourselves
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
            
        if not success:
            st.error("Something went wrong with the setup. Maybe try again?")
            return
            
        st.success("Got everything downloaded!")
        st.info("Starting LifeCheck app...")
        st.rerun()
    
    # Now we can run the actual app
    try:
        # Add our app folder to Python's path
        if APP_FOLDER not in sys.path:
            sys.path.insert(0, APP_FOLDER)
        
        # Import the main module
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", os.path.join(APP_FOLDER, MAIN_FILE))
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        # Run the app
        main_module.main()
    except Exception as e:
        # Handle that annoying page config error
        if "set_page_config" in str(e):
            st.warning("LifeCheck is running! Just refresh the page.")
            st.stop()
        else:
            # Show an error for other problems
            st.set_page_config(**PAGE_CONFIG)
            st.title("LifeCheck - Health Assistant")
            st.error(f"Error running LifeCheck: {e}")
            logger.error(f"Error running app: {e}")

if __name__ == "__main__":
    main()
