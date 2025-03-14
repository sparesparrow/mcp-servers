#!/bin/bash
# End-to-End Test Runner for Mermaid MCP Server
# This script runs both direct server tests and Claude Desktop integration tests

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Print header
function print_header() {
  echo
  echo -e "${BLUE}=================================================================="
  echo -e "  $1  "
  echo -e "==================================================================${RESET}"
  echo
}

# Check if API key is set
if [[ -z "${ANTHROPIC_API_KEY}" ]]; then
  echo -e "${RED}ERROR: ANTHROPIC_API_KEY environment variable is not set!"
  echo -e "Please set your API key first:${RESET}"
  echo "  export ANTHROPIC_API_KEY=your-api-key-here"
  exit 1
fi

# Check if python is available
if ! command -v python &> /dev/null; then
  echo -e "${RED}ERROR: Python is not installed or not in PATH!${RESET}"
  exit 1
fi

# Make sure we're in the project root
cd "$(dirname "$0")"

# Check for dependencies
print_header "CHECKING DEPENDENCIES"
echo -e "${YELLOW}Installing required packages...${RESET}"
pip install -r requirements.txt

# Run server test
print_header "RUNNING SERVER TESTS"
echo -e "${YELLOW}Testing direct MCP server functionality...${RESET}"
python e2e_test.py

# Check if Claude Desktop is running
print_header "CHECKING CLAUDE DESKTOP"
echo -e "${YELLOW}Checking if Claude Desktop is running...${RESET}"

if curl -s http://localhost:3000/health | grep -q "ok"; then
  echo -e "${GREEN}Claude Desktop is running.${RESET}"
else
  echo -e "${RED}ERROR: Claude Desktop does not appear to be running at http://localhost:3000"
  echo -e "Please start Claude Desktop and ensure it's running on the default port.${RESET}"
  exit 1
fi

# Run Claude Desktop integration test
print_header "RUNNING CLAUDE DESKTOP INTEGRATION TESTS"
echo -e "${YELLOW}Testing integration with Claude Desktop...${RESET}"
python test_claude_integration.py

# Summarize test results
print_header "TEST RESULTS"
echo -e "${GREEN}All end-to-end tests completed successfully!${RESET}"
echo
echo "Test outputs are available in these directories:"
echo "  - $(pwd)/e2e_test_output (server tests)"
echo "  - $(pwd)/claude_integration_test (Claude Desktop tests)"
echo

exit 0 