"""ChatSession - Manages the chat session with AI"""
from shello_cli.agent.shello_agent import ShelloAgent, ChatEntry
from datetime import datetime
import os
from shello_cli.ui.ui_renderer import (
    render_spinner,
    render_ai_response,
    console,
    render_terminal_command,
    render_terminal_output
)
from rich.markdown import Markdown
from rich.live import Live
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
    
    def start_conversation(self, user_message: str) -> None:
        """Start a new conversation with initial instructions and user message"""
        current_datetime = datetime.now().strftime("%A %B %d, %Y at %I:%M %p")
        
        # Format system context
        context = (
            f"Current system information:\n"
            f"- OS: {self.system_info['os_name']}\n"
            f"- Shell: {self.system_info['shell']} ({self.system_info['shell_executable']})\n"
            f"- Working Directory: {self.system_info['cwd']}\n"
            f"- Date/Time: {current_datetime}\n\n"
            f"User message: {user_message}"
        )
        
        # Process the message through the agent
        self._process_message(context)
        self.conversation_started = True
    
    def continue_conversation(self, user_message: str) -> None:
        """Continue an existing conversation with a new user message"""
        self._process_message(user_message)
    
    def _process_message(self, message: str) -> None:
        """Process a message through the agent and handle the response with streaming"""
        # Use streaming for better UX
        console.print()
        console.print("🤖 AI", style="bold blue")
        console.print()  # Add spacing after header
        
        accumulated_content = ""
        current_tool_call = None
        
        try:
            stream = self.agent.process_user_message_stream(message)
            
            if stream is None:
                console.print("\n✗ Error: Failed to get response from agent", style="bold red")
                console.print()
                return
            
            # Use Live display for streaming markdown updates
            with Live(Markdown(""), console=console, refresh_per_second=10) as live:
                for chunk in stream:
                    if chunk.type == "content":
                        # Accumulate content and update live markdown display
                        if chunk.content:
                            accumulated_content += chunk.content
                            # Update the live display with current markdown
                            live.update(Markdown(accumulated_content))
                    
                    elif chunk.type == "tool_calls":
                        # Tool calls received - stop live display and render final markdown
                        if chunk.tool_calls and accumulated_content:
                            live.stop()
                            console.print()
                            accumulated_content = ""  # Reset for next section
                    
                    elif chunk.type == "tool_call":
                        # Individual tool call starting
                        if chunk.tool_call:
                            current_tool_call = chunk.tool_call
                            self._handle_tool_call(chunk.tool_call)
                    
                    elif chunk.type == "tool_output":
                        # Stream tool output as it arrives
                        if chunk.content:
                            console.print(chunk.content, end="", markup=False)
                    
                    elif chunk.type == "tool_result":
                        # Tool execution complete
                        if chunk.tool_result:
                            # Display final result status if there was an error
                            if not chunk.tool_result.success and chunk.tool_result.error:
                                console.print(f"\n✗ Error: {chunk.tool_result.error}", style="bold red")
                            console.print()  # Add spacing after tool output
                    
                    elif chunk.type == "done":
                        # Streaming complete
                        break
            
            # Final newline after response
            console.print()
            
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
        """Handle a tool call from the AI"""
        function_data = tool_call.get("function", {})
        function_name = function_data.get("name")
        
        if function_name == "bash":
            # Parse arguments
            try:
                arguments_str = function_data.get("arguments", "{}")
                arguments = json.loads(arguments_str)
                command = arguments.get("command", "")
                
                if command:
                    # Display the command
                    render_terminal_command(
                        command,
                        None,  # No output filter for now
                        cwd=self.agent.get_current_directory(),
                        user=self.user,
                        hostname=self.hostname
                    )
            except json.JSONDecodeError:
                pass
