# GCP Deployment Guide for tau2-bench-agent

**Last Updated:** 2025-12-29

This guide covers building, deploying, and troubleshooting the tau2-bench-agent services on Google Cloud Platform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Secret Management](#secret-management)
4. [Building and Deploying](#building-and-deploying)
5. [Verifying Deployment](#verifying-deployment)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Prerequisites

### Required Tools

```bash
# Google Cloud SDK
gcloud --version

# Verify authentication
gcloud auth list

# Set project
gcloud config set project tau2agent
```

### Required Secrets

Before deployment, ensure these secrets exist in GCP Secret Manager:
- `google-api-key` - Gemini API key for LLM calls
- `dd-api-key` - Datadog API key (optional, for LLM Observability)
- `dd-site` - Datadog site (optional, e.g., `datadoghq.com`)

---

## Project Structure

```
tau2-bench-agent/
├── cloudbuild.yaml                    # Cloud Build configuration
├── tau2_agent/
│   ├── docker_setup/
│   │   ├── Dockerfile                 # Multi-stage Docker build
│   │   ├── requirements.txt           # Runtime dependencies
│   │   └── service.yaml               # Knative service definition
│   └── scripts/
│       ├── setup-secrets.sh           # Create GCP secrets
│       └── deploy.sh                  # Manual deployment script
└── simple_gemini_agent/
    └── docker_setup/
        ├── Dockerfile
        └── cloudbuild.yaml            # Separate build for mock agent
```

---

## Secret Management

### Creating Secrets

Use the setup script (interactive):

```bash
./tau2_agent/scripts/setup-secrets.sh
```

Or manually:

```bash
# Create secrets (values read from stdin for security)
echo -n "your-api-key" | gcloud secrets create google-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project=tau2agent

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding google-api-key \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@tau2agent.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=tau2agent
```

### Updating Secrets

```bash
# Update existing secret
echo -n "new-value" | gcloud secrets versions add google-api-key \
    --data-file=- \
    --project=tau2agent
```

---

## Building and Deploying

### Method 1: Cloud Build (Recommended)

Cloud Build automatically builds and deploys using `cloudbuild.yaml`:

```bash
# Build and deploy tau2-agent
gcloud builds submit --config=cloudbuild.yaml --project=tau2agent
```

This command:
1. Uploads source to Cloud Storage
2. Builds Docker image
3. Pushes to Artifact Registry
4. Deploys to Cloud Run

### Method 2: Manual Deployment

For more control or debugging:

```bash
# 1. Build image locally
docker build -f tau2_agent/docker_setup/Dockerfile -t tau2-agent .

# 2. Tag for Artifact Registry
docker tag tau2-agent us-west2-docker.pkg.dev/tau2agent/tau2-agent/tau2-agent:latest

# 3. Push to registry
docker push us-west2-docker.pkg.dev/tau2agent/tau2-agent/tau2-agent:latest

# 4. Deploy to Cloud Run
gcloud run deploy tau2-agent \
    --image=us-west2-docker.pkg.dev/tau2agent/tau2-agent/tau2-agent:latest \
    --region=us-west2 \
    --project=tau2agent \
    --set-secrets="GOOGLE_API_KEY=google-api-key:latest,DD_API_KEY=dd-api-key:latest,DD_SITE=dd-site:latest" \
    --set-env-vars="DD_TRACE_ENABLED=true,DD_LLMOBS_ENABLED=true,DD_LLMOBS_AGENTLESS_ENABLED=true"
```

### Forcing a Fresh Deployment

Cloud Run may not detect image changes if the tag hasn't changed. To force a new revision:

```bash
# Option 1: Use image digest
gcloud run deploy tau2-agent \
    --image=us-west2-docker.pkg.dev/tau2agent/tau2-agent/tau2-agent@sha256:DIGEST_HERE \
    --region=us-west2 \
    --project=tau2agent

# Option 2: Route traffic to new revision manually
gcloud run services update-traffic tau2-agent \
    --region=us-west2 \
    --project=tau2agent \
    --to-revisions=tau2-agent-00017-xyz=100
```

---

## Verifying Deployment

### Check Revision Status

```bash
# List all revisions
gcloud run revisions list \
    --service=tau2-agent \
    --region=us-west2 \
    --project=tau2agent \
    --format="table(name,creationTime)"

# Check current traffic routing
gcloud run services describe tau2-agent \
    --region=us-west2 \
    --project=tau2agent \
    --format='yaml(status.traffic)'
```

### Test Agent Endpoints

```bash
# Check agent card (health check)
curl -s https://tau2-agent-676371821546.us-west2.run.app/a2a/tau2_agent/.well-known/agent-card.json | jq .

# Run a quick evaluation test
PYTHONPATH=.:src uv run python src/experiments/datadog/scripts/traffic_generator.py \
    --domain airline \
    --num-tasks 1 \
    --num-trials 1 \
    --count 1
```

---

## Troubleshooting

### Viewing Logs

```bash
# Recent logs from latest revision
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="tau2-agent"' \
    --project=tau2agent \
    --limit=50 \
    --format="json" | jq -r '.[].textPayload // .[].jsonPayload.message // empty'

# Logs from specific revision
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.revision_name="tau2-agent-00017-g8z"' \
    --project=tau2agent \
    --limit=30

# Filter by severity
gcloud logging read 'resource.labels.service_name="tau2-agent" AND severity>=ERROR' \
    --project=tau2agent \
    --limit=20

# Search for specific errors
gcloud logging read 'resource.labels.service_name="tau2-agent" AND textPayload:"list index out of range"' \
    --project=tau2agent \
    --limit=10
```

### Common Issues

#### 1. "generator didn't stop after throw()"

**Cause:** Usually a secondary error from an underlying exception in async code.

**Debug Steps:**
1. Check logs for the primary error (often appears before this message)
2. Look for `IndexError`, `KeyError`, or other exceptions
3. The root cause is typically in the stack trace preceding this error

#### 2. "list index out of range" on Task 1+

**Cause:** Fixed in 2025-12-29. The `is_tool_call()` method was returning `True` for empty lists.

**Solution:** Ensure you're running the latest code with the fix in `src/tau2/data_model/message.py`.

#### 3. Cloud Run Not Using New Image

**Symptoms:** Deploy succeeds but behavior doesn't change.

**Solution:**
```bash
# Check which revision is serving traffic
gcloud run services describe tau2-agent --region=us-west2 --project=tau2agent --format='yaml(status.traffic)'

# Force traffic to new revision
gcloud run services update-traffic tau2-agent \
    --region=us-west2 \
    --project=tau2agent \
    --to-revisions=NEW_REVISION_NAME=100
```

#### 4. "failed to send traces to localhost:8126"

**Cause:** Expected warning when running ddtrace without a local Datadog Agent.

**Impact:** None - this is informational. LLM Observability still works via agentless mode.

#### 5. Cold Start Timeouts

**Symptoms:** First request after idle period times out.

**Solution:**
- Increase client timeout
- Configure minimum instances in Cloud Run
- The traffic generator already handles this with retry logic

### Rolling Back

```bash
# Route traffic back to previous revision
gcloud run services update-traffic tau2-agent \
    --region=us-west2 \
    --project=tau2agent \
    --to-revisions=tau2-agent-00015-qtj=100
```

---

## Security Best Practices

### CRITICAL: Never Log Sensitive Information

**DO NOT** log, print, or expose:
- API keys (GOOGLE_API_KEY, DD_API_KEY)
- Authentication tokens
- Secret values
- User credentials
- Personal data

**Examples of what NOT to do:**

```python
# WRONG - Never log secrets
logger.info(f"Using API key: {os.environ['GOOGLE_API_KEY']}")
logger.debug(f"Auth token: {auth_token}")
print(f"Secret: {secret_value}")

# WRONG - Never include secrets in error messages
raise ValueError(f"Invalid key: {api_key}")
```

**Correct approaches:**

```python
# RIGHT - Log presence, not value
logger.info("GOOGLE_API_KEY is set" if os.environ.get('GOOGLE_API_KEY') else "GOOGLE_API_KEY not set")

# RIGHT - Mask sensitive data
logger.debug(f"Using API key: {api_key[:4]}...{api_key[-4:]}")

# RIGHT - Generic error messages
raise ValueError("Invalid API key provided")
```

### Secret Handling Checklist

- [ ] Never hardcode secrets in source code
- [ ] Use GCP Secret Manager for all sensitive values
- [ ] Grant minimal IAM permissions (secretAccessor only)
- [ ] Rotate secrets periodically
- [ ] Audit secret access via Cloud Audit Logs
- [ ] Never commit `.env` files to version control

### Log Sanitization

The logging configuration automatically:
- Filters ADK experimental warnings
- Uses structured JSON format in GCP (no accidental secret leakage in console output)
- Separates evaluation metrics from sensitive operation details

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key (from Secret Manager) |
| `DD_API_KEY` | No | Datadog API key for LLM Observability |
| `DD_SITE` | No | Datadog site (default: datadoghq.com) |
| `DD_TRACE_ENABLED` | No | Enable ddtrace (default: true in container) |
| `DD_LLMOBS_ENABLED` | No | Enable LLM Observability (default: true) |
| `DD_LLMOBS_AGENTLESS_ENABLED` | No | Use agentless mode (default: true) |
| `DD_LLMOBS_ML_APP` | No | ML app name for LLM Obs |
| `DD_SERVICE` | No | Service name for tracing |
| `DD_ENV` | No | Environment name (production/demo) |
| `DD_HTTPX_DISTRIBUTED_TRACING` | No | Disable to avoid async conflicts |
| `PORT` | No | Server port (default: 8001) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

---

## Quick Reference

```bash
# Build and deploy
gcloud builds submit --config=cloudbuild.yaml --project=tau2agent

# Check revisions
gcloud run revisions list --service=tau2-agent --region=us-west2 --project=tau2agent

# View logs
gcloud logging read 'resource.labels.service_name="tau2-agent"' --project=tau2agent --limit=30

# Route traffic
gcloud run services update-traffic tau2-agent --region=us-west2 --project=tau2agent --to-revisions=REVISION=100

# Test endpoint
curl -s https://tau2-agent-676371821546.us-west2.run.app/a2a/tau2_agent/.well-known/agent-card.json
```
