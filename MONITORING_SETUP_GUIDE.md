# Monitoring Setup Guide

This guide explains how to deploy and access the monitoring stack (Prometheus, Grafana, Alertmanager) for the Dynamic Pod Lifecycle Management System.

## Overview

The monitoring stack provides:
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards
- **Alertmanager**: Alert routing and notifications

## Prerequisites

- kubectl configured to access your EKS cluster
- Monitoring manifests in `k8s-manifests/` directory

## Deployment Steps

### 1. Deploy the Monitoring Stack

Run the deployment script:

```powershell
.\deploy-monitoring.ps1
```

This will:
- Create the `monitoring` namespace
- Deploy Prometheus with RBAC and alert rules
- Deploy Alertmanager with configuration
- Deploy Grafana with pre-configured dashboards
- Wait for all components to be ready

### 2. Verify Deployment

Check that all pods are running:

```powershell
kubectl get pods -n monitoring
```

Expected output:
```
NAME                            READY   STATUS    RESTARTS   AGE
prometheus-xxxxxxxxxx-xxxxx     1/1     Running   0          2m
alertmanager-xxxxxxxxx-xxxxx    1/1     Running   0          2m
grafana-xxxxxxxxxx-xxxxx        1/1     Running   0          2m
```

Check services:

```powershell
kubectl get svc -n monitoring
```

## Accessing the Monitoring Services

### Access Prometheus

```powershell
.\access-prometheus.ps1
```

Then open: http://localhost:9090

**What to check:**
- Go to Status → Targets to see scrape targets
- Go to Alerts to see configured alert rules
- Query metrics like `session_pods_active`

### Access Grafana

```powershell
.\access-grafana.ps1
```

Then open: http://localhost:3000

**Login credentials:**
- Username: `admin`
- Password: `admin`

**Pre-configured Dashboards:**
1. **Pod Lifecycle Dashboard**: Shows active sessions, pod creation/deletion rates, request latency
2. **Karpenter Dashboard**: Shows node provisioning and scaling metrics

### Access Alertmanager

```powershell
.\access-alertmanager.ps1
```

Then open: http://localhost:9093

**What to check:**
- View active alerts
- Check alert routing configuration
- Test alert notifications

## Key Metrics to Monitor

### Pod Lifecycle Metrics

- `session_pods_active` - Current number of active session pods
- `session_pod_creation_duration_seconds` - Time to create a pod
- `session_pod_creation_total` - Total pods created (by status)
- `session_pod_deletion_total` - Total pods deleted (by reason)
- `session_idle_timeout_total` - Total idle timeouts

### Request Metrics

- `session_request_duration_seconds` - Request processing time
- `session_request_total` - Total requests (by endpoint, method, status)
- `session_routing_errors_total` - Routing errors (by reason)

### Resource Metrics

- `session_redis_operations_total` - Redis operations (by operation, status)
- `session_vault_operations_total` - Vault operations (by operation, status)
- `session_kubernetes_api_calls_total` - Kubernetes API calls (by operation, status)

## Alert Rules

The following alerts are pre-configured:

### Critical Alerts
- **PodCreationFailureRate**: Pod creation failure rate > 10% for 5 minutes
- **LifecycleControllerDown**: Lifecycle Controller unavailable
- **APIGatewayDown**: API Gateway unavailable
- **VaultSealed**: Vault is sealed
- **RedisDown**: Redis unavailable

### Warning Alerts
- **HighPodCreationLatency**: Pod creation latency > 30s (p95)
- **HighPodDeletionRate**: Pod deletion rate > 50/min
- **KarpenterProvisioningFailures**: Karpenter failing to provision nodes
- **CertificateExpiringSoon**: Certificate expiring in < 7 days

## Grafana Dashboard Guide

### Pod Lifecycle Dashboard

**Panels:**
1. **Active Sessions** (Gauge): Current number of active session pods
2. **Pod Creation Rate** (Graph): Rate of pod creation over time
3. **Pod Deletion Rate by Reason** (Graph): Deletion rate categorized by reason
4. **Request Latency** (Heatmap): Distribution of request latencies
5. **Error Rate** (Graph): Rate of errors over time
6. **Top Sessions by Request Count** (Table): Most active sessions

### Karpenter Dashboard

**Panels:**
1. **Node Count** (Graph): Number of nodes over time
2. **Node Utilization** (Graph): CPU and memory utilization
3. **Karpenter Provisioning Activity** (Graph): Node provisioning events
4. **Pending Pods** (Graph): Pods waiting for nodes

## Troubleshooting

### Prometheus Not Scraping Targets

Check if the lifecycle-controller and api-gateway services are exposing metrics:

```powershell
kubectl get svc -n sessions
kubectl port-forward -n sessions svc/lifecycle-controller 8080:8080
# Visit http://localhost:8080/metrics
```

### Grafana Dashboard Not Showing Data

1. Check Prometheus data source in Grafana:
   - Go to Configuration → Data Sources
   - Verify Prometheus URL: `http://prometheus:9090`
   - Click "Test" to verify connection

2. Check if metrics are being collected:
   - Open Prometheus UI
   - Query for `session_pods_active`
   - Verify data is present

### Alerts Not Firing

1. Check Prometheus alert rules:
   ```powershell
   kubectl get configmap prometheus-rules -n monitoring -o yaml
   ```

2. Check Alertmanager configuration:
   ```powershell
   kubectl get configmap alertmanager-config -n monitoring -o yaml
   ```

3. View Prometheus logs:
   ```powershell
   kubectl logs -n monitoring deployment/prometheus
   ```

## Cleanup

To remove the monitoring stack:

```powershell
kubectl delete namespace monitoring
```

## Next Steps

1. Deploy the monitoring stack
2. Access Grafana and explore the dashboards
3. Deploy the lifecycle-controller and api-gateway applications
4. Generate some test traffic to see metrics
5. Verify alerts are working by simulating failures

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
