# Dashboard Debug Guide

Practical guide for debugging and iterating on the tau2-bench Datadog dashboard.

## Dashboard Versions

| Version | Config File | Purpose |
|---------|-------------|---------|
| v1 | `dashboards.json` | Original health dashboard with time series |
| v2 | `dashboards_v2.json` | Model comparison dashboard (deprecated) |
| **v3** | `dashboards_v3.json` | Agent + Difficulty dashboard (default) |

**v3 is the default** - groups by `agent_endpoint` (not model), includes difficulty-based filtering, and uses observable efficiency metrics.

### v3 Changes from v2:
- Renamed "Model" to "Agent" throughout
- Removed confusing time series (Pass Rate by Model, Avg Reward by Model)
- Added `difficulty` template variable and filtering
- Added "Performance by Difficulty" section with complexity score
- Fixed efficiency widgets to use observable task metrics (`tau2.task.reward_per_turn`, etc.)
- Removed `tau2.model.*` metrics (were using simulator tokens, misleading)

### v3.1 Changes (Latest):
- **Replaced redundant "Avg Reward" leaderboard** - was essentially same as Pass Rate
- **Added difficulty-stratified leaderboards**:
  - "Hard/Expert Tasks (What Matters)" - the metric that differentiates agents
  - "Easy/Medium Tasks (Baseline)" - sanity check, most agents should do well here
  - "Pass^1 (Official tau2 Metric)" - industry-standard from tau2-bench paper
- **Added "Full Agent x Difficulty Matrix"** - shows every agent's performance across all difficulty tiers
- **Fixed SUCCESS_THRESHOLD** - now matches tau2 exactly (`1.0 - 1e-6` instead of `0.99`)
- **Reorganized efficiency section** - moved Tool Accuracy here, removed duplicate pass^1

## Quick Reference

| Resource | URL |
|----------|-----|
| Dashboard | https://us3.datadoghq.com/dashboard/sbn-qic-mun/tau2-bench-health-dashboard |
| Metrics Explorer | https://us3.datadoghq.com/metric/explorer |
| APM Traces | https://us3.datadoghq.com/apm/traces |
| LLM Observability | https://us3.datadoghq.com/llm/traces |

## Environment Setup

Required environment variables in `.env`:

```bash
DD_API_KEY=your_api_key
DD_APP_KEY=your_app_key      # Required for dashboard/monitor creation AND queries
DD_SITE=us3.datadoghq.com    # Your Datadog site
```

## Core Scripts

| Script | Purpose |
|--------|---------|
| `traffic_generator.py` | Run evaluations and generate traffic |
| `setup_datadog.py` | Create monitors, SLOs, dashboards |
| `emit_metrics.py` | Emit stored evaluation metrics to Datadog |

## Debug Workflow

### Step 1: Verify Metrics Exist

Before debugging dashboard widgets, confirm metrics are actually in Datadog:

```bash
# List all tau2 metrics
curl -s "https://api.us3.datadoghq.com/api/v1/metrics?filter=tau2" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" | jq '.metrics[]'
```

Expected output: List of `tau2.*` metric names.

### Step 2: Query Specific Metrics

Test that a specific metric returns data:

```bash
# Query tau2.task.reward over last hour
END=$(date +%s)
START=$((END - 3600))

curl -s "https://api.us3.datadoghq.com/api/v1/query?from=${START}&to=${END}&query=avg:tau2.task.reward{*}" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" | jq '.series[0].pointlist | length'
```

If returns 0 or null: No data points in the time range.

### Step 3: Count Local Evaluations

Check how many evaluation files exist locally:

```bash
# Count evaluation files
find data/evaluations -name "*.json" 2>/dev/null | wc -l

# View recent evaluation
ls -t data/evaluations/*.json | head -1 | xargs cat | jq '.summary'
```

### Step 4: Emit Metrics from Local Data

If metrics are missing, emit from stored evaluations:

```bash
# Emit all stored evaluation metrics
uv run python -m experiments.datadog.scripts.emit_metrics

# Check output for "Submitted X metrics"
```

### Step 5: Recreate Dashboard

If dashboard widgets are empty or broken:

```bash
# Create new dashboard (old one remains, delete manually)
uv run python -m experiments.datadog.scripts.setup_datadog --dashboard

# Output shows new dashboard ID and URL
```

## Common Issues

### Issue: Dashboard Widgets Empty

**Symptoms**: Dashboard loads but all widgets show "No data"

**Debug Steps**:
1. Check metrics exist (Step 1 above)
2. Verify time range in dashboard matches when data was emitted
3. Check widget queries match actual metric names and tags

**Root Cause History**: Widget definitions have nested `definition` structure that code wasn't handling. Fixed in `_convert_widgets` method.

### Issue: API Returns "Unauthorized"

**Symptoms**: `curl` queries return 403 or empty results

**Fix**: Ensure BOTH headers are set:
```bash
-H "DD-API-KEY: $DD_API_KEY"
-H "DD-APPLICATION-KEY: $DD_APP_KEY"  # Required for queries!
```

### Issue: Metrics Not Appearing

**Symptoms**: `emit_metrics.py` runs but metrics don't show in Explorer

**Debug**:
```bash
# Check emit_metrics output for errors
uv run python -m experiments.datadog.scripts.emit_metrics 2>&1 | grep -E "(ERROR|Submitted)"

# Verify site matches
echo $DD_SITE  # Should match your Datadog URL (e.g., us3.datadoghq.com)
```

### Issue: Wrong Widget Types Displayed

**Symptoms**: Widgets render as gray "note" placeholders

**Cause**: Unsupported widget type in `_convert_widgets`

**Debug**:
```bash
# Check what widget types are in config
cat src/experiments/datadog/configs/dashboards.json | jq '.. | .type? // empty' | sort | uniq -c
```

**Fix**: Add handler for missing widget type in `setup_datadog.py:_convert_widgets()`

## Dashboard Configuration

### Config Files

```
src/experiments/datadog/configs/
├── dashboards.json   # Dashboard layout and widget definitions
├── monitors.json     # Alert monitor definitions
└── slos.json         # SLO definitions
```

### Widget Structure

The JSON config uses nested `definition` blocks:

```json
{
  "widgets": [
    {
      "definition": {
        "type": "group",
        "title": "KPIs",
        "widgets": [
          {
            "definition": {
              "type": "query_value",
              "title": "Total Tasks",
              "requests": [{"q": "sum:tau2.task.count{*}"}]
            },
            "layout": {"x": 0, "y": 0, "width": 3, "height": 2}
          }
        ]
      },
      "layout": {"x": 0, "y": 0, "width": 12, "height": 4}
    }
  ]
}
```

### Supported Widget Types

| Type | Status | Notes |
|------|--------|-------|
| `note` | Supported | Static text/markdown |
| `group` | Supported | Container with nested widgets |
| `timeseries` | Supported | Line/bar charts over time |
| `query_value` | Supported | Single metric value |
| `toplist` | Supported | Ranked list of values |
| `slo` | Not yet | SLO status widget |
| `heatmap` | Not yet | Heat map visualization |

## Key Metrics and Tags

### Agent/Model Tags (v2)

All metrics now include `agent_model`, `agent_type`, and `agent_endpoint` tags for model/endpoint comparison:

| Tag | Description | Example Values |
|-----|-------------|----------------|
| `agent_model` | LLM model being evaluated | `o4-mini-2025-04-16`, `claude-3-7-sonnet-20250219` |
| `agent_type` | Agent implementation | `llm_agent_solo` |
| `agent_endpoint` | A2A agent endpoint (sanitized) | `agent.example.com`, `myagent-123.run.app` |
| `domain` | Evaluation domain | `airline`, `retail`, `telecom` |
| `evaluation_id` | Unique evaluation run | `eval-1766571137908-a03a16` |

Note: `agent_endpoint` is sanitized (protocol stripped, invalid chars replaced) for use as a Datadog tag.

### Environment Tags

All metrics include an `env` tag to distinguish between different runtime contexts:

| Env Value | When Used | Set By |
|-----------|-----------|--------|
| `test` | E2E tests | `tests/test_datadog_e2e/conftest.py` |
| `demo` | Manual testing | `DD_ENV=demo` environment variable |
| `dev` | Everything else including GCP deployment | `.env`, `service.yaml`, script defaults |

**Configuration Sources**:

| File | Sets | Purpose |
|------|------|---------|
| `.env` | `DD_ENV=dev` | Local development default |
| `service.yaml` | `DD_ENV=dev` | GCP Cloud Run deployment |
| `tracing.py` | default `dev` | APM tracing fallback |
| `emit_metrics.py` | default `dev` | Metrics emission fallback |

**Alignment Across Resources**:

| Resource | Env Filter | Notes |
|----------|------------|-------|
| Dashboard v3 | `$env` template variable (default: `dev`) | User-selectable |
| Monitors | `env:demo` hardcoded | Alerts on manual testing traffic |
| SLOs | `env:dev` | Tracks GCP deployment quality |

**Important**: When switching between environments, ensure you:
1. Set the dashboard `env` template variable to match your data
2. Use time ranges that include when metrics were emitted
3. Allow ~5 minutes for new tag values to be indexed by Datadog

### Efficiency Metrics (v2)

New per-model efficiency metrics for comparison:

| Metric | Description |
|--------|-------------|
| `tau2.model.tokens_per_task` | Average tokens used per task |
| `tau2.model.cost_per_task` | Average simulator cost per task |
| `tau2.model.reward_per_token` | Efficiency: reward earned per token |
| `tau2.model.cost_per_success` | Cost per successful task |

### Task Efficiency Metrics (v3)

Observable efficiency metrics per task:

| Metric | Description | Higher is Better? |
|--------|-------------|-------------------|
| `tau2.task.reward_per_turn` | Reward earned per conversation turn | Yes |
| `tau2.task.reward_per_second` | Reward earned per second (speed) | Yes |
| `tau2.task.reward_per_tool_call` | Reward earned per tool call | Yes |
| `tau2.task.turns_total` | Total conversation turns | No (fewer = more direct) |
| `tau2.task.tool_calls_total` | Total tool calls made | Context-dependent |
| `tau2.task.tool_accuracy` | Ratio of correct tool calls | Yes |
| `tau2.task.first_attempt_success` | 1.0 if success in ≤4 turns | Yes |

**Interpreting Tool Calls**:
- Fewer tool calls + success = efficient agent (knew exactly what to do)
- Fewer tool calls + failure = agent gave up early
- More tool calls + success = agent recovered from mistakes
- `reward_per_tool_call` normalizes this: higher = more efficient regardless of count

### Difficulty Metrics (v3)

Task difficulty is derived from observable evaluation criteria, NOT domain assumptions:

| Metric | Description |
|--------|-------------|
| `tau2.task.complexity_score` | Raw complexity score (actions*2 + nl_assertions*2 + checks) |

| Difficulty Tier | Complexity Score | Description |
|-----------------|-----------------|-------------|
| `unknown` | 0 | Incomplete evaluation data |
| `easy` | 1-2 | 1 action or assertion |
| `medium` | 3-5 | 2-3 actions/assertions |
| `hard` | 6-10 | 4-5 actions/assertions |
| `expert` | 11+ | 6+ actions/assertions |

**Note**: Difficulty is based purely on task evaluation criteria count, not domain. If `reward_info` lacks breakdown data (action_checks, nl_assertions, etc.), difficulty will be "unknown".

### Validation / Gaming Protection (v3)

The metrics system validates that simulations were produced by tau2 (not hand-crafted test data):

**Key Insight**: Tau2 is NOT awarding success to fake endpoints. The "fake" evaluations were **manually seeded test data** that was never run through tau2. They were written directly to the evaluation store during development.

**How Tau2 Evaluations Work**:
1. Tau2 runs actual agent/simulator conversations → produces `messages[]`
2. Tau2 evaluates against task criteria → produces `reward_info` with breakdown
3. Even in edge cases (no criteria, premature termination), tau2 includes `info` field

**Validation Criteria** (`is_valid_simulation` in `emit_metrics.py`):
1. Must have conversation messages (tau2 always produces these)
2. Must have tau2-specific fields in reward_info: `db_check`, `action_checks`, `nl_assertions`, `reward_basis`, `reward_breakdown`, or `info`

**What Gets Filtered** (hand-crafted test data):
- Empty `messages: []` (no actual agent interaction)
- Minimal `reward_info: {"reward": 1.0}` (no evaluation breakdown)
- Placeholder endpoints like `agent.example.com`

**Logging**:
```
WARNING - Evaluation eval-123: Filtered out 10/10 invalid simulations (missing messages or evaluation data)
WARNING - Skipping evaluation eval-123: all 10 simulations are invalid/fake
```

**Why This Matters**: Without validation, seeded test data pollutes real metrics. The validation ensures only genuine tau2 evaluations influence dashboards.

## Iteration Workflow

### Fast Dashboard Iteration

1. **Edit config**: Modify `configs/dashboards_v3.json` (or `dashboards_v2.json`/`dashboards.json` for older versions)
2. **Recreate**: `uv run python -m experiments.datadog.scripts.setup_datadog --dashboard --dashboard-version v3`
3. **Check**: Open new dashboard URL from output
4. **Delete old**: Remove previous dashboard in Datadog UI

### Test Metrics Flow

```bash
# Quick test: emit metrics + verify
uv run python -m experiments.datadog.scripts.demo --local --normal 1 --failure 0
```

### Full Demo (Setup + Traffic + Metrics)

```bash
# Complete workflow
uv run python -m experiments.datadog.scripts.demo --setup --normal 5 --failure 3
```

## API Reference

### Metrics API

```bash
# List metrics matching filter
GET /api/v1/metrics?filter=tau2

# Query metric data
GET /api/v1/query?from=START&to=END&query=QUERY
```

### Dashboard API

```bash
# List all dashboards
GET /api/v1/dashboard

# Get specific dashboard
GET /api/v1/dashboard/{dashboard_id}

# Create dashboard
POST /api/v1/dashboard
```

### Authentication Headers

| Header | Purpose | Required For |
|--------|---------|--------------|
| `DD-API-KEY` | API authentication | All requests |
| `DD-APPLICATION-KEY` | App-level access | Queries, dashboard CRUD |

## Useful Datadog URLs

Adjust `us3` to your site:

- **Metrics Explorer**: `https://us3.datadoghq.com/metric/explorer`
- **Dashboard List**: `https://us3.datadoghq.com/dashboard/lists`
- **Monitors**: `https://us3.datadoghq.com/monitors/manage`
- **SLOs**: `https://us3.datadoghq.com/slo/manage`
- **API Keys**: `https://us3.datadoghq.com/organization-settings/api-keys`
- **App Keys**: `https://us3.datadoghq.com/organization-settings/application-keys`

## Code References

| File | Key Functions |
|------|---------------|
| `setup_datadog.py:395` | `_convert_widgets()` - Widget conversion |
| `setup_datadog.py:331` | `create_dashboard()` - Dashboard creation |
| `emit_metrics.py:150` | `emit_evaluation_metrics()` - Metric submission |
| `dashboards.json` | Widget layout configuration |
