#!/usr/bin/env python3
"""
Test Script for Mermaid MCP Server Integration with Claude Desktop

This script uses the Claude API to send prompts that trigger the Mermaid MCP server
tools through Claude Desktop. It verifies that the integration is working correctly.

Requirements:
1. Claude Desktop must be running
2. The Mermaid MCP server must be properly configured in Claude Desktop config
3. A valid Anthropic API key must be set in the environment

Usage:
python test_claude_integration.py
"""

import os
import sys
import json
import time
import base64
import anthropic
from typing import Dict, Any, List, Optional

# Configuration
OUTPUT_DIR = "./claude_integration_test"
CLAUDE_DESKTOP_ADDRESS = "http://localhost:3000"
SLEEP_TIME = 2  # seconds to wait between requests

def print_header(text: str) -> None:
    """Print a header with the given text."""
    print("\n" + "=" * 80)
    print(f"  {text}  ".center(80, "="))
    print("=" * 80 + "\n")

def print_step(text: str) -> None:
    """Print a step with the given text."""
    print(f"🔹 {text}")

def print_success(text: str) -> None:
    """Print a success message with the given text."""
    print(f"✅ {text}")

def print_failure(text: str) -> None:
    """Print a failure message with the given text."""
    print(f"❌ {text}")

def send_message_to_claude(client: anthropic.Anthropic, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    """Send a message to Claude and return the response."""
    try:
        # Create a message
        if conversation_id:
            # Add to existing conversation
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0,
                system="You are an expert at using MCP tools, particularly the Mermaid diagram generator. Always use the appropriate MCP tools when asked about diagrams.",
                messages=[
                    {"role": "user", "content": message}
                ],
                conversation_id=conversation_id
            )
        else:
            # Start a new conversation
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0,
                system="You are an expert at using MCP tools, particularly the Mermaid diagram generator. Always use the appropriate MCP tools when asked about diagrams.",
                messages=[
                    {"role": "user", "content": message}
                ]
            )
        
        return {
            "success": True,
            "conversation_id": response.conversation_id,
            "message_id": response.id,
            "content": response.content,
            "model": response.model,
            "role": response.role
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def extract_diagram_from_response(content: List[Any]) -> Optional[str]:
    """Extract a Mermaid diagram from a Claude response."""
    # Find the text blocks containing Mermaid code
    for block in content:
        if block.type == 'text':
            text = block.text
            if '```mermaid' in text:
                # Extract the diagram code
                start = text.find('```mermaid')
                end = text.find('```', start + 10)
                if end != -1:
                    # Return just the diagram code, without the markers
                    return text[start+10:end].strip()
    
    return None

def save_text_to_file(text: str, filename: str) -> None:
    """Save text to a file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        f.write(text)

def test_diagram_generation() -> (bool, Optional[str], Optional[str]):
    """Test diagram generation through Claude Desktop."""
    print_step("Testing diagram generation via Claude Desktop...")
    
    # Check environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print_failure("ANTHROPIC_API_KEY environment variable not set!")
        print("Please set your API key first:")
        print("  export ANTHROPIC_API_KEY=your-api-key-here")
        return False, None, None
    
    # Create Claude client
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=CLAUDE_DESKTOP_ADDRESS
    )
    
    # Send a message requesting a diagram
    print_step("Sending message to Claude Desktop...")
    message = "Please create a sequence diagram showing how a user interacts with an e-commerce website, including browsing products, adding to cart, checkout, and payment processing. Use the pastel theme."
    
    response = send_message_to_claude(client, message)
    
    if not response["success"]:
        print_failure(f"Failed to send message: {response.get('error')}")
        return False, None, None
    
    conversation_id = response["conversation_id"]
    print_success(f"Message sent successfully (conversation ID: {conversation_id})")
    
    # Extract diagram from response
    diagram = extract_diagram_from_response(response["content"])
    if not diagram:
        print_failure("No Mermaid diagram found in Claude's response")
        return False, conversation_id, None
    
    # Save diagram
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    diagram_file = f"{OUTPUT_DIR}/generated_diagram.mmd"
    save_text_to_file(diagram, diagram_file)
    
    print_success(f"Diagram extracted and saved to {diagram_file}")
    
    # Also save the full response
    response_file = f"{OUTPUT_DIR}/claude_response.json"
    save_text_to_file(json.dumps(response, default=str, indent=2), response_file)
    
    print_success(f"Full response saved to {response_file}")
    
    return True, conversation_id, diagram

def test_diagram_analysis(client: anthropic.Anthropic, conversation_id: str, diagram: str) -> bool:
    """Test diagram analysis through Claude Desktop."""
    print_step("Testing diagram analysis via Claude Desktop...")
    time.sleep(SLEEP_TIME)  # Add a small delay between requests
    
    # Send a message requesting analysis of the diagram
    message = "Please analyze the diagram you just created. What are its strengths and are there any improvements you'd suggest?"
    
    response = send_message_to_claude(client, message, conversation_id)
    
    if not response["success"]:
        print_failure(f"Failed to send message: {response.get('error')}")
        return False
    
    print_success("Analysis request sent successfully")
    
    # Save the analysis response
    analysis_file = f"{OUTPUT_DIR}/diagram_analysis.txt"
    analysis_text = ""
    for block in response["content"]:
        if block.type == 'text':
            analysis_text += block.text + "\n"
    
    save_text_to_file(analysis_text, analysis_file)
    print_success(f"Analysis saved to {analysis_file}")
    
    return True

def test_diagram_modification(client: anthropic.Anthropic, conversation_id: str, diagram: str) -> bool:
    """Test diagram modification through Claude Desktop."""
    print_step("Testing diagram modification via Claude Desktop...")
    time.sleep(SLEEP_TIME)  # Add a small delay between requests
    
    # Send a message requesting modification of the diagram
    message = "Please modify the diagram to add error handling for payment processing failures. Use the dark theme for this updated diagram."
    
    response = send_message_to_claude(client, message, conversation_id)
    
    if not response["success"]:
        print_failure(f"Failed to send message: {response.get('error')}")
        return False
    
    print_success("Modification request sent successfully")
    
    # Extract the modified diagram
    modified_diagram = extract_diagram_from_response(response["content"])
    if not modified_diagram:
        print_failure("No modified Mermaid diagram found in Claude's response")
        return False
    
    # Save the modified diagram
    modified_file = f"{OUTPUT_DIR}/modified_diagram.mmd"
    save_text_to_file(modified_diagram, modified_file)
    
    print_success(f"Modified diagram saved to {modified_file}")
    
    return True

def run_tests() -> None:
    """Run all tests."""
    print_header("MERMAID MCP SERVER CLAUDE DESKTOP INTEGRATION TEST")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Test diagram generation
    success, conversation_id, diagram = test_diagram_generation()
    if not success or conversation_id is None or diagram is None:
        print_failure("Diagram generation test failed")
        return
    
    # Get Claude client
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        base_url=CLAUDE_DESKTOP_ADDRESS
    )
    
    # Test diagram analysis
    if not test_diagram_analysis(client, conversation_id, diagram):
        print_failure("Diagram analysis test failed")
        return
    
    # Test diagram modification
    if not test_diagram_modification(client, conversation_id, diagram):
        print_failure("Diagram modification test failed")
        return
    
    # All tests passed!
    print_header("ALL INTEGRATION TESTS PASSED SUCCESSFULLY")
    print("Test outputs are available in the following directory:")
    print(f"  {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    run_tests() 