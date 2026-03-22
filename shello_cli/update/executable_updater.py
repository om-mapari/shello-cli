"""Executable binary download and replacement functionality."""

import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Optional, Callable

import requests
from rich.progress import Progress, DownloadColumn, TransferSpeedColumn

from shello_cli.update.exceptions import DownloadError, UpdateError


class ExecutableUpdater:
    """Downloads and replaces executable binary from GitHub releases."""
    
    def __init__(self, repo_owner: str, repo_name: str):
        """Initialize executable updater.
        
        Args:
            repo_owner: GitHub repository owner (e.g., "om-mapari")
            repo_name: GitHub repository name (e.g., "shello-cli")
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://github.com/{repo_owner}/{repo_name}/releases/download"
    
    def download_binary(
        self, 
        version: str, 
        asset_name: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """Download binary from GitHub release.
        
        Args:
            version: Version tag (e.g., "v0.4.4" or "0.4.4")
            asset_name: Asset filename to download (e.g., "shello.exe")
            progress_callback: Optional callback for progress updates (bytes_downloaded, total_bytes)
            
        Returns:
            Path to downloaded file in temporary directory
            
        Raises:
            DownloadError: If download fails
        """
        # Ensure version has 'v' prefix for GitHub URL
        if not version.startswith('v'):
            version = f'v{version}'
        
        # Construct download URL
        download_url = f"{self.base_url}/{version}/{asset_name}"
        
        try:
            # Create temporary file for download
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"shello_update_{asset_name}")
            
            # Start download with streaming
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            
            # Download with progress tracking
            if progress_callback:
                # Use callback for progress updates
                downloaded = 0
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress_callback(downloaded, total_size)
            else:
                # Download without progress tracking
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            return temp_path
            
        except requests.RequestException as e:
            raise DownloadError(f"Failed to download binary from {download_url}: {e}")
        except IOError as e:
            raise DownloadError(f"Failed to write downloaded binary to {temp_path}: {e}")
    
    def verify_binary(self, binary_path: str) -> bool:
        """Verify downloaded binary is valid.
        
        Args:
            binary_path: Path to binary file
            
        Returns:
            True if binary appears valid (size > 0)
        """
        try:
            file_size = os.path.getsize(binary_path)
            return file_size > 0
        except OSError:
            return False
    
    def replace_executable(self, new_binary_path: str, target_path: str) -> None:
        """Replace current executable with new binary.
        
        Creates backup, replaces executable, removes backup on success.
        Restores backup on failure.
        
        Args:
            new_binary_path: Path to downloaded binary
            target_path: Path to current executable
            
        Raises:
            UpdateError: If replacement fails
        """
        old_path = f"{target_path}.old"
        new_binary_moved = False

        try:
            # Step 1: On Windows, rename the running exe out of the way first.
            # Windows locks running executables against overwrite but allows rename.
            if os.name == 'nt':
                if os.path.exists(old_path):
                    os.remove(old_path)
                if os.path.exists(target_path):
                    os.rename(target_path, old_path)

            # Step 2: Move new binary into place
            shutil.move(new_binary_path, target_path)
            new_binary_moved = True

            # Step 3: Set executable permissions on Unix systems
            if os.name != 'nt':
                current_permissions = os.stat(target_path).st_mode
                os.chmod(target_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            # Step 4: Remove old binary on success (best effort — may still be locked)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass  # Will be cleaned up on next run

        except Exception as e:
            # Restore old binary on failure
            if os.name == 'nt' and os.path.exists(old_path):
                try:
                    if new_binary_moved and os.path.exists(target_path):
                        os.remove(target_path)
                    os.rename(old_path, target_path)
                except Exception as restore_error:
                    raise UpdateError(
                        f"Failed to replace executable and restore backup: {e}. "
                        f"Restore error: {restore_error}"
                    )

            # Clean up new binary if it wasn't moved
            if not new_binary_moved and os.path.exists(new_binary_path):
                try:
                    os.remove(new_binary_path)
                except Exception:
                    pass

            raise UpdateError(f"Failed to replace executable: {e}")
