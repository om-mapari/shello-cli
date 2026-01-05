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
from shello_cli.settings import SettingsManager
from shello_cli.api.client_factory import create_client
from shello_cli.commands.command_detector import CommandDetector, InputType
from shello_cli.commands.direct_executor import DirectExecutor
from shello_cli.commands.context_manager import ContextManager
from shello_cli.tools.bash_tool import BashTool
import shello_cli as version_module


def create_new_session(settings_manager, provider=None):
    """Create a new ShelloAgent and chat session.
    
    This function uses the client factory to create the appropriate client
    based on the configured provider (OpenAI or Bedrock), then creates an
    agent with that client using dependency injection.
    
    Args:
        settings_manager: The settings manager instance containing provider configuration
        provider: Optional provider override (for switching providers)
    
    Returns:
        Tuple of (agent, chat_session) ready for use
    
    Raises:
        SystemExit: If client creation fails due to missing configuration or errors
    """
    # Use factory to create client based on provider configuration
    try:
        client = create_client(settings_manager, provider=provider)
    except ValueError as e:
        # Configuration error - display helpful message
        console.print(f"✗ [red]{str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        # Unexpected error - display error and suggest setup
        console.print(f"✗ [red]Failed to create client: {str(e)}[/red]")
        console.print("💡 [yellow]Run 'shello setup' to configure your provider.[/yellow]")
        sys.exit(1)
    
    # Create agent with client (dependency injection)
    agent = ShelloAgent(client=client)
    chat_session = ChatSession(agent)
    return agent, chat_session


def switch_provider(settings_manager, agent, chat_session, context_manager, direct_executor):
    """Switch to a different provider during chat session.
    
    This function allows users to switch between configured providers (OpenAI and Bedrock)
    during an active chat session. It preserves conversation history and reconnects
    all components to the new agent.
    
    Args:
        settings_manager: The settings manager instance
        agent: Current agent instance
        chat_session: Current chat session
        context_manager: Context manager instance
        direct_executor: Direct executor instance
    
    Returns:
        Tuple of (new_agent, new_chat_session) if switch succeeds, or (None, None) if cancelled/failed
    """
    # Get available providers
    available_providers = settings_manager.get_available_providers()
    current_provider = settings_manager.get_provider()
    
    # Check if we have multiple providers configured
    if len(available_providers) < 2:
        console.print("\n⚠️  [yellow]Only one provider is configured.[/yellow]")
        console.print("💡 [cyan]Run 'shello setup' to configure additional providers.[/cyan]\n")
        return None, None
    
    # Display available providers with descriptive labels
    console.print("\n🔄 [bold]Switch Provider:[/bold]")
    provider_labels = {
        "openai": "OpenAI-compatible API",
        "bedrock": "AWS Bedrock"
    }
    
    for i, prov in enumerate(available_providers, 1):
        marker = "✓" if prov == current_provider else " "
        label = provider_labels.get(prov, prov.capitalize())
        console.print(f"  {i}. [{marker}] {label}")
    
    current_label = provider_labels.get(current_provider, current_provider)
    console.print(f"\n  Current: {current_label}")
    
    # Get user choice
    try:
        choice = click.prompt(
            "\nSelect provider (or 'c' to cancel)",
            type=str,
            default="c"
        )
        
        if choice.lower() == 'c':
            console.print("✗ [yellow]Provider switch cancelled.[/yellow]\n")
            return None, None
        
        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= len(available_providers):
            console.print("✗ [red]Invalid choice.[/red]\n")
            return None, None
        
        new_provider = available_providers[choice_idx]
        
        if new_provider == current_provider:
            console.print(f"✓ [green]Already using {new_provider}.[/green]\n")
            return None, None
        
    except (ValueError, click.Abort):
        console.print("\n✗ [yellow]Provider switch cancelled.[/yellow]\n")
        return None, None
    
    # Save conversation history before switching
    old_history = agent.get_chat_history()
    old_messages = agent._messages.copy()
    
    # Clear cache before switching
    agent.clear_cache()
    
    # Update settings to new provider
    settings_manager.set_provider(new_provider)
    
    # Create new session with new provider
    try:
        new_agent, new_chat_session = create_new_session(settings_manager)
        
        # Restore conversation history
        new_agent._chat_history = old_history
        new_agent._messages = old_messages
        
        # Reconnect direct executor to new agent's bash tool
        direct_executor.set_bash_tool(new_agent.get_bash_tool())
        
        # Get new model info
        new_model = new_agent.get_current_model()
        
        console.print(f"\n✓ [green]Switched to {new_provider}[/green]")
        console.print(f"  Model: [cyan]{new_model}[/cyan]")
        console.print(f"  Conversation history preserved\n")
        
        return new_agent, new_chat_session
        
    except Exception as e:
        console.print(f"\n✗ [red]Failed to switch provider: {str(e)}[/red]")
        console.print("⚠️  [yellow]Staying on current provider.[/yellow]\n")
        
        # Restore original provider in settings
        settings_manager.set_provider(current_provider)
        
        return None, None



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
@click.option("--yolo", is_flag=True, help="Enable YOLO mode (bypass approval checks)")
def chat(debug, new, yolo):
    """Start a chat session with AI"""
    # Get settings manager
    settings_manager = SettingsManager.get_instance()
    
    # Enable YOLO mode if flag is set
    if yolo:
        settings_manager.enable_yolo_mode_for_session()
        console.print("⚠️  [yellow]YOLO MODE ENABLED - Approval checks bypassed (denylist still active)[/yellow]\n")
    
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
            
            elif user_input.lower() == "/switch":
                # Switch provider
                result = switch_provider(
                    settings_manager, agent, chat_session,
                    context_manager, direct_executor
                )
                
                if result[0] is not None:
                    agent, chat_session = result
                
                continue
            
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
@click.option("--edit", is_flag=True, help="Open settings file in editor")
@click.option("--get", type=str, help="Get a specific setting value")
@click.option("--set", "set_key", type=str, help="Set a specific setting (use with value)")
@click.option("--value", type=str, help="Value to set (use with --set)")
@click.option("--reset", is_flag=True, help="Reset settings to defaults")
def config(edit, get, set_key, value, reset):
    """Show current configuration"""
    from shello_cli.commands.settings_commands import (
        config_edit,
        config_get,
        config_set,
        config_reset
    )
    
    # Handle --edit flag
    if edit:
        config_edit()
        return
    
    # Handle --get flag
    if get:
        config_get(get)
        return
    
    # Handle --set flag
    if set_key:
        if value is None:
            console.print("✗ [red]Error: --set requires --value[/red]")
            console.print("Usage: shello config --set <key> --value <value>")
            sys.exit(1)
        config_set(set_key, value)
        return
    
    # Handle --reset flag
    if reset:
        config_reset()
        return
    
    # Default: show current configuration
    settings_manager = SettingsManager.get_instance()
    user_settings = settings_manager.load_user_settings()
    project_settings = settings_manager.load_project_settings()
    
    # Get current provider
    current_provider = settings_manager.get_provider()
    
    # Provider labels for display
    provider_labels = {
        "openai": "OpenAI-compatible API",
        "bedrock": "AWS Bedrock"
    }
    
    console.print("\n📋 [bold blue]Current Configuration:[/bold blue]")
    console.print()
    
    # Display current provider with descriptive label
    provider_label = provider_labels.get(current_provider, current_provider.capitalize())
    console.print(f"  🤖 [bold]Provider:[/bold] {provider_label}")
    console.print()
    
    # Display provider-specific configuration
    if current_provider == "openai":
        # OpenAI-compatible API configuration
        try:
            config = settings_manager.get_provider_config("openai")
            
            # Display API key (masked)
            api_key = config.get("api_key")
            if api_key:
                masked_key = '***' + api_key[-4:] if len(api_key) >= 4 else '***'
                console.print(f"  🔑 [bold]API Key:[/bold] {masked_key}")
            else:
                console.print(f"  🔑 [bold]API Key:[/bold] [red]Not set[/red]")
            
            # Display base URL
            base_url = config.get("base_url", "https://api.openai.com/v1")
            console.print(f"  📡 [bold]Base URL:[/bold] {base_url}")
            
        except ValueError as e:
            console.print(f"  [red]Configuration error: {e}[/red]")
    
    elif current_provider == "bedrock":
        # AWS Bedrock configuration
        try:
            config = settings_manager.get_provider_config("bedrock")
            
            # Display AWS region
            region = config.get("region", "Not set")
            console.print(f"  🌍 [bold]AWS Region:[/bold] {region}")
            
            # Display credential method
            profile = config.get("profile")
            access_key = config.get("access_key")
            
            if profile:
                console.print(f"  🔐 [bold]Credentials:[/bold] AWS Profile ({profile})")
            elif access_key:
                # Mask access key
                masked_key = access_key[:4] + '***' + access_key[-4:] if len(access_key) >= 8 else '***'
                console.print(f"  🔐 [bold]Credentials:[/bold] Explicit credentials ({masked_key})")
            else:
                console.print(f"  🔐 [bold]Credentials:[/bold] Default credential chain")
            
        except ValueError as e:
            console.print(f"  [red]Configuration error: {e}[/red]")
    
    console.print()
    
    # Display current model
    current_model = settings_manager.get_current_model()
    console.print(f"  🎯 [bold]Current Model:[/bold] {current_model}")
    
    # Display available models for current provider
    try:
        config = settings_manager.get_provider_config(current_provider)
        models = config.get("models", [])
        if models:
            console.print(f"  📚 [bold]Available Models:[/bold]")
            for model in models:
                marker = "✓" if model == current_model else " "
                console.print(f"     [{marker}] {model}")
        else:
            console.print(f"  📚 [bold]Available Models:[/bold] [dim]None configured[/dim]")
    except ValueError:
        console.print(f"  📚 [bold]Available Models:[/bold] [dim]None configured[/dim]")
    
    # Display project-level overrides if present
    if project_settings.model:
        console.print()
        console.print(f"  ⚙️  [bold]Project Override:[/bold]")
        console.print(f"     Model: {project_settings.model}")
    
    # Display configured alternate providers
    available_providers = settings_manager.get_available_providers()
    if len(available_providers) > 1:
        console.print()
        console.print(f"  🔄 [bold]Alternate Providers:[/bold]")
        for provider in available_providers:
            if provider != current_provider:
                label = provider_labels.get(provider, provider.capitalize())
                console.print(f"     • {label}")
        console.print(f"     [dim]Use '/switch' during chat to switch providers[/dim]")
    
    console.print()


@cli.command()
def setup():
    """Interactive setup wizard for first-time configuration"""
    from shello_cli.settings import UserSettings
    from shello_cli.commands.settings_commands import setup_openai_provider, setup_bedrock_provider
    from pathlib import Path
    
    settings_manager = SettingsManager.get_instance()
    user_settings_path = Path.home() / ".shello_cli" / "user-settings.yml"
    
    console.print("\n🌊 [bold cyan]Welcome to Shello CLI Setup![/bold cyan]\n")
    
    # Check if settings already exist
    existing_settings = None
    if user_settings_path.exists():
        console.print("⚠ [yellow]Settings file already exists.[/yellow]")
        overwrite = click.confirm("Do you want to reconfigure?", default=False)
        if not overwrite:
            console.print("✓ [green]Setup cancelled. Use 'shello config' to view current settings.[/green]\n")
            return
        console.print()
        # Load existing settings to preserve other provider config
        try:
            existing_settings = settings_manager.load_user_settings()
        except:
            existing_settings = None
    
    # Provider selection
    console.print("🤖 [bold]Select AI Provider:[/bold]")
    console.print("  1. OpenAI-compatible API (OpenAI, OpenRouter, custom)")
    console.print("  2. AWS Bedrock (Claude, Nova, etc.)")
    
    provider_choice = click.prompt("\nChoose provider", type=click.IntRange(1, 2), default=1)
    
    if provider_choice == 1:
        # OpenAI-compatible setup flow
        provider = "openai"
        openai_config, bedrock_config = setup_openai_provider(existing_settings)
    else:
        # AWS Bedrock setup flow
        provider = "bedrock"
        openai_config, bedrock_config = setup_bedrock_provider(existing_settings)
    
    # Save configuration
    console.print("\n💾 [bold]Saving configuration...[/bold]")
    
    new_settings = UserSettings(
        provider=provider,
        openai_config=openai_config,
        bedrock_config=bedrock_config,
        # Preserve output_management and command_trust if they exist
        output_management=existing_settings.output_management if existing_settings else None,
        command_trust=existing_settings.command_trust if existing_settings else None
    )
    
    try:
        settings_manager.save_user_settings(new_settings)
        console.print("✓ [green]Configuration saved successfully![/green]")
        console.print(f"  Location: [dim]{user_settings_path}[/dim]")
        
        # Offer to configure alternate provider
        console.print()
        configure_alternate = click.confirm(
            "Would you like to configure an alternate provider for easy switching?",
            default=False
        )
        
        if configure_alternate:
            console.print()
            if provider == "openai":
                # Configure Bedrock as alternate
                console.print("☁️  [bold]Configuring AWS Bedrock as alternate provider...[/bold]\n")
                _, bedrock_config = setup_bedrock_provider(None)
                new_settings.bedrock_config = bedrock_config
            else:
                # Configure OpenAI as alternate
                console.print("📡 [bold]Configuring OpenAI-compatible API as alternate provider...[/bold]\n")
                openai_config, _ = setup_openai_provider(None)
                new_settings.openai_config = openai_config
            
            # Save updated settings with both providers
            settings_manager.save_user_settings(new_settings)
            console.print("✓ [green]Alternate provider configured![/green]")
            console.print("💡 [cyan]Use '/switch' during chat to switch between providers.[/cyan]")
        
        console.print("\n🚀 [bold green]Setup complete! You can now run 'shello' to start chatting.[/bold green]\n")
    except Exception as e:
        console.print(f"✗ [red]Failed to save settings: {str(e)}[/red]\n")
        sys.exit(1)


if __name__ == '__main__':
    cli()
