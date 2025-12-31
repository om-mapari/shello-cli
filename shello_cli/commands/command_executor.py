"""Command execution and parsing with intelligent output filtering"""
import re
import subprocess
from typing import Tuple, Optional
from shello_cli.utils.json_schema_analyzer import json_to_jq_paths


class CommandExecutor:
    """Handles command execution and parsing with intelligent output filtering"""
    
    @staticmethod
    def extract_command(response: str) -> Tuple[Optional[str], bool, Optional[str]]:
        """Extract command from AI response
        
        Returns: (command, requires_approval, output_filter)
        """
        # Look for execute_command XML tags
        pattern = r'<execute_command>(.*?)</execute_command>'
        match = re.search(pattern, response, re.DOTALL)
        
        if not match:
            return None, False, None
        
        try:
            # Get the raw content between tags
            xml_content = match.group(1)
            
            # Extract command using regex instead of XML parsing to avoid issues with special characters
            cmd_match = re.search(r'<command>(.*?)</command>', xml_content, re.DOTALL)
            approval_match = re.search(r'<requires_approval>(.*?)</requires_approval>', xml_content, re.DOTALL)
            filter_match = re.search(r'<output_filter>(.*?)</output_filter>', xml_content, re.DOTALL)
            
            if not cmd_match or not approval_match:
                print("\033[91mMissing required command elements\033[0m")
                return None, False, None
            
            command = cmd_match.group(1).strip()
            requires_approval = approval_match.group(1).strip().lower() == 'true'
            
            # Extract output filter if present
            output_filter = None
            if filter_match:
                output_filter = filter_match.group(1).strip()
            
            return command, requires_approval, output_filter
        
        except Exception as e:
            print(f"\033[91mError parsing command: {e}\033[0m")
            return None, False, None
    
    @staticmethod
    def execute(command: str, system_info: dict) -> dict:
        """Execute a shell command and return the raw output and return code info separately"""
        try:
            # Determine execution method based on shell
            if system_info["os_name"] == "Windows" and system_info["shell"] == "bash":
                # Use Git Bash on Windows
                if system_info["shell_executable"] == "bash":
                    # bash is available in PATH, use it directly
                    full_command = ["bash", "-c", command]
                else:
                    # Use full path to bash executable
                    full_command = [system_info["shell_executable"], "-c", command]
                
                result = subprocess.run(
                    full_command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors='replace',
                    cwd=system_info["cwd"]
                )
            else:
                # Use default shell execution
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',  # Replace invalid characters instead of crashing
                    cwd=system_info["cwd"]
                )
            
            # Prepare the raw output (stdout + stderr only)
            raw_output = ""
            if result.stdout:
                raw_output = result.stdout
            if result.stderr:
                if raw_output:
                    raw_output += "\n"
                raw_output += f"\033[91mERROR: {result.stderr}\033[0m"
            
            # Return both raw output and return code info separately
            return {
                'raw_output': raw_output,
                'returncode': result.returncode,
                'success': result.returncode == 0
            }
        
        except Exception as e:
            return {
                'raw_output': f"\033[91mFailed to execute command: {str(e)}\033[0m",
                'returncode': -1,
                'success': False
            }
    
    @staticmethod
    def apply_output_filter(output: str, output_filter: str) -> str:
        """Apply filtering to command output based on filter specification"""
        if not output_filter:
            return output
        
        lines = output.splitlines()
        result = []
        
        try:
            if output_filter.startswith('head:'):
                # Get first N lines
                count = int(output_filter.split(':')[1])
                result = lines[:min(count, len(lines))]
            
            elif output_filter.startswith('tail:'):
                # Get last N lines
                count = int(output_filter.split(':')[1])
                result = lines[-min(count, len(lines)):]
            
            elif output_filter == 'count_lines':
                # Just return the line count
                return f"\033[1m\033[94mOutput contains {len(lines)} lines.\033[0m"
            
            elif output_filter == 'json_schema':
                # Analyze JSON structure and return jq paths
                try:
                    schema_output = json_to_jq_paths(output)
                    return schema_output
                except Exception as e:
                    return f"\033[91mError analyzing JSON: {str(e)}\033[0m\n\nOriginal output (first 20 lines):\n" + '\n'.join(lines[:20])
            
            else:
                # Unknown filter, return original output
                return output
            
            return '\n'.join(result)
        
        except Exception as e:
            return f"\033[91mError applying filter: {str(e)}\033[0m\n\nOriginal output:\n{output}"
    
    @staticmethod
    def format_result_with_status(filtered_output: str, returncode: int) -> str:
        """Add return code information to the filtered output"""
        output = filtered_output
        
        # Add return code information
        if returncode == 0:
            output += f"\n\nCommand completed successfully (exit code: {returncode})"
        else:
            output += f"\n\n\033[91mCommand exited with code: {returncode}\033[0m"
        
        return output
