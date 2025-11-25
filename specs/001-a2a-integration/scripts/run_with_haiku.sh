#!/bin/bash
# Helper script to run tau2 benchmarks with Claude 3 Haiku (cost-effective)
#
# Usage:
#   ./run_with_haiku.sh airline
#   ./run_with_haiku.sh retail --num-trials 3
#   ./run_with_haiku.sh telecom --max-steps 50

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not set in .env"
    exit 1
fi

# Get domain from first argument
DOMAIN="${1}"
if [ -z "$DOMAIN" ]; then
    echo "Error: Please specify a domain (airline, retail, telecom, or mock)"
    echo "Usage: ./run_with_haiku.sh <domain> [additional tau2 args]"
    exit 1
fi

# Shift to get remaining arguments
shift

# Run tau2 with Claude 3 Haiku
echo "Running tau2 benchmark on domain: $DOMAIN"
echo "Using model: claude-3-haiku-20240307 (via Anthropic)"
echo ""

tau2 run "$DOMAIN" \
  --agent llm_agent \
  --agent-llm "claude-3-haiku-20240307" \
  "$@"