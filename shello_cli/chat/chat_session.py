"""ChatSession - Manages the chat session with AI"""
from shello_cli.agent.shello_agent import ShelloAgent, ChatEntry
from datetime import datetime
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


class ChatSession:
    """Manages the chat session with AI"""
    
    def __init__(self, agent: ShelloAgent):
        self.agent = agent
        self.conversation_started = False
        self.system_info = get_shell_info()
        self.user = getpass.getuser()
        self.hostname = socket.gethostname()
        self._last_interrupted = False  # Track if last execution was interrupted
        self._interrupted_command = None  # Store the interrupted command
    
    def start_conversation(self, user_message: str) -> None:
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
        
        self._process_message(user_message)
    
    def _process_message(self, message: str) -> None:
        """Process a message through the agent and handle the response with streaming"""
        # Use streaming for better UX
        console.print()
        console.print("🐚 Shello", style="bold blue")
        console.print()  # Add spacing after header
        
        accumulated_content = ""
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
                            # Extract command for interrupt tracking
                            func_data = chunk.tool_call.get("function", {})
                            if func_data.get("name") == "bash":
                                try:
                                    args = json.loads(func_data.get("arguments", "{}"))
                                    current_command = args.get("command", "")
                                except:
                                    current_command = "unknown command"
                            else:
                                current_command = f"{func_data.get('name', 'tool')} execution"
                            
                            self._handle_tool_call(chunk.tool_call)
                            console.print()  # Add newline after tool header
                    
                    elif chunk.type == "tool_output":
                        # Stream tool output as it arrives
                        if chunk.content:
                            console.print(chunk.content, end="", markup=False)
                    
                    elif chunk.type == "tool_result":
                        # Tool execution complete
                        current_command = None  # Clear command tracking
                        if chunk.tool_result:
                            # Display final result status if there was an error
                            if not chunk.tool_result.success and chunk.tool_result.error:
                                console.print(f"\n✗ Error: {chunk.tool_result.error}", style="bold red")
                            console.print()  # Add spacing after tool output
                    
                    elif chunk.type == "done":
                        # Streaming complete
                        break
                
                # After the loop ends, handle any remaining accumulated content
                if accumulated_content:
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
            console.print(f"\n✗ Error: {str(e)}", style="bold red")
            console.print("This might be due to an API configuration issue.", style="yellow")
            console.print()
        except Exception as e:
            console.print(f"\n✗ Error: {str(e)}", style="bold red")
            import traceback
            console.print(traceback.format_exc(), style="dim red")
            console.print()
    
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
