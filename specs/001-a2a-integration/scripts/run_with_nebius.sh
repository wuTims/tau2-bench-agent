#!/bin/bash
# Helper script to run tau2 benchmarks with Nebius Llama 3.1 8B model
#
# Usage:
#   ./run_with_nebius.sh airline
#   ./run_with_nebius.sh retail --num-trials 3
#   ./run_with_nebius.sh telecom --max-steps 50

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if NEBIUS_API_KEY is set
if [ -z "$NEBIUS_API_KEY" ]; then
    echo "Error: NEBIUS_API_KEY not set in .env"
    exit 1
fi

# Get domain from first argument
DOMAIN="${1}"
if [ -z "$DOMAIN" ]; then
    echo "Error: Please specify a domain (airline, retail, telecom, or mock)"
    echo "Usage: ./run_with_nebius.sh <domain> [additional tau2 args]"
    exit 1
fi

# Shift to get remaining arguments
shift

# Run tau2 with Nebius Llama 3.1 8B
echo "Running tau2 benchmark on domain: $DOMAIN"
echo "Using model: meta-llama/Meta-Llama-3.1-8B-Instruct (via Nebius)"
echo ""

tau2 run "$DOMAIN" \
  --agent llm_agent \
  --agent-llm "openai/meta-llama/Meta-Llama-3.1-8B-Instruct" \
  --agent-llm-args "{\"temperature\": 0.0, \"api_base\": \"$NEBIUS_API_BASE\", \"api_key\": \"$NEBIUS_API_KEY\"}" \
  "$@"