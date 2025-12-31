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
        
        accumulated_content = ""
        current_tool_calls = []
        
        try:
            stream = self.agent.process_user_message_stream(message)
            
            if stream is None:
                console.print("\n✗ Error: Failed to get response from agent", style="bold red")
                console.print()
                return
            
            for chunk in stream:
                if chunk.type == "content":
                    # Stream content as it arrives
                    if chunk.content:
                        console.print(chunk.content, end="", markup=False)
                        accumulated_content += chunk.content
                
                elif chunk.type == "tool_calls":
                    # Tool calls received
                    if chunk.tool_calls:
                        current_tool_calls = chunk.tool_calls
                        # Print newline before tool execution
                        if accumulated_content:
                            console.print()
                            console.print()
                
                elif chunk.type == "tool_result":
                    # Display tool execution
                    if chunk.tool_call:
                        self._handle_tool_call(chunk.tool_call)
                    if chunk.tool_result:
                        self._display_tool_result(chunk.tool_call, chunk.tool_result)
                
                elif chunk.type == "done":
                    # Streaming complete
                    if accumulated_content:
                        console.print()
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
    
    def _display_tool_result(self, tool_call: dict, tool_result) -> None:
        """Display the result of a tool execution"""
        function_data = tool_call.get("function", {})
        function_name = function_data.get("name")
        
        if function_name == "bash":
            # Display the output
            if tool_result.success:
                output = tool_result.output or ""
            else:
                output = f"Error: {tool_result.error or 'Unknown error'}"
            
            render_terminal_output(
                output,
                cwd=self.agent.get_current_directory(),
                user=self.user,
                hostname=self.hostname
            )
