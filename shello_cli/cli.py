"""Command-line interface for Shello CLI"""
import click
import os
import sys
from shello_cli.agent.shello_agent import ShelloAgent
from shello_cli.chat.chat_session import ChatSession
from shello_cli.ui.ui_renderer import (
    console,
    print_welcome_banner,
    print_header,
    display_help,
    display_about
)
from shello_cli.ui.user_input import get_user_input_with_clear
from shello_cli.utils.settings_manager import SettingsManager
import shello_cli as version_module


def create_new_session(settings_manager):
    """Create a new ShelloAgent and chat session"""
    api_key = settings_manager.get_api_key()
    if not api_key:
        console.print("✗ [red]No API key found. Please set OPENAI_API_KEY environment variable or configure in settings.[/red]")
        sys.exit(1)
    
    base_url = settings_manager.get_base_url()
    model = settings_manager.get_current_model()
    
    agent = ShelloAgent(
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    chat_session = ChatSession(agent)
    return agent, chat_session



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
    # Get settings manager
    settings_manager = SettingsManager.get_instance()
    
    # Create initial session
    try:
        agent, chat_session = create_new_session(settings_manager)
        
        # Get user name from environment or use default
        name = os.environ.get('USER', os.environ.get('USERNAME', 'User'))
    except Exception as e:
        console.print(f"✗ [red]Failed to initialize agent: {str(e)}[/red]")
        console.print("⚠ [yellow]Please check your API key and settings[/yellow]")
        sys.exit(1)
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Display welcome banner (pass None for user_info since we don't have GitLab user)
    print_welcome_banner(None, getattr(version_module, '__version__', '0.1.0'))
    
    # Main chat loop
    while True:
        try:
            user_input = get_user_input_with_clear(name)
            
            if user_input is None:  # Handle Ctrl+C or Ctrl+D
                console.print("\n\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break
            
            # Check for commands
            if user_input.lower() in ["/quit", "/exit"]:
                console.print("\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break
            
            elif user_input.lower() == "/new":
                # Create completely new session
                agent, chat_session = create_new_session(settings_manager)
                console.print("\n\n✓ [green]Starting new conversation...[/green]")
                print_header("New conversation started")
                continue
            
            elif user_input.lower() == "/help":
                # Display help and shortcuts
                display_help()
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
            if debug:
                import traceback
                console.print(traceback.format_exc(), style="red")


@cli.command()
def config():
    """Show current configuration"""
    settings_manager = SettingsManager.get_instance()
    user_settings = settings_manager.load_user_settings()
    project_settings = settings_manager.load_project_settings()
    
    console.print("\n📋 Current Configuration:", style="bold blue")
    console.print(f"  API Key: {'***' + settings_manager.get_api_key()[-4:] if settings_manager.get_api_key() else 'Not set'}")
    console.print(f"  Base URL: {user_settings.base_url}")
    console.print(f"  Current Model: {settings_manager.get_current_model()}")
    console.print(f"  Available Models: {', '.join(user_settings.models)}")
    if project_settings.model:
        console.print(f"  Project Model Override: {project_settings.model}")
    console.print()


if __name__ == '__main__':
    cli()
