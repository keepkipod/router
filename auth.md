# Router API Authentication Usage Guide

## How to Enable API Authentication

### 1. Using Helm Values (Recommended)

Create a values file for your environment:

```yaml
# router-values-with-auth.yaml
auth:
  enabled: true
  apiKeys:
    - key: "prod-key-abc123"
      client: "frontend-app"
    - key: "prod-key-xyz789"
      client: "mobile-app"
    - key: "prod-key-def456"
      client: "partner-integration"
```

Deploy with authentication:
```bash
helm upgrade --install router k8s/router-helm \
  -n router \
  -f router-values-with-auth.yaml
```

### 2. Using Existing Secret

First, create a secret manually:
```bash
# Create secret with JSON map
kubectl create secret generic custom-api-keys \
  -n router \
  --from-literal=api-keys.json='{
    "secure-key-1": "web-client",
    "secure-key-2": "mobile-client",
    "secure-key-3": "api-client"
  }'
```

Then reference it in values:
```yaml
# router-values-existing-secret.yaml
auth:
  enabled: true
  existingSecret: "custom-api-keys"
```

### 3. Different Environments

Development (no auth):
```yaml
# values-dev.yaml
auth:
  enabled: false
```

Staging (with test keys):
```yaml
# values-staging.yaml
auth:
  enabled: true
  apiKeys:
    - key: "staging-test-key"
      client: "test-client"
```

Production (with secure keys):
```yaml
# values-prod.yaml
auth:
  enabled: true
  existingSecret: "production-api-keys"  # Created separately
```

## Testing Authentication

### Without Authentication
```bash
# When auth.enabled: false
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -d '{"cellID": "1"}'
# Works without API key
```

### With Authentication
```bash
# When auth.enabled: true

# Without API key - returns 401
curl -i -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -d '{"cellID": "1"}'

# With valid API key - returns 200
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -H "X-API-Key: prod-key-abc123" \
  -d '{"cellID": "1"}'

# With invalid API key - returns 403
curl -i -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid-key" \
  -d '{"cellID": "1"}'
```

### Check Auth Status
```bash
# Health endpoint shows if auth is enabled
curl http://localhost:8080/health | jq .auth_enabled
```

## Managing API Keys

### Rotate Keys
```bash
# Update the secret
kubectl create secret generic router-api-keys \
  -n router \
  --from-literal=api-keys.json='{
    "new-key-1": "client1",
    "new-key-2": "client2"
  }' \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new keys
kubectl rollout restart deployment/router -n router
```

### Add New Client
```yaml
# Update values and upgrade
auth:
  enabled: true
  apiKeys:
    - key: "existing-key"
      client: "existing-client"
    - key: "new-client-key"      # New client
      client: "new-client-name"
```

## Monitoring API Usage

When authentication is enabled, metrics include client labels:
```promql
# Requests per client
sum(rate(router_requests_total[5m])) by (client)

# Error rate per client
sum(rate(router_requests_total{status=~"5.."}[5m])) by (client)
/ 
sum(rate(router_requests_total[5m])) by (client)
```

## Security Best Practices

1. **Never commit real API keys** to version control
2. **Use Kubernetes secrets** for production keys
3. **Rotate keys regularly** (monthly/quarterly)
4. **Monitor for unauthorized access** attempts
5. **Use different keys** for different environments
6. **Implement rate limiting** per API key (future enhancement)

## ArgoCD Integration

For GitOps with ArgoCD, create a sealed secret:
```bash
# Install sealed-secrets controller first
# Then create sealed secret
echo -n '{
  "prod-key-1": "client1",
  "prod-key-2": "client2"
}' | kubectl create secret generic router-api-keys \
  --dry-run=client \
  --from-file=api-keys.json=/dev/stdin \
  -o yaml | kubeseal -o yaml > k8s/router/sealed-secret.yaml
```

Then in ArgoCD application:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: router
spec:
  source:
    helm:
      values: |
        auth:
          enabled: true
          existingSecret: router-api-keys
```