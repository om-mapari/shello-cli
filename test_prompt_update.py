#!/usr/bin/env python3
"""
Test to verify the updated system prompt is being used
"""
import os
from shello_cli.agent.shello_agent import ShelloAgent
from shello_cli.utils.settings_manager import SettingsManager

def test_prompt_update():
    """Test that the agent uses the updated system prompt"""
    print("=" * 60)
    print("System Prompt Update Test")
    print("=" * 60)
    
    # Check for API key
    settings_manager = SettingsManager.get_instance()
    api_key = settings_manager.get_api_key()
    
    if not api_key:
        print("✗ No API key found. Skipping test.")
        return True
    
    # Initialize agent
    agent = ShelloAgent(
        api_key=api_key,
        base_url=settings_manager.get_base_url(),
        model=settings_manager.get_current_model()
    )
    
    # Check that the system message contains key elements from the new prompt
    system_message = agent._messages[0]
    system_content = system_message.get("content", "")
    
    print("\nChecking system prompt contains key elements:")
    
    checks = [
        ("Shello CLI branding", "Shello CLI" in system_content),
        ("Output management strategy", "OUTPUT MANAGEMENT STRATEGY" in system_content),
        ("JSON processing guidance", "JSON PROCESSING BEST PRACTICES" in system_content),
        ("AWS CLI integration", "AWS CLI INTEGRATION" in system_content),
        ("Common command patterns", "COMMON COMMAND PATTERNS" in system_content),
        ("Error handling guidance", "ERROR HANDLING & RECOVERY" in system_content),
        ("Safety considerations", "SAFETY CONSIDERATIONS" in system_content),
        ("System information", "SYSTEM INFORMATION" in system_content),
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False
    
    # Print a sample of the system prompt
    print("\nSystem prompt preview (first 500 chars):")
    print("-" * 60)
    print(system_content[:500])
    print("...")
    print("-" * 60)
    
    if all_passed:
        print("\n✓ All checks passed!")
        return True
    else:
        print("\n✗ Some checks failed")
        return False

if __name__ == "__main__":
    import sys
    success = test_prompt_update()
    sys.exit(0 if success else 1)
