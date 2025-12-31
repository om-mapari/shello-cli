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


def render_history_table(threads):
    """Render conversation history table and return user selection"""
    console.print("\n[cyan]📜 Conversation History:[/cyan]")
    
    if not threads:
        console.print("No previous conversations found.", style="yellow")
        return None
    
    # Create a rich table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="green", width=3)
    table.add_column("First User Message", style="white", min_width=48)
    table.add_column("Created At", style="dim", width=20)
    
    # Add threads to table with full messages
    for i, thread in enumerate(threads, 1):
        full_message = thread.get('FirstUserMessage', 'N/A')
        created_at = thread.get('CreatedAt', 'N/A')
        
        # Display full message without truncation
        table.add_row(
            str(i),
            full_message,  # Full message, no truncation
            created_at
        )
    
    console.print(table)
    console.print()
    console.print("[yellow]0.[/yellow] [white]Go back to main menu[/white]")
    console.print()
    
    # Get user selection
    while True:
        try:
            choice = console.input("Select conversation number (0 to go back): ").strip()
            
            if choice == "0":
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(threads):
                selected_thread = threads[choice_num - 1]
                console.print(f"\n[green]✓ Selected conversation:[/green] {selected_thread['FirstUserMessage']}")
                return selected_thread['id']
            else:
                console.print(f"✗ Please enter a number between 0 and {len(threads)}", style="red")
        
        except ValueError:
            console.print("✗ Please enter a valid number", style="red")
        except KeyboardInterrupt:
            console.print("\n")
            return None


def render_markdown(text):
    """Render markdown text using Rich"""
    markdown = Markdown(text)
    console.print(markdown)


def clean_execute_command_tags(response):
    """Remove execute_command XML tags and Action line from the response"""
    # Remove execute_command XML tags
    pattern = r'<execute_command>.*?</execute_command>'
    cleaned = re.sub(pattern, '', response, flags=re.DOTALL)
    
    # Remove "Action: execute_command" line
    action_pattern = r'Action:\s*execute_command\s*\n?'
    cleaned = re.sub(action_pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up multiple newlines
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def render_ai_response(response):
    """Render AI response with simple formatting"""
    cleaned_response = clean_execute_command_tags(response)
    
    console.print()
    console.print("🤖 AI", style="bold blue")
    
    # Render markdown content directly
    markdown = Markdown(cleaned_response)
    console.print(markdown)
    console.print()


def render_terminal_command(command, output_filter, cwd=None, user="user", hostname="win"):
    """Simple terminal command rendering without panels"""
    if cwd:
        try:
            home_path = str(Path.home())
            short_cwd = cwd.replace(home_path, "~") if home_path in cwd else cwd
        except Exception:
            short_cwd = cwd
    else:
        short_cwd = "~"
    
    # Create the terminal line
    terminal_line = Text()
    
    if output_filter:
        terminal_line.append(f"📊 (Filter: {output_filter})\n", style="yellow")
    
    terminal_line.append("💻 ", style="blue")
    terminal_line.append(user, style="bold green")
    terminal_line.append("@", style="white")
    terminal_line.append(hostname, style="bold green")
    terminal_line.append(":", style="white")
    terminal_line.append(short_cwd, style="bold blue")
    terminal_line.append("$ ", style="white")
    terminal_line.append(command, style="bright_white bold")
    
    console.print(terminal_line)


def render_terminal_output(output, cwd=None, user="user", hostname="win"):
    """Simple terminal output rendering - just plain text"""
    if output:
        # Remove ANSI color codes
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        console.print(clean_output, style="white")


def render_spinner(text="Processing..."):
    """Return a spinner context manager"""
    return console.status(text, spinner="dots")


def display_help():
    """Display keyboard shortcuts and commands help"""
    console.print("\n[cyan]📚 Shello CLI Help & Shortcuts:[/cyan]")
    
    # Commands table
    commands_table = Table(show_header=True, header_style="bold magenta", title="Chat Commands")
    commands_table.add_column("Command", style="yellow", width=12)
    commands_table.add_column("Description", style="white")
    
    commands_table.add_row("/quit", "Exit the application")
    commands_table.add_row("/new", "Start a new conversation")
    commands_table.add_row("/history", "View and continue previous conversations")
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
    banner_content.append(">> Next-Gen CLI Powered by GitLab Duo + jqlang + BLZ CLI <<".center(60), style="bright_blue")
    
    console.print(Panel(
        banner_content,
        border_style="cyan",
        box=ROUNDED,
        width=width,
        expand=False,
        padding=(1, 2),
        title=f"[bold bright_white]✨ Shello CLI ({version}) ✨[/bold bright_white]",
        title_align="center"
    ))
    console.print()
    
    # User info
    if user_info:
        name = user_info.get('name', 'Unknown')
        username = user_info.get('username', 'unknown')
        console.print(f"\n[bold cyan]👋 {name}[/bold cyan] [bright_black](@{username})[/bright_black] [bright_black]• Shello CLI Ready to assist![/bright_black]")
    else:
        console.print(f"\n[bold bright_blue]👤 Guest User[/bold bright_blue] [bright_black]• Shello CLI Ready to assist![/bright_black]")
    
    console.print(f"\n[bold cyan]📋 Available commands:[/bold cyan]")
    console.print("  [bold bright_blue]/about[/bold bright_blue] [bright_black]─[/bright_black] [white]Show information about Shello CLI[/white]")
    console.print("  [bold bright_blue]/quit[/bold bright_blue] [bright_black]─[/bright_black] [white]Exit the application[/white]")
    console.print("  [bold bright_blue]/new[/bold bright_blue] [bright_black]─[/bright_black] [white]Save current and start a new conversation[/white]")
    console.print("  [bold bright_blue]/history[/bold bright_blue] [bright_black]─[/bright_black] [white]View and continue from previous conversations[/white]")
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
# 🚀 Shello CLI

*"Making terminals less... terminal"*

## What is Shello CLI?

**An intelligent AI assistant that helps you troubleshoot and resolve technical problems through natural conversation and smart command execution.**

## Key Features

- 💬 Intelligent issue diagnosis in plain English
- ☁️ AWS & Cloud debugging assistance
- ⚡ Smart command execution with approval
- 🧠 Context-aware analysis and insights
- 🔒 Secure local execution
- 📜 Conversation history management

## Developer

**Made with ❤️ by Om Mapari**

*Version: {version}*
    """
    
    # Create a panel with the markdown content
    markdown_content = Markdown(about_markdown)
    about_panel = Panel(
        markdown_content,
        border_style="cyan",
        box=ROUNDED,
        title=f"[bold bright_white]ℹ️ About Shello CLI ({version})[/bold bright_white]",
        title_align="center",
        padding=(1, 2)
    )
    
    console.print(about_panel)
    console.print()
