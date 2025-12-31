"""ChatSession - Manages the chat session with AI"""
from shello_cli.commands.command_executor import CommandExecutor
from shello_cli.chat.template import INSTRUCTION_TEMPLATE
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


class ChatSession:
    """Manages the chat session with AI"""
    
    def __init__(self, gitlab_client):
        self.gitlab_client = gitlab_client
        self.command_executor = CommandExecutor()
        self.conversation_started = False
        self.max_output_size = int(os.getenv("MAX_OUTPUT_SIZE", "4000"))
        self.system_info = get_shell_info()
        self.user = getpass.getuser()
        self.hostname = socket.gethostname()
    
    def start_conversation(self, user_message: str) -> None:
        """Start a new conversation with initial instructions and user message"""
        current_datetime = datetime.now().strftime("%A %B %d, %Y at %I:%M %p")
        
        # Format the instruction template with system information
        instruction = INSTRUCTION_TEMPLATE.format(
            os_name=self.system_info["os_name"],
            shell=self.system_info["shell"],
            shell_executable=self.system_info["shell_executable"],
            cwd=self.system_info["cwd"],
            current_datetime=current_datetime
        )
        
        # Combine instruction with user message
        initial_message = f"{instruction}\n\nUser: {user_message}"
        
        # Use Rich spinner for AI thinking
        with render_spinner("AI thinking..."):
            response = self.gitlab_client.send_message(initial_message)
        
        if response:
            render_ai_response(response)
            self.conversation_started = True
            self.process_command_in_response(response)
        else:
            console.print("Sorry, I couldn't generate a response. Please try again.", style="bold red")
    
    def continue_conversation(self, user_message: str) -> None:
        """Continue an existing conversation with a new user message"""
        # Use Rich spinner for AI thinking
        with render_spinner("AI thinking..."):
            response = self.gitlab_client.send_message(f"User: {user_message}")
        
        if response:
            render_ai_response(response)
            self.process_command_in_response(response)
        else:
            console.print("Sorry, I couldn't generate a response. Please try again.", style="bold red")
    
    def process_command_in_response(self, response: str) -> None:
        """Process any command in the AI's response"""
        command, requires_approval, output_filter = self.command_executor.extract_command(response)
        
        if not command:
            return
        
        # Step 1: Show command in first box
        render_terminal_command(
            command,
            output_filter,
            cwd=self.system_info.get("cwd"),
            user=self.user,
            hostname=self.hostname
        )
        
        if requires_approval:
            approval = console.input("[bold]Do you want to execute this command? (y/n): [/bold]").lower()
            if approval != 'y':
                console.print("✗ Command execution cancelled.", style="red")
                self.send_command_result("Command execution was cancelled by the user.")
                return
        
        # Step 2: Show executing animation
        with render_spinner("⚙ Executing command..."):
            # Step 3: Execute command and get structured result
            execution_result = self.command_executor.execute(command, self.system_info)
        
        # Get raw output (without return code info)
        raw_result = execution_result["raw_output"]
        
        # Apply output filtering if specified (only on raw output)
        if output_filter:
            filtered_result = self.command_executor.apply_output_filter(raw_result, output_filter)
            console.print(f"ℹ Applied filter: {output_filter}", style="yellow")
        else:
            filtered_result = raw_result
        
        # Auto-summarize large outputs if no filter was specified
        if len(filtered_result) > self.max_output_size:
            filtered_result = self.truncate_output(filtered_result)
            console.print("⚠ Output was automatically truncated due to large size.", style="yellow")
        
        # Add return code information to the filtered result for sending to AI
        result_with_status = self.command_executor.format_result_with_status(
            filtered_result,
            execution_result['returncode']
        )
        
        # Step 4: Show output in second box (spinner automatically disappears)
        render_terminal_output(
            result_with_status,
            cwd=self.system_info.get("cwd"),
            user=self.user,
            hostname=self.hostname
        )
        
        # Send the command result back to the AI (with status info and filter info)
        self.send_command_result(result_with_status, output_filter)
    
    def send_command_result(self, result: str, output_filter: str = None) -> None:
        """Send command execution result back to AI"""
        # Check if truncation is needed
        if len(result) > self.max_output_size:
            truncated_result = self.truncate_output(result)
            
            # Include filter information in the message if a filter was applied
            if output_filter:
                message = f"Command execution result (truncated due to size, filter applied: {output_filter}):\n\n{truncated_result}\n"
            else:
                message = f"Command execution result (truncated due to size):\n\n{truncated_result}\n"
        else:
            # Include filter information in the message if a filter was applied
            if output_filter:
                message = f"Command execution result (filter applied: {output_filter}):\n\n{result}\n"
            else:
                message = f"Command execution result:\n\n{result}\n"
        
        # Use Rich spinner for AI thinking
        with render_spinner("AI processing command results..."):
            response = self.gitlab_client.send_message(message)
        
        if response:
            render_ai_response(response)
            # Check if there's another command in the response
            self.process_command_in_response(response)
        else:
            console.print("Sorry, I couldn't generate a response. Please try again.", style="bold red")
    
    def truncate_output(self, result: str, max_size: int = None) -> str:
        """Truncate large output to a manageable size
        
        Args:
            result: The output string to potentially truncate
            max_size: Maximum size threshold (defaults to self.max_output_size)
        
        Returns:
            Original result if small enough, otherwise truncated version
        """
        if max_size is None:
            max_size = self.max_output_size
        
        if len(result) <= max_size:
            return result
        
        lines = result.splitlines()
        total_lines = len(lines)
        total_chars = len(result)
        
        # Create a truncated version
        first_part = '\n'.join(lines[:20])
        last_part = '\n'.join(lines[-20:])
        
        truncated_result = (
            f"Output truncated ({total_lines} lines, {total_chars} characters total):\n"
            f"--- First 20 lines ---\n"
            f"{first_part}\n"
            f"--- Last 20 lines ---\n"
            f"{last_part}"
        )
        
        return truncated_result
