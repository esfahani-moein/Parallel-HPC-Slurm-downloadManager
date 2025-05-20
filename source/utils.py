import os
import sys
from urllib.parse import urlparse
from datetime import datetime


def load_config(config_dict_from_file): # Renamed input to avoid confusion
    """
    Load the configuration and create necessary directories.
    Returns the full configuration dictionary, download_dir, and state_dir.
    """
    if 'download_dir' not in config_dict_from_file:
        log_message("Error: 'download_dir' not found in configuration.")
        sys.exit("Configuration error: download_dir missing.")

    download_dir = config_dict_from_file['download_dir']
    os.makedirs(download_dir, exist_ok=True)

    state_dir = os.path.join(download_dir, "download_state")
    os.makedirs(state_dir, exist_ok=True)

    # Return the full config, download_dir, and the derived state_dir
    return config_dict_from_file, download_dir, state_dir

def download_file_handler(links_file_path):
    links = []

    try:
        with open(links_file_path, 'r') as f:
            links = [line.strip() for line in f if line.strip()] # Read lines and remove whitespace/empty lines
        if not links:
            log_message(f"No links found in {links_file_path}. Exiting.")
            exit()
        log_message(f"Loaded {len(links)} URLs from {links_file_path}")
    except FileNotFoundError:
        log_message(f"Error: Links file '{links_file_path}' not found. Exiting.")
        exit(1)
    except Exception as e:
        log_message(f"Error reading links file '{links_file_path}': {e}. Exiting.")
        exit(1)

    # The rest of your script remains the same
    if not links: # This check is now somewhat redundant due to earlier checks but good for safety
        log_message("No links provided. Exiting.")
        exit()
    
    return links


def log_message(message):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()  # Force immediate output


def verify_downloads(download_dir, links):
    """Verify all downloads are complete and consistent"""
    log_message("Verifying downloaded files...")
    
    all_files = []
    for url in links:
        filename = os.path.basename(urlparse(url).path)
        filepath = os.path.join(download_dir, filename)
        all_files.append((filename, filepath, url))
    
    missing = []
    zero_size = []
    suspicious_size = []
    
    for filename, filepath, url in all_files:
        if not os.path.exists(filepath):
            missing.append((filename, url))
        elif os.path.getsize(filepath) == 0:
            zero_size.append((filename, url))
        elif os.path.getsize(filepath) < 1024*1024:  # Less than 1MB may be suspicious for these files
            suspicious_size.append((filename, os.path.getsize(filepath), url))
    
    if not missing and not zero_size and not suspicious_size:
        log_message("✓ All files appear to be downloaded correctly")
        return True
    
    log_message("! Issues found with downloads:")
    if missing:
        log_message("  Missing files:")
        for filename, url in missing:
            log_message(f"    - {filename} ({url})")
    
    if zero_size:
        log_message("  Zero-size files:")
        for filename, url in zero_size:
            log_message(f"    - {filename} ({url})")
    
    if suspicious_size:
        log_message("  Suspiciously small files:")
        for filename, size, url in suspicious_size:
            log_message(f"    - {filename}: {size/1024:.2f} KB ({url})")
    
    return False