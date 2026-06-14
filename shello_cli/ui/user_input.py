"""User input handling with enhanced completion and key bindings"""
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, Completion, PathCompleter, merge_completers
import os
from pathlib import Path
from shello_cli.patterns import APP_DIR
from shello_cli.utils.output_utils import sanitize_surrogates


def abbreviate_path(path: str) -> str:
    """Replace home directory with ~ for cleaner display.
    
    Args:
        path: The full path to abbreviate
        
    Returns:
        Path with home directory replaced by ~
    """
    home_dir = str(Path.home())
    if path.startswith(home_dir):
        return "~" + path[len(home_dir):]
    return path


def truncate_path(path: str, max_length: int = 40) -> str:
    """Truncate long paths to maintain prompt readability.
    
    Args:
        path: The path to truncate
        max_length: Maximum length for the path (default: 40)
        
    Returns:
        Truncated path prefixed with "..." if longer than max_length
    """
    if len(path) <= max_length:
        return path
    return "..." + path[-(max_length - 3):]

# Add this for clipboard support
try:
    import pyperclip
except ImportError:
    pyperclip = None

class SanitizedFileHistory(FileHistory):
    """FileHistory wrapper that sanitizes surrogate characters before writing."""
    
    def append_string(self, string: str) -> None:
        """Append a string to history after sanitizing surrogates.
        
        This is called by prompt_toolkit during input validation.
        
        Args:
            string: The string to append to history
        """
        # Sanitize surrogates before appending (with warning)
        sanitized = sanitize_surrogates(string, warn=True)
        super().append_string(sanitized)
    
    def store_string(self, string: str) -> None:
        """Store a string in history after sanitizing surrogates.
        
        Args:
            string: The string to store in history
        """
        # Sanitize surrogates before storing
        sanitized = sanitize_surrogates(string)
        super().store_string(sanitized)


# Create history file path in shello_cli directory (consistent with other config)
history_file = APP_DIR / ".shello_history"
command_history = SanitizedFileHistory(str(history_file))


class BAICompleter(Completer):
    """Custom completer for BAI commands and common phrases"""
    
    def __init__(self, history_obj=None):
        self.history = history_obj
        self.commands = ['/quit', '/exit', '/new', '/about', '/help', '/history', '/switch', '/model', '/update']
        self.common_phrases = [
            'can you help me with',
            'how do I',
            'what is the best way to',
            'please explain',
            'show me how to',
            'create a script for',
            'debug this code',
            'optimize this',
            'refactor this code',
            'write a function to',
            'generate code',
            'fix this error',
            'install',
            'configure',
            'deploy',
            'test this',
            'run this',
            'execute',
            'check if',
            'list all',
            'show me',
            'find the',
            'search for',
            'update the',
            'delete this',
            'create a new',
            'build a'
        ]
        
        # Programming-related completions
        self.programming_terms = [
            'python script',
            'javascript function',
            'bash command',
            'docker container',
            'git repository',
            'database query',
            'API endpoint',
            'web application',
            'mobile app',
            'machine learning',
            'data analysis',
            'unit test',
            'integration test',
            'code review',
            'performance optimization',
            'security vulnerability',
            'error handling',
            'logging system',
            'configuration file',
            'environment variable'
        ]
    
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        text_lower = text.lower()
        
        # Complete commands that start with / - ONLY return command completions
        if text.startswith('/'):
            for command in self.commands:
                if command.lower().startswith(text_lower):
                    yield Completion(
                        command,
                        start_position=-len(text),
                        display_meta="Command"
                    )
            return
        
        # Skip very short text
        if len(text.strip()) < 2:
            return
        
        # History-based completion (ENHANCED)
        if self.history:
            try:
                history_entries = []
                try:
                    history_entries = list(self.history.get_strings())
                except Exception:
                    try:
                        if hasattr(self.history, 'filename') and os.path.exists(self.history.filename):
                            with open(self.history.filename, 'r', encoding='utf-8') as f:
                                history_entries = [line.strip() for line in f.readlines() if line.strip()]
                    except Exception:
                        pass
                
                seen_completions = set()
                completion_count = 0
                
                # Reverse to get most recent first
                for entry in reversed(history_entries[-50:]):
                    entry = entry.strip()
                    if (len(entry) < 3 or 
                        entry.startswith('/') or 
                        entry.lower() in seen_completions):
                        continue
                    
                    # Exact start match (highest priority)
                    if entry.lower().startswith(text_lower) and entry.lower() != text_lower:
                        # Truncate long entries for display
                        display_text = entry if len(entry) <= 60 else entry[:57] + "..."
                        yield Completion(
                            entry,
                            start_position=-len(text),
                            display=display_text,
                            display_meta="Recent"
                        )
                        seen_completions.add(entry.lower())
                        completion_count += 1
                        if completion_count >= 8:
                            break
                
                # Word-based matching for partial completions
                if completion_count < 5:
                    for entry in reversed(history_entries[-30:]):
                        entry = entry.strip()
                        if (len(entry) < 3 or 
                            entry.startswith('/') or 
                            entry.lower() in seen_completions):
                            continue
                        
                        words = entry.lower().split()
                        for word in words:
                            if word.startswith(text_lower) and len(word) > len(text):
                                display_text = entry if len(entry) <= 60 else entry[:57] + "..."
                                yield Completion(
                                    entry,
                                    start_position=-len(text),
                                    display=display_text,
                                    display_meta="History"
                                )
                                seen_completions.add(entry.lower())
                                completion_count += 1
                                break
                        
                        if completion_count >= 6:
                            break
            
            except Exception as e:
                pass
        
        # Complete programming terms
        for term in self.programming_terms:
            if term.lower().startswith(text_lower):
                yield Completion(
                    term,
                    start_position=-len(text),
                    display_meta="Tech"
                )
        
        # Complete common phrases
        for phrase in self.common_phrases:
            if phrase.lower().startswith(text_lower):
                yield Completion(
                    phrase,
                    start_position=-len(text),
                    display_meta="Phrase"
                )


class EnhancedPathCompleter(PathCompleter):
    """Enhanced path completer with metadata"""
    
    def get_completions(self, document, complete_event):
        for completion in super().get_completions(document, complete_event):
            # Create NEW Completion object with metadata instead of modifying existing one
            if document.text_before_cursor.startswith('/'):
                return
            
            path = completion.text
            if os.path.isdir(path):
                meta = "Dir"
            elif os.path.isfile(path):
                meta = "File"
            else:
                meta = "Path"
            
            # Create new Completion object with all original properties plus metadata
            yield Completion(
                text=completion.text,
                start_position=completion.start_position,
                display=completion.display or completion.text,
                display_meta=meta  # Set metadata during creation
            )


# Create completers
bai_completer = BAICompleter(command_history)
path_completer = EnhancedPathCompleter()
merged_completer = merge_completers([bai_completer, path_completer])


def build_prompt_parts(name: str, current_directory: str = None):
    """Build prompt parts for display.
    
    Args:
        name: Username to display
        current_directory: Current working directory path (optional)
        
    Returns:
        List of tuples (style, text) for prompt_toolkit
    """
    prompt_parts = [
        ('class:prompt.icon', '🌊 '),
        ('class:prompt.username', f'{name}'),
    ]
    
    # Add directory if provided
    if current_directory:
        display_path = abbreviate_path(current_directory)
        display_path = truncate_path(display_path, max_length=40)
        prompt_parts.append(('class:prompt.path', f' [{display_path}]'))
    
    prompt_parts.append(('class:prompt.arrow', '\n──└─⟩ '))
    
    return prompt_parts


def get_user_input_with_clear(name, current_directory=None):
    """Get user input with enhanced completion UI.
    
    Args:
        name: Username to display in prompt
        current_directory: Current working directory path (optional)
        
    Returns:
        User input string or None if interrupted
    """
    bindings = KeyBindings()
    
    @bindings.add('c-x')
    def cut_input(event):
        buffer = event.current_buffer
        current_text = buffer.text
        if current_text:
            try:
                import pyperclip
                pyperclip.copy(current_text)
            except ImportError:
                pass
            buffer.reset()
    
    @bindings.add('c-a')
    def select_all(event):
        buffer = event.current_buffer
        buffer.cursor_position = 0
        buffer.start_selection()
        buffer.cursor_position = len(buffer.text)
    
    @bindings.add('backspace')
    def smart_backspace(event):
        buffer = event.current_buffer
        if buffer.selection_state:
            buffer.cut_selection()
        else:
            buffer.delete_before_cursor(count=1)
    
    @bindings.add('c-j')
    def insert_newline(event):
        event.current_buffer.insert_text('\n')
    
    @bindings.add('c-v')
    def paste_text(event):
        try:
            import pyperclip
            clipboard_text = pyperclip.paste()
            if clipboard_text:
                event.current_buffer.insert_text(clipboard_text)
        except ImportError:
            pass
    
    @bindings.add('c-z')
    def undo(event):
        event.current_buffer.undo()
    
    @bindings.add('c-y')
    def redo(event):
        event.current_buffer.redo()
    
    @bindings.add('c-w')
    def delete_word_backwards(event):
        buffer = event.current_buffer
        word_start = buffer.document.find_start_of_previous_word()
        # Ensure count is non-negative
        count = max(0, abs(word_start)) if word_start else 0
        if count > 0:
            buffer.delete_before_cursor(count=count)
    
    @bindings.add('c-k')
    def delete_to_end(event):
        event.current_buffer.delete(count=len(event.current_buffer.document.text_after_cursor))
    
    @bindings.add('c-u')
    def delete_to_beginning(event):
        event.current_buffer.delete_before_cursor(count=len(event.current_buffer.document.text_before_cursor))
    
    @bindings.add('enter')
    def submit_input(event):
        event.current_buffer.validate_and_handle()
    
    # Enhanced style with modern terminal look
    enhanced_style = Style.from_dict({
        # Modern terminal prompt styling
        'prompt.icon': '#00d7ff bold',       # Cyan icon
        'prompt.username': '#00ff87 bold',   # Green username
        'prompt.path': '#ffaf00',            # Orange path
        'prompt.arrow': '#00d7ff bold',      # Cyan arrow with box drawing
        
        # Completion menu styling - improved colors and contrast
        'completion-menu': 'bg:#1a1a1a border:#444444',
        'completion-menu.completion': 'bg:#2a2a2a #e0e0e0',
        'completion-menu.completion.current': 'bg:#0078d4 #ffffff bold',
        
        # Meta information styling with better visibility
        'completion-menu.meta': 'bg:#333333 #888888 italic',
        'completion-menu.meta.current': 'bg:#005a9e #ffffff italic',
        
        # Scrollbar improvements
        'scrollbar.background': 'bg:#2a2a2a',
        'scrollbar.button': 'bg:#555555',
        'scrollbar.arrow': '#777777',
        
        # Additional styling for better UX
        'completion-menu.scrollbar': 'bg:#333333',
    })
    
    # Build prompt parts with optional directory
    prompt_parts = build_prompt_parts(name, current_directory)
    
    try:
        user_input = prompt(
            prompt_parts,
            key_bindings=bindings,
            complete_style='multi-column',  # Multi-column layout
            multiline=True,
            wrap_lines=True,
            mouse_support=False,
            vi_mode=False,
            history=command_history,
            completer=merged_completer,
            complete_while_typing=True,
            style=enhanced_style,
            # Valid completion settings
            reserve_space_for_menu=6,  # Reserve vertical space for menu
        )
        # Sanitize surrogates from user input
        if user_input:
            user_input = sanitize_surrogates(user_input)
        return user_input
    except KeyboardInterrupt:
        # Print a newline so the next prompt is on a new line, and return empty string
        print()
        return ""
    except EOFError:
        return None


def select_option(title: str, options: list, default_index: int = 0) -> any:
    """Display a selection menu using prompt_toolkit and return the chosen value.
    
    Args:
        title: The prompt title/question to display
        options: A list of tuples (label, value)
        default_index: Default selected option index
        
    Returns:
        The selected value
    """
    from prompt_toolkit import Application
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style
    from rich.console import Console
    
    console = Console()
    console.print(f"\n{title}")
    
    state = {"selected": default_index, "result": None}
    
    kb = KeyBindings()
    
    @kb.add("up")
    @kb.add("k")
    def _up(event):
        state["selected"] = (state["selected"] - 1) % len(options)
        
    @kb.add("down")
    @kb.add("j")
    def _down(event):
        state["selected"] = (state["selected"] + 1) % len(options)
        
    @kb.add("enter")
    def _enter(event):
        state["result"] = options[state["selected"]][1]
        event.app.exit()
        
    # Support direct key input for numbers if 1-9 are mapped
    for idx in range(min(len(options), 9)):
        key = str(idx + 1)
        @kb.add(key)
        def _num_press(event, key=key):
            state["result"] = options[int(key) - 1][1]
            event.app.exit()
            
    @kb.add("escape")
    @kb.add("c-c")
    def _cancel(event):
        state["result"] = options[default_index][1]
        event.app.exit()
        
    def _get_content():
        lines = []
        for i, (label, val) in enumerate(options):
            # Show number prefix for keyboard accessibility (1., 2., etc.)
            num_prefix = f" [{i + 1}]" if i < 9 else "    "
            if i == state["selected"]:
                lines.append(("class:selected", f"  ❯{num_prefix} {label}\n"))
            else:
                lines.append(("", f"   {num_prefix} {label}\n"))
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
        "selected": "bold reverse cyan",
    })
    
    app: Application = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )
    
    try:
        app.run()
        # Clear the options from the terminal
        import sys
        num_lines = len(options)
        sys.stdout.write(f"\033[{num_lines}F\033[J")
        sys.stdout.flush()
    except KeyboardInterrupt:
        try:
            import sys
            num_lines = len(options)
            sys.stdout.write(f"\033[{num_lines}F\033[J")
            sys.stdout.flush()
        except Exception:
            pass
        return options[default_index][1]
        
    return state["result"]
