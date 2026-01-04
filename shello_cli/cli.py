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
    display_about,
    render_direct_command_output
)
from shello_cli.ui.user_input import get_user_input_with_clear
from shello_cli.utils.settings_manager import SettingsManager
from shello_cli.commands.command_detector import CommandDetector, InputType
from shello_cli.commands.direct_executor import DirectExecutor
from shello_cli.commands.context_manager import ContextManager
from shello_cli.tools.bash_tool import BashTool
import shello_cli as version_module


def create_new_session(settings_manager):
    """Create a new ShelloAgent and chat session"""
    api_key = settings_manager.get_api_key()
    if not api_key:
        console.print("✗ [red]No API key found.[/red]")
        console.print("💡 [yellow]Run 'shello setup' to configure your API key.[/yellow]")
        console.print("   Or set OPENAI_API_KEY environment variable.\n")
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
        
        # Get hostname for display
        import socket
        hostname = socket.gethostname()
    except Exception as e:
        console.print(f"✗ [red]Failed to initialize agent: {str(e)}[/red]")
        console.print("⚠ [yellow]Please check your API key and settings[/yellow]")
        sys.exit(1)
    
    # Initialize command detection and execution components
    command_detector = CommandDetector()
    direct_executor = DirectExecutor()
    context_manager = ContextManager()
    
    # Connect direct executor to agent's bash tool for shared caching
    direct_executor.set_bash_tool(agent.get_bash_tool())
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Display welcome banner (pass None for user_info since we don't have GitLab user)
    print_welcome_banner(None, getattr(version_module, '__version__', '0.1.0'))
    
    # Main chat loop
    while True:
        try:
            # Get current directory for prompt
            current_directory = direct_executor.get_current_directory()
            user_input = get_user_input_with_clear(name, current_directory)
            
            if user_input is None:  # Handle Ctrl+C or Ctrl+D
                console.print("\n\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break
            
            # Check for commands
            if user_input.lower() in ["/quit", "/exit"]:
                console.print("\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break
            
            elif user_input.lower() == "/new":
                # Clear cache before creating new session
                agent.clear_cache()
                
                # Create completely new session
                agent, chat_session = create_new_session(settings_manager)
                context_manager.clear_history()
                
                # Reconnect direct executor to new agent's bash tool
                direct_executor.set_bash_tool(agent.get_bash_tool())
                
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
            
            # Detect if input is a direct command or AI query
            detection_result = command_detector.detect(user_input)
            
            if detection_result.input_type == InputType.DIRECT_COMMAND:
                # Execute command directly without AI
                execution_result = direct_executor.execute(
                    detection_result.command,
                    detection_result.args
                )
                
                # Render command header
                console.print()
                render_direct_command_output(
                    command=user_input,
                    cwd=current_directory,
                    user=name,
                    hostname=hostname
                )
                
                # Display output
                if execution_result.success:
                    if execution_result.output:
                        console.print(execution_result.output)
                else:
                    if execution_result.error:
                        console.print(f"[red]{execution_result.error}[/red]")
                
                console.print()  # Add spacing after output
                
                # Record command in context for AI awareness
                context_manager.record_command(
                    command=user_input,
                    output=execution_result.output,
                    success=execution_result.success,
                    directory=current_directory,
                    cache_id=execution_result.cache_id  # Include cache_id
                )
            else:
                # Route to AI processing
                # Include context from direct commands if any
                ai_context = context_manager.get_context_for_ai()
                
                # Prepend context to user message if available
                if ai_context:
                    enhanced_input = f"{ai_context}\n\nUser query: {user_input}"
                else:
                    enhanced_input = user_input
                
                # Start or continue conversation
                if not chat_session.conversation_started:
                    chat_session.start_conversation(enhanced_input)
                else:
                    chat_session.continue_conversation(enhanced_input)
        
        except KeyboardInterrupt:
            # Clear cache on Ctrl+C
            agent.clear_cache()
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


@cli.command()
def setup():
    """Interactive setup wizard for first-time configuration"""
    from shello_cli.utils.settings_manager import UserSettings
    from pathlib import Path
    
    settings_manager = SettingsManager.get_instance()
    user_settings_path = Path.home() / ".shello_cli" / "user-settings.json"
    
    console.print("\n🌊 [bold cyan]Welcome to Shello CLI Setup![/bold cyan]\n")
    
    # Check if settings already exist
    if user_settings_path.exists():
        console.print("⚠ [yellow]Settings file already exists.[/yellow]")
        overwrite = click.confirm("Do you want to reconfigure?", default=False)
        if not overwrite:
            console.print("✓ [green]Setup cancelled. Use 'shello config' to view current settings.[/green]\n")
            return
        console.print()
    
    # API Provider selection
    console.print("📡 [bold]Select API Provider:[/bold]")
    console.print("  1. OpenAI (https://api.openai.com/v1)")
    console.print("  2. OpenRouter (https://openrouter.ai/api/v1)")
    console.print("  3. Custom URL")
    
    provider_choice = click.prompt("\nChoose provider", type=click.IntRange(1, 3), default=1)
    
    if provider_choice == 1:
        base_url = "https://api.openai.com/v1"
        default_model = "gpt-4o"
        models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    elif provider_choice == 2:
        base_url = "https://openrouter.ai/api/v1"
        default_model = "mistralai/devstral-2512:free"
        models = ["mistralai/devstral-2512:free", "gpt-4o", "gpt-4o-mini"]
    else:
        base_url = click.prompt("Enter custom API base URL", type=str)
        default_model = click.prompt("Enter default model name", type=str)
        models = [default_model]
    
    console.print(f"\n✓ Base URL: [cyan]{base_url}[/cyan]")
    
    # API Key
    console.print("\n🔑 [bold]API Key Configuration:[/bold]")
    api_key = click.prompt("Enter your API key", type=str, hide_input=True)
    
    if not api_key or len(api_key) < 10:
        console.print("✗ [red]Invalid API key. Setup cancelled.[/red]\n")
        return
    
    console.print("✓ API key received")
    
    # Model selection
    console.print(f"\n🤖 [bold]Default Model:[/bold]")
    console.print(f"  Suggested: {default_model}")
    use_default = click.confirm("Use suggested model?", default=True)
    
    if not use_default:
        default_model = click.prompt("Enter model name", type=str, default=default_model)
    
    console.print(f"✓ Default model: [cyan]{default_model}[/cyan]")
    
    # Save settings
    console.print("\n💾 [bold]Saving configuration...[/bold]")
    
    new_settings = UserSettings(
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        models=models
    )
    
    try:
        settings_manager.save_user_settings(new_settings)
        console.print("✓ [green]Configuration saved successfully![/green]")
        console.print(f"  Location: [dim]{user_settings_path}[/dim]")
        console.print("\n🚀 [bold green]Setup complete! You can now run 'shello' to start chatting.[/bold green]\n")
    except Exception as e:
        console.print(f"✗ [red]Failed to save settings: {str(e)}[/red]\n")
        sys.exit(1)


if __name__ == '__main__':
    cli()
