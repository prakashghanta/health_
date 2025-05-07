import streamlit as st
import os
import sys
import logging
import zipfile
import requests
import re
import shutil
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LifeCheck.Launcher")

# Config - Google Drive file ID and URL
FILE_ID = "1nmgbgX8unUmGaDzphUSWCw_kLoQHk68P"
APP_FOLDER = "lifecheck"
MAIN_FILE = "main.py"

def download_with_direct_confirmation(file_id, output_path):
    """Directly handle Google Drive's virus scan confirmation page"""
    try:
        import requests
        import re
        
        # Initial URL
        url = f"https://drive.google.com/uc?id={file_id}&export=download"
        st.info(f"Downloading from Google Drive with confirmation handling: {url}")
        
        # Use a session to maintain cookies
        session = requests.Session()
        
        # First request - will usually return the confirmation page
        response = session.get(url)
        
        # Check if we got the confirmation page
        if 'Virus scan warning' in response.text:
            st.info("Handling virus scan warning page...")
            
            # Extract the confirmation token using regex
            confirm_token = re.search(r'confirm=([0-9A-Za-z_-]+)', response.text)
            if not confirm_token:
                st.error("Could not find confirmation token in response")
                st.error("Response content preview: " + response.text[:200] + "...")
                return False
                
            token = confirm_token.group(1)
            st.info(f"Found confirmation token: {token}")
            
            # Build the confirmed URL and download with the token
            confirmed_url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm={token}"
            response = session.get(confirmed_url, stream=True)
        else:
            # If we somehow got the file directly without confirmation
            response = session.get(url, stream=True)
        
        # Save the file with progress indicator
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        progress_bar = None
        
        if total_size > 0:
            progress_bar = st.progress(0)
            st.info(f"Total file size: {total_size / (1024*1024):.2f} MB")
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_bar and total_size > 0:
                        progress_bar.progress(min(downloaded / total_size, 1.0))
        
        file_size = os.path.getsize(output_path)
        st.info(f"Downloaded file size: {file_size} bytes")
        
        # Check if it's a valid zip file
        with open(output_path, 'rb') as f:
            header = f.read(4)
            if not header.startswith(b'PK\x03\x04'):
                st.error("Downloaded file is not a valid ZIP archive")
                # Show a preview of what we got instead
                with open(output_path, 'r', errors='ignore') as f2:
                    content_preview = f2.read(200)
                st.error(f"File content preview: {content_preview}")
                return False
                
        return True
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
        st.warning("LifeCheck files not found. Downloading...")
        
        # Create temporary zip file path
        temp_zip = "archive.zip"
        
        # Remove existing file if it exists
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        
        # Download the zip file from Google Drive with advanced handling
        success = download_with_direct_confirmation(FILE_ID, temp_zip)
        
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
