"""ChatSession - Manages the chat session with AI"""
from shello_cli.agent.shello_agent import ShelloAgent, ChatEntry
from datetime import datetime, timezone
import os
from shello_cli.ui.ui_renderer import (
    console,
    render_tool_execution
)
from rich.markdown import Markdown
from rich.live import Live
from shello_cli.ui.custom_markdown import EnhancedMarkdown
import getpass
import socket
from shello_cli.utils.system_info import get_shell_info
import json
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from shello_cli.session.recorder import SessionRecorder


class ChatSession:
    """Manages the chat session with AI"""
    
    def __init__(self, agent: ShelloAgent, recorder: Optional["SessionRecorder"] = None):
        self.agent = agent
        self.conversation_started = False
        self.system_info = get_shell_info()
        self.user = getpass.getuser()
        self.hostname = socket.gethostname()
        self._last_interrupted = False  # Track if last execution was interrupted
        self._interrupted_command = None  # Store the interrupted command
        self._recorder: Optional["SessionRecorder"] = recorder

    def set_recorder(self, recorder: Optional["SessionRecorder"]) -> None:
        """Attach or replace the session recorder."""
        self._recorder = recorder
    
    def start_conversation(self, user_message: str, raw_user_message: str = "") -> None:
        """Start a new conversation with initial instructions and user message"""
        current_datetime = datetime.now().strftime("%A %B %d, %Y at %I:%M %p")
        
        # Check if previous execution was interrupted
        if self._last_interrupted:
            interrupt_context = f"\n\n[SYSTEM: Previous command was interrupted by user (Ctrl+C): {self._interrupted_command}]"
            self._last_interrupted = False
            self._interrupted_command = None
        else:
            interrupt_context = ""
        
        # Format system context
        context = (
            f"Current system information:\n"
            f"- OS: {self.system_info['os_name']}\n"
            f"- Shell: {self.system_info['shell']} ({self.system_info['shell_executable']})\n"
            f"- Working Directory: {self.system_info['cwd']}\n"
            f"- Date/Time: {current_datetime}\n\n"
            f"User message: {user_message}{interrupt_context}"
        )
        
        # Record user_prompt entry (use raw message for readability)
        self._record_user_prompt(raw_user_message or user_message)

        # Process the message through the agent
        self._process_message(context)
        self.conversation_started = True
    
    def continue_conversation(self, user_message: str) -> None:
        """Continue an existing conversation with a new user message"""
        # Check if previous execution was interrupted
        if self._last_interrupted:
            interrupt_context = f"\n\n[SYSTEM: Previous command was interrupted by user (Ctrl+C): {self._interrupted_command}]"
            user_message = user_message + interrupt_context
            self._last_interrupted = False
            self._interrupted_command = None

        # Record user_prompt entry
        self._record_user_prompt(user_message)

        self._process_message(user_message)

    def _record_user_prompt(self, message: str) -> None:
        """Record a user_prompt entry and the corresponding api_message."""
        if self._recorder is None:
            return
        from shello_cli.session.models import SessionEntry
        cwd = self.agent.get_current_directory()
        self._recorder.record(SessionEntry(
            entry_type="user_prompt",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            content=message,
            metadata={"working_directory": cwd, "username": self.user},
        ))
        self._recorder.record_api_message({"role": "user", "content": message})
    
    def _process_message(self, message: str) -> None:
        """Process a message through the agent and handle the response with streaming"""
        # Use streaming for better UX
        console.print()
        console.print("🐚 Shello", style="bold blue")
        console.print()  # Add spacing after header
        
        accumulated_content = ""
        accumulated_tool_output = ""
        current_tool_call = None
        current_command = None  # Track current executing command
        live_display_active = True  # Track if live display is still active
        
        try:
            stream = self.agent.process_user_message_stream(message)
            
            if stream is None:
                console.print("\n✗ Error: Failed to get response from agent", style="bold red")
                console.print()
                return
            
            # Use Live display for streaming markdown updates
            with Live(EnhancedMarkdown(""), console=console, refresh_per_second=10) as live:
                for chunk in stream:
                    if chunk.type == "content":
                        # Accumulate content and update live markdown display
                        if chunk.content:
                            accumulated_content += chunk.content
                            # Only update live display if it's still active
                            if live_display_active:
                                live.update(EnhancedMarkdown(accumulated_content))
                    
                    elif chunk.type == "tool_calls":
                        # Tool calls received - finalize any accumulated content before showing tools
                        if chunk.tool_calls:
                            # Record accumulated AI response before tool calls
                            if accumulated_content:
                                self._record_ai_response(accumulated_content)
                            # Always record assistant api_message with tool_calls (even if no text content)
                            self._record_assistant_api_message(accumulated_content, chunk.tool_calls)

                            if live_display_active:
                                # Live display is active - stop it (this preserves what's shown)
                                live.stop()
                                live_display_active = False
                                # Content was shown via live display, just add spacing
                                if accumulated_content:
                                    console.print()
                            else:
                                # Live display was already stopped - content needs to be printed now
                                if accumulated_content:
                                    console.print(EnhancedMarkdown(accumulated_content))
                                    console.print()
                            accumulated_content = ""  # Reset for next section
                    
                    elif chunk.type == "tool_call":
                        # Individual tool call starting
                        if chunk.tool_call:
                            current_tool_call = chunk.tool_call
                            accumulated_tool_output = ""
                            # Extract command for interrupt tracking
                            func_data = chunk.tool_call.get("function", {})
                            if func_data.get("name") == "run_shell_command":
                                try:
                                    args = json.loads(func_data.get("arguments", "{}"))
                                    current_command = args.get("command", "")
                                except Exception:
                                    current_command = "unknown command"
                            else:
                                current_command = f"{func_data.get('name', 'tool')} execution"
                            
                            self._handle_tool_call(chunk.tool_call)
                            self._record_tool_execution(chunk.tool_call)
                            console.print()  # Add newline after tool header
                    
                    elif chunk.type == "tool_output":
                        # Stream tool output as it arrives
                        if chunk.content:
                            accumulated_tool_output += chunk.content
                            console.print(chunk.content, end="", markup=False)
                    
                    elif chunk.type == "tool_result":
                        # Tool execution complete — record output and api_message
                        if accumulated_tool_output:
                            self._record_tool_output(accumulated_tool_output, current_tool_call)
                            accumulated_tool_output = ""
                        if chunk.tool_result:
                            self._record_tool_result_api_message(chunk.tool_result, current_tool_call)
                            # Display final result status if there was an error
                            if not chunk.tool_result.success and chunk.tool_result.error:
                                console.print(f"\n✗ Error: {chunk.tool_result.error}", style="bold red")
                            console.print()  # Add spacing after tool output
                        current_command = None  # Clear command tracking
                    
                    elif chunk.type == "done":
                        # Streaming complete
                        break
                
                # After the loop ends, handle any remaining accumulated content
                if accumulated_content:
                    self._record_ai_response(accumulated_content)
                    self._record_assistant_api_message(accumulated_content, None)
                    if live_display_active:
                        # Live display is still active - stop it and let it show the final content
                        live.stop()
                        live_display_active = False
                    else:
                        # Live was stopped earlier (after tool_calls), but we have new content
                        # This content hasn't been displayed yet, so print it now
                        console.print(EnhancedMarkdown(accumulated_content))
            
            # Final newline after response
            console.print()
            
        except KeyboardInterrupt:
            # User pressed Ctrl+C - interrupt execution
            console.print("\n")
            console.print("⚠️  Interrupted by user (Ctrl+C)", style="bold yellow")
            console.print()
            
            # Store interrupt state for next message
            self._last_interrupted = True
            self._interrupted_command = current_command or "AI response"
            
            # Add tool responses for any pending tool calls to keep message history valid
            pending_tool_calls = self.agent.get_pending_tool_calls()
            for tool_call_id in pending_tool_calls:
                self.agent.add_interrupted_tool_response(tool_call_id, self._interrupted_command)
            
        except TypeError as e:
            self._record_error(str(e))
            console.print(f"\n✗ Error: {str(e)}", style="bold red")
            console.print("This might be due to an API configuration issue.", style="yellow")
            console.print()
        except Exception as e:
            self._record_error(str(e))
            console.print(f"\n✗ Error: {str(e)}", style="bold red")
            import traceback
            console.print(traceback.format_exc(), style="dim red")
            console.print()

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def _record_ai_response(self, content: str) -> None:
        if self._recorder is None or not self._recorder.is_recording:
            return
        from shello_cli.session.models import SessionEntry
        self._recorder.record(SessionEntry(
            entry_type="ai_response",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            content=content,
        ))

    def _record_assistant_api_message(self, content: str, tool_calls) -> None:
        if self._recorder is None or not self._recorder.is_recording:
            return
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._recorder.record_api_message(msg)

    def _record_tool_execution(self, tool_call: dict) -> None:
        if self._recorder is None or not self._recorder.is_recording:
            return
        from shello_cli.session.models import SessionEntry
        func_data = tool_call.get("function", {})
        tool_name = func_data.get("name", "")
        try:
            parameters = json.loads(func_data.get("arguments", "{}"))
        except Exception:
            parameters = {}
        self._recorder.record(SessionEntry(
            entry_type="tool_execution",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            content="",
            metadata={
                "tool_name": tool_name,
                "parameters": parameters,
                "cwd": self.agent.get_current_directory(),
            },
        ))

    def _record_tool_output(self, output: str, tool_call) -> None:
        if self._recorder is None or not self._recorder.is_recording:
            return
        from shello_cli.session.models import SessionEntry
        tool_name = ""
        if tool_call:
            tool_name = tool_call.get("function", {}).get("name", "")
        self._recorder.record(SessionEntry(
            entry_type="tool_output",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            content=output,
            metadata={"tool_name": tool_name},
        ))

    def _record_tool_result_api_message(self, tool_result, tool_call) -> None:
        if self._recorder is None or not self._recorder.is_recording:
            return
        tool_call_id = tool_call.get("id", "") if tool_call else ""
        # Use the exact content string that was sent to the AI (set by MessageProcessor).
        # This includes truncation metadata and cache IDs, matching what the AI actually saw.
        # Fall back to raw output only if api_content wasn't set (e.g. non-streaming path).
        content = tool_result.api_content or tool_result.output or tool_result.error or ""
        self._recorder.record_api_message({
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id,
        })

    def _record_error(self, error_msg: str) -> None:
        if self._recorder is None or not self._recorder.is_recording:
            return
        from shello_cli.session.models import SessionEntry
        self._recorder.record(SessionEntry(
            entry_type="error",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            content=error_msg,
        ))
    
    def _handle_tool_call(self, tool_call: dict) -> None:
        """Handle a tool call from the AI - renders tool execution for any tool"""
        function_data = tool_call.get("function", {})
        function_name = function_data.get("name")
        
        if not function_name:
            return
        
        # Parse arguments
        try:
            arguments_str = function_data.get("arguments", "{}")
            arguments = json.loads(arguments_str)
            
            # Render tool execution for ALL tools (bash, analyze_json, etc.)
            render_tool_execution(
                tool_name=function_name,
                parameters=arguments,
                cwd=self.agent.get_current_directory(),
                user=self.user,
                hostname=self.hostname
            )
        except json.JSONDecodeError:
            pass
