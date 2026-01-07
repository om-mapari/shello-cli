"""
Interactive test to find prompts that produce content + tool_calls.

Run this to test different prompts and see which ones produce both content and tool calls.
"""

import pytest
from shello_cli.agent.message_processor import MessageProcessor
from shello_cli.agent.tool_executor import ToolExecutor
from shello_cli.api.openai_client import ShelloClient
from shello_cli.utils.settings_manager import SettingsManager


# Test prompts - ordered from most likely to least likely to produce content + tool_calls
TEST_PROMPTS = [
    # High probability - asks for explanation
    {
        "name": "Explain + Execute",
        "prompt": "Explain what the 'pwd' command does, then run it to show me the current directory.",
        "expected": "content + tool_calls"
    },
    {
        "name": "Conversational Request",
        "prompt": "I need to know what directory I'm in. Can you help me check that?",
        "expected": "content + tool_calls"
    },
    {
        "name": "Step-by-step",
        "prompt": "Walk me through checking the current date using a bash command.",
        "expected": "content + tool_calls"
    },
    {
        "name": "Reasoning Request",
        "prompt": "Why is 'ls -la' useful? Show me by running it.",
        "expected": "content + tool_calls"
    },
    {
        "name": "Teaching Request",
        "prompt": "Teach me how to check disk usage by running the 'df -h' command.",
        "expected": "content + tool_calls"
    },
    {
        "name": "Comparison Request",
        "prompt": "What's the difference between 'echo $HOME' and 'pwd'? Run both to show me.",
        "expected": "content + tool_calls"
    },
    {
        "name": "Problem Solving",
        "prompt": "I want to see hidden files. What command should I use and can you run it?",
        "expected": "content + tool_calls"
    },
    
    # Medium probability
    {
        "name": "Polite Request",
        "prompt": "Could you please check what files are in the current directory?",
        "expected": "content + tool_calls (maybe)"
    },
    {
        "name": "Question Format",
        "prompt": "What files are in this directory?",
        "expected": "content + tool_calls (maybe)"
    },
    
    # Low probability - direct commands
    {
        "name": "Direct Command",
        "prompt": "Run 'ls -la'",
        "expected": "tool_calls only"
    },
    {
        "name": "Imperative",
        "prompt": "Execute: pwd",
        "expected": "tool_calls only"
    },
    {
        "name": "Minimal",
        "prompt": "pwd",
        "expected": "tool_calls only"
    },
]


@pytest.mark.integration
class TestContentPlusToolCallsPrompts:
    """Test different prompts to see which produce content + tool_calls."""
    
    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        settings_manager = SettingsManager.get_instance()
        api_key = settings_manager.get_api_key()
        base_url = settings_manager.get_base_url()
        model = settings_manager.get_current_model()
        
        if not api_key:
            pytest.skip("No API key configured")
        
        client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
        tool_executor = ToolExecutor()
        processor = MessageProcessor(
            client=client,
            tool_executor=tool_executor,
            max_tool_rounds=5
        )
        
        return {
            "processor": processor,
            "model": model
        }
    
    @pytest.mark.parametrize("test_case", TEST_PROMPTS, ids=[t["name"] for t in TEST_PROMPTS])
    def test_prompt(self, setup, test_case):
        """Test a specific prompt to see what it produces."""
        processor = setup["processor"]
        model = setup["model"]
        
        prompt = test_case["prompt"]
        expected = test_case["expected"]
        name = test_case["name"]
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant with bash access."},
            {"role": "user", "content": prompt}
        ]
        chat_history = []
        
        print(f"\n{'='*80}")
        print(f"🧪 Test: {name}")
        print(f"{'='*80}")
        print(f"Prompt: \"{prompt}\"")
        print(f"Expected: {expected}")
        print(f"Model: {model}")
        print(f"-"*80)
        
        # Process message
        entries = processor.process_message(messages, chat_history)
        
        # Analyze the response
        has_tool_calls = False
        has_content_before_tools = False
        
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                has_tool_calls = True
                content = msg.get("content")
                if content and content.strip():
                    has_content_before_tools = True
                    print(f"✅ BOTH PRESENT!")
                    print(f"   Content: \"{content[:100]}...\"")
                    print(f"   Tool: {msg['tool_calls'][0]['function']['name']}")
                else:
                    print(f"⚠️  Tool calls only (no content)")
                    print(f"   Tool: {msg['tool_calls'][0]['function']['name']}")
                break
        
        if not has_tool_calls:
            # Check if there's just a text response
            for msg in messages:
                if msg.get("role") == "assistant" and not msg.get("tool_calls"):
                    print(f"📝 Content only (no tool calls)")
                    print(f"   Response: \"{msg.get('content', '')[:100]}...\"")
                    break
        
        print(f"{'='*80}\n")
        
        # Don't assert - just observe the results
        # This is an exploratory test


def run_interactive_test():
    """Run the test interactively to see results."""
    print("\n" + "="*80)
    print("INTERACTIVE TEST: Finding prompts that produce content + tool_calls")
    print("="*80)
    print("\nThis will test various prompts to see which ones make the AI")
    print("produce BOTH explanatory text AND tool calls in the same response.\n")
    
    pytest.main([
        __file__,
        "-v",
        "-s",
        "-m", "integration",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_interactive_test()
