# Dynamic Pod Lifecycle Management System

## Overview

The Dynamic Pod Lifecycle Management System is a cloud-native solution built on AWS EKS that provides on-demand, session-specific compute resources. The system dynamically creates, manages, and destroys Kubernetes pods and nodes based on incoming REST API requests associated with unique session IDs.

### Key Features

- **Dynamic Pod Creation**: Automatically creates dedicated pods for each unique session ID
- **Intelligent Routing**: Routes all requests with the same session ID to the corresponding pod
- **Automatic Cleanup**: Terminates pods after 10 minutes of inactivity to optimize resource usage
- **Auto-scaling**: Leverages Karpenter for intelligent node provisioning and deprovisioning
- **Security**: TLS encryption, RBAC policies, and HashiCorp Vault for secrets management
- **Observability**: Comprehensive monitoring with Prometheus and Grafana
- **Self-Healing**: Automatic pod recreation on failures

## Architecture

For detailed architecture diagrams including request flow, pod creation, cleanup, and self-healing processes, see [Architecture Documentation](docs/architecture-diagram.md).

```
Client → ALB → API Gateway → Lifecycle Controller → Kubernetes API → Session Pods
                                    ↓
                              Redis (Session Mappings)
                                    ↓
                              Vault (Secrets)
                                    ↓
                          Prometheus/Grafana (Monitoring)
```

### Components

- **API Gateway**: REST API entry point that routes requests to session-specific pods (Python/Flask with Gunicorn)
- **Lifecycle Controller**: Manages pod creation, deletion, and idle timeout cleanup (Python with Kubernetes client)
- **Session Pods**: Stateful pods dedicated to individual session IDs (Python/Flask applications)
- **Karpenter**: Node autoscaler for dynamic infrastructure provisioning (t2.medium, t2.large instances)
- **HashiCorp Vault**: Secrets management and TLS certificate generation (HA with 3 replicas)
- **Redis**: Session-to-pod mapping storage with persistence (AOF enabled)
- **Prometheus/Grafana**: Metrics collection and visualization with alerting

## Project Structure

```
.
├── terraform/              # Infrastructure as Code
│   ├── modules/           # Reusable Terraform modules
│   │   ├── vpc/          # VPC and networking
│   │   ├── eks/          # EKS cluster
│   │   └── karpenter/    # Karpenter configuration
│   └── environments/      # Environment-specific configs
│       ├── dev/
│       ├── staging/
│       └── production/
├── k8s-manifests/         # Kubernetes resource definitions
│   ├── api-gateway/      # API Gateway deployment
│   ├── lifecycle-controller/  # Lifecycle Controller deployment
│   ├── session-pod/      # Session Pod templates
│   ├── vault/            # Vault deployment
│   ├── redis/            # Redis deployment
│   ├── monitoring/       # Prometheus and Grafana
│   └── rbac/             # RBAC policies
├── src/                   # Application source code
│   ├── api-gateway/      # API Gateway application
│   ├── lifecycle-controller/  # Lifecycle Controller application
│   └── session-pod/      # Session Pod application
├── tests/                 # Test suites
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── property/         # Property-based tests
├── docs/                  # Documentation
│   ├── architecture/     # Architecture diagrams
│   ├── setup/            # Setup guides
│   └── troubleshooting/  # Troubleshooting guides
└── .kiro/                # Kiro specs and configuration
    └── specs/
        └── dynamic-pod-lifecycle/
```

## Prerequisites

Before setting up the project, ensure you have the following tools installed:

### Required Tools

- **AWS CLI** (v2.x or later)
  ```bash
  aws --version
  ```

- **kubectl** (v1.28 or later)
  ```bash
  kubectl version --client
  ```

- **Terraform** (v1.5 or later)
  ```bash
  terraform version
  ```

- **Docker** (v20.x or later)
  ```bash
  docker --version
  ```

- **Python** (v3.10 or later)
  ```bash
  python --version
  ```

- **Helm** (v3.x or later)
  ```bash
  helm version
  ```

### AWS Account Requirements

- Active AWS account with appropriate permissions
- IAM user or role with permissions to create:
  - VPC and networking resources
  - EKS clusters
  - EC2 instances
  - IAM roles and policies
  - Application Load Balancers
  - ECR repositories

## Setup Instructions

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dynamic-pod-lifecycle
   ```

2. **Set up Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure AWS credentials**
   ```bash
   aws configure
   ```

5. **Run local tests**
   ```bash
   pytest tests/
   ```

### AWS Deployment Setup

#### Step 1: Configure AWS Credentials

```bash
# Configure AWS CLI with your credentials
aws configure

# Verify credentials
aws sts get-caller-identity
```

Set the following environment variables:
```bash
export AWS_REGION=us-east-1
export CLUSTER_NAME=dynamic-pod-lifecycle
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

#### Step 2: Create Terraform Variables File

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your specific values:
```hcl
aws_region         = "us-east-1"
cluster_name       = "dynamic-pod-lifecycle"
vpc_cidr           = "10.0.0.0/16"
environment        = "production"
```

#### Step 3: Validate Terraform Configuration

```bash
# Run validation script (bash)
chmod +x validate.sh
./validate.sh

# Or use Python script
python3 validate.py
```

#### Step 4: Initialize and Apply Terraform

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan -out=tfplan

# Apply the configuration
terraform apply tfplan
```

This will provision (approximately 15-20 minutes):
- VPC with public and private subnets across 3 availability zones
- NAT gateways and internet gateway
- EKS cluster with OIDC provider
- Initial node group (t2.medium instances)
- Karpenter for node autoscaling
- Application Load Balancer with HTTPS listener
- IAM roles and policies for EKS, Karpenter, and service accounts
- Security groups and network ACLs

#### Step 5: Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# Verify cluster access
kubectl get nodes
kubectl get namespaces
```

#### Step 6: Create Namespaces

```bash
# Create required namespaces
kubectl apply -f k8s-manifests/sessions-namespace.yaml
kubectl apply -f k8s-manifests/vault-namespace.yaml
kubectl apply -f k8s-manifests/redis-namespace.yaml
kubectl apply -f k8s-manifests/prometheus-namespace.yaml
```

#### Step 7: Deploy HashiCorp Vault

```bash
# Deploy Vault StatefulSet
kubectl apply -f k8s-manifests/vault-serviceaccount.yaml
kubectl apply -f k8s-manifests/vault-configmap.yaml
kubectl apply -f k8s-manifests/vault-statefulset.yaml
kubectl apply -f k8s-manifests/vault-service.yaml

# Wait for Vault pods to be ready
kubectl wait --for=condition=ready pod -l app=vault -n vault --timeout=300s

# Initialize Vault (run on first deployment only)
chmod +x k8s-manifests/vault-init.sh
./k8s-manifests/vault-init.sh

# Unseal Vault (save unseal keys securely!)
chmod +x k8s-manifests/vault-unseal.sh
./k8s-manifests/vault-unseal.sh

# Configure Vault policies and secrets
chmod +x k8s-manifests/vault-configure.sh
./k8s-manifests/vault-configure.sh
```

**Important**: Save the Vault unseal keys and root token in a secure location (e.g., AWS Secrets Manager).

#### Step 8: Deploy Redis

```bash
# Deploy Redis with persistence
chmod +x k8s-manifests/redis-deploy.sh
./k8s-manifests/redis-deploy.sh

# Verify Redis is running
kubectl get pods -n redis
kubectl logs -n redis -l app=redis
```

#### Step 9: Deploy Monitoring Stack

```bash
# Deploy Prometheus, Grafana, and Alertmanager
chmod +x k8s-manifests/deploy-monitoring.sh
./k8s-manifests/deploy-monitoring.sh

# Wait for monitoring pods to be ready
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=300s
kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=300s

# Get Grafana admin password
kubectl get secret -n monitoring grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```

#### Step 10: Build and Push Docker Images

```bash
# Login to Amazon ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repositories
aws ecr create-repository --repository-name lifecycle-controller --region $AWS_REGION
aws ecr create-repository --repository-name api-gateway --region $AWS_REGION
aws ecr create-repository --repository-name session-pod --region $AWS_REGION

# Build and push Lifecycle Controller
cd src/lifecycle-controller
docker build -t lifecycle-controller:latest .
docker tag lifecycle-controller:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/lifecycle-controller:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/lifecycle-controller:latest

# Build and push API Gateway
cd ../api-gateway
docker build -t api-gateway:latest .
docker tag api-gateway:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/api-gateway:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/api-gateway:latest

# Build and push Session Pod
cd ../session-pod
docker build -t session-pod:latest .
docker tag session-pod:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/session-pod:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/session-pod:latest

cd ../../
```

#### Step 11: Deploy Application Components

```bash
# Update image references in manifests
export ECR_REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
sed -i "s|<ECR_REGISTRY>|$ECR_REGISTRY|g" k8s-manifests/lifecycle-controller-deployment.yaml
sed -i "s|<ECR_REGISTRY>|$ECR_REGISTRY|g" k8s-manifests/api-gateway-deployment.yaml

# Deploy application using deployment script
chmod +x k8s-manifests/deploy-application.sh
./k8s-manifests/deploy-application.sh

# Verify deployments
kubectl get deployments -n sessions
kubectl get pods -n sessions
kubectl get svc -n sessions
```

#### Step 12: Configure Network Policies

```bash
# Apply network policies for security
kubectl apply -f k8s-manifests/network-policies.yaml

# Verify network policies
kubectl get networkpolicies -n sessions
```

#### Step 13: Verify Deployment

```bash
# Check all pods are running
kubectl get pods --all-namespaces

# Check Lifecycle Controller logs
kubectl logs -n sessions -l app=lifecycle-controller --tail=50

# Check API Gateway logs
kubectl logs -n sessions -l app=api-gateway --tail=50

# Get API Gateway endpoint
export API_GATEWAY_URL=$(kubectl get svc api-gateway -n sessions -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "API Gateway URL: https://$API_GATEWAY_URL"

# Test health endpoint
curl -k https://$API_GATEWAY_URL/health
```

#### Step 14: Access Monitoring Dashboards

```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000 &

# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090 &

# Access dashboards
echo "Grafana: http://localhost:3000 (admin / <password from step 9>)"
echo "Prometheus: http://localhost:9090"
```

## Configuration

### Environment Variables

Key environment variables for each component:

#### API Gateway

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LIFECYCLE_CONTROLLER_URL` | URL of the Lifecycle Controller | `http://lifecycle-controller:8080` | Yes |
| `TLS_CERT_PATH` | Path to TLS certificate | `/etc/tls/tls.crt` | Yes |
| `TLS_KEY_PATH` | Path to TLS private key | `/etc/tls/tls.key` | Yes |
| `AUTH_TOKEN_SECRET` | Secret for JWT token validation | - | Yes |
| `VAULT_ADDR` | Vault server address | `http://vault:8200` | Yes |
| `VAULT_ROLE` | Vault role for authentication | `api-gateway` | Yes |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `METRICS_PORT` | Prometheus metrics port | `9090` | No |

#### Lifecycle Controller

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_HOST` | Redis server hostname | `redis` | Yes |
| `REDIS_PORT` | Redis server port | `6379` | Yes |
| `REDIS_PASSWORD` | Redis password (from Vault) | - | Yes |
| `VAULT_ADDR` | Vault server address | `http://vault:8200` | Yes |
| `VAULT_ROLE` | Vault role for authentication | `lifecycle-controller` | Yes |
| `KUBERNETES_NAMESPACE` | Namespace for session pods | `sessions` | Yes |
| `IDLE_TIMEOUT_SECONDS` | Idle timeout in seconds | `600` | No |
| `CLEANUP_INTERVAL_SECONDS` | Cleanup check interval | `60` | No |
| `POD_CREATION_TIMEOUT` | Pod creation timeout | `120` | No |
| `MAX_CONCURRENT_SESSIONS` | Maximum concurrent sessions | `1000` | No |
| `SESSION_POD_IMAGE` | Docker image for session pods | - | Yes |
| `SESSION_POD_CPU_REQUEST` | CPU request for session pods | `100m` | No |
| `SESSION_POD_CPU_LIMIT` | CPU limit for session pods | `500m` | No |
| `SESSION_POD_MEMORY_REQUEST` | Memory request for session pods | `128Mi` | No |
| `SESSION_POD_MEMORY_LIMIT` | Memory limit for session pods | `512Mi` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `METRICS_PORT` | Prometheus metrics port | `9090` | No |

#### Session Pod

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SESSION_ID` | Unique session identifier | - | Yes (injected) |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `STATE_FILE_PATH` | Path for state persistence | `/tmp/session-state.json` | No |

### ConfigMaps

Configuration is managed through Kubernetes ConfigMaps:

- **api-gateway-config**: API Gateway configuration (see `k8s-manifests/api-gateway-configmap.yaml`)
- **lifecycle-controller-config**: Lifecycle Controller configuration (see `k8s-manifests/lifecycle-controller-configmap.yaml`)
- **session-config**: Session Pod configuration (see `k8s-manifests/session-config-configmap.yaml`)

### Secrets

Secrets are managed through HashiCorp Vault:

- **TLS Certificates**: Generated by Vault PKI engine
- **Redis Password**: Stored in Vault KV store at `secret/redis/password`
- **API Keys**: Stored in Vault KV store at `secret/api/keys`
- **AWS Credentials**: For ECR access (if needed)

## Usage

### Creating a Session

Send a POST request to the API Gateway:

```bash
curl -X POST https://<api-gateway-url>/api/v1/session/<session-id>/execute \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"data": "your-request-data"}'
```

### Checking Session Status

```bash
curl -X GET https://<api-gateway-url>/api/v1/session/<session-id>/status \
  -H "Authorization: Bearer <token>"
```

### Monitoring

Access Grafana dashboard:

```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

Open http://localhost:3000 in your browser.

## Testing

### Unit Tests

Run unit tests for individual components:

```bash
# API Gateway tests
cd src/api-gateway
pytest test_*.py -v

# Lifecycle Controller tests
cd src/lifecycle-controller
pytest test_*.py -v

# Session Pod tests
cd src/session-pod
pytest test_*.py -v
```

### Property-Based Tests

Run property-based tests using Hypothesis:

```bash
# Run all property tests
pytest tests/ -v --hypothesis-show-statistics

# Run with increased iterations
pytest tests/ -v --hypothesis-profile=ci
```

### Integration Tests

Run integration tests for Vault and Redis:

```bash
pytest tests/test_vault_redis_integration.py -v
pytest tests/test_monitoring_setup.py -v
```

### Final Validation Tests

After deploying the complete system to AWS EKS, run comprehensive validation tests:

```bash
# Make scripts executable
chmod +x tests/*.sh

# Run complete validation suite
./tests/run_all_validations.sh
```

This will execute:
1. **Deployment Verification** - Verify all components are deployed
2. **Smoke Tests** - Quick validation of basic functionality
3. **Comprehensive Tests** - Full validation of all requirements
4. **Manual Test Instructions** - Guide for manual validation procedures

Or run individual test suites:

```bash
# Deployment verification
./tests/verify_deployment.sh

# Smoke tests
./tests/smoke_tests.sh

# Comprehensive validation (requires deployed system)
export API_GATEWAY_URL="https://your-alb-url.amazonaws.com"
export AUTH_TOKEN="your-auth-token"
python tests/final_validation.py
```

### Validation Checklist

Use the comprehensive validation checklist to track testing progress:

```bash
# Open the validation checklist
cat FINAL_VALIDATION_CHECKLIST.md
```

The checklist includes:
- Automated test results
- Manual test procedures
- Sign-off section
- Issue tracking

For detailed validation instructions, see:
- `tests/VALIDATION_GUIDE.md` - Comprehensive validation guide
- `tests/README.md` - Test suite overview
- `TEST_RESULTS.md` - Test execution status and results

## CI/CD Pipeline

The project uses Jenkins for continuous integration and deployment. The pipeline includes:

1. **Code Quality**: Linting and SonarQube analysis
2. **Build**: Docker image creation
3. **Security Scan**: Trivy vulnerability scanning
4. **Test**: Unit, integration, and property-based tests
5. **Push**: Push images to Amazon ECR
6. **Deploy**: Deploy to EKS cluster
7. **Verify**: Smoke tests

See `Jenkinsfile` for pipeline configuration.

## Monitoring and Observability

### Metrics

Key metrics exposed by the system:

- `session_pods_active`: Number of active session pods
- `session_pod_creation_duration_seconds`: Pod creation latency
- `session_pod_deletion_total`: Total pods deleted
- `session_idle_timeout_total`: Total idle timeouts
- `session_request_duration_seconds`: Request processing time

### Logs

Structured JSON logs are collected by Fluent Bit and sent to CloudWatch Logs.

View logs:
```bash
kubectl logs -n sessions -l app=lifecycle-controller --tail=100
```

### Alerts

Prometheus alerts are configured for:
- Pod creation failures
- High pod creation latency
- Component unavailability
- Certificate expiration

## Troubleshooting

### Common Issues

#### Issue: Pods not being created

**Symptoms:**
- Requests return 503 Service Unavailable
- Lifecycle Controller logs show pod creation failures
- Session status shows "creating" for extended period

**Diagnosis:**
```bash
# Check Lifecycle Controller logs
kubectl logs -n sessions -l app=lifecycle-controller --tail=100

# Check Kubernetes events
kubectl get events -n sessions --sort-by='.lastTimestamp'

# Check node capacity
kubectl describe nodes

# Check Karpenter status
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter
```

**Solutions:**
- Verify Kubernetes API connectivity: `kubectl get nodes`
- Check node capacity and Karpenter provisioner configuration
- Verify ECR image pull permissions
- Check resource quotas: `kubectl describe resourcequota -n sessions`
- Verify pod security policies are not blocking creation

#### Issue: Requests not routing to pods

**Symptoms:**
- Requests return 502 Bad Gateway
- API Gateway logs show routing errors
- Session exists but requests fail

**Diagnosis:**
```bash
# Check API Gateway logs
kubectl logs -n sessions -l app=api-gateway --tail=100

# Verify session mapping in Redis
kubectl exec -n redis redis-0 -- redis-cli GET "session:<session-id>"

# Check service endpoints
kubectl get endpoints -n sessions

# Check pod status
kubectl get pods -n sessions -l session-id=<session-id>
```

**Solutions:**
- Verify session mapping exists in Redis
- Check Kubernetes service discovery: `kubectl get svc -n sessions`
- Verify network policies allow traffic from API Gateway to session pods
- Check pod readiness probes: `kubectl describe pod <pod-name> -n sessions`
- Verify DNS resolution: `kubectl exec -n sessions <api-gateway-pod> -- nslookup <service-name>`

#### Issue: Pods not terminating after idle timeout

**Symptoms:**
- Pods remain running after 10 minutes of inactivity
- Cleanup process not running
- Redis timestamps not updating

**Diagnosis:**
```bash
# Check Lifecycle Controller cleanup logs
kubectl logs -n sessions -l app=lifecycle-controller | grep "cleanup"

# Check Redis timestamps
kubectl exec -n redis redis-0 -- redis-cli HGETALL "session:<session-id>"

# Verify cleanup interval configuration
kubectl get configmap lifecycle-controller-config -n sessions -o yaml
```

**Solutions:**
- Verify cleanup interval is set correctly (default: 60 seconds)
- Check Lifecycle Controller is running: `kubectl get pods -n sessions -l app=lifecycle-controller`
- Verify Redis connectivity from Lifecycle Controller
- Check timestamp update logic in API Gateway
- Verify leader election is working (only leader performs cleanup)

#### Issue: Karpenter not provisioning nodes

**Symptoms:**
- Pods stuck in "Pending" state
- No new nodes being created
- Karpenter logs show provisioning errors

**Diagnosis:**
```bash
# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter --tail=100

# Check provisioner configuration
kubectl get provisioner -o yaml

# Check pending pods
kubectl get pods -n sessions --field-selector=status.phase=Pending

# Check AWS IAM permissions
aws sts get-caller-identity
```

**Solutions:**
- Verify Karpenter provisioner configuration: `kubectl get provisioner session-pods -o yaml`
- Check AWS IAM permissions for Karpenter role
- Verify instance types are available in the region
- Check AWS service quotas for EC2 instances
- Verify subnet configuration and availability zones
- Check security group rules

#### Issue: Vault authentication failures

**Symptoms:**
- Pods cannot retrieve secrets
- TLS certificate errors
- Authentication errors in logs

**Diagnosis:**
```bash
# Check Vault status
kubectl exec -n vault vault-0 -- vault status

# Check Vault logs
kubectl logs -n vault vault-0

# Test Vault authentication from pod
kubectl exec -n sessions <pod-name> -- curl -k https://vault:8200/v1/sys/health
```

**Solutions:**
- Verify Vault is unsealed: `kubectl exec -n vault vault-0 -- vault status`
- Check Kubernetes auth method is enabled
- Verify service account tokens are being mounted
- Check Vault policies for the service account
- Verify network connectivity to Vault

#### Issue: Redis connection failures

**Symptoms:**
- Session mappings not being stored
- Connection timeout errors
- Redis unavailable errors

**Diagnosis:**
```bash
# Check Redis status
kubectl get pods -n redis

# Check Redis logs
kubectl logs -n redis redis-0

# Test Redis connectivity
kubectl exec -n redis redis-0 -- redis-cli ping
```

**Solutions:**
- Verify Redis is running: `kubectl get pods -n redis`
- Check Redis password configuration
- Verify network policies allow traffic to Redis
- Check Redis persistence (AOF) is working
- Verify Redis service DNS resolution

#### Issue: High pod creation latency

**Symptoms:**
- Pod creation takes > 30 seconds
- Slow response times for new sessions
- Prometheus alerts firing

**Diagnosis:**
```bash
# Check pod creation metrics
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Query: histogram_quantile(0.95, session_pod_creation_duration_seconds)

# Check image pull times
kubectl describe pod <pod-name> -n sessions | grep -A 10 "Events:"

# Check node provisioning time
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter | grep "provisioning"
```

**Solutions:**
- Pre-pull session pod images on nodes
- Use smaller base images (Alpine)
- Optimize container startup time
- Increase Karpenter provisioner limits
- Use on-demand instances instead of spot for critical workloads

#### Issue: TLS certificate errors

**Symptoms:**
- HTTPS requests fail with certificate errors
- Certificate expired warnings
- TLS handshake failures

**Diagnosis:**
```bash
# Check certificate expiration
kubectl get secret -n sessions api-gateway-tls -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates

# Check Vault PKI engine
kubectl exec -n vault vault-0 -- vault list pki/certs
```

**Solutions:**
- Verify Vault PKI engine is configured
- Check certificate rotation logic
- Manually rotate certificates if needed
- Verify TLS configuration in API Gateway

### Getting Help

For additional support:
1. Check the [Architecture Documentation](docs/architecture-diagram.md)
2. Review [Pod Lifecycle Flow](docs/pod-lifecycle-flow.md)
3. Review [Security Implementation](docs/security-implementation.md)
4. Open an issue on GitHub with logs and configuration details

## Security Considerations

- All communication uses TLS encryption
- Secrets are managed through HashiCorp Vault
- RBAC policies enforce least privilege access
- Network policies restrict traffic between components
- Container images are scanned for vulnerabilities
- Pods run as non-root users with read-only filesystems

## Performance

### Scalability Targets

- Support for 1000 concurrent sessions
- Pod creation time < 10s (p95)
- Request routing latency < 50ms (p95)
- Handle 10,000 requests/minute

### Resource Requirements

**Per Session Pod:**
- CPU: 100m request, 500m limit
- Memory: 128Mi request, 512Mi limit

**Control Plane:**
- API Gateway: 3 pods × (200m CPU, 256Mi memory)
- Lifecycle Controller: 2 pods × (500m CPU, 512Mi memory)

## Contributing

[Contributing guidelines to be added]

## License

[License information to be added]

## Documentation

- [Architecture Diagrams](docs/architecture-diagram.md) - Comprehensive system architecture with request flow, cleanup, and self-healing diagrams
- [Pod Lifecycle Flow](docs/pod-lifecycle-flow.md) - Detailed explanation of pod creation, routing, and termination
- [Security Implementation](docs/security-implementation.md) - TLS, RBAC, Vault integration, and network policies
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Step-by-step deployment instructions
- [Credentials Setup](CREDENTIALS_SETUP.md) - AWS and Vault credentials configuration
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute to the project
- [Security Policy](SECURITY.md) - Security vulnerability reporting
- [Changelog](CHANGELOG.md) - Version history and changes

## Demo Video

🎥 [Loom Video Walkthrough](https://www.loom.com/share/your-video-id) - 5-7 minute demonstration covering:
- Architecture overview
- Pod creation for new session ID
- Request routing to same pod for multiple requests
- Idle timeout and automatic pod termination
- Self-healing by manually deleting a pod
- Grafana dashboard with real-time metrics
- Prometheus alerts

*Note: Video link will be added after recording*

## Support

For issues and questions, please [open an issue](https://github.com/your-org/dynamic-pod-lifecycle/issues).
