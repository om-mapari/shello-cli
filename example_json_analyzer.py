#!/usr/bin/env python3
"""
Example demonstrating the JSON analyzer tool usage.

This shows how the AI uses the analyze_json tool to understand
JSON structures from commands WITHOUT flooding the terminal.

The key insight: The tool accepts a COMMAND (not JSON), executes it
internally, and returns ONLY the jq paths - preventing large JSON
outputs from flooding the terminal.
"""

from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
from unittest.mock import patch, MagicMock

# Create the tool
tool = JsonAnalyzerTool()

print("=" * 70)
print("JSON Analyzer Tool - Command-Based Analysis")
print("=" * 70)
print()
print("The analyze_json tool accepts a COMMAND that produces JSON output.")
print("It executes the command internally and returns ONLY the jq paths.")
print("This prevents large JSON outputs from flooding the terminal.")
print()

# Example 1: Simulated AWS S3 list-buckets
print("=" * 70)
print("Example 1: AWS S3 list-buckets")
print("=" * 70)
print()
print("Command: aws s3api list-buckets --output json")
print()

# Mock the subprocess to simulate AWS output
aws_s3_output = '''
{
    "Buckets": [
        {"Name": "bucket-1", "CreationDate": "2023-01-15T10:30:00.000Z"},
        {"Name": "bucket-2", "CreationDate": "2023-02-20T14:45:00.000Z"},
        {"Name": "bucket-3", "CreationDate": "2023-03-25T09:15:00.000Z"}
    ],
    "Owner": {
        "DisplayName": "john-doe",
        "ID": "abc123def456"
    }
}
'''

with patch('subprocess.run') as mock_run:
    mock_run.return_value = MagicMock(returncode=0, stdout=aws_s3_output, stderr='')
    result = tool.analyze('aws s3api list-buckets --output json')
    print("Result (jq paths only - no JSON flooding!):")
    print(result.output)
    print()

# Example 2: Simulated AWS Lambda list-functions (100 functions!)
print("=" * 70)
print("Example 2: AWS Lambda list-functions (100 functions!)")
print("=" * 70)
print()
print("Command: aws lambda list-functions --output json")
print()
print("Imagine this returns 100 Lambda functions (5000+ lines of JSON)...")
print("The tool analyzes the structure and returns ONLY the paths!")
print()

lambda_output = '''
{
    "Functions": [
        {
            "FunctionName": "function-1",
            "Runtime": "python3.9",
            "Handler": "index.handler",
            "CodeSize": 1024,
            "LastModified": "2023-01-01T00:00:00.000+0000",
            "MemorySize": 128,
            "Timeout": 30,
            "Environment": {
                "Variables": {
                    "ENV": "production"
                }
            }
        }
    ]
}
'''

with patch('subprocess.run') as mock_run:
    mock_run.return_value = MagicMock(returncode=0, stdout=lambda_output, stderr='')
    result = tool.analyze('aws lambda list-functions --output json')
    print("Result (jq paths only):")
    print(result.output)
    print()

# Example 3: Show the workflow
print("=" * 70)
print("Complete Workflow Example")
print("=" * 70)
print("""
User: "Show me my Lambda function names"

AI Workflow:
------------

Step 1: AI doesn't know the JSON structure, so it uses analyze_json
        → analyze_json(command="aws lambda list-functions --output json")
        
        Tool executes command internally (user doesn't see 5000 lines of JSON!)
        Tool returns:
          .Functions[] | array[100]
          .Functions[].FunctionName | string
          .Functions[].Runtime | string
          ...

Step 2: Now AI knows the path! It constructs a filtered command:
        → bash(command="aws lambda list-functions --output json | jq '.Functions[].FunctionName'")
        
        User sees:
          "function-1"
          "function-2"
          ...
          "function-100"

Result: User gets clean output without terminal flooding!
""")

print("=" * 70)
print("Key Benefits:")
print("=" * 70)
print("""
1. NO TERMINAL FLOODING: Large JSON is never displayed to user
2. AI LEARNS STRUCTURE: AI discovers available fields and paths
3. EFFICIENT: Only the final filtered result is shown
4. SMART: AI can construct precise jq queries
""")
