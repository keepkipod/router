Wavers:

No cloud = so no external secrets with some secret store as a backend
  Thus using clear text secrets inside the helm chart

If had more time I would implement the use of SOAPS sealed secrets operator to intiate secured secret for the API Key

The python app is critical, it inspects the body to determine the cell to direct the request to
because of that need to make it HA and so on which I did but if I had more time I would also add keda based on the metrics that prometheus scrapes anyway to increase replicas according to the amount of requests

If I had more time I would not choose kind but k3s instead as it is more light but I already had the Go Task prepared

With more time I would go with distroless image

Tried instate rate limit but got into troubles with it so skipped for now

Had many issues with argocd, turns out it's because I am using colima instead of docker desktop and limited resources
after some digging found out how to allocate more

When I was working on the python app with deploying all workloads via helm install manuually - the networkPolicy worked just fine
but when I moved on to work via GitOps, something went wrong. I wish to get back to it, but for now, to save time I will make it as:
networkPolicy:
  enabled: false
so I can get on with all other stuff

Still not sure why the apps are being deployed right away and not waiting to become ready before moving on to next sync-wave

Spent far too much time on fixing the release workflow so I haven't made it to fix the argocd app of apps

For conclusion, what could be done better:
Missing:

Some missing CI/CD pipeline
- How to implement: Add GitHub Actions workflow with:
  - Ssecurity scans
  - Semantic versioning with automatic releases
  - Update ArgoCD app manifests with new image tags

Weak security implementation
- How to implement: 
  - Use Sealed Secrets operator for encrypted API keys
  - Enable NetworkPolicies (fix DNS issues first)
  - Better RBAC policies for service accounts
  - Use distroless images

Limited high availability
- How to implement:
  - Increase router replicas to 3 minimum
  - Configure proper PodDisruptionBudgets
  - Add anti-affinity rules to spread pods across nodes
  - Implement circuit breakers in router code

Could setup Service Mesh
- How to implement:
  - Deploy Istio for:
    - Automatic mTLS
    - Advanced traffic management
    - Built-in observability
    - Circuit breaking/retries

No rate limiting
- How to implement:
  - Add rate limiting per API key in router

Incomplete testing strategy
- How to implement:
  - Add integration tests with Kind in CI
  - Implement load testing with k6/Locust
  - Add chaos engineering tests

Basic oservability
- How to implement:
  - Add distributed tracing with Jaeger
  - Implement structured logging with Loki
  - Create SLI/SLO dashboards
