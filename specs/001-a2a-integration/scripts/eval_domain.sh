#!/bin/bash
#
# Run domain evaluation with the simple Nebius agent
#
# Usage:
#   ./eval_domain.sh [DOMAIN] [NUM_TRIALS] [NUM_TASKS]
#
# Examples:
#   ./eval_domain.sh telecom 1 5           # Telecom domain, 1 trial, 5 tasks
#   ./eval_domain.sh airline 3             # Airline domain, 3 trials, all tasks
#   ./eval_domain.sh retail                # Retail domain, 1 trial, all tasks
#
# Environment Variables:
#   NEBIUS_API_KEY - Required. Your Nebius API key for both the agent and user simulator.
#   PORT - Optional. Server port (default: 8001)
#   LOG_LEVEL - Optional. Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
#   KEEP_AGENT_RUNNING - Optional. Set to "true" to keep agent running after eval

set -e

# Configuration
DEFAULT_PORT=8001
DEFAULT_DOMAIN="telecom"
DEFAULT_NUM_TRIALS=1
DEFAULT_NUM_TASKS=""  # Empty means all tasks

PORT="${PORT:-$DEFAULT_PORT}"
DOMAIN="${1:-$DEFAULT_DOMAIN}"
NUM_TRIALS="${2:-$DEFAULT_NUM_TRIALS}"
NUM_TASKS="${3:-$DEFAULT_NUM_TASKS}"
KEEP_RUNNING="${KEEP_AGENT_RUNNING:-false}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    if [ "$KEEP_RUNNING" = "false" ] && [ -n "$AGENT_PID" ] && kill -0 "$AGENT_PID" 2>/dev/null; then
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
echo "Domain Evaluation with Nebius Agent"
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

# Display configuration
echo "Evaluation Configuration:"
echo "  Domain: ${CYAN}$DOMAIN${NC}"
echo "  Number of Trials: ${CYAN}$NUM_TRIALS${NC}"
if [ -n "$NUM_TASKS" ]; then
    echo "  Number of Tasks: ${CYAN}$NUM_TASKS${NC}"
else
    echo "  Number of Tasks: ${CYAN}All tasks${NC}"
fi
echo "  Port: ${CYAN}$PORT${NC}"
echo ""

# Check if agent directory exists
AGENT_DIR="simple_nebius_agent"
if [ ! -d "$AGENT_DIR" ]; then
    echo -e "${RED}Error: $AGENT_DIR directory not found${NC}"
    echo ""
    echo "Please run this script from the project root:"
    echo "  cd /path/to/tau2-bench-agent"
    echo "  ./specs/001-a2a-integration/scripts/eval_domain.sh"
    exit 1
fi

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

    # Start agent in background
    adk api_server --a2a . --port "$PORT" > /tmp/eval_agent.log 2>&1 &
    AGENT_PID=$!

    echo -e "${GREEN}✓${NC} Agent started (PID: $AGENT_PID)"
    echo "  Log file: /tmp/eval_agent.log"
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
        cat /tmp/eval_agent.log
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Agent is ready"
    echo ""
else
    echo -e "${GREEN}✓${NC} Using existing agent on port $PORT"
    echo ""
fi

# Determine user LLM model
# Use Nebius model for user simulator (uses NEBIUS_API_KEY)
USER_LLM="openai/Qwen/Qwen3-30B-A3B-Thinking-2507"
USER_LLM_ARGS='{"base_url": "https://api.tokenfactory.nebius.com/v1/", "api_key": "'"$NEBIUS_API_KEY"'"}'
echo -e "${GREEN}✓${NC} Using Nebius Qwen3-30B-A3B-Thinking-2507 for user simulator"

# Build tau2 command
LOG_LEVEL="${LOG_LEVEL:-INFO}"
TAU2_CMD="python -m tau2.cli run \
    --agent a2a_agent \
    --agent-a2a-endpoint \"http://localhost:$PORT/a2a/simple_nebius_agent\" \
    --domain \"$DOMAIN\" \
    --num-trials $NUM_TRIALS \
    --user-llm \"$USER_LLM\" \
    --user-llm-args '$USER_LLM_ARGS' \
    --log-level \"$LOG_LEVEL\" \
    --a2a-debug"

if [ -n "$NUM_TASKS" ]; then
    TAU2_CMD="$TAU2_CMD --num-tasks $NUM_TASKS"
fi

# Run evaluation
echo "========================================="
echo "Running Domain Evaluation"
echo "========================================="
echo ""
echo -e "${BLUE}Command:${NC}"
echo "$TAU2_CMD"
echo ""
echo -e "${BLUE}Starting evaluation (this may take several minutes)...${NC}"
echo ""

# Execute evaluation
eval $TAU2_CMD

EVAL_EXIT_CODE=$?

echo ""
echo "========================================="
echo "Evaluation Complete"
echo "========================================="
echo ""

if [ $EVAL_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Evaluation completed successfully"
else
    echo -e "${RED}✗${NC} Evaluation failed with exit code: $EVAL_EXIT_CODE"
fi
echo ""

# Display summary
echo "Summary:"
echo "  Domain: $DOMAIN"
echo "  Number of Trials: $NUM_TRIALS"
if [ -n "$NUM_TASKS" ]; then
    echo "  Number of Tasks: $NUM_TASKS"
fi
echo "  Exit Code: $EVAL_EXIT_CODE"
echo ""

# Agent status
if [ "$AGENT_ALREADY_RUNNING" = false ]; then
    if [ "$KEEP_RUNNING" = "true" ]; then
        echo -e "${CYAN}Agent is still running on port $PORT${NC}"
        echo "To stop it manually:"
        echo "  kill $AGENT_PID"
        echo ""
        echo "Agent card URL:"
        echo "  http://localhost:$PORT/a2a/simple_nebius_agent/.well-known/agent-card.json"
    else
        echo -e "${YELLOW}Agent will be stopped automatically...${NC}"
    fi
else
    echo "Agent is still running on port $PORT"
    echo "To stop it manually:"
    echo "  kill \$(lsof -t -i:$PORT)"
fi
echo ""

# Show results location
echo "Results have been saved to the current directory."
echo "Check for simulation logs and metrics files."
echo ""

exit $EVAL_EXIT_CODE
