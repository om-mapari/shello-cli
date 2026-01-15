"""UI rendering utilities using Rich library"""
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from pathlib import Path
import re
from rich.table import Table

# Create console with auto-detection of width
console = Console(highlight=True)


def print_header(title):
    """Print a styled header"""
    console.print(f"\n[bold blue]── {title} ──[/bold blue]\n")





def render_terminal_command(command, output_filter, cwd=None, user="user", hostname="win"):
    """Modern two-line terminal command rendering with box-drawing characters"""
    if cwd:
        try:
            home_path = str(Path.home())
            short_cwd = cwd.replace(home_path, "~") if home_path in cwd else cwd
        except Exception:
            short_cwd = cwd
    else:
        short_cwd = "~"
    
    # First line: top box with user@hostname and path
    first_line = Text()
    first_line.append("┌─[", style="white")
    first_line.append("💻 ", style="blue")
    first_line.append(user, style="bold green")
    first_line.append("@", style="white")
    first_line.append(hostname, style="bold cyan")
    first_line.append("]─[", style="white")
    first_line.append(short_cwd, style="bold magenta")
    first_line.append("]", style="white")
    
    if output_filter:
        first_line.append("─[", style="white")
        first_line.append(f"📊 Filter: {output_filter}", style="yellow")
        first_line.append("]", style="white")
    
    console.print(first_line)
    
    # Second line: bottom box with command
    second_line = Text()
    second_line.append("└─", style="white")
    second_line.append("$ ", style="bold yellow")
    second_line.append(command, style="bright_white bold")
    
    console.print(second_line)


def render_direct_command_output(command: str, cwd=None, user="user", hostname="win"):
    """Render direct command execution header without AI branding.
    
    This function renders direct command execution in a consistent terminal format
    without the "🐚 Shello" header, to differentiate from AI-processed commands.
    
    Args:
        command: The command being executed
        cwd: Current working directory (optional)
        user: Username for display
        hostname: Hostname for display
    """
    if cwd:
        try:
            home_path = str(Path.home())
            short_cwd = cwd.replace(home_path, "~") if home_path in cwd else cwd
        except Exception:
            short_cwd = cwd
    else:
        short_cwd = "~"
    
    # First line: top box with user@hostname and path
    first_line = Text()
    first_line.append("┌─[", style="white")
    first_line.append("💻 ", style="blue")
    first_line.append(user, style="bold green")
    first_line.append("@", style="white")
    first_line.append(hostname, style="bold cyan")
    first_line.append("]─[", style="white")
    first_line.append(short_cwd, style="bold magenta")
    first_line.append("]", style="white")
    
    console.print(first_line)
    
    # Second line: command with $ prompt
    second_line = Text()
    second_line.append("└─", style="white")
    second_line.append("$ ", style="bold yellow")
    second_line.append(command, style="bright_white bold")
    
    console.print(second_line)


def render_tool_execution(tool_name: str, parameters: dict, cwd=None, user="user", hostname="win"):
    """Generic tool execution rendering with box-drawing characters.
    
    This function renders any tool execution in a consistent format.
    For shell commands, it shows user@hostname with the command.
    For other tools, it shows a simpler format with just icon and path.
    
    Args:
        tool_name: Name of the tool being executed (e.g., "run_shell_command", "analyze_json")
        parameters: Dictionary of parameters passed to the tool
        cwd: Current working directory (optional)
        user: Username for display
        hostname: Hostname for display
    """
    # Tool icons mapping
    tool_icons = {
        "run_shell_command": "💻",
        "analyze_json": "🔍",
        "python_code_executor": "🐍",
        "file_read": "📄",
        "file_write": "✏️",
        "web_search": "🌐",
        "default": "🔧"
    }
    
    icon = tool_icons.get(tool_name, tool_icons["default"])
    
    if cwd:
        try:
            home_path = str(Path.home())
            short_cwd = cwd.replace(home_path, "~") if home_path in cwd else cwd
        except Exception:
            short_cwd = cwd
    else:
        short_cwd = "~"
    
    # First line: top box - different format for shell commands vs other tools
    first_line = Text()
    first_line.append("┌─[", style="white")
    
    if tool_name == "run_shell_command":
        # For shell commands, show icon + user@hostname
        first_line.append(f"{icon} ", style="blue")
        first_line.append(user, style="bold green")
        first_line.append("@", style="white")
        first_line.append(hostname, style="bold cyan")
    else:
        # For other tools, just show icon (no trailing space)
        first_line.append(icon, style="blue")
    
    first_line.append("]─[", style="white")
    first_line.append(short_cwd, style="bold magenta")
    first_line.append("]", style="white")
    
    console.print(first_line)
    
    # Second line: tool name and main parameter
    second_line = Text()
    second_line.append("└─", style="white")
    
    if tool_name == "run_shell_command":
        # For shell commands, show the command directly
        command = parameters.get("command", "")
        second_line.append("$ ", style="bold yellow")
        second_line.append(command, style="bright_white bold")
    else:
        # For other tools, show ⟩ then tool name and parameters
        second_line.append("⟩ ", style="bold yellow")
        second_line.append(f"{tool_name}", style="bold cyan")
        second_line.append("(", style="white")
        
        # Format parameters
        param_parts = []
        for key, value in parameters.items():
            # Truncate long values
            str_value = str(value)
            if len(str_value) > 60:
                str_value = str_value[:57] + "..."
            param_parts.append(f"{key}={repr(str_value)}")
        
        second_line.append(", ".join(param_parts), style="bright_white")
        second_line.append(")", style="white")
    
    console.print(second_line)





def display_help():
    """Display keyboard shortcuts and commands help"""
    console.print("\n[cyan]📚 Shello CLI Help & Shortcuts:[/cyan]")
    
    # Commands table
    commands_table = Table(show_header=True, header_style="bold magenta", title="Chat Commands")
    commands_table.add_column("Command", style="yellow", width=12)
    commands_table.add_column("Description", style="white")
    
    commands_table.add_row("/quit", "Exit the application")
    commands_table.add_row("/exit", "Exit the application")
    commands_table.add_row("/new", "Start a new conversation")
    commands_table.add_row("/switch", "Switch between AI providers")
    commands_table.add_row("/about", "Show information about Shello CLI")
    commands_table.add_row("/help", "Show this help message")
    
    console.print(commands_table)
    console.print()
    
    # Keyboard shortcuts table
    shortcuts_table = Table(show_header=True, header_style="bold magenta", title="Keyboard Shortcuts")
    shortcuts_table.add_column("Shortcut", style="cyan", width=15)
    shortcuts_table.add_column("Action", style="white")
    
    shortcuts_table.add_row("Enter", "Send message")
    shortcuts_table.add_row("Ctrl+J", "Insert new line")
    shortcuts_table.add_row("Ctrl+A", "Select all text")
    shortcuts_table.add_row("Ctrl+X", "Cut (copy and clear)")
    shortcuts_table.add_row("Ctrl+V", "Paste from clipboard")
    shortcuts_table.add_row("Ctrl+Z", "Undo")
    shortcuts_table.add_row("Ctrl+Y", "Redo")
    shortcuts_table.add_row("Ctrl+W", "Delete word backwards")
    shortcuts_table.add_row("Ctrl+K", "Delete to end of line")
    shortcuts_table.add_row("Ctrl+U", "Delete to beginning of line")
    shortcuts_table.add_row("Backspace", "Smart delete (selection or char)")
    shortcuts_table.add_row("Ctrl+C", "Cancel/Exit")
    
    console.print(shortcuts_table)
    console.print()


def print_welcome_banner(user_info, version):
    """Print a welcome banner that adapts to terminal width"""
    # Get current terminal width
    width = min(console.width - 4, 120)
    
    shello_cli_art = """
███████╗██╗  ██╗███████╗██╗     ██╗      ██████╗      ██████╗██╗     ██╗
██╔════╝██║  ██║██╔════╝██║     ██║     ██╔═══██╗    ██╔════╝██║     ██║
███████╗███████║█████╗  ██║     ██║     ██║   ██║    ██║     ██║     ██║
╚════██║██╔══██║██╔══╝  ██║     ██║     ██║   ██║    ██║     ██║     ██║
███████║██║  ██║███████╗███████╗███████╗╚██████╔╝    ╚██████╗███████╗██║
╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝ ╚═════╝      ╚═════╝╚══════╝╚═╝
    """
    
    # Create centered banner content
    banner_content = Text(justify="center")
    banner_content.append(shello_cli_art, style="bold cyan")
    banner_content.append("\n")
    banner_content.append("Say Hello to Shello. Making terminals less... terminal".center(55), style="white")
    banner_content.append("\n")
    banner_content.append("\n")
    
    console.print(Panel(
        banner_content,
        border_style="cyan",
        box=ROUNDED,
        width=width,
        expand=False,
        padding=(1, 2),
        title=f"[bold bright_white]🐚 Shello CLI ({version}) [/bold bright_white]",
        title_align="center"
    ))
    console.print()
    
    # User info
    if user_info:
        name = user_info.get('name', 'Unknown')
        username = user_info.get('username', 'unknown')
        console.print(f"\n[bold cyan]👋 {name}[/bold cyan] [bright_black](@{username})[/bright_black] [bright_black]• Shello CLI Ready to assist![/bright_black]")
    else:
        console.print(f"\n[bold bright_blue]👤 Welcome![/bold bright_blue] [bright_black]• Shello CLI Ready to assist![/bright_black]")
    
    console.print(f"\n[bold cyan]📋 Available commands:[/bold cyan]")
    console.print("  [bold bright_blue]/about[/bold bright_blue] [bright_black]─[/bright_black] [white]Show information about Shello CLI[/white]")
    console.print("  [bold bright_blue]/quit[/bold bright_blue] [bright_black]─[/bright_black] [white]Exit the application[/white]")
    console.print("  [bold bright_blue]/new[/bold bright_blue] [bright_black]─[/bright_black] [white]Start a new conversation[/white]")
    console.print("  [bold bright_blue]/switch[/bold bright_blue] [bright_black]─[/bright_black] [white]Switch between AI providers[/white]")
    console.print("  [bold bright_blue]/help[/bold bright_blue] [bright_black]─[/bright_black] [white]Show keyboard shortcuts and help[/white]")
    console.print("  [bold bright_blue]↑/↓[/bold bright_blue] [bright_black]─[/bright_black] [white]Navigate command history[/white]")
    console.print()
    console.print("  [bright_black]💡 Start by describing what you'd like to do...[/bright_black]")
    
    print_header("Starting new conversation")
    console.print()


def display_about(version):
    """Display about information for Shello CLI"""
    # Create markdown content as a string
    about_markdown = f"""

**🐚 Shello CLI**

**What is Shello CLI?**

An AI-powered terminal assistant that not only suggests commands but executes them intelligently with awareness and safety.

**Core Capabilities**

- ⚡ **Instant Command Mode** - Executes common system commands directly, bypassing AI latency
- 🧠 **Intelligent Output Processing** - Applies semantic-aware truncation instead of blind clipping
- 💾 **Command Output Memory** - Stores and retrieves historical outputs via a persistent 100MB cache
- 📊 **JSON-Aware Intelligence** - Auto-analyzes large JSON responses and suggests optimal `jq` query paths
- 🎯 **Context-Specific Compression** - Uses different output collapsing strategies based on command behavior
- 🚨 **Semantic Line Prioritization** - Ensures critical errors and failure causes are never hidden
- 🔁 **Repetition Folding** - Compresses redundant progress logs and repetitive streaming output
- 🧪 **Reliability First** - Backed by 1,400+ automated tests including property-based validation
- 🛠️ **Battle-Tested for Production** - Designed for real systems, real failures, real fixes

**Developer**

- Made with ❤️ by **Om Mapari**
- Contributions welcome at GitHub: **https://github.com/om-mapari/shello-cli**

---

**Version**: {version}
    """


    
    # Create a panel with the markdown content
    markdown_content = Markdown(about_markdown)
    about_panel = Panel(
        markdown_content,
        border_style="cyan",
        box=ROUNDED,
        title=f"[bold bright_white]🐚 About Shello CLI v{version}[/bold bright_white]",
        title_align="center",
        padding=(1, 2)
    )
    
    console.print(about_panel)
    console.print()
