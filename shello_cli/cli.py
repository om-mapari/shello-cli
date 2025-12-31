"""Command-line interface for Shello CLI"""
import click
import os
import sys
from config import get_config, update_config
from api.gitlab_client import GitLabConfig, GitLabAIChat
from chat.chat_session import ChatSession
from ui.ui_renderer import (
    console,
    print_welcome_banner,
    print_header,
    display_help,
    display_about,
    render_history_table
)
from ui.user_input import get_user_input_with_clear
from utils.gitlab_token import get_gitlab_token, clear_stored_token
import __init__ as version_module


def create_new_session(config):
    """Create a new GitLab client and chat session"""
    gitlab_client = GitLabAIChat(config)
    chat_session = ChatSession(gitlab_client)
    return gitlab_client, chat_session


def display_history_menu(gitlab_client):
    """Display conversation history and handle selection"""
    # Get thread history as a list of dictionaries
    threads = gitlab_client.get_thread_history(max_threads=20)
    return render_history_table(threads)


@click.group(invoke_without_command=True)
@click.version_option(version=getattr(version_module, '__version__', '0.1.0'))
@click.pass_context
def cli(ctx):
    """Shello CLI - AI Assistant with Command Execution"""
    # If no subcommand is provided, run the chat command
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@cli.command()
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--new", is_flag=True, help="Start a new conversation")
def chat(debug, new):
    """Start a chat session with AI"""
    # Get configuration
    app_config = get_config()
    
    # Override debug setting if specified
    if debug:
        app_config["debug"] = True
    
    # Get GitLab configuration
    gitlab_url = app_config.get("gitlab_url", "https://app.gitlab.server.com")
    access_token = get_gitlab_token()
    
    # Initialize GitLab client config
    config = GitLabConfig(
        gitlab_url=gitlab_url,
        access_token=access_token,
        debug=app_config.get("debug", False)
    )
    
    # Create initial session
    try:
        gitlab_client, chat_session = create_new_session(config)
        
        # Test the token by getting user info
        user = gitlab_client.get_current_user()
        name = user.get('name', 'Unknown').split(" ")[0] if user else "User"
    except Exception as e:
        console.print(f"✗ [red]Failed to connect to GitLab: {str(e)}[/red]")
        console.print("⚠ [yellow]Please check your token and try again[/yellow]")
        
        # Offer to clear stored token if connection fails
        clear_choice = console.input("\n[cyan]Clear stored token and try again? (y/n): [/cyan]").strip().lower()
        if clear_choice in ['y', 'yes']:
            clear_stored_token()
        sys.exit(1)
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Display welcome banner
    print_welcome_banner(user, getattr(version_module, '__version__', '0.1.0'))
    
    # Main chat loop
    while True:
        try:
            user_input = get_user_input_with_clear(name)
            
            if user_input is None:  # Handle Ctrl+C or Ctrl+D
                console.print("\n\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break
            
            # Check for commands
            if user_input.lower() == "/quit":
                console.print("\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break
            
            elif user_input.lower() == "/new":
                # Create completely new session
                gitlab_client, chat_session = create_new_session(config)
                console.print("\n\n✓ [green]Starting new conversation...[/green]")
                print_header("New conversation started")
                continue
            
            elif user_input.lower() == "/history":
                # Display history and handle selection
                selected_thread_id = display_history_menu(gitlab_client)
                if selected_thread_id:
                    # Continue the selected conversation
                    gitlab_client.thread_id = selected_thread_id
                    chat_session = ChatSession(gitlab_client)
                    chat_session.conversation_started = True  # Mark as started since we're continuing
                    console.print("\n[green]✓ Continuing selected conversation...[/green]")
                    print_header("Continuing previous conversation")
                else:
                    console.print("\n")
                continue
            
            elif user_input.lower() == "/help":
                # Display help and shortcuts
                display_help()
                continue
            
            elif user_input.lower() == "/clear-gitlab-token":
                # New command to clear stored token
                if clear_stored_token():
                    console.print("✓ [green]Token cleared successfully[/green]")
                    console.print("ℹ [blue]Restart the application to enter a new token[/blue]")
                continue
            
            elif user_input.lower() == "/about":
                # Display about information
                display_about(getattr(version_module, '__version__', '0.1.0'))
                continue
            
            # Skip empty input
            if not user_input.strip():
                continue
            
            # Start or continue conversation
            if not chat_session.conversation_started:
                chat_session.start_conversation(user_input)
            else:
                chat_session.continue_conversation(user_input)
        
        except KeyboardInterrupt:
            console.print("\n\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
            break
        except Exception as e:
            console.print(f"\n✗ Error: {str(e)}", style="bold red")
            if app_config.get("debug", False):
                import traceback
                console.print(traceback.format_exc(), style="red")


@cli.command()
def clear_token():
    """Clear stored GitLab token"""
    if clear_stored_token():
        console.print("✓ [green]Token cleared successfully[/green]")
    else:
        console.print("✗ [red]Failed to clear token[/red]")


@cli.command("config-set")
@click.option('--gitlab-url', help='Set GitLab URL')
@click.option('--max-output-size', type=int, help='Set maximum output size')
@click.option('--debug/--no-debug', default=None, help='Enable/disable debug mode')
def config_set(gitlab_url, max_output_size, debug):
    """Set configuration values"""
    config_updated = False
    
    if gitlab_url:
        update_config('gitlab_url', gitlab_url)
        console.print(f"✓ GitLab URL set to: {gitlab_url}")
        config_updated = True
    
    if max_output_size:
        update_config('max_output_size', max_output_size)
        console.print(f"✓ Max output size set to: {max_output_size}")
        config_updated = True
    
    if debug is not None:
        update_config('debug', debug)
        console.print(f"✓ Debug mode {'enabled' if debug else 'disabled'}")
        config_updated = True
    
    if not config_updated:
        # Show current configuration
        current_config = get_config()
        console.print("\n📋 Current Configuration:", style="bold blue")
        console.print(f"  GitLab URL: {current_config.get('gitlab_url')}")
        console.print(f"  Max Output Size: {current_config.get('max_output_size')}")
        console.print(f"  Debug Mode: {current_config.get('debug')}")
        console.print(f"  Theme: {current_config.get('theme')}")
        console.print(f"  Completion Style: {current_config.get('completion_style')}")
        console.print("\nUse options like --gitlab-url, --max-output-size, --debug to modify settings.")


# Make sure to add this command to your CLI group
cli.add_command(config_set)


