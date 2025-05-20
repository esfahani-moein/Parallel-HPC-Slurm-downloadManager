import os
import subprocess
import time
from urllib.parse import urlparse
from .utils import log_message # Assuming log_message is in source/utils.py
import concurrent.futures
from datetime import datetime

def download_file(url, download_dir, state_dir, links_list, 
                  # Curl parameters
                  curl_retry_attempts,
                  curl_retry_delay_seconds,
                  curl_retry_max_time_seconds,
                  curl_connect_timeout_seconds,
                  curl_max_time_seconds, 
                  curl_speed_time_seconds,
                  curl_speed_limit_bytes_per_sec,
                  # Downloader loop parameters
                  downloader_max_retries, 
                  downloader_initial_retry_delay_seconds
                  ):  
    """
    Download a single file using curl with specified retry and timeout parameters.
    Manages state and logs progress.
    """
    filename = "" # Initialize to ensure it's defined in case of early exception
    try:
        filename = os.path.basename(urlparse(url).path)
        if not filename: # Fallback for URLs without a clear filename part
            try:
                idx = links_list.index(url) # Use original list for consistent naming
                filename = f"file_{idx}.download"
            except ValueError: # Should not happen if links_list is the original list
                timestamp = int(time.time())
                filename = f"file_unknown_{timestamp}.download"
        
        output_path = os.path.join(download_dir, filename)
        state_file = os.path.join(state_dir, f"{filename}.state")

        # Check existing state
        if os.path.exists(state_file):
            with open(state_file, 'r') as f_state:
                status = f_state.read().strip()
                if status == "COMPLETED":
                    log_message(f"[SKIPPED] {filename} (URL: {url}) already marked as COMPLETED.")
                    return True, url, "Skipped, already completed"
        
        log_message(f"[STARTED] Downloading {filename} from {url}")
        
        current_script_retry_count = 0
        current_script_retry_delay = downloader_initial_retry_delay_seconds
        operation_successful = False
        
        while current_script_retry_count <= downloader_max_retries and not operation_successful:
            if current_script_retry_count > 0:
                log_message(f"[SCRIPT RETRY {current_script_retry_count}/{downloader_max_retries}] For {filename}, waiting {current_script_retry_delay}s.")
                time.sleep(current_script_retry_delay)
                current_script_retry_delay = min(current_script_retry_delay * 2, 300) # Exponential backoff, max 5 mins

            cmd = [
                "curl", "-L", "-C", "-", 
                "--retry", str(curl_retry_attempts),
                "--retry-delay", str(curl_retry_delay_seconds),
                "--retry-max-time", str(curl_retry_max_time_seconds),
                "--connect-timeout", str(curl_connect_timeout_seconds),
                "--max-time", str(curl_max_time_seconds),
                "--speed-time", str(curl_speed_time_seconds),
                "--speed-limit", str(curl_speed_limit_bytes_per_sec),
                "-#", # Progress bar
                "-o", output_path, url
            ]
            
            log_message(f"[CURL CMD] For {filename}: {' '.join(cmd)}")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, text=True)
            
            # Log curl's output line by line
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    log_message(f"  {filename} (curl): {line.strip()}")
            
            process.wait() # Wait for curl to complete
            
            if process.returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    operation_successful = True
                    file_size_mb = os.path.getsize(output_path) / (1024*1024)
                    log_message(f"[COMPLETED] {filename} (URL: {url}). Size: {file_size_mb:.2f} MB.")
                    with open(state_file, 'w') as f_state:
                        f_state.write("COMPLETED")
                    return True, url, f"Completed, Size: {file_size_mb:.2f} MB"
                else:
                    log_message(f"[FAILED ATTEMPT] {filename} (URL: {url}). Curl success (code 0), but file is missing or zero size.")
                    # operation_successful remains False, will trigger script retry if applicable
            else:
                log_message(f"[FAILED ATTEMPT] {filename} (URL: {url}). Curl exit code: {process.returncode}.")
            
            current_script_retry_count += 1
            
        # If loop finishes and not successful
        if not operation_successful:
            error_message = f"Failed after {downloader_max_retries} script retries (curl errors or zero-size file)."
            log_message(f"[EXHAUSTED RETRIES/FAILED] {filename} (URL: {url}). {error_message}")
            with open(state_file, 'w') as f_state:
                f_state.write(f"FAILED: {error_message}")
            return False, url, error_message

    except Exception as e:
        error_message = f"Exception during download of {url} (filename: {filename}): {str(e)}"
        log_message(f"[ERROR] {error_message}")
        # Attempt to write FAILED state even on general exception
        if filename: # Check if filename was determined before exception
            state_file = os.path.join(state_dir, f"{filename}.state")
            try:
                with open(state_file, 'w') as f_state:
                    f_state.write(f"FAILED: Exception - {str(e)}")
            except Exception as se:
                log_message(f"Could not write state file for {filename} after exception: {se}")
        return False, url, error_message
    
    # Fallback, should ideally not be reached if logic above is complete
    return False, url, "Unknown failure in download_file"


def download_files_concurrently(
        urls, download_dir, state_dir,
        main_params, 
        curl_params, 
        downloader_params, 
        aggressive_retry_specific_params
    ):    
    max_workers = main_params.get("max_workers", 3)
    log_message(f"Starting concurrent download of {len(urls)} files with {max_workers} workers.")
    
    results = {"success": [], "failed": [], "pending": list(urls)}
    status_file_path = os.path.join(download_dir, "download_status.txt") # Used by update_status

    def update_status_file(pass_name="Initial Pass"):
        # Appends to the status file. Initial header is written by hpc_downloader.py
        with open(status_file_path, 'a') as sf:
            sf.write(f"\n--- Status Update ({pass_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
            sf.write(f"Total URLs: {len(urls)}\n")
            sf.write(f"Successful/Skipped: {len(results['success'])}\n")
            sf.write(f"Failed (this pass/total): {len(results['failed'])}\n") # This will show cumulative failures after retry pass
            sf.write(f"Still Pending: {len(results['pending'])}\n\n")
            
            if results["success"]:
                sf.write("Successful/Skipped Downloads:\n")
                for s_url, msg in results["success"]:
                    sf.write(f"  ✓ {s_url} ({msg})\n")
            if results["failed"]:
                sf.write("\nFailed Downloads (current list):\n")
                for f_url, error in results["failed"]:
                    sf.write(f"  ✗ {f_url} (Error: {error})\n")
            if results["pending"]:
                sf.write("\nPending Downloads:\n")
                for p_url in results["pending"]:
                    sf.write(f"  ⟳ {p_url}\n")
            sf.write("--- End Status Update ---\n")

    # update_status_file("Before Downloads Start") # Optional: initial detailed status

    failed_urls_for_retry_pass = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                download_file, url, download_dir, state_dir, urls, # Pass 'urls' as links_list
                **curl_params, 
                **downloader_params
            ): url for url in urls
        }
        
        for future in concurrent.futures.as_completed(future_to_url):
            url_processed = future_to_url[future]
            if url_processed in results["pending"]:
                 results["pending"].remove(url_processed)
            
            try:
                is_success, completed_url, message = future.result()
                if is_success:
                    results["success"].append((completed_url, message))
                else:
                    results["failed"].append((completed_url, message))
                    if completed_url not in failed_urls_for_retry_pass:
                        failed_urls_for_retry_pass.append(completed_url)
            except Exception as exc:
                error_msg = f"Future processing error for {url_processed}: {exc}"
                log_message(f"[ERROR] {error_msg}")
                results["failed"].append((url_processed, error_msg))
                if url_processed not in failed_urls_for_retry_pass:
                    failed_urls_for_retry_pass.append(url_processed)
            
            update_status_file("During Initial Pass")

    log_message("\n===== Summary of Initial Download Pass =====")
    log_message(f"Successfully downloaded/skipped: {len(results['success'])} files.")
    log_message(f"Failed in initial pass: {len(results['failed'])} files.")
    if results["failed"]:
        log_message("Details of initial failures:")
        for f_url, err in results["failed"]:
            log_message(f"  - {f_url}: {err}")

    if failed_urls_for_retry_pass:
        log_message(f"\n===== Attempting Aggressive Retry for {len(failed_urls_for_retry_pass)} Failed Downloads =====")
        
        retry_pass_results = retry_failed_downloads(
            list(set(failed_urls_for_retry_pass)), # Ensure unique URLs
            download_dir, state_dir, urls, # Pass original 'urls' as links_list
            main_params, # Can reuse main_params for max_workers or have a specific one
            curl_params, # Base curl params
            aggressive_retry_specific_params # Aggressive settings
        )
        
        # Update main results based on retry pass
        # Remove successfully retried URLs from the main 'failed' list
        # Add successfully retried URLs to the main 'success' list
        
        newly_succeeded_urls_in_retry = [s_url for s_url, _ in retry_pass_results["success"]]
        
        # Add to main success list
        results["success"].extend(retry_pass_results["success"])
        
        # Rebuild the main failed list: only those that failed in initial AND also failed in retry
        final_failed_list = []
        for initial_fail_url, initial_error in results["failed"]:
            if initial_fail_url not in newly_succeeded_urls_in_retry:
                # Check if it was part of the retry attempt and if it's in retry_pass_results["failed"]
                found_in_retry_failures = False
                for retry_fail_url, retry_error_msg in retry_pass_results["failed"]:
                    if retry_fail_url == initial_fail_url:
                        final_failed_list.append((retry_fail_url, retry_error_msg)) # Use the latest error
                        found_in_retry_failures = True
                        break
                if not found_in_retry_failures:
                     # This means it failed initially but wasn't in the retry batch (should not happen if failed_urls_for_retry_pass is correct)
                     # OR it was in the retry batch but somehow not in retry_pass_results["failed"] (e.g. an exception before it was added there)
                     # For safety, keep its original failure status if not explicitly succeeded or re-failed.
                     final_failed_list.append((initial_fail_url, initial_error))


        results["failed"] = final_failed_list
        update_status_file("After Aggressive Retry Pass")

    log_message("\n===== Final Download Job Summary =====")
    log_message(f"Total successfully downloaded/skipped: {len(results['success'])} files.")
    log_message(f"Permanently failed after all attempts: {len(results['failed'])} files.")
    if results["failed"]:
        log_message("Details of permanently failed downloads:")
        for f_url, err in results["failed"]:
            log_message(f"  - {f_url}: {err}")
    else:
        log_message("All downloads were successful or skipped.")
            
    return results


def retry_failed_downloads(
        urls_to_retry, download_dir, state_dir, original_links_list,
        main_params_for_retry, # Contains max_workers for retry
        base_curl_params, 
        aggressive_retry_config
    ):
    if not urls_to_retry:
        return {"success": [], "failed": []}

    max_workers = main_params_for_retry.get("max_workers", 2) # Default to 2 workers for retry if not specified
    log_message(f"Aggressive retry: {len(urls_to_retry)} URLs with {max_workers} workers.")

    retry_results = {"success": [], "failed": []}

    # Prepare parameters for aggressive download_file attempts
    # Start with base curl parameters and override specific ones for aggression
    aggressive_curl_params_for_call = base_curl_params.copy()
    if "curl_max_time_seconds" in aggressive_retry_config: # Check if specific override exists
        aggressive_curl_params_for_call["curl_max_time_seconds"] = aggressive_retry_config["curl_max_time_seconds"]
    # Potentially override other curl params if defined in aggressive_retry_config

    # Prepare aggressive downloader loop parameters
    aggressive_downloader_params_for_call = {
        "downloader_max_retries": aggressive_retry_config.get("downloader_max_retries", 8),
        "downloader_initial_retry_delay_seconds": aggressive_retry_config.get("downloader_initial_retry_delay_seconds", 30),
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                download_file, url, download_dir, state_dir, original_links_list,
                **aggressive_curl_params_for_call,
                **aggressive_downloader_params_for_call
            ): url for url in urls_to_retry
        }
        
        for future in concurrent.futures.as_completed(future_to_url):
            url_processed = future_to_url[future]
            try:
                is_success, completed_url, message = future.result()
                if is_success:
                    retry_results["success"].append((completed_url, message))
                else:
                    retry_results["failed"].append((completed_url, message))
            except Exception as exc:
                error_msg = f"Aggressive retry future processing error for {url_processed}: {exc}"
                log_message(f"[ERROR] {error_msg}")
                retry_results["failed"].append((url_processed, error_msg))
    
    log_message(f"Aggressive retry summary: {len(retry_results['success'])} succeeded, {len(retry_results['failed'])} failed.")
    return retry_results