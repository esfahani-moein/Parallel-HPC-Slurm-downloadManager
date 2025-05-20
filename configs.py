config = {
    "download_dir": "/data/Parallel-HPC-Slurm-downloadManager/downloads", # Directory to save downloaded files
    "max_concurrent_downloads": 3, # Max parallel downloads

    # Curl specific parameters
    "curl_retry_attempts": 3,         # --retry: Number of retries for curl internal transient errors
    "curl_retry_delay_seconds": 5,    # --retry-delay: Delay between curl internal retries
    "curl_retry_max_time_seconds": 60,# --retry-max-time: Max time for curl internal retries
    "curl_connect_timeout_seconds": 30,# --connect-timeout: Max time to connect
    "curl_max_time_seconds": 1800,    # --max-time: Max time for the entire curl operation (one attempt)
    "curl_speed_time_seconds": 60,    # --speed-time: Abort if speed is below limit for this duration
    "curl_speed_limit_bytes_per_sec": 1000, # --speed-limit: Minimum speed in bytes/sec (1KB/s)

    # Downloader's own retry loop parameters (for the Python script's loop)
    "downloader_max_retries": 5,      # Number of times the script will re-attempt a failed download_file call
    "downloader_initial_retry_delay_seconds": 10, # Initial delay for the script's retry loop

    # Parameters for the more aggressive retry in retry_failed_downloads
    "downloader_aggressive_max_retries": 8,
    "downloader_aggressive_initial_retry_delay_seconds": 30,
    "downloader_aggressive_timeout_seconds": 3600, # Corresponds to curl_max_time_seconds for aggressive retries
}
