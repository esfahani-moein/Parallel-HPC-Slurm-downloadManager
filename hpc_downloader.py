import os
from datetime import datetime
from configs import config as config_dict
from source.utils import *
from source.downloader import download_files_concurrently

# Force unbuffered output for real-time monitoring in batch jobs
sys.stdout.reconfigure(line_buffering=0)  # For Python 3.7+


if __name__ == "__main__":
    app_config, download_dir, state_dir = load_config(config_dict)

    links_file_path = "download_links.txt"
    
    links = download_file_handler(links_file_path)

    status_file_path = os.path.join(download_dir, "download_status.txt")
    try:
        with open(status_file_path, 'w') as f:
            f.write(f"Download job started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Downloading {len(links)} files\n")
    except IOError as e:
        log_message(f"Error: Could not write to status file {status_file_path}: {e}")
        exit(1) 
    
    log_message("=== Starting download job ===")
    
    # Group parameters into dictionaries
    main_params = {
        "max_workers": app_config.get("max_concurrent_downloads", 3),
    }

    curl_params = {
        "curl_retry_attempts": app_config.get("curl_retry_attempts", 3),
        "curl_retry_delay_seconds": app_config.get("curl_retry_delay_seconds", 5),
        "curl_retry_max_time_seconds": app_config.get("curl_retry_max_time_seconds", 60),
        "curl_connect_timeout_seconds": app_config.get("curl_connect_timeout_seconds", 30),
        "curl_max_time_seconds": app_config.get("curl_max_time_seconds", 1800),
        "curl_speed_time_seconds": app_config.get("curl_speed_time_seconds", 60),
        "curl_speed_limit_bytes_per_sec": app_config.get("curl_speed_limit_bytes_per_sec", 1000),
    }

    downloader_params = {
        "downloader_max_retries": app_config.get("downloader_max_retries", 5),
        "downloader_initial_retry_delay_seconds": app_config.get("downloader_initial_retry_delay_seconds", 10),
    }

    aggressive_retry_specific_params = {
        # For the retry function, these will be used to override/set specific values
        "downloader_max_retries": app_config.get("downloader_aggressive_max_retries", 8),
        "downloader_initial_retry_delay_seconds": app_config.get("downloader_aggressive_initial_retry_delay_seconds", 30),
        # This key 'curl_max_time_seconds' is specifically looked for in retry_failed_downloads
        # to override the one from base_curl_params for aggressive retries.
        "curl_max_time_seconds": app_config.get("downloader_aggressive_timeout_seconds", 3600),
    }

    results = download_files_concurrently(
        links,
        download_dir,
        state_dir,
        main_params=main_params,
        curl_params=curl_params,
        downloader_params=downloader_params,
        aggressive_retry_specific_params=aggressive_retry_specific_params
    )
    
    if not verify_downloads(download_dir, links):
        log_message("!!! Verification failed for some files. Please check logs. !!!")
    
    log_message("=== Download job completed ===")