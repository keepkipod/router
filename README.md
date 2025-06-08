# Cell Router - Kubernetes Production Simulation

A production-grade Kubernetes system simulating a multi-cell architecture with intelligent request routing, observability, and GitOps deployment. The system consists of a Python-based router that directs traffic to three independent NGINX cells based on request payload, with monitoring via Prometheus/Grafana and automated deployment through ArgoCD.

## Architecture Overview

- **Router Service**: FastAPI application that inspects request body and routes to appropriate NGINX cell
- **3 NGINX Cells**: Independent deployments serving as backend services
- **Observability Stack**: Prometheus, Grafana, AlertManager with custom dashboards and alerts
- **GitOps**: ArgoCD managing all deployments with proper dependency ordering
- **Local Kubernetes**: Kind cluster with 3 worker nodes

## Quick Start

### 1. Setup Dependencies

(tested on Macbook Pro with M3 + Colima + KinD)

CLI tools required to be installed:
[KinD](https://kind.sigs.k8s.io/), [Kubectl](https://kubernetes.io/docs/reference/kubectl/), [ArgoCD](https://argo-cd.readthedocs.io/en/stable/getting_started/#2-download-argo-cd-cli) & [go-task](https://taskfile.dev/)

```bash
# Clone the repository
git clone https://github.com/keepkipod/router.git
cd router

# If needed, for macOS with Colima (if not using Docker Desktop)
colima start --cpu 6 --memory 12 --kubernetes
```

### 2. Deploy Everything

```bash
# This will:
# - Create Kind cluster
# - Install ArgoCD
# - Deploy all applications in correct order
# - Build and load router image
task deploy-all-argocd
```

## Testing the System

### Access Points

```bash
# Router API (via Ingress)
task port-forward-ingress
# Access: http://localhost:8080

# ArgoCD UI
task port-forward-argocd
# Access: http://localhost:8081
# Username: admin
# In order to obtain Password, execute: task get-argocd-password

# Grafana Dashboards
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# Access: http://localhost:3000
# Username: admin / Password: admin

# Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Access: http://localhost:9090

# AlertManager
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093
# Access: http://localhost:9093
```

### Test Router Functionality

```bash
# Route to Cell 1
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-1" \
  -d '{"cellID": "1"}'

# Route to Cell 2
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-2" \
  -d '{"cellID": "2"}'

# Test invalid cell (should return 422)
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-1" \
  -d '{"cellID": "99"}'

# Health check
curl http://localhost:8080/health

# View metrics
curl http://localhost:8080/metrics
```

### Load Testing

```bash
# Run the fuzzy load test to generate various traffic patterns
python scripts/fuzzy-load-test.py

# This will generate:
# - Normal traffic to all cells
# - Burst traffic patterns
# - Invalid requests
# - Authentication failures
# - Shows real-time statistics
```

## Monitoring

### Grafana Dashboards

After port-forwarding to Grafana (port 3000):

1. **Cell Router - Complete Monitoring**: Shows router metrics with golden signals
2. **NGINX Cells - Golden Signals**: Displays per-cell NGINX metrics
3. **Cell Router & NGINX - Combined Overview**: Unified view of the entire system

### Prometheus Alerts

View active alerts at http://localhost:9090/alerts

Key alerts configured:
- `RouterHighErrorRate`: >5% errors for any cell
- `RouterCellRoutingFailure`: Upstream connection failures
- `NginxCellDown`: NGINX instance unavailable
- `RouterHighP99Latency`: P99 latency >3s

### AlertManager

Check firing alerts and silences at http://localhost:9093

## Implementation Notes

### Areas for Improvement

Given more time, I would implement:

1. **Security Enhancements**
   - Sealed Secrets operator for encrypted secrets in Git
   - Network policies properly configured (currently disabled due to DNS issues)
   - mTLS between services

2. **Scaling & Performance**
   - KEDA for autoscaling based on custom metrics
   - Rate limiting per API key

3. **Production Readiness**
   - Distroless container images
   - Proper ingress rate limiting
   - External DNS configuration
   - Cert-manager - TLS

4. **Better Observability**
   - Real latency metrics from NGINX (requires additional modules)
   - Business metrics and SLI/SLO dashboards
   - Log aggregation with Loki

### Known Issues

- ArgoCD sync waves don't wait for resources to be ready (worked around with manual ordering)
- NetworkPolicy blocks some legitimate traffic when enabled
- Resource constraints with Colima require careful allocation

## Cleanup

```bash
# Destroy local kind cluster
task clean
```