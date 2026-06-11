"""Approval dialog UI component for command trust and safety.

This module provides the ApprovalDialog component that displays interactive
approval dialogs for command execution. The dialog shows command details,
warning messages, and prompts the user to approve or deny execution.

Dialog Features:
    - Rich UI with colored panels and formatting
    - Shows command, current directory, and warnings
    - Keyboard-driven interaction (A to approve, D to deny)
    - Graceful error handling (defaults to denial for safety)
    - Ctrl+C support (treated as denial)

Dialog Layout:
    ┌─────────────────────────────────────────────────────────┐
    │  ⚠️  COMMAND APPROVAL REQUIRED                          │
    ├─────────────────────────────────────────────────────────┤
    │                                                          │
    │  ⚠️ CRITICAL: This command is in DENYLIST!              │
    │                                                          │
    │  Command: rm -rf node_modules                           │
    │  Directory: /home/user/project                          │
    │                                                          │
    │  [A] Approve    [D] Deny                                │
    │                                                          │
    └─────────────────────────────────────────────────────────┘

Warning Types:
    - Denylist warnings: "⚠️ CRITICAL: This command is in DENYLIST!"
    - AI warnings: "⚠️ AI WARNING: This command may be dangerous!"
    - Combined warnings: Both denylist and AI warnings shown together

Example Usage:
    >>> from shello_cli.trust.approval_dialog import ApprovalDialog
    >>> 
    >>> dialog = ApprovalDialog()
    >>> 
    >>> # Show approval dialog
    >>> approved = dialog.show(
    ...     command="rm -rf node_modules",
    ...     warning_message="⚠️ CRITICAL: This command is in DENYLIST!",
    ...     current_directory="/home/user/project"
    ... )
    >>> 
    >>> if approved:
    ...     print("User approved command")
    ... else:
    ...     print("User denied command")

Keyboard Controls:
    - A or a: Approve command execution (press A then Enter)
    - D or d: Deny command execution (press D then Enter)
    - Enter only: Deny (defaults to safe option)
    - Ctrl+C: Cancel (treated as denial)

Error Handling:
    - All exceptions are caught and logged
    - Errors default to denial for safety
    - KeyboardInterrupt is handled gracefully
    - No exceptions propagate to caller

See Also:
    - TrustManager: Uses ApprovalDialog for user approval
    - Rich library: Used for UI rendering
"""
from typing import Optional, Union
from rich.console import Console
import sys


# Create console for rendering
console = Console(highlight=True)


class ApprovalDialog:
    """Interactive approval dialog for command execution.
    
    Displays command details and warning messages, then prompts user
    to approve or deny execution.
    """
    
    def show(
        self,
        command: str,
        warning_message: Optional[str],
        current_directory: str
    ) -> Union[bool, str]:
        """Show approval dialog and return user decision.
        
        Args:
            command: The command to approve
            warning_message: Optional warning to display (e.g., denylist or AI warning)
            current_directory: Current working directory
            
        Returns:
            True if approved, False if denied, or a str of custom feedback
            
        Raises:
            No exceptions - handles KeyboardInterrupt and errors gracefully
        """
        try:
            return self._show_dialog(command, warning_message, current_directory)
        except KeyboardInterrupt:
            # User pressed Ctrl+C, treat as denial
            console.print("\n[yellow]Command execution cancelled[/yellow]")
            return False
        except Exception as e:
            # Log error and default to denial for safety
            console.print(f"[red]Error showing approval dialog: {e}[/red]")
            return False
    
    def _show_dialog(
        self,
        command: str,
        warning_message: Optional[str],
        current_directory: str
    ) -> Union[bool, str]:
        """Internal method to show the approval dialog.
        
        Args:
            command: The command to approve
            warning_message: Optional warning to display
            current_directory: Current working directory
            
        Returns:
            True if approved, False if denied, or a str of custom feedback
        """
        # Visual separator and header
        console.print("[dim]─────────────────────────────────────────────────────────────[/dim]")
        console.print("[bold yellow]⚠️  COMMAND APPROVAL REQUIRED[/bold yellow]")
        console.print("[dim]─────────────────────────────────────────────────────────────[/dim]")
        
        # Add warning message if present
        if warning_message:
            console.print()
            console.print(f"[bold red]{warning_message}[/bold red]")
        
        # Add command details
        console.print()
        console.print(f"  [dim]Command:[/dim]   [bright_white]{command}[/bright_white]")
        console.print(f"  [dim]Directory:[/dim] [cyan]{current_directory}[/cyan]")
        console.print()
        console.print("  [green][A] Approve[/green]    [red][D] Deny[/red]    [cyan]Or type custom feedback directly[/cyan]")
        console.print("[dim]─────────────────────────────────────────────────────────────[/dim]")
        
        # Get user input
        return self._get_user_decision()
    
    def _get_user_decision(self) -> Union[bool, str]:
        """Get user decision via keyboard input.
        
        Returns:
            True if approved, False if denied, or a str of custom feedback.
        """
        while True:  # Loop until valid input
            try:
                # Force flush all output streams
                sys.stdout.flush()
                sys.stderr.flush()
                if hasattr(console, 'file') and console.file:
                    console.file.flush()
                
                # Use plain print for prompt
                print("\nYour choice [a/d/custom] (d): ", end="", flush=True)
                
                # On Windows, use msvcrt for input with manual echo
                # This fixes the echo issue caused by Rich console terminal state
                if sys.platform == 'win32':
                    import msvcrt
                    chars = []
                    while True:
                        char = msvcrt.getwch()
                        if char in ('\r', '\n'):
                            print()  # Newline after input
                            break
                        elif char == '\x03':  # Ctrl+C
                            raise KeyboardInterrupt
                        elif char == '\x08' or char == '\x7f':  # Backspace
                            if chars:
                                chars.pop()
                                sys.stdout.write('\b \b')
                                sys.stdout.flush()
                        elif char == '\x00' or char == '\xe0':  # Special key prefix
                            msvcrt.getwch()  # Discard next char
                        elif ' ' <= char <= '~':  # Printable ASCII
                            chars.append(char)
                            sys.stdout.write(char)
                            sys.stdout.flush()
                    raw_choice = ''.join(chars).strip()
                else:
                    # Unix - regular input works fine
                    raw_choice = input().strip()
                
                # Default to 'd' (deny) if empty
                if not raw_choice:
                    console.print("[red]✗ Command denied[/red]")
                    return False
                
                choice_lower = raw_choice.lower()
                
                # Check for direct approve/deny
                if choice_lower in ('a', 'approve'):
                    console.print("[green]✓ Command approved[/green]")
                    return True
                elif choice_lower in ('d', 'deny'):
                    console.print("[red]✗ Command denied[/red]")
                    return False
                else:
                    # Custom feedback/instruction for the AI
                    console.print(f"[yellow]↩ Sending custom feedback to AI: '{raw_choice}'[/yellow]")
                    return raw_choice
                    
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Command execution cancelled[/yellow]")
                return False

                    # Loop continues to ask again
                    
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Command execution cancelled[/yellow]")
                return False
