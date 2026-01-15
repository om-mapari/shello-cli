#!/usr/bin/env python3
"""
Simple script to test the OpenAI client with the configured model.

This script loads settings from .shello/user-settings.json and makes
a simple API call to verify everything works.
"""

from shello_cli.api.openai_client import ShelloClient
from shello_cli.settings import SettingsManager


def main():
    print("=" * 60)
    print("Testing OpenAI Client with Configured Model")
    print("=" * 60)
    
    # Load settings
    settings_manager = SettingsManager.get_instance()
    
    api_key = settings_manager.get_api_key()
    base_url = settings_manager.get_base_url()
    model = settings_manager.get_current_model()
    
    print(f"\n📋 Configuration:")
    print(f"   Base URL: {base_url}")
    print(f"   Model: {model}")
    print(f"   API Key: {'*' * 20}{api_key[-10:] if api_key else 'NOT SET'}")
    
    if not api_key:
        print("\n❌ Error: No API key configured!")
        print("   Please set OPENAI_API_KEY environment variable or")
        print("   configure api_key in .shello/user-settings.json")
        return 1
    
    # Initialize client
    print(f"\n🔧 Initializing client...")
    client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
    print(f"✓ Client initialized with model: {client.get_current_model()}")
    
    # Test 1: Simple chat completion
    print(f"\n🧪 Test 1: Simple Chat Completion")
    print(f"   Sending message: 'Say hello in one sentence.'")
    
    messages = [
        {"role": "user", "content": "Say hello in one sentence."}
    ]
    
    try:
        response = client.chat(messages)
        content = response["choices"][0]["message"]["content"]
        print(f"✓ Response received:")
        print(f"   {content}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    # Test 2: Model switching
    print(f"\n🧪 Test 2: Model Switching")
    original_model = client.get_current_model()
    print(f"   Current model: {original_model}")
    
    new_model = "gpt-4o-mini"
    client.set_model(new_model)
    print(f"   Switched to: {client.get_current_model()}")
    
    client.set_model(original_model)
    print(f"   Switched back to: {client.get_current_model()}")
    print(f"✓ Model switching works correctly")
    
    # Test 3: Streaming
    print(f"\n🧪 Test 3: Streaming Chat Completion")
    print(f"   Sending message: 'Count from 1 to 3.'")
    
    messages = [
        {"role": "user", "content": "Count from 1 to 3, one number per line."}
    ]
    
    try:
        print(f"   Streaming response: ", end="", flush=True)
        chunk_count = 0
        for chunk in client.chat_stream(messages):
            chunk_count += 1
            if chunk["choices"] and chunk["choices"][0].get("delta", {}).get("content"):
                content = chunk["choices"][0]["delta"]["content"]
                print(content, end="", flush=True)
        print(f"\n✓ Received {chunk_count} chunks")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    print(f"\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
