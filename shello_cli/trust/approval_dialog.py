"""Approval dialog UI component for command trust and safety.

This module provides the ApprovalDialog component that displays interactive
approval dialogs for command execution. The dialog shows command details,
warning messages, and prompts the user to approve or deny execution.

Dialog Features:
    - Rich UI with colored panels and formatting
    - Shows command, current directory, and warnings
    - Keyboard-driven selection and shortcuts (A to approve, D to deny, C to feedback)
    - Graceful error handling (defaults to denial for safety)
    - Ctrl+C support (treated as denial)

Dialog Layout:
    ┌─────────────────────────────────────────────────────────┐
    │  ⚠️  COMMAND APPROVAL REQUIRED                          │
    ├─────────────────────────────────────────────────────────┤
    │                                                         │
    │  ⚠️ CRITICAL: This command is in DENYLIST!              │
    │                                                         │
    │  Command: rm -rf node_modules                           │
    │  Directory: /home/user/project                          │
    │                                                         │
    │  Choose an action:                                      │
    │  > [A] Approve command                                  │
    │    [D] Deny command                                     │
    │    [C] Provide custom feedback to AI                    │
    │                                                         │
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
    - Up/Down or J/K: Navigate between options
    - Enter: Select the highlighted option
    - A or a: Immediately approve command execution
    - D or d: Immediately deny command execution
    - C or c: Immediately prompt for custom feedback to AI
    - Escape or Ctrl+C: Cancel (treated as denial)

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
import sys

from rich.console import Console
from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit import prompt

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
        # Show compact header with warning (since command and directory are already visible in prompt)
        if warning_message:
            clean_warning = warning_message.lstrip("⚠️ ").strip()
            console.print(f"\n⚠️  [bold yellow]COMMAND APPROVAL REQUIRED[/bold yellow] ── [bold red]{clean_warning}[/bold red]")
        else:
            console.print("\n⚠️  [bold yellow]COMMAND APPROVAL REQUIRED[/bold yellow]")
        
        # Define choices: (style_class, shortcut, text, value)
        labels = [
            ("approve", "[A]", " Approve command", True),
            ("deny", "[D]", " Deny command", False),
            ("custom", "[C]", " Provide custom feedback to AI", "custom")
        ]
        
        state = {"selected": 0, "result": None}
        
        kb = KeyBindings()
        
        @kb.add("up")
        @kb.add("k")
        def _up(event):
            state["selected"] = (state["selected"] - 1) % len(labels)
            
        @kb.add("down")
        @kb.add("j")
        def _down(event):
            state["selected"] = (state["selected"] + 1) % len(labels)
            
        @kb.add("enter")
        def _enter(event):
            state["result"] = labels[state["selected"]][3]
            event.app.exit()
            
        @kb.add("a")
        @kb.add("A")
        def _approve(event):
            state["result"] = True
            event.app.exit()
            
        @kb.add("d")
        @kb.add("D")
        def _deny(event):
            state["result"] = False
            event.app.exit()
            
        @kb.add("c")
        @kb.add("C")
        def _custom(event):
            state["result"] = "custom"
            event.app.exit()
            
        @kb.add("escape")
        def _escape(event):
            state["result"] = False
            event.app.exit()
            
        @kb.add("c-c")
        def _ctrl_c(event):
            state["result"] = False
            event.app.exit()
            
        def _get_content():
            lines = []
            lines.append(("", "\n  Choose an action:\n"))
            for i, (style_class, shortcut, text, val) in enumerate(labels):
                if i == state["selected"]:
                    lines.append((f"class:selected_{style_class}", f"  ❯ {shortcut}{text}\n"))
                else:
                    lines.append(("", "    "))
                    lines.append((f"class:shortcut_{style_class}", f"{shortcut}"))
                    lines.append((f"class:text_{style_class}", f"{text}\n"))
            return FormattedText(lines)
            
        layout = Layout(
            HSplit([
                Window(
                    content=FormattedTextControl(text=_get_content, focusable=True),
                    wrap_lines=False,
                )
            ])
        )
        
        style = Style.from_dict({
            # Selected styles (reverse background with bold foreground)
            "selected_approve": "bold green reverse",
            "selected_deny": "bold red reverse",
            "selected_custom": "bold cyan reverse",
            
            # Unselected styles
            "shortcut_approve": "bold green",
            "text_approve": "green",
            
            "shortcut_deny": "bold red",
            "text_deny": "red",
            
            "shortcut_custom": "bold cyan",
            "text_custom": "cyan",
        })
        
        app: Application = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=False,
        )
        
        # Run prompt_toolkit Application to get action selection
        app.run()
        
        # Clear the selection menu (5 lines) from the screen
        try:
            sys.stdout.write("\033[5F\033[J")
            sys.stdout.flush()
        except Exception:
            pass
        
        # Process decision
        if state["result"] is True:
            console.print("[green]✓ Command approved[/green]")
            return True
        elif state["result"] is False or state["result"] is None:
            console.print("[red]✗ Command denied[/red]")
            return False
        elif state["result"] == "custom":
            # Prompt user for custom feedback
            try:
                # Force flush all output streams before prompt
                sys.stdout.flush()
                sys.stderr.flush()
                
                feedback_prompt = FormattedText([
                    ("class:prompt", "\nEnter custom feedback for AI: ")
                ])
                feedback_style = Style.from_dict({
                    "prompt": "cyan bold"
                })
                
                raw_feedback = prompt(feedback_prompt, style=feedback_style).strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Command execution cancelled[/yellow]")
                return False
                
            if not raw_feedback:
                console.print("[red]✗ Command denied (empty feedback)[/red]")
                return False
                
            console.print(f"[yellow]↩ Sending custom feedback to AI: '{raw_feedback}'[/yellow]")
            return raw_feedback
