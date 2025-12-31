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
        """Process a message through the agent and handle the response"""
        # Use Rich spinner for AI thinking
        with render_spinner("AI thinking..."):
            entries = self.agent.process_user_message(message)
        
        # Process each entry in the response
        for entry in entries:
            if entry.type == "user":
                # Skip user entries (we already displayed the input)
                continue
            
            elif entry.type == "assistant":
                # Display assistant response
                if entry.content:
                    render_ai_response(entry.content)
            
            elif entry.type == "tool_call":
                # Display and execute tool calls
                if entry.tool_calls:
                    for tool_call in entry.tool_calls:
                        self._handle_tool_call(tool_call)
            
            elif entry.type == "tool_result":
                # Display tool result
                if entry.tool_result:
                    self._display_tool_result(entry.tool_call, entry.tool_result)
    
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
