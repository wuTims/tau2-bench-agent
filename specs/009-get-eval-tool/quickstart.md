# Quickstart: GetEvaluationResults Tool

**Feature Branch**: `009-get-eval-tool`
**Date**: 2025-12-27

## Overview

The updated `GetEvaluationResults` tool retrieves evaluation data from the EvaluationStore with support for filtering by domain, status, time range, and agent endpoint.

## Usage Examples

### List All Evaluations

```python
# Via LLM tool call
{"tool_call": {"name": "get_evaluation_results", "arguments": {"list_available": true}}}

# Response
{
    "evaluations": [
        {
            "evaluation_id": "eval-1703697600000-a1b2c3",
            "domain": "airline",
            "agent_endpoint": "https://my-agent.example.com",
            "status": "completed",
            "created_at": "2024-01-15T14:30:00Z",
            "completed_at": "2024-01-15T14:35:00Z",
            "summary": {
                "success_rate": 0.85,
                "total_tasks": 10,
                "successful": 8
            }
        }
    ],
    "total_count": 1,
    "filters_applied": {}
}
```

### Filter by Domain

```python
{"tool_call": {"name": "get_evaluation_results", "arguments": {
    "list_available": true,
    "domain": "airline"
}}}
```

### Filter by Time Range (Natural Language → LLM Conversion)

User says: *"Show me evaluations from yesterday"*

LLM converts to ISO 8601 (using system prompt's current time):

```python
{"tool_call": {"name": "get_evaluation_results", "arguments": {
    "list_available": true,
    "after": "2024-01-14T00:00:00Z",
    "before": "2024-01-15T00:00:00Z"
}}}
```

### Get Single Evaluation Details

```python
{"tool_call": {"name": "get_evaluation_results", "arguments": {
    "evaluation_id": "eval-1703697600000-a1b2c3"
}}}

# Response
{
    "evaluation_id": "eval-1703697600000-a1b2c3",
    "domain": "airline",
    "agent_endpoint": "https://my-agent.example.com",
    "status": "completed",
    "created_at": "2024-01-15T14:30:00Z",
    "completed_at": "2024-01-15T14:35:00Z",
    "state_history": [
        {"state": "submitted", "at": "2024-01-15T14:30:00Z"},
        {"state": "working", "at": "2024-01-15T14:30:01Z", "progress": 0},
        {"state": "completed", "at": "2024-01-15T14:35:00Z"}
    ],
    "request": {
        "user_llm": "gpt-4o",
        "num_trials": 1,
        "num_tasks": 10
    },
    "results": {
        "success_rate": 0.85,
        "total_tasks": 10,
        "successful": 8,
        "tasks": [
            {"task_id": "task_001", "success": true, "reward": 0.95}
        ]
    }
}
```

### Include Full Simulation Data

```python
{"tool_call": {"name": "get_evaluation_results", "arguments": {
    "evaluation_id": "eval-1703697600000-a1b2c3",
    "include_simulations": true
}}}

# Response includes results.simulations with full message history
```

### Filter Completed Only (Exclude In-Progress)

```python
{"tool_call": {"name": "get_evaluation_results", "arguments": {
    "list_available": true,
    "include_sessions": false
}}}
```

## System Prompt Integration

The agent's system prompt includes current UTC time for natural language interpretation:

```
You are tau2_agent, an evaluation service...

Current UTC time: 2024-01-15T14:30:00Z

When users ask for evaluations by relative time (e.g., "yesterday", "last week"),
convert to ISO 8601 timestamps for the get_evaluation_results tool.

Examples:
- "yesterday" → after: "2024-01-14T00:00:00Z", before: "2024-01-15T00:00:00Z"
- "last 24 hours" → after: "2024-01-14T14:30:00Z"
- "this week" → after: "2024-01-08T00:00:00Z" (Monday)
```

## Common Error Responses

### Invalid Evaluation ID

```python
{
    "error": "Evaluation not found: eval-invalid",
    "message": "No evaluation with this ID exists",
    "available_evaluations": ["eval-1703697600000-a1b2c3"]
}
```

### Invalid Timestamp Format

```python
{
    "error": "Invalid 'after' timestamp",
    "message": "Use ISO 8601 format (e.g., 2024-01-14T00:00:00Z)"
}
```

### Missing Required Parameter

```python
{
    "error": "Missing evaluation_id",
    "message": "Provide evaluation_id or set list_available=true"
}
```

## Implementation Checklist

- [ ] Tool reads from EvaluationStore (not simulations/)
- [ ] Tool supports domain filter
- [ ] Tool supports status filter
- [ ] Tool supports after/before ISO 8601 timestamps
- [ ] Tool supports agent_endpoint filter
- [ ] Tool supports limit parameter (1-100)
- [ ] Tool supports include_simulations parameter
- [ ] Tool supports include_sessions parameter
- [ ] System prompt includes current UTC time
- [ ] Response includes filters_applied metadata
