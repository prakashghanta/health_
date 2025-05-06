import streamlit as st
import requests
import zipfile
import io
import os
import sys
import logging
import re
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LifeCheck.Launcher")

# Config - Google Drive file ID for Archive.zip
FILE_ID = "REPLACE_WITH_YOUR_FILE_ID"  # Replace with the actual file ID
APP_FOLDER = "lifecheck"
MAIN_FILE = "main.py"

def download_file_from_google_drive(file_id, destination):
    """
    Download a file from Google Drive, handling large files correctly
    """
    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768
        with open(destination, "wb") as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()

    response = session.get(URL, params={'id': file_id}, stream=True)
    token = get_confirm_token(response)

    if token:
        st.info("Handling large file download...")
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)
    return os.path.exists(destination)

def extract_zip(zip_path, extract_to="./"):
    """Extract zip file to the specified directory"""
    try:
        st.info("Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_to)
        return True
    except Exception as e:
        st.error(f"Error extracting: {e}")
        return False

def main():
    st.set_page_config(
        page_title="LifeCheck - Health Assistant",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("LifeCheck - Health Assistant")
    
    # Check if the app folder exists
    if not os.path.exists(APP_FOLDER):
        st.warning("LifeCheck files not found. Downloading...")
        
        # Create temporary zip file path
        temp_zip = "temp_archive.zip"
        
        # Download the zip file from Google Drive
        success = download_file_from_google_drive(FILE_ID, temp_zip)
        
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
        st.error(f"Error running LifeCheck: {e}")
        logger.error(f"Error running app: {e}")

if __name__ == "__main__":
    main()