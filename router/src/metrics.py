"""Prometheus metrics configuration."""
from prometheus_client import Counter, Histogram, CollectorRegistry

# Create registry
registry = CollectorRegistry()

# Define metrics
request_count = Counter(
    'router_requests_total',
    'Total number of requests by cell_id and status',
    ['cell_id', 'status', 'method', 'client'],
    registry=registry
)

request_duration = Histogram(
    'router_request_duration_seconds',
    'Request duration in seconds',
    ['cell_id', 'method'],
    registry=registry
)

upstream_errors = Counter(
    'router_upstream_errors_total',
    'Total number of upstream errors by cell_id',
    ['cell_id', 'upstream'],
    registry=registry
)

auth_failures = Counter(
    'router_auth_failures_total',
    'Total number of authentication failures',
    ['reason'],
    registry=registry
)
