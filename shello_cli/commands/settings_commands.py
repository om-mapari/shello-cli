"""
Settings-related CLI commands (setup, config).

This module contains the implementation of setup and config commands,
keeping cli.py clean and focused on routing.
"""

import click
import os
import sys
import subprocess
from pathlib import Path
from shello_cli.settings import SettingsManager, UserSettings, ProviderConfig
from shello_cli.ui.ui_renderer import console


def config_edit():
    """Open settings file in the default editor.
    
    Uses $EDITOR environment variable or falls back to platform defaults.
    
    Requirements: 15.2
    """
    settings_manager = SettingsManager.get_instance()
    settings_path = Path.home() / ".shello_cli" / "user-settings.yml"
    
    # Create settings file if it doesn't exist
    if not settings_path.exists():
        console.print("⚠ [yellow]Settings file doesn't exist. Creating default settings...[/yellow]")
        user_settings = settings_manager.load_user_settings()
        settings_manager.save_user_settings(user_settings)
        console.print(f"✓ [green]Created settings file at {settings_path}[/green]\n")
    
    # Get editor from environment or use platform default
    editor = os.environ.get('EDITOR')
    
    if editor:
        # Use user's preferred editor
        try:
            subprocess.run([editor, str(settings_path)], check=True)
            console.print("\n✓ [green]Settings file closed. Changes will take effect on next run.[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"✗ [red]Failed to open editor: {e}[/red]")
            sys.exit(1)
        except FileNotFoundError:
            console.print(f"✗ [red]Editor '{editor}' not found. Please check your $EDITOR environment variable.[/red]")
            sys.exit(1)
    else:
        # Use platform default
        try:
            if sys.platform == 'win32':
                os.startfile(str(settings_path))
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(settings_path)], check=True)
            else:
                # Linux - try common editors
                for editor_cmd in ['xdg-open', 'nano', 'vim', 'vi']:
                    try:
                        subprocess.run([editor_cmd, str(settings_path)], check=True)
                        break
                    except FileNotFoundError:
                        continue
                else:
                    console.print("✗ [red]No suitable editor found. Please set the $EDITOR environment variable.[/red]")
                    sys.exit(1)
            
            console.print("\n✓ [green]Settings file opened. Changes will take effect on next run.[/green]")
        except Exception as e:
            console.print(f"✗ [red]Failed to open settings file: {e}[/red]")
            sys.exit(1)


def config_get(key: str):
    """Get a specific setting value using dot notation.
    
    Args:
        key: Setting key in dot notation (e.g., "provider", "openai_config.api_key")
        
    Requirements: 15.4
    """
    settings_manager = SettingsManager.get_instance()
    user_settings = settings_manager.load_user_settings()
    
    # Parse dot notation
    parts = key.split('.')
    value = user_settings
    
    try:
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                console.print(f"✗ [red]Setting '{key}' not found[/red]")
                sys.exit(1)
        
        # Mask sensitive values
        if 'key' in key.lower() or 'secret' in key.lower():
            if value and isinstance(value, str) and len(value) >= 4:
                value = '***' + value[-4:]
            else:
                value = '***'
        
        console.print(f"\n📋 [bold]{key}:[/bold] {value}\n")
    
    except Exception as e:
        console.print(f"✗ [red]Error getting setting: {e}[/red]")
        sys.exit(1)


def config_set(key: str, value: str):
    """Set a specific setting value using dot notation.
    
    Args:
        key: Setting key in dot notation (e.g., "provider", "openai_config.default_model")
        value: Value to set
        
    Requirements: 15.3
    """
    settings_manager = SettingsManager.get_instance()
    user_settings = settings_manager.load_user_settings()
    
    # Parse dot notation
    parts = key.split('.')
    
    # Special handling for top-level provider
    if key == "provider":
        valid_providers = ["openai", "bedrock", "gemini", "vertex"]
        if value not in valid_providers:
            console.print(f"✗ [red]Invalid provider: {value}[/red]")
            console.print(f"Valid providers: {', '.join(valid_providers)}")
            sys.exit(1)
        
        user_settings.provider = value
        settings_manager.save_user_settings(user_settings)
        console.print(f"\n✓ [green]Set {key} = {value}[/green]\n")
        return
    
    # Handle nested settings
    if len(parts) < 2:
        console.print(f"✗ [red]Invalid key format. Use dot notation (e.g., openai_config.default_model)[/red]")
        sys.exit(1)
    
    # Navigate to parent object
    obj = user_settings
    for part in parts[:-1]:
        if not hasattr(obj, part):
            console.print(f"✗ [red]Setting '{key}' not found[/red]")
            sys.exit(1)
        obj = getattr(obj, part)
        
        # If the nested object is None, we need to create it
        if obj is None:
            console.print(f"✗ [red]Cannot set '{key}' because parent object is not configured[/red]")
            console.print(f"💡 Run 'shello setup' to configure the provider first")
            sys.exit(1)
    
    # Set the final attribute
    final_key = parts[-1]
    if not hasattr(obj, final_key):
        console.print(f"✗ [red]Setting '{key}' not found[/red]")
        sys.exit(1)
    
    # Type conversion based on current value type
    current_value = getattr(obj, final_key)
    try:
        if isinstance(current_value, bool):
            # Convert string to boolean
            if value.lower() in ['true', '1', 'yes', 'on']:
                typed_value = True
            elif value.lower() in ['false', '0', 'no', 'off']:
                typed_value = False
            else:
                console.print(f"✗ [red]Invalid boolean value: {value}[/red]")
                sys.exit(1)
        elif isinstance(current_value, int):
            typed_value = int(value)
        elif isinstance(current_value, float):
            typed_value = float(value)
        elif isinstance(current_value, list):
            # Parse comma-separated list
            typed_value = [v.strip() for v in value.split(',')]
        else:
            # String or None
            typed_value = value
    except ValueError as e:
        console.print(f"✗ [red]Invalid value type: {e}[/red]")
        sys.exit(1)
    
    # Set the value
    setattr(obj, final_key, typed_value)
    
    # Save settings
    settings_manager.save_user_settings(user_settings)
    
    # Display confirmation (mask sensitive values)
    display_value = value
    if 'key' in key.lower() or 'secret' in key.lower():
        if len(value) >= 4:
            display_value = '***' + value[-4:]
        else:
            display_value = '***'
    
    console.print(f"\n✓ [green]Set {key} = {display_value}[/green]\n")


def config_reset():
    """Reset settings to defaults with confirmation.
    
    Requirements: 15.5
    """
    settings_manager = SettingsManager.get_instance()
    settings_path = Path.home() / ".shello_cli" / "user-settings.yml"
    
    console.print("\n⚠ [yellow bold]Warning: This will reset all settings to defaults![/yellow bold]")
    console.print("Your current configuration will be lost.\n")
    
    # Confirm with user
    confirmed = click.confirm("Are you sure you want to reset settings?", default=False)
    
    if not confirmed:
        console.print("✗ [yellow]Reset cancelled.[/yellow]\n")
        return
    
    # Delete settings file
    if settings_path.exists():
        settings_path.unlink()
        console.print(f"✓ [green]Settings file deleted: {settings_path}[/green]")
    
    # Clear cached settings
    settings_manager._user_settings = None
    
    console.print("✓ [green]Settings reset to defaults.[/green]")
    console.print("💡 [cyan]Run 'shello setup' to configure your provider.[/cyan]\n")


def setup_openai_provider(existing_settings):
    """Setup OpenAI-compatible provider configuration.
    
    Args:
        existing_settings: Existing UserSettings to preserve other provider config
        
    Returns:
        Tuple of (openai_config, bedrock_config) where bedrock_config is preserved from existing
    """
    console.print("\n📡 [bold]OpenAI-compatible API Setup:[/bold]")
    console.print("  1. OpenAI (https://api.openai.com/v1)")
    console.print("  2. OpenRouter (https://openrouter.ai/api/v1)")
    console.print("  3. Custom URL")
    
    api_choice = click.prompt("\nChoose API", type=click.IntRange(1, 3), default=1)
    
    if api_choice == 1:
        base_url = "https://api.openai.com/v1"
        default_model = "gpt-4o"
        models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    elif api_choice == 2:
        base_url = "https://openrouter.ai/api/v1"
        default_model = "anthropic/claude-3.5-sonnet"
        models = ["anthropic/claude-3.5-sonnet", "anthropic/claude-3-opus", "gpt-4o"]
    else:
        base_url = click.prompt("Enter custom API base URL", type=str)
        default_model = click.prompt("Enter default model name", type=str)
        models = [default_model]
    
    console.print(f"\n✓ Base URL: [cyan]{base_url}[/cyan]")
    
    # API Key
    console.print("\n🔑 [bold]API Key:[/bold]")
    api_key = click.prompt("Enter your API key", type=str, hide_input=True)
    
    if not api_key or len(api_key) < 10:
        console.print("✗ [red]Invalid API key. Setup cancelled.[/red]\n")
        import sys
        sys.exit(1)
    
    # Model selection
    console.print(f"\n🤖 [bold]Default Model:[/bold]")
    console.print(f"  Suggested: {default_model}")
    use_default = click.confirm("Use suggested model?", default=True)
    
    if not use_default:
        default_model = click.prompt("Enter model name", type=str, default=default_model)
    
    # Create OpenAI config
    openai_config = ProviderConfig(
        provider_type="openai",
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        models=models
    )
    
    # Preserve existing Bedrock config if present
    bedrock_config = existing_settings.bedrock_config if existing_settings else None
    
    return openai_config, bedrock_config


def setup_bedrock_provider(existing_settings):
    """Setup AWS Bedrock provider configuration.
    
    Args:
        existing_settings: Existing UserSettings to preserve other provider config
        
    Returns:
        Tuple of (openai_config, bedrock_config) where openai_config is preserved from existing
    """
    console.print("\n☁️  [bold]AWS Bedrock Setup:[/bold]")
    
    # Region
    console.print("\n🌍 [bold]AWS Region:[/bold]")
    aws_region = click.prompt("Enter AWS region", type=str, default="us-east-1")
    
    # Credential method
    console.print("\n🔐 [bold]AWS Credentials:[/bold]")
    console.print("  1. AWS Profile (recommended)")
    console.print("  2. Explicit credentials (access key + secret key)")
    console.print("  3. Default credential chain (environment/IAM)")
    
    cred_choice = click.prompt("\nChoose credential method", type=click.IntRange(1, 3), default=1)
    
    aws_profile = None
    aws_access_key = None
    aws_secret_key = None
    
    if cred_choice == 1:
        aws_profile = click.prompt("Enter AWS profile name", type=str, default="default")
        console.print(f"✓ Using AWS profile: [cyan]{aws_profile}[/cyan]")
    elif cred_choice == 2:
        aws_access_key = click.prompt("Enter AWS access key", type=str)
        aws_secret_key = click.prompt("Enter AWS secret key", type=str, hide_input=True)
        console.print("✓ Using explicit credentials")
    else:
        console.print("✓ Using default credential chain")
    
    # Model selection
    console.print("\n🤖 [bold]Default Model:[/bold]")
    console.print("  Suggested: anthropic.claude-3-5-sonnet-20241022-v2:0")
    default_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    models = [
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "amazon.nova-pro-v1:0",
        "amazon.nova-lite-v1:0"
    ]
    
    use_default = click.confirm("Use suggested model?", default=True)
    
    if not use_default:
        default_model = click.prompt("Enter Bedrock model ID", type=str, default=default_model)
    
    # Create Bedrock config
    bedrock_config = ProviderConfig(
        provider_type="bedrock",
        aws_region=aws_region,
        aws_profile=aws_profile,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        default_model=default_model,
        models=models
    )
    
    # Preserve existing OpenAI config if present
    openai_config = existing_settings.openai_config if existing_settings else None
    
    return openai_config, bedrock_config
