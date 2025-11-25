# Domain Evaluation Guide

Quick reference for evaluating the Nebius agent across different tau2-bench domains.

## Prerequisites

```bash
export NEBIUS_API_KEY="your-api-key-here"
```

## Quick Start

### Telecom Domain (Default)

```bash
./specs/001-a2a-integration/scripts/eval_domain.sh
```

Runs: `telecom` domain, 1 trial, all tasks

### Specific Domain

```bash
# Airline domain
./specs/001-a2a-integration/scripts/eval_domain.sh airline

# Retail domain
./specs/001-a2a-integration/scripts/eval_domain.sh retail

# Mock domain (fast test)
./specs/001-a2a-integration/scripts/eval_domain.sh mock
```

### With Multiple Trials

```bash
# Run 3 trials for better statistical significance
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 3
```

### Limited Tasks (Faster)

```bash
# Run only 5 tasks (good for quick testing)
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 1 5

# Run 10 tasks with 2 trials
./specs/001-a2a-integration/scripts/eval_domain.sh airline 2 10
```

## Available Domains

| Domain | Description | Typical Tasks | Difficulty |
|--------|-------------|---------------|------------|
| `mock` | Simple test scenarios | 5-10 | Easy |
| `airline` | Flight booking & management | 20-30 | Medium |
| `retail` | Product orders & returns | 20-30 | Medium |
| `telecom` | Technical support & billing | 25-35 | Medium |
| `telecom-workflow` | Complex multi-step workflows | 10-15 | Hard |

## Configuration Options

### Command Line

```bash
./eval_domain.sh [DOMAIN] [NUM_TRIALS] [NUM_TASKS]
```

**Parameters**:
- `DOMAIN`: Domain name (default: `telecom`)
- `NUM_TRIALS`: Number of trials per task (default: `1`)
- `NUM_TASKS`: Number of tasks to run (default: all tasks)

### Environment Variables

```bash
# Required
export NEBIUS_API_KEY="your-key"

# Optional
export PORT=8001                        # Agent port (default: 8001)
export KEEP_AGENT_RUNNING=true          # Keep agent after eval (default: false)
```

## Example Workflows

### Quick Sanity Check

```bash
# Run 5 mock tasks to verify everything works
./specs/001-a2a-integration/scripts/eval_domain.sh mock 1 5
```

Expected time: ~2-3 minutes

### Development Testing

```bash
# Test telecom domain with limited tasks
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 1 10
```

Expected time: ~10-15 minutes

### Production Evaluation

```bash
# Full airline evaluation with multiple trials
./specs/001-a2a-integration/scripts/eval_domain.sh airline 3
```

Expected time: ~1-2 hours

### Keep Agent Running for Multiple Evals

```bash
# Start agent and keep it running
export KEEP_AGENT_RUNNING=true

# Run multiple evaluations
./specs/001-a2a-integration/scripts/eval_domain.sh mock 1 5
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 1 10
./specs/001-a2a-integration/scripts/eval_domain.sh retail 1 10

# Stop agent manually
kill $(lsof -t -i:8001)
```

## Understanding Results

### Output Files

After evaluation, check for:
- **Logs**: Console output shows task-by-task progress
- **Metrics**: Success rates, average latency, token usage
- **Trajectories**: Detailed conversation logs (if saved)

### Key Metrics

- **Pass Rate**: Percentage of tasks completed successfully
- **Average Turns**: Number of conversation turns per task
- **Token Usage**: Total tokens (input + output)
- **Latency**: Average response time per turn

### Example Output

```
Task airline_001: PASS (5 turns, 842 tokens, 12.3s)
Task airline_002: FAIL (3 turns, timeout)
Task airline_003: PASS (4 turns, 623 tokens, 9.1s)

Summary:
  Domain: airline
  Pass Rate: 66.7% (2/3)
  Avg Turns: 4.0
  Total Tokens: 1465
```

## Troubleshooting

### Evaluation Takes Too Long

**Solution**: Limit number of tasks
```bash
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 1 5
```

### Agent Errors

**Check logs**:
```bash
tail -f /tmp/eval_agent.log
```

**Common issues**:
- API key invalid: Check `NEBIUS_API_KEY`
- Rate limiting: Reduce `NUM_TRIALS` or add delays
- Timeout: Increase task timeout in tau2 config

### Out of Memory

**Solution**: Run smaller batches
```bash
# Instead of full domain
./specs/001-a2a-integration/scripts/eval_domain.sh airline 1 10

# Run again with different tasks
# (use task IDs to specify which tasks)
```

## Performance Optimization

### Faster Testing

```bash
# Use mock domain for quick iterations
./specs/001-a2a-integration/scripts/eval_domain.sh mock 1 3

# Single trial only
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 1 10
```

### Better Results

```bash
# Multiple trials for statistical significance
./specs/001-a2a-integration/scripts/eval_domain.sh airline 3

# More trials = more reliable metrics
./specs/001-a2a-integration/scripts/eval_domain.sh retail 5
```

## Cost Estimation

**Nebius Llama 3.1 8B Pricing**: ~$0.20 per 1M tokens

**Estimated costs per evaluation**:
- Mock domain (5 tasks): ~$0.001
- Telecom domain (10 tasks): ~$0.01
- Full airline domain: ~$0.05-0.10
- Full evaluation with 3 trials: ~$0.15-0.30

**Formula**: `tokens_per_task × num_tasks × num_trials × $0.20 / 1M`

## Advanced Usage

### Custom Output Directory

```bash
# Run evaluation and save to specific directory
python -m tau2.cli run \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8001/a2a/simple_nebius_agent \
  --domain telecom \
  --num-trials 1 \
  --save-to results/telecom-eval
```

### Specific Task IDs

```bash
# Run only specific tasks (requires manual command)
python -m tau2.cli run \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8001/a2a/simple_nebius_agent \
  --domain airline \
  --task-ids task_001 task_005 task_010
```

### Compare Multiple Runs

```bash
# Run baseline
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 3 > baseline.log

# Make changes to agent...

# Run comparison
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 3 > comparison.log

# Compare results
diff baseline.log comparison.log
```

## Best Practices

1. **Start Small**: Use mock domain first
2. **Iterate Quickly**: Limit tasks during development
3. **Multiple Trials**: Use 3+ trials for production metrics
4. **Monitor Logs**: Watch `/tmp/eval_agent.log` for issues
5. **Cost Control**: Track token usage, limit trials
6. **Save Results**: Keep logs for comparison

## Next Steps

After running evaluations:

1. **Analyze Results**: Review pass rates and failure patterns
2. **Improve Agent**: Adjust instructions or tools
3. **Re-evaluate**: Compare before/after metrics
4. **Scale Up**: Run full evaluations with multiple trials

## References

- [tau2-bench Documentation](https://github.com/sierra-research/tau2-bench)
- [Domain Descriptions](https://github.com/sierra-research/tau2-bench/tree/main/data/tau2/domains)
- [ADK Agent Quickstart](adk-agent-quickstart.md)
- [Local Test Architecture](testing/local-test-architecture.md)
