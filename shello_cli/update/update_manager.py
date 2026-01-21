"""Update manager orchestration for Shello CLI updates."""

import threading
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.progress import Progress, DownloadColumn, TransferSpeedColumn

from shello_cli.update.version_checker import VersionChecker
from shello_cli.update.platform_detector import PlatformDetector
from shello_cli.update.executable_updater import ExecutableUpdater
from shello_cli.update.exceptions import UpdateError, UnsupportedPlatformError


@dataclass
class UpdateCheckResult:
    """Result of update availability check."""
    update_available: bool
    current_version: str
    latest_version: Optional[str]
    error: Optional[str] = None


@dataclass
class UpdateResult:
    """Result of update operation."""
    success: bool
    message: str
    new_version: Optional[str] = None
    error: Optional[str] = None


class UpdateManager:
    """Orchestrates the update process for Shello CLI."""
    
    def __init__(self, repo_owner: str = "om-mapari", repo_name: str = "shello-cli"):
        """Initialize update manager.
        
        Args:
            repo_owner: GitHub repository owner (default: "om-mapari")
            repo_name: GitHub repository name (default: "shello-cli")
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.version_checker = VersionChecker(repo_owner, repo_name)
        self.platform_detector = PlatformDetector()
        self.executable_updater = ExecutableUpdater(repo_owner, repo_name)
        self.console = Console()
    
    def check_for_updates(self) -> UpdateCheckResult:
        """Check if updates are available.
        
        Returns:
            UpdateCheckResult with status and version information
        """
        try:
            update_available, current_version, latest_version = self.version_checker.is_update_available()
            
            if current_version is None:
                return UpdateCheckResult(
                    update_available=False,
                    current_version="unknown",
                    latest_version=None,
                    error="Could not determine current version"
                )
            
            if latest_version is None:
                return UpdateCheckResult(
                    update_available=False,
                    current_version=current_version,
                    latest_version=None,
                    error="Could not check for updates. Please check your internet connection."
                )
            
            return UpdateCheckResult(
                update_available=update_available,
                current_version=current_version,
                latest_version=latest_version,
                error=None
            )
            
        except Exception as e:
            return UpdateCheckResult(
                update_available=False,
                current_version="unknown",
                latest_version=None,
                error=f"Update check failed: {str(e)}"
            )
    
    def perform_update(self, force: bool = False) -> UpdateResult:
        """Perform the update process.
        
        Args:
            force: If True, re-download even if on latest version
            
        Returns:
            UpdateResult with success status and messages
        """
        try:
            # Step 1: Check for updates
            check_result = self.check_for_updates()
            
            if check_result.error and not force:
                return UpdateResult(
                    success=False,
                    message="Update check failed",
                    error=check_result.error
                )
            
            # If no update available and not forcing, inform user
            if not check_result.update_available and not force:
                return UpdateResult(
                    success=True,
                    message=f"You are already on the latest version ({check_result.current_version})",
                    new_version=check_result.current_version
                )
            
            # Determine target version
            target_version = check_result.latest_version if check_result.latest_version else check_result.current_version
            
            if force:
                self.console.print(f"[yellow]Force update: Re-downloading version {target_version}[/yellow]")
            else:
                self.console.print(
                    f"[cyan]Update available:[/cyan] {check_result.current_version} → {target_version}"
                )
            
            # Step 2: Detect platform
            try:
                platform = self.platform_detector.get_platform()
                asset_name = self.platform_detector.get_asset_name(platform)
            except UnsupportedPlatformError as e:
                return UpdateResult(
                    success=False,
                    message="Platform not supported",
                    error=str(e)
                )
            
            # Step 3: Download binary with progress bar
            self.console.print(f"[cyan]Downloading {asset_name}...[/cyan]")
            
            try:
                with Progress(
                    *Progress.get_default_columns(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    console=self.console
                ) as progress:
                    task_id = progress.add_task("[cyan]Downloading...", total=100)
                    
                    def progress_callback(downloaded: int, total: int):
                        if total > 0:
                            progress.update(task_id, completed=(downloaded / total) * 100)
                    
                    downloaded_path = self.executable_updater.download_binary(
                        version=target_version,
                        asset_name=asset_name,
                        progress_callback=progress_callback
                    )
            except Exception as e:
                return UpdateResult(
                    success=False,
                    message="Download failed",
                    error=str(e)
                )
            
            # Step 4: Verify downloaded binary
            if not self.executable_updater.verify_binary(downloaded_path):
                return UpdateResult(
                    success=False,
                    message="Downloaded binary verification failed",
                    error="Binary file is empty or corrupted"
                )
            
            # Step 5: Replace executable
            try:
                executable_path = self.platform_detector.get_executable_path()
                self.console.print("[cyan]Installing update...[/cyan]")
                self.executable_updater.replace_executable(downloaded_path, executable_path)
            except UpdateError as e:
                return UpdateResult(
                    success=False,
                    message="Failed to replace executable",
                    error=str(e)
                )
            
            # Success!
            return UpdateResult(
                success=True,
                message="Update completed successfully",
                new_version=target_version
            )
            
        except Exception as e:
            return UpdateResult(
                success=False,
                message="Update failed",
                error=f"Unexpected error: {str(e)}"
            )
    
    def check_for_updates_async(self, timeout: float = 2.0) -> Optional[UpdateCheckResult]:
        """Check for updates with timeout (for startup check).
        
        Args:
            timeout: Maximum time to wait for check in seconds
            
        Returns:
            UpdateCheckResult or None if timeout/error
        """
        result_container = [None]
        exception_occurred = [False]
        
        def check_thread():
            try:
                result_container[0] = self.check_for_updates()
            except Exception:
                # Silently fail - startup checks should never crash
                exception_occurred[0] = True
                result_container[0] = None
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        # If thread is still alive, it timed out
        if thread.is_alive():
            return None
        
        # If exception occurred, return None
        if exception_occurred[0]:
            return None
        
        return result_container[0]
