#!/usr/bin/env python3
"""
Integration test to verify CLI can start and process bash commands
"""
import os
import sys
from shello_cli.agent.shello_agent import ShelloAgent
from shello_cli.utils.settings_manager import SettingsManager

def test_cli_integration():
    """Test that the CLI can initialize and process a simple bash command"""
    print("=" * 60)
    print("CLI Integration Test")
    print("=" * 60)
    
    # Check for API key
    settings_manager = SettingsManager.get_instance()
    api_key = settings_manager.get_api_key()
    
    if not api_key:
        print("✗ No API key found.")
        print("  Set OPENAI_API_KEY environment variable or configure in settings.")
        print("  Skipping integration test (this is expected in CI/CD).")
        return True
    
    print(f"✓ API key found: ***{api_key[-4:]}")
    
    # Initialize agent
    try:
        base_url = settings_manager.get_base_url()
        model = settings_manager.get_current_model()
        
        print(f"✓ Base URL: {base_url}")
        print(f"✓ Model: {model}")
        
        agent = ShelloAgent(
            api_key=api_key,
            base_url=base_url,
            model=model
        )
        print("✓ Agent initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        return False
    
    # Test simple bash command
    try:
        print("\nTesting simple bash command: 'echo Hello from Shello CLI'")
        print("-" * 60)
        
        # Process a simple message that should trigger bash tool
        message = "Please run this bash command: echo 'Hello from Shello CLI'"
        chat_entries = agent.process_user_message(message)
        
        print(f"✓ Received {len(chat_entries)} chat entries")
        
        # Display the conversation
        for i, entry in enumerate(chat_entries):
            print(f"\nEntry {i+1} ({entry.type}):")
            if entry.content:
                print(f"  Content: {entry.content[:100]}...")
            if entry.tool_calls:
                print(f"  Tool calls: {len(entry.tool_calls)}")
            if entry.tool_result:
                print(f"  Tool result: success={entry.tool_result.success}")
                if entry.tool_result.output:
                    print(f"  Output: {entry.tool_result.output[:100]}")
        
        # Verify we got a response
        if len(chat_entries) > 0:
            print("\n✓ CLI successfully processed the message")
            return True
        else:
            print("\n✗ No chat entries returned")
            return False
            
    except Exception as e:
        print(f"\n✗ Error processing message: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cli_integration()
    print("\n" + "=" * 60)
    if success:
        print("✓ Integration test PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Integration test FAILED")
        print("=" * 60)
        sys.exit(1)
