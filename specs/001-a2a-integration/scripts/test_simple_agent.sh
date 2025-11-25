#!/bin/bash
#
# Test the simple Nebius agent with tau2-bench evaluation
#
# This script:
# 1. Starts the simple Nebius agent server
# 2. Waits for it to be ready
# 3. Runs a tau2-bench evaluation
# 4. Displays results
# 5. Cleans up
#
# Usage:
#   ./test_simple_agent.sh [DOMAIN] [NUM_TRIALS]
#
# Environment Variables:
#   NEBIUS_API_KEY - Required. Your Nebius API key.
#   NEBIUS_API_BASE - Optional. Defaults to https://api.tokenfactory.nebius.com/v1/

set -e

# Default configuration
DEFAULT_PORT=8001
DEFAULT_DOMAIN="mock"
DEFAULT_NUM_TRIALS=1

PORT="${PORT:-$DEFAULT_PORT}"
DOMAIN="${1:-$DEFAULT_DOMAIN}"
NUM_TRIALS="${2:-$DEFAULT_NUM_TRIALS}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    if [ -n "$AGENT_PID" ] && kill -0 "$AGENT_PID" 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}Stopping agent server (PID: $AGENT_PID)...${NC}"
        kill "$AGENT_PID" 2>/dev/null || true
        wait "$AGENT_PID" 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Agent stopped"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

echo "========================================="
echo "Simple Nebius Agent Test"
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
echo ""

# Check if agent directory exists
AGENT_DIR="simple_nebius_agent"
if [ ! -d "$AGENT_DIR" ]; then
    echo -e "${RED}Error: $AGENT_DIR directory not found${NC}"
    echo ""
    echo "Please run this script from the project root:"
    echo "  cd /path/to/tau2-bench-agent"
    echo "  ./specs/001-a2a-integration/scripts/test_simple_agent.sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} Agent directory found: $AGENT_DIR"
echo ""

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Warning: Port $PORT is already in use${NC}"
    echo "Assuming agent is already running..."
    AGENT_ALREADY_RUNNING=true
else
    AGENT_ALREADY_RUNNING=false
fi
echo ""

# Start agent if not already running
if [ "$AGENT_ALREADY_RUNNING" = false ]; then
    echo "========================================="
    echo "Starting Agent Server"
    echo "========================================="
    echo ""
    echo "Configuration:"
    echo "  Port: $PORT"
    echo "  Endpoint: http://localhost:$PORT"
    echo ""

    # Start agent in background
    # Note: Pass current directory (parent of agent dirs), not agent dir itself
    adk api_server --a2a . --port "$PORT" > /tmp/simple_agent.log 2>&1 &
    AGENT_PID=$!

    echo -e "${GREEN}✓${NC} Agent started (PID: $AGENT_PID)"
    echo "  Log file: /tmp/simple_agent.log"
    echo ""

    # Wait for agent to be ready
    echo -e "${BLUE}Waiting for agent to be ready...${NC}"
    MAX_RETRIES=30
    RETRY_COUNT=0
    AGENT_READY=false

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s -f "http://localhost:$PORT/a2a/simple_nebius_agent/.well-known/agent-card.json" > /dev/null 2>&1; then
            AGENT_READY=true
            break
        fi
        echo -n "."
        sleep 1
        RETRY_COUNT=$((RETRY_COUNT + 1))
    done
    echo ""

    if [ "$AGENT_READY" = false ]; then
        echo -e "${RED}Error: Agent failed to start within $MAX_RETRIES seconds${NC}"
        echo ""
        echo "Agent logs:"
        cat /tmp/simple_agent.log
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Agent is ready"
    echo ""
fi

# Verify agent card
echo "========================================="
echo "Verifying Agent"
echo "========================================="
echo ""
echo "Fetching agent card..."
AGENT_CARD=$(curl -s "http://localhost:$PORT/a2a/simple_nebius_agent/.well-known/agent-card.json")
echo "$AGENT_CARD" | jq '.' 2>/dev/null || echo "$AGENT_CARD"
echo ""
echo -e "${GREEN}✓${NC} Agent card retrieved successfully"
echo ""

# Run tau2-bench evaluation
echo "========================================="
echo "Running tau2-bench Evaluation"
echo "========================================="
echo ""
echo "Evaluation Configuration:"
echo "  Domain: $DOMAIN"
echo "  Agent Endpoint: http://localhost:$PORT"
echo "  Number of Trials: $NUM_TRIALS"
echo ""
echo -e "${BLUE}Starting evaluation...${NC}"
echo ""

# Run evaluation
python -m tau2.cli run \
    --agent a2a_agent \
    --agent-a2a-endpoint "http://localhost:$PORT/a2a/simple_nebius_agent" \
    --domain "$DOMAIN" \
    --num-trials "$NUM_TRIALS"

EVAL_EXIT_CODE=$?

echo ""
if [ $EVAL_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Evaluation completed successfully"
else
    echo -e "${RED}✗${NC} Evaluation failed with exit code: $EVAL_EXIT_CODE"
fi
echo ""

# Show summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "Agent Configuration:"
echo "  Name: simple_nebius_agent"
echo "  Model: meta-llama/Meta-Llama-3.1-8B-Instruct"
echo "  Port: $PORT"
echo ""
echo "Evaluation Configuration:"
echo "  Domain: $DOMAIN"
echo "  Number of Trials: $NUM_TRIALS"
echo "  Exit Code: $EVAL_EXIT_CODE"
echo ""

if [ "$AGENT_ALREADY_RUNNING" = false ]; then
    echo "Agent will be stopped automatically..."
else
    echo "Agent is still running on port $PORT"
    echo "To stop it manually:"
    echo "  kill \$(lsof -t -i:$PORT)"
fi
echo ""

exit $EVAL_EXIT_CODE
