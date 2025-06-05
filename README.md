# Cell Router - Kubernetes DevOps Project

A production-ready Kubernetes application demonstrating DevOps best practices including GitOps with ArgoCD, observability with Prometheus/Grafana, and secure multi-service routing.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        K8s Cluster (Kind)                    │
│                                                              │
│  ┌────────────┐    ┌──────────────────────────────────┐    │
│  │   ArgoCD   │───▶│  GitOps Repository               │    │
│  └────────────┘    └──────────────────────────────────┘    │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Applications                         │   │
│  │                                                       │   │
│  │  ┌──────────┐   ┌──────────────────────────────┐   │   │
│  │  │  Router  │──▶│  NGINX Deployments (1,2,3)   │   │   │
│  │  │   API    │   └──────────────────────────────┘   │   │
│  │  └──────────┘                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Observability Stack                      │   │
│  │  ┌────────────┐  ┌─────────┐  ┌───────────────┐   │   │
│  │  │ Prometheus │  │ Grafana │  │ Alert Manager │   │   │
│  │  └────────────┘  └─────────┘  └───────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker installed and running
- Git configured with your repository
- Linux/MacOS environment (or WSL2 for Windows)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/keepkipod/router.git
cd YOUR_REPO

# Install dependencies (kubectl, helm, kind, task, argocd-cli)
make install-dependencies
```

### 2. Update Repository URLs

Update your Git repository URL in these files:
- `k8s/argocd/app-of-apps.yaml`
- `k8s/argocd/applications/router.yaml`
- `k8s/argocd/applications/nginx-*.yaml`

### 3. Deploy Everything

```bash
# Deploy cluster with ArgoCD and all applications
task deploy-all-argocd

# Build and load router image
task build-app
```

### 4. Access Services

```bash
# ArgoCD UI (admin/[password shown])
task port-forward-argocd

# Router API
task port-forward-ingress
# Then access http://localhost:8080

# Grafana (admin/admin)
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
```

## 📁 Project Structure

```
.
├── Makefile                    # Dependency installation
├── Taskfile.yml               # Task automation
├── kind-config.yaml           # Kind cluster configuration
├── router/                    # Python router application
│   ├── Dockerfile            # Multi-stage, secure Docker build
│   ├── requirements.txt      # Python dependencies
│   └── src/
│       └── main.py          # FastAPI application
├── k8s/
│   ├── argocd/              # ArgoCD configuration
│   │   ├── argocd-values.yaml
│   │   ├── app-of-apps.yaml
│   │   └── applications/    # Application definitions
│   ├── nginx/               # NGINX deployments
│   │   ├── nginx-1/
│   │   ├── nginx-2/
│   │   └── nginx-3/
│   ├── router/              # Router K8s manifests
│   └── monitoring/          # Prometheus rules & dashboards
└── README.md

```

## 🛠️ Technical Implementation

### Router Application

**Technology Stack:**
- **FastAPI**: Modern, async Python web framework
- **Pydantic**: Data validation and settings management
- **httpx**: Async HTTP client for upstream requests
- **Prometheus Client**: Metrics exposition

**Key Features:**
- Cell-based routing logic
- Health and readiness probes
- Prometheus metrics (Golden Signals)
- Structured logging
- Async request handling
- Comprehensive error handling

**API Endpoints:**
- `POST /api/route` - Route requests based on cellID
- `GET /health` - Health check with upstream status
- `GET /ready` - Readiness probe
- `GET /metrics` - Prometheus metrics
- `GET /docs` - OpenAPI documentation

### Security Best Practices

1. **Container Security:**
   - Multi-stage builds for minimal attack surface
   - Non-root user execution (UID 1001)
   - Read-only root filesystem
   - No privilege escalation
   - Dropped all Linux capabilities

2. **Network Security:**
   - NetworkPolicies restricting traffic
   - Service-to-service communication only
   - CORS configured appropriately
   - Security headers (X-Frame-Options, etc.)

3. **Resource Management:**
   - Resource requests and limits
   - PodDisruptionBudgets
   - HorizontalPodAutoscaler
   - Liveness and readiness probes

### Observability Stack

**Metrics Collection:**
- Prometheus scraping all services
- ServiceMonitors for automatic discovery
- Custom application metrics

**Golden Signals Monitored:**
1. **Latency**: Request duration histograms
2. **Traffic**: Request rate by cell_id
3. **Errors**: 5xx error rates
4. **Saturation**: CPU, memory, connections

**Alerting Rules:**
- High error rates (>5%)
- High latency (P95 > 2s)
- Service downtime
- Resource exhaustion
- Upstream failures

### GitOps with ArgoCD

**Implementation:**
- App-of-Apps pattern for scalability
- Automated sync and self-healing
- Declarative application definitions
- Git as single source of truth

## 📊 Monitoring and Dashboards

### Accessing Grafana

```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
```
- URL: http://localhost:3000
- Username: admin
- Password: admin

### Available Dashboards

1. **Cell Router Dashboard**
   - Request rates by cell
   - Error rates and latency
   - Upstream health status

2. **NGINX Metrics**
   - Active connections
   - Request rates
   - Response times

3. **Kubernetes Dashboards**
   - Cluster health
   - Resource utilization
   - Pod status

## 🧪 Testing the Application

### Basic Routing Test

```bash
# Route to Cell 1
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -d '{"cellID": "1"}'

# Route to Cell 2
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -d '{"cellID": "2"}'

# Route to Cell 3
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -d '{"cellID": "3"}'
```

### Health Checks

```bash
# Router health with upstream status
curl http://localhost:8080/health

# Prometheus metrics
curl http://localhost:8080/metrics
```

## 🔧 Common Operations

### View Application Status

```bash
# ArgoCD applications
task get-apps-status

# All pods
kubectl get pods -A

# Router logs
task logs
```

### Manual Sync

```bash
# Sync all ArgoCD apps
task sync-all-apps
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment router -n router --replicas=5

# HPA will auto-scale based on load
kubectl get hpa -n router
```

## 🚨 Troubleshooting

### Common Issues

1. **ArgoCD Apps Not Syncing**
   - Check repository URL is correct
   - Ensure Git repository is accessible
   - Check ArgoCD logs: `kubectl logs -n argocd deployment/argocd-server`

2. **Router Can't Reach NGINX**
   - Verify NGINX pods are running: `kubectl get pods -n nginx`
   - Check NetworkPolicies: `kubectl get netpol -A`
   - Test DNS: `kubectl exec -it deployment/router -n router -- nslookup nginx-1.nginx.svc.cluster.local`

3. **Metrics Not Appearing**
   - Check ServiceMonitor: `kubectl get servicemonitor -n monitoring`
   - Verify Prometheus targets: Access Prometheus UI → Status → Targets

### Debug Commands

```bash
# Check all resources
kubectl get all -A

# Describe problematic pod
kubectl describe pod <pod-name> -n <namespace>

# Check events
kubectl get events -A --sort-by='.lastTimestamp'

# ArgoCD app details
kubectl get application -n argocd
kubectl describe application <app-name> -n argocd
```

## 🏆 Production Considerations

### For Real Production Deployment:

1. **Security Enhancements:**
   - Implement RBAC with least privilege
   - Add Pod Security Policies/Standards
   - Enable audit logging
   - Implement secrets management (Sealed Secrets, Vault)
   - Add admission controllers (OPA/Gatekeeper)

2. **High Availability:**
   - Multi-master control plane
   - Cross-AZ node distribution
   - Persistent storage for stateful components
   - Database for router state (Redis/PostgreSQL)

3. **Performance:**
   - Implement caching layer
   - Connection pooling for upstreams
   - Circuit breakers for resilience
   - Rate limiting per cell

4. **Monitoring:**
   - Add distributed tracing (Jaeger/Tempo)
   - Implement SLOs and error budgets
   - Add business metrics
   - Log aggregation (ELK/Loki)

5. **CI/CD Pipeline:**
   - Automated testing (unit, integration, e2e)
   - Security scanning (SAST, DAST, container scanning)
   - Automated rollbacks
   - Blue/green or canary deployments

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

**Note**: This is a demonstration project showcasing DevOps best practices. Always review and adapt security measures for your specific production requirements.