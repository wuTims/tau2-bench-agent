#!/bin/bash
#
# Start the simple Nebius agent server on localhost:8001
#
# Usage:
#   ./run_simple_agent.sh [PORT]
#
# Environment Variables:
#   NEBIUS_API_KEY - Required. Your Nebius API key.
#   NEBIUS_API_BASE - Optional. Defaults to https://api.tokenfactory.nebius.com/v1/

set -e

# Default configuration
DEFAULT_PORT=8001
PORT="${1:-$DEFAULT_PORT}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Simple Nebius Agent Server"
echo "========================================="
echo ""

# Check if NEBIUS_API_KEY is set
if [ -z "$NEBIUS_API_KEY" ]; then
    echo -e "${RED}Error: NEBIUS_API_KEY environment variable is not set${NC}"
    echo ""
    echo "Please set your Nebius API key:"
    echo "  export NEBIUS_API_KEY='your-api-key-here'"
    echo ""
    echo "Get your API key from: https://tokenfactory.nebius.com/"
    exit 1
fi

echo -e "${GREEN}✓${NC} NEBIUS_API_KEY is set"

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}Error: Port $PORT is already in use${NC}"
    echo ""
    echo "Process using port $PORT:"
    lsof -Pi :$PORT -sTCP:LISTEN
    echo ""
    echo "To kill the process:"
    echo "  kill \$(lsof -t -i:$PORT)"
    echo ""
    echo "Or use a different port:"
    echo "  $0 8002"
    exit 1
fi

echo -e "${GREEN}✓${NC} Port $PORT is available"
echo ""

# Set default API base if not provided
if [ -z "$NEBIUS_API_BASE" ]; then
    export NEBIUS_API_BASE="https://api.tokenfactory.nebius.com/v1/"
    echo "Using default NEBIUS_API_BASE: $NEBIUS_API_BASE"
else
    echo "Using custom NEBIUS_API_BASE: $NEBIUS_API_BASE"
fi
echo ""

# Check if adk is installed
if ! command -v adk &> /dev/null; then
    echo -e "${RED}Error: adk command not found${NC}"
    echo ""
    echo "Please install the project dependencies:"
    echo "  pip install -e ."
    exit 1
fi

echo -e "${GREEN}✓${NC} ADK CLI is installed"
echo ""

# Check if simple_nebius_agent directory exists
AGENT_DIR="simple_nebius_agent"
if [ ! -d "$AGENT_DIR" ]; then
    echo -e "${RED}Error: $AGENT_DIR directory not found${NC}"
    echo ""
    echo "Please run this script from the project root:"
    echo "  cd /path/to/tau2-bench-agent"
    echo "  ./specs/001-a2a-integration/scripts/run_simple_agent.sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} Agent directory found: $AGENT_DIR"
echo ""

echo "========================================="
echo "Starting Agent Server"
echo "========================================="
echo ""
echo "Configuration:"
echo "  Agent: simple_nebius_agent"
echo "  Model: meta-llama/Meta-Llama-3.1-8B-Instruct"
echo "  Port: $PORT"
echo "  Endpoint: http://localhost:$PORT"
echo ""
echo "Agent Card URL:"
echo "  http://localhost:$PORT/a2a/simple_nebius_agent/.well-known/agent-card.json"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""
echo "========================================="
echo ""

# Start the ADK server with A2A support
# Note: Pass current directory (parent of agent dirs), not agent dir itself
adk api_server --a2a . --port "$PORT"
