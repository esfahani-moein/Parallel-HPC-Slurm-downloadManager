# Parallel-HPC-Slurm-downloadManager

A robust parallel file download manager tool designed for High-Performance Computing (HPC) clusters using SLURM. 
This tool efficiently downloads a list of files, It uses `curl` for the download operations (so make sure thats available in your server), and includes features like retries, state management, and download verification.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
  - [Main Configuration (`configs.py`)](#main-configuration-configspy)
  - [Input Links (`download_links.txt`)](#input-links-download_linkstxt)
- [How to Run](#how-to-run)
  - [Using SLURM (Recommended for HPC)](#using-slurm-recommended-for-hpc)
  - [Direct Execution (for testing or non-SLURM environments)](#direct-execution-for-testing-or-non-slurm-environments)
- [Output and Logging](#output-and-logging)
- [State Management](#state-management)
- [Error Handling and Retries](#error-handling-and-retries)
- [License](#license)

## Features

*   **Parallel Downloads**: The tool uses `concurrent.futures.ThreadPoolExecutor` to download multiple files simultaneously, configured via `max_concurrent_downloads` in [`configs.py`](configs.py).
*   **Robust Error Handling & Retries**:
    *   **Curl Retries**: Configurable retries for transient network errors directly within `curl` (e.g., `curl_retry_attempts`, `curl_retry_delay_seconds`).
    *   **Script-level Retries**: The script implements its own retry logic for failed downloads with exponential backoff (see [`source.downloader.download_file`](source/downloader.py)).
    *   **Aggressive Retry Pass**: A final attempt is made for any files that failed during the initial passes, using potentially more aggressive timeout and retry settings (see [`source.downloader.retry_failed_downloads`](source/downloader.py)).
*   **State Management**: Keeps track of download states (e.g., "COMPLETED", "FAILED") in `.state` files within a `download_state` subdirectory. This allows the script to skip already completed files if restarted.
*   **SLURM Integration**: Designed to be submitted as a job on HPC clusters using the provided [`slurm_job.sh`](slurm_job.sh) script.(just modify .sh file)
*   **Configuration**: All major parameters are configurable through the [`configs.py`](configs.py) file.
*   **Download Verification**: After downloads, the script can verify files by checking for existence, zero size, or suspiciously small sizes using the [`source.utils.verify_downloads`](source/utils.py) function.
*   **Detailed Logging**:
    *   Timestamped console logs via [`source.utils.log_message`](source/utils.py).
    *   A summary status file `download_status.txt` is created in the download directory.
    *   `curl` command output is logged for each download attempt.
*   **Dynamic Filename Generation**: If a URL doesn't have a clear filename, a unique name is generated.

## Prerequisites

*   **Python**: Python 3.7+ is recommended. I used Python 3.13. Ensure your Python environment (e.g., the one activated in [`slurm_job.sh`](slurm_job.sh)) meets this requirement.
*   **`curl`**: The `curl` command-line utility must be installed and accessible in the system's PATH.
*   **Standard Python Libraries**: The script uses standard Python libraries. No external PyPI packages are required beyond these.

## Project Structure

```
.
├── .gitignore
├── configs.py                     # Main configuration file
├── download_links.txt             # List of URLs to download
├── hpc_downloader.py              # Main script entry point
├── LICENSE                        # Project license (MIT)
├── README.md                      # This file
├── slurm_job.sh                   # SLURM job submission script
├── source/                        # Source code directory
│   ├── __init__.py
│   ├── downloader.py              # Core download logic, concurrency
│   └── utils.py                   # Utility functions (config, logging, verification)
└── ... (other files like outputs, pycache)
```

## Configuration

### Main Configuration (`configs.py`)

The primary configuration is managed in the [`configs.py`](configs.py) file. Key parameters include:

*   `download_dir`: Absolute path to the directory where files will be downloaded.
*   `max_concurrent_downloads`: Maximum number of files to download in parallel.
*   **Curl Parameters**:
    *   `curl_retry_attempts`: Number of retries for `curl` internal transient errors.
    *   `curl_retry_delay_seconds`: Delay between `curl` internal retries.
    *   `curl_retry_max_time_seconds`: Max time allocated for `curl` internal retries for a single attempt.
    *   `curl_connect_timeout_seconds`: Max time for `curl` to establish a connection.
    *   `curl_max_time_seconds`: Max time for the entire `curl` operation (for one attempt).
    *   `curl_speed_time_seconds`: Duration for which speed can be below `curl_speed_limit_bytes_per_sec` before aborting.
    *   `curl_speed_limit_bytes_per_sec`: Minimum download speed; `curl` aborts if speed is below this for `curl_speed_time_seconds`.
*   **Downloader Script Retry Parameters (Initial Pass)**:
    *   `downloader_max_retries`: Number of times the Python script will re-attempt a failed `download_file` call.
    *   `downloader_initial_retry_delay_seconds`: Initial delay for the script's retry loop (uses exponential backoff).
*   **Downloader Script Retry Parameters (Aggressive Retry Pass)**:
    *   `downloader_aggressive_max_retries`: Max retries for the aggressive pass.
    *   `downloader_aggressive_initial_retry_delay_seconds`: Initial delay for the aggressive pass.
    *   `downloader_aggressive_timeout_seconds`: Corresponds to `curl_max_time_seconds` for aggressive retries, potentially allowing longer download times.

Modify these values in [`configs.py`](configs.py) to suit your needs and network conditions.

### Input Links (`download_links.txt`)

The list of URLs to download should be placed in the [`download_links.txt`](download_links.txt) file, with one URL per line. Empty lines or lines with only whitespace will be ignored.

Example [`download_links.txt`](download_links.txt):
```txt
https://example.com/file1.zip
https://example.com/another/file2.tar.gz
http://example.org/data/archive.rar
```

## How to Run

### Using SLURM (Recommended for HPC)

1.  **Customize Configuration**:
    *   Edit [`configs.py`](configs.py) with your desired settings (especially `download_dir`).
    *   Populate [`download_links.txt`](download_links.txt) with the URLs.
2.  **Customize SLURM Script**:
    *   Open [`slurm_job.sh`](slurm_job.sh).
    *   Adjust SLURM directives (e.g., `#SBATCH -A <your_account>`, `#SBATCH -p <partition>`, `#SBATCH -t <time_limit>`, output file path).
    *   Ensure the Python environment activation command (e.g., `source activate mydev1`) is correct for your setup.
    *   **Important**: The script [`hpc_downloader.py`](hpc_downloader.py) expects to be run from the project's root directory (where [`download_links.txt`](download_links.txt) is located). The current [`slurm_job.sh`](slurm_job.sh) runs `python Parallel-HPC-Slurm-downloadManager/hpc_downloader.py`. This implies the SLURM job's working directory is the parent of `Parallel-HPC-Slurm-downloadManager`. It's highly recommended to add a `cd /path/to/your/Parallel-HPC-Slurm-downloadManager` command in [`slurm_job.sh`](slurm_job.sh) before the `python hpc_downloader.py` line to ensure correct relative path resolution for [`download_links.txt`](download_links.txt).
        ```sh
        # In slurm_job.sh, before python command:
        # cd /path/to/your/Parallel-HPC-Slurm-downloadManager 
        # python hpc_downloader.py
        ```
3.  **Submit Job**:
    ```bash
    sbatch slurm_job.sh
    ```
4.  **Monitor**:
    *   Check the SLURM output file specified with `#SBATCH -o`.
    *   Monitor the `download_status.txt` file in your configured `download_dir`.

### Direct Execution (for testing or non-SLURM environments)

1.  **Customize Configuration**:
    *   Edit [`configs.py`](configs.py).
    *   Populate [`download_links.txt`](download_links.txt).
2.  **Activate Python Environment**: Ensure your Python 3.7+ environment with `curl` access is active.
3.  **Run Script**: Navigate to the project root directory in your terminal and execute:
    ```bash
    python hpc_downloader.py
    ```
4.  **Monitor**:
    *   Observe the console output for real-time logs.
    *   Check the `download_status.txt` file in your configured `download_dir`.

## Output and Logging

*   **Downloaded Files**: Stored in the directory specified by `download_dir` in [`configs.py`](configs.py).
*   **State Files**: Located in `[download_dir]/download_state/`. Each file corresponds to a download and stores its status (e.g., `filename.ext.state`).
*   **Status File**: A summary file named `download_status.txt` is created in the `download_dir`. It logs the start time, total files, and periodic updates on successful, failed, and pending downloads.
*   **Console Logs**: Detailed, timestamped logs are printed to standard output (and captured in the SLURM output file). This includes `curl` command execution and its output for each attempt. The main script [`hpc_downloader.py`](hpc_downloader.py) attempts to force unbuffered output for real-time monitoring.

## State Management

The downloader creates a `.state` file for each URL in the `[download_dir]/download_state/` directory.
*   If a file is successfully downloaded, its state file will contain "COMPLETED".
*   If a file fails after all retry attempts, its state file will contain "FAILED" along with an error message.
*   On subsequent runs, if a `.state` file indicates "COMPLETED", the download for that URL will be skipped. This allows for resuming interrupted download jobs.

This is handled by the [`source.downloader.download_file`](source/downloader.py) function.

## Error Handling and Retries

The script employs a multi-layered retry mechanism:

1.  **Curl Internal Retries**: `curl` itself is configured to retry a certain number of times (`curl_retry_attempts`) with a specified delay (`curl_retry_delay_seconds`) for transient errors. This is the first line of defense.
2.  **Script-Level Retries (Initial Pass)**: If a `curl` command (including its internal retries) ultimately fails, or if the downloaded file is empty, the [`source.downloader.download_file`](source/downloader.py) function will attempt to re-download the file. It uses an exponential backoff strategy for delays between these script-level retries, configurable via `downloader_max_retries` and `downloader_initial_retry_delay_seconds`.
3.  **Aggressive Retry Pass**: After the initial download pass for all URLs, any files that still failed are collected. The [`source.downloader.retry_failed_downloads`](source/downloader.py) function then attempts to download these files again, potentially using more lenient timeout settings (e.g., `downloader_aggressive_timeout_seconds` which overrides `curl_max_time_seconds` for this pass) and a different set of retry counts (`downloader_aggressive_max_retries`).

This robust approach aims to maximize the success rate of downloads even in unstable network conditions.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
