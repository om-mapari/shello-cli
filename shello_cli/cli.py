"""Command-line interface for Shello CLI"""
import click
import os
import sys
from pathlib import Path
from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
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

# Session store path
_SESSION_STORE = Path.home() / ".shello_cli" / "sessions"


def _interactive_pick(title: str, items: list[str], current: str | None = None) -> str | None:
    """Arrow-key interactive picker. Returns selected item or None if cancelled."""
    state = {"selected": 0, "result": None}

    # Pre-select the current item if present
    if current and current in items:
        state["selected"] = items.index(current)

    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        state["selected"] = (state["selected"] - 1) % len(items)

    @kb.add("down")
    def _down(event):
        state["selected"] = (state["selected"] + 1) % len(items)

    @kb.add("enter")
    def _enter(event):
        state["result"] = items[state["selected"]]
        event.app.exit()

    @kb.add("escape")
    @kb.add("c-c")
    def _cancel(event):
        event.app.exit()

    def _get_content():
        lines = [("class:title", f" {title}\n\n")]
        for i, item in enumerate(items):
            marker = "✓ " if item == current else "  "
            if i == state["selected"]:
                lines.append(("class:selected", f" > {marker}{item}\n"))
            else:
                lines.append(("", f"   {marker}{item}\n"))
        lines.append(("class:hint", "\n ↑/↓ navigate  Enter select  Esc cancel\n"))
        return FormattedText(lines)

    layout = Layout(HSplit([
        Window(content=FormattedTextControl(text=_get_content, focusable=True), wrap_lines=False)
    ]))

    style = Style.from_dict({
        "selected": "reverse bold",
        "title": "bold cyan",
        "hint": "ansidarkgray",
    })

    Application(layout=layout, key_bindings=kb, style=style, full_screen=False, mouse_support=False).run()
    return state["result"]


def _get_session_config(settings_manager):
    """Return (enabled, max_storage_mb) from user settings."""
    try:
        user_settings = settings_manager.load_user_settings()
        cfg = user_settings.session_history
        if cfg is not None:
            return cfg.enabled, cfg.max_storage_mb
    except Exception:
        pass
    return True, 50


def _make_recorder(settings_manager, provider: str, model: str):
    """Create a SessionRecorder if session history is enabled, else return None."""
    enabled, max_mb = _get_session_config(settings_manager)
    if not enabled:
        return None
    from shello_cli.session.recorder import SessionRecorder
    return SessionRecorder(_SESSION_STORE, provider=provider, model=model)


def _start_pruner_async(max_mb: int) -> None:
    """Run SessionPruner.prune() in a background thread (non-blocking)."""
    import threading
    from shello_cli.session.pruner import SessionPruner

    def _prune():
        try:
            pruner = SessionPruner(_SESSION_STORE, max_storage_mb=max_mb)
            pruner.prune()
        except Exception:
            pass

    t = threading.Thread(target=_prune, daemon=True)
    t.start()


def create_new_session(settings_manager, provider=None):
    """Create a new ShelloAgent and chat session."""
    try:
        client = create_client(settings_manager, provider=provider)
    except ValueError as e:
        console.print(f"✗ [red]{str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"✗ [red]Failed to create client: {str(e)}[/red]")
        console.print("💡 [yellow]Run 'shello setup' to configure your provider.[/yellow]")
        sys.exit(1)

    agent = ShelloAgent(client=client)
    chat_session = ChatSession(agent)
    return agent, chat_session


def switch_provider(settings_manager, agent, chat_session, context_manager, direct_executor):
    """Switch to a different provider during chat session."""
    available_providers = settings_manager.get_available_providers()
    current_provider = settings_manager.get_provider()

    if len(available_providers) < 2:
        console.print("\n⚠️  [yellow]Only one provider is configured.[/yellow]")
        console.print("💡 [cyan]Run 'shello setup' to configure additional providers.[/cyan]\n")
        return None, None

    provider_labels = {
        "openai": "OpenAI-compatible API",
        "bedrock": "AWS Bedrock"
    }
    labels = [provider_labels.get(p, p.capitalize()) for p in available_providers]
    current_label = provider_labels.get(current_provider, current_provider.capitalize())
    current_model = agent.get_current_model()

    console.print(f"\n🔄 [bold]Switch Provider[/bold]  [bright_black]current: {current_label} / {current_model}[/bright_black]\n")

    selected_label = _interactive_pick("Select a provider:", labels, current_label)

    if selected_label is None:
        console.print("✗ [yellow]Provider switch cancelled.[/yellow]\n")
        return None, None

    new_provider = available_providers[labels.index(selected_label)]

    if new_provider == current_provider:
        console.print(f"✓ [green]Already using {current_label}.[/green]\n")
        return None, None

    old_history = agent.get_chat_history()
    old_messages = agent._messages.copy()
    agent.clear_cache()
    settings_manager.set_provider(new_provider)

    try:
        new_agent, new_chat_session = create_new_session(settings_manager)
        new_agent._chat_history = old_history
        new_agent._messages = old_messages
        direct_executor.set_bash_tool(new_agent.get_bash_tool())
        new_model = new_agent.get_current_model()

        console.print(f"\n✓ [green]Switched to {selected_label}[/green]")
        console.print(f"  Model: [cyan]{new_model}[/cyan]")
        console.print(f"  Conversation history preserved\n")

        return new_agent, new_chat_session

    except Exception as e:
        console.print(f"\n✗ [red]Failed to switch provider: {str(e)}[/red]")
        console.print("⚠️  [yellow]Staying on current provider.[/yellow]\n")
        settings_manager.set_provider(current_provider)
        return None, None


def switch_model(settings_manager, agent):
    """Switch the active model within the current provider (session-scoped)."""
    current_provider = settings_manager.get_provider()
    current_model = agent.get_current_model()

    try:
        provider_config = settings_manager.get_provider_config(current_provider)
        available_models = provider_config.get("models", [])
    except (ValueError, KeyError):
        available_models = []

    if not available_models or (len(available_models) == 1 and available_models[0] == current_model):
        console.print("⚠️  [yellow]No additional models available. Configure models in your settings.[/yellow]\n")
        return

    console.print(f"\n🔄 [bold]Switch Model[/bold]  [bright_black]provider: {current_provider} / current: {current_model}[/bright_black]\n")

    selected_model = _interactive_pick("Select a model:", available_models, current_model)

    if selected_model is None:
        console.print("✗ [yellow]Model switch cancelled.[/yellow]\n")
        return

    if selected_model == current_model:
        console.print(f"✓ [green]Already using {selected_model}.[/green]\n")
        return

    agent.set_model(selected_model)
    console.print(f"\n✓ [green]Switched to model:[/green] [cyan]{selected_model}[/cyan]\n")


def handle_history_command(
    user_input: str,
    settings_manager,
    agent,
    chat_session,
    recorder,
    direct_executor,
    name: str,
):
    """Handle /history, /history clear, /history delete commands.

    Returns the (possibly new) recorder after any resume operation.
    """
    from shello_cli.session.picker import SessionPicker
    from shello_cli.session.viewer import SessionViewer
    from shello_cli.session.restorer import SessionRestorer
    from shello_cli.session.pruner import SessionPruner
    from shello_cli.session.models import SessionEntry
    from datetime import datetime, timezone

    parts = user_input.strip().split()
    subcommand = parts[1].lower() if len(parts) > 1 else ""

    # /history clear
    if subcommand == "clear":
        confirm = click.confirm(
            "\n⚠️  Delete ALL session history? This cannot be undone",
            default=False
        )
        if confirm:
            pruner = SessionPruner(_SESSION_STORE)
            count = pruner.clear_all()
            console.print(f"✓ [green]Deleted {count} session(s).[/green]\n")
        else:
            console.print("✗ [yellow]Cancelled.[/yellow]\n")
        return recorder

    # /history delete
    if subcommand == "delete":
        picker = SessionPicker(_SESSION_STORE)
        session_id = picker.pick()
        if session_id is None:
            console.print("\n✗ [yellow]No session selected.[/yellow]\n")
            return recorder
        confirm = click.confirm(
            f"\n⚠️  Delete session {session_id}?",
            default=False
        )
        if confirm:
            pruner = SessionPruner(_SESSION_STORE)
            if pruner.delete_session(session_id):
                console.print(f"✓ [green]Session deleted.[/green]\n")
            else:
                console.print("✗ [red]Session not found.[/red]\n")
        else:
            console.print("✗ [yellow]Cancelled.[/yellow]\n")
        return recorder

    # /history (no args) — browse and optionally resume
    picker = SessionPicker(_SESSION_STORE)
    session_id = picker.pick()
    if session_id is None:
        console.print("\n✗ [yellow]No session selected.[/yellow]\n")
        return recorder

    # Load index to get metadata for the selected session
    from shello_cli.session.serializer import SessionSerializer
    index_path = _SESSION_STORE / "index.json"
    original_meta = None
    if index_path.exists():
        try:
            idx = SessionSerializer.deserialize_index(index_path.read_text(encoding="utf-8"))
            original_meta = idx.sessions.get(session_id)
        except Exception:
            pass

    # Display summary header
    console.print()
    if original_meta:
        start_str = original_meta.start_time.strftime("%Y-%m-%d %H:%M:%S")
        console.print(
            f"[bold cyan]── Session from {start_str} "
            f"│ {original_meta.entry_count} entries "
            f"│ {original_meta.provider}/{original_meta.model} ──[/bold cyan]"
        )
    console.print()

    viewer = SessionViewer(_SESSION_STORE)
    has_state = viewer.render(session_id)

    console.print()

    if not has_state:
        console.print(
            "[yellow]⚠ This session has no conversation state — "
            "it can be viewed but not resumed.[/yellow]\n"
        )
        return recorder

    # Resume: restore conversation state into agent
    conversation_state = viewer.get_conversation_state(session_id)
    if conversation_state is None:
        console.print(
            "[yellow]⚠ Could not load conversation state.[/yellow]\n"
        )
        return recorder

    restorer = SessionRestorer()
    restorer.restore(agent, conversation_state, original_meta)
    chat_session.conversation_started = True

    # Finalize old recorder (if any) and reuse the original session file
    if recorder is not None:
        recorder.finalize()

    _, max_mb = _get_session_config(settings_manager)
    current_provider = settings_manager.get_provider()
    current_model = agent.get_current_model()
    resumed_recorder = _make_recorder(settings_manager, current_provider, current_model)

    if resumed_recorder is not None:
        # Resume into the original session file — append to it directly
        resumed_recorder.resume(session_id)
        # Record a session_resumed marker entry
        resumed_recorder.record(SessionEntry(
            entry_type="session_resumed",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            content="",
            metadata={"original_session_id": session_id},
        ))

    chat_session.set_recorder(resumed_recorder)
    console.print(
        "[green]✓ Conversation restored. Continue chatting below.[/green]\n"
    )
    return resumed_recorder


def version_callback(ctx, param, value):
    """Custom version display"""
    if not value or ctx.resilient_parsing:
        return

    version = getattr(version_module, '__version__', '0.1.0')
    try:
        click.echo(f"🌊 Shello CLI - Version: {version}")
    except UnicodeEncodeError:
        click.echo(f"Shello CLI - Version: {version}")

    ctx.exit()


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, callback=version_callback, expose_value=False, is_eager=True, help='Show version and exit')
@click.pass_context
def cli(ctx):
    """Shello CLI - AI Assistant with Command Execution"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@cli.command()
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--new", is_flag=True, help="Start a new conversation")
@click.option("--yolo", is_flag=True, help="Enable YOLO mode (bypass approval checks)")
def chat(debug, new, yolo):
    """Start a chat session with AI"""
    settings_manager = SettingsManager.get_instance()

    if yolo:
        settings_manager.enable_yolo_mode_for_session()
        console.print("⚠️  [yellow]YOLO MODE ENABLED - Approval checks bypassed (denylist still active)[/yellow]\n")

    try:
        agent, chat_session = create_new_session(settings_manager)
        name = os.environ.get('USER', os.environ.get('USERNAME', 'User'))
        import socket
        hostname = socket.gethostname()
    except Exception as e:
        console.print(f"✗ [red]Failed to initialize agent: {str(e)}[/red]")
        console.print("⚠ [yellow]Please check your API key and settings[/yellow]")
        sys.exit(1)

    command_detector = CommandDetector()
    direct_executor = DirectExecutor()
    context_manager = ContextManager()
    direct_executor.set_bash_tool(agent.get_bash_tool())

    os.system('cls' if os.name == 'nt' else 'clear')
    print_welcome_banner(None, getattr(version_module, '__version__', '0.1.0'))

    # --- Session recording setup ---
    enabled, max_mb = _get_session_config(settings_manager)
    recorder = None
    if enabled:
        current_provider = settings_manager.get_provider()
        current_model = agent.get_current_model()
        recorder = _make_recorder(settings_manager, current_provider, current_model)
        # Recorder starts lazily on first user message (no empty sessions created)
        # Kick off background pruning
        _start_pruner_async(max_mb)

    chat_session.set_recorder(recorder)
    # --- End session recording setup ---

    # Check for updates on startup
    user_settings = settings_manager.load_user_settings()
    if user_settings.update_config and user_settings.update_config.check_on_startup:
        from shello_cli.update.update_manager import UpdateManager
        update_manager = UpdateManager()
        check_result = update_manager.check_for_updates_async(timeout=2.0)
        if check_result and check_result.update_available:
            console.print(
                f"\n💡 [cyan]Update available:[/cyan] "
                f"[dim]{check_result.current_version}[/dim] → "
                f"[bold]{check_result.latest_version}[/bold]"
            )
            console.print("   Run [bold]/update[/bold] to upgrade\n")

    # Main chat loop
    while True:
        try:
            current_directory = direct_executor.get_current_directory()
            user_input = get_user_input_with_clear(name, current_directory)

            if user_input is None:  # Ctrl+C or Ctrl+D
                if recorder is not None:
                    recorder.finalize()
                console.print("\n\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break

            if user_input.lower() in ["/quit", "/exit"]:
                if recorder is not None:
                    recorder.finalize()
                console.print("\n👋 Goodbye! Thanks for using Shello CLI", style="yellow")
                break

            elif user_input.lower() == "/switch":
                result = switch_provider(
                    settings_manager, agent, chat_session,
                    context_manager, direct_executor
                )
                if result[0] is not None:
                    agent, chat_session = result
                continue

            elif user_input.lower() == "/model":
                switch_model(settings_manager, agent)
                continue

            elif user_input.lower() == "/new":
                # Finalize current recorder
                if recorder is not None:
                    recorder.finalize()

                agent.clear_cache()
                agent, chat_session = create_new_session(settings_manager)
                context_manager.clear_history()
                direct_executor.set_bash_tool(agent.get_bash_tool())

                # Start a fresh recorder for the new session (lazy — starts on first message)
                current_provider = settings_manager.get_provider()
                current_model = agent.get_current_model()
                recorder = _make_recorder(settings_manager, current_provider, current_model)
                chat_session.set_recorder(recorder)

                console.print("\n\n✓ [green]Starting new conversation...[/green]")
                print_header("New conversation started")
                continue

            elif user_input.lower().startswith("/history"):
                recorder = handle_history_command(
                    user_input, settings_manager, agent, chat_session,
                    recorder, direct_executor, name
                )
                continue

            elif user_input.lower() == "/help":
                display_help()
                continue

            elif user_input.lower() == "/about":
                display_about(getattr(version_module, '__version__', '0.1.0'))
                continue

            elif user_input.lower().startswith("/update"):
                from shello_cli.update.update_manager import UpdateManager
                force = "--force" in user_input.lower()
                update_manager = UpdateManager()
                console.print()
                result = update_manager.perform_update(force=force)
                if result.success:
                    console.print(f"✓ [green]{result.message}[/green]")
                    if result.new_version and "already on the latest version" not in result.message.lower():
                        console.print(f"  Updated to version [cyan]{result.new_version}[/cyan]")
                        console.print("\n⚠️  [yellow]Please restart Shello CLI to use the new version.[/yellow]\n")
                    else:
                        console.print()
                else:
                    console.print(f"✗ [red]{result.message}[/red]")
                    if result.error:
                        console.print(f"  Error: {result.error}\n")
                continue

            if not user_input.strip():
                continue

            detection_result = command_detector.detect(user_input)

            if detection_result.input_type == InputType.DIRECT_COMMAND:
                execution_result = direct_executor.execute(
                    detection_result.command,
                    detection_result.args
                )

                console.print()
                render_direct_command_output(
                    command=user_input,
                    cwd=current_directory,
                    user=name,
                    hostname=hostname
                )

                if execution_result.success:
                    if execution_result.output:
                        console.print(execution_result.output)
                else:
                    if execution_result.error:
                        console.print(f"[red]{execution_result.error}[/red]")

                console.print()

                # Record direct_command entry
                if recorder is not None and recorder.is_recording:
                    from shello_cli.session.models import SessionEntry
                    from datetime import datetime, timezone
                    recorder.record(SessionEntry(
                        entry_type="direct_command",
                        timestamp=datetime.now(timezone.utc),
                        sequence=0,
                        content=execution_result.output or execution_result.error or "",
                        metadata={
                            "command": user_input,
                            "cwd": current_directory,
                            "success": execution_result.success,
                        },
                    ))

                context_manager.record_command(
                    command=user_input,
                    output=execution_result.output,
                    success=execution_result.success,
                    directory=current_directory,
                    cache_id=execution_result.cache_id
                )
            else:
                ai_context = context_manager.get_context_for_ai()
                if ai_context:
                    enhanced_input = f"{ai_context}\n\nUser query: {user_input}"
                else:
                    enhanced_input = user_input

                if not chat_session.conversation_started:
                    chat_session.start_conversation(enhanced_input, raw_user_message=user_input)
                else:
                    chat_session.continue_conversation(user_input)

        except KeyboardInterrupt:
            agent.clear_cache()
            if recorder is not None:
                recorder.finalize()
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

    if edit:
        config_edit()
        return

    if get:
        config_get(get)
        return

    if set_key:
        if value is None:
            console.print("✗ [red]Error: --set requires --value[/red]")
            console.print("Usage: shello config --set <key> --value <value>")
            sys.exit(1)
        config_set(set_key, value)
        return

    if reset:
        config_reset()
        return

    settings_manager = SettingsManager.get_instance()
    user_settings = settings_manager.load_user_settings()
    project_settings = settings_manager.load_project_settings()
    current_provider = settings_manager.get_provider()

    provider_labels = {
        "openai": "OpenAI-compatible API",
        "bedrock": "AWS Bedrock"
    }

    console.print("\n📋 [bold blue]Current Configuration:[/bold blue]")
    console.print()

    provider_label = provider_labels.get(current_provider, current_provider.capitalize())
    console.print(f"  🤖 [bold]Provider:[/bold] {provider_label}")
    console.print()

    if current_provider == "openai":
        try:
            cfg = settings_manager.get_provider_config("openai")
            api_key = cfg.get("api_key")
            if api_key:
                masked_key = '***' + api_key[-4:] if len(api_key) >= 4 else '***'
                console.print(f"  🔑 [bold]API Key:[/bold] {masked_key}")
            else:
                console.print(f"  🔑 [bold]API Key:[/bold] [red]Not set[/red]")
            base_url = cfg.get("base_url", "https://api.openai.com/v1")
            console.print(f"  📡 [bold]Base URL:[/bold] {base_url}")
        except ValueError as e:
            console.print(f"  [red]Configuration error: {e}[/red]")

    elif current_provider == "bedrock":
        try:
            cfg = settings_manager.get_provider_config("bedrock")
            region = cfg.get("region", "Not set")
            console.print(f"  🌍 [bold]AWS Region:[/bold] {region}")
            profile = cfg.get("profile")
            access_key = cfg.get("access_key")
            if profile:
                console.print(f"  🔐 [bold]Credentials:[/bold] AWS Profile ({profile})")
            elif access_key:
                masked_key = access_key[:4] + '***' + access_key[-4:] if len(access_key) >= 8 else '***'
                console.print(f"  🔐 [bold]Credentials:[/bold] Explicit credentials ({masked_key})")
            else:
                console.print(f"  🔐 [bold]Credentials:[/bold] Default credential chain")
        except ValueError as e:
            console.print(f"  [red]Configuration error: {e}[/red]")

    console.print()

    current_model = settings_manager.get_current_model()
    console.print(f"  🎯 [bold]Current Model:[/bold] {current_model}")

    try:
        cfg = settings_manager.get_provider_config(current_provider)
        models = cfg.get("models", [])
        if models:
            console.print(f"  📚 [bold]Available Models:[/bold]")
            for model in models:
                marker = "✓" if model == current_model else " "
                console.print(f"     [{marker}] {model}")
        else:
            console.print(f"  📚 [bold]Available Models:[/bold] [dim]None configured[/dim]")
    except ValueError:
        console.print(f"  📚 [bold]Available Models:[/bold] [dim]None configured[/dim]")

    if project_settings.model:
        console.print()
        console.print(f"  ⚙️  [bold]Project Override:[/bold]")
        console.print(f"     Model: {project_settings.model}")

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

    existing_settings = None
    if user_settings_path.exists():
        console.print("⚠ [yellow]Settings file already exists.[/yellow]")
        overwrite = click.confirm("Do you want to reconfigure?", default=False)
        if not overwrite:
            console.print("✓ [green]Setup cancelled. Use 'shello config' to view current settings.[/green]\n")
            return
        console.print()
        try:
            existing_settings = settings_manager.load_user_settings()
        except Exception:
            existing_settings = None

    console.print("🤖 [bold]Select AI Provider:[/bold]")
    console.print("  1. OpenAI-compatible API (OpenAI, OpenRouter, custom)")
    console.print("  2. AWS Bedrock (Claude, Nova, etc.)")

    provider_choice = click.prompt("\nChoose provider", type=click.IntRange(1, 2), default=1)

    if provider_choice == 1:
        provider = "openai"
        openai_config, bedrock_config = setup_openai_provider(existing_settings)
    else:
        provider = "bedrock"
        openai_config, bedrock_config = setup_bedrock_provider(existing_settings)

    console.print("\n💾 [bold]Saving configuration...[/bold]")

    new_settings = UserSettings(
        provider=provider,
        openai_config=openai_config,
        bedrock_config=bedrock_config,
        output_management=existing_settings.output_management if existing_settings else None,
        command_trust=existing_settings.command_trust if existing_settings else None
    )

    try:
        settings_manager.save_user_settings(new_settings)
        console.print("✓ [green]Configuration saved successfully![/green]")
        console.print(f"  Location: [dim]{user_settings_path}[/dim]")

        console.print()
        configure_alternate = click.confirm(
            "Would you like to configure an alternate provider for easy switching?",
            default=False
        )

        if configure_alternate:
            console.print()
            if provider == "openai":
                console.print("☁️  [bold]Configuring AWS Bedrock as alternate provider...[/bold]\n")
                _, bedrock_config = setup_bedrock_provider(None)
                new_settings.bedrock_config = bedrock_config
            else:
                console.print("📡 [bold]Configuring OpenAI-compatible API as alternate provider...[/bold]\n")
                openai_config, _ = setup_openai_provider(None)
                new_settings.openai_config = openai_config

            settings_manager.save_user_settings(new_settings)
            console.print("✓ [green]Alternate provider configured![/green]")
            console.print("💡 [cyan]Use '/switch' during chat to switch between providers.[/cyan]")

        console.print("\n🚀 [bold green]Setup complete! You can now run 'shello' to start chatting.[/bold green]\n")
    except Exception as e:
        console.print(f"✗ [red]Failed to save settings: {str(e)}[/red]\n")
        sys.exit(1)


if __name__ == '__main__':
    cli()
