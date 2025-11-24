# AWS Deployment Guide - Mumbai Region (ap-south-1)

## Prerequisites

Before deploying, ensure you have:
- AWS Account with appropriate permissions
- AWS CLI installed
- Terraform installed (v1.0+)
- kubectl installed
- Docker installed (for building container images)

## Step 1: Configure AWS Credentials

### Option A: Using AWS CLI (Recommended - Most Secure)

1. **Install AWS CLI** (if not already installed):
   ```bash
   # Windows (using pip)
   pip install awscli
   
   # Or download installer from: https://aws.amazon.com/cli/
   ```

2. **Configure AWS CLI with your credentials**:
   ```bash
   aws configure
   ```
   
   When prompted, enter:
   ```
   AWS Access Key ID: [YOUR_ACCESS_KEY_HERE]
   AWS Secret Access Key: [YOUR_SECRET_KEY_HERE]
   Default region name: ap-south-1
   Default output format: json
   ```

3. **Verify configuration**:
   ```bash
   aws sts get-caller-identity
   ```
   
   You should see your AWS account details.

### Option B: Using Environment Variables (Alternative)

Create a file named `.env` in your project root (this file is already in .gitignore):

```bash
# .env file (DO NOT COMMIT THIS FILE)
export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_HERE"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY_HERE"
export AWS_DEFAULT_REGION="ap-south-1"
```

Then load it:
```bash
# On Windows PowerShell
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_HERE"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY_HERE"
$env:AWS_DEFAULT_REGION="ap-south-1"

# On Windows CMD
set AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_HERE
set AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY_HERE
set AWS_DEFAULT_REGION=ap-south-1
```

## Step 2: Configure Terraform Variables

1. **Navigate to terraform directory**:
   ```bash
   cd terraform
   ```

2. **Create your terraform.tfvars file** (copy from example):
   ```bash
   copy terraform.tfvars.example terraform.tfvars
   ```

3. **Edit terraform.tfvars** and fill in your values:

   **File location**: `terraform/terraform.tfvars`
   
   ```hcl
   # terraform/terraform.tfvars
   # This file contains your deployment configuration
   # DO NOT COMMIT THIS FILE (it's in .gitignore)
   
   # AWS Region - Mumbai
   aws_region = "ap-south-1"
   
   # Project Configuration
   project_name = "dynamic-pod-lifecycle"
   environment  = "dev"  # or "staging", "production"
   
   # VPC Configuration
   vpc_cidr = "10.0.0.0/16"
   availability_zones = [
     "ap-south-1a",
     "ap-south-1b",
     "ap-south-1c"
   ]
   
   # EKS Configuration
   cluster_name    = "dynamic-pod-cluster"
   cluster_version = "1.28"
   
   # Node Group Configuration
   node_instance_types = ["t3.medium"]  # t3 is better than t2 in Mumbai
   node_desired_size   = 2
   node_min_size       = 1
   node_max_size       = 5
   
   # Karpenter Configuration
   karpenter_instance_types = ["t3.medium", "t3.large"]
   
   # Tags
   tags = {
     Project     = "DynamicPodLifecycle"
     Environment = "dev"
     ManagedBy   = "Terraform"
     Region      = "ap-south-1"
   }
   ```

## Step 3: Initialize and Deploy Infrastructure

1. **Initialize Terraform**:
   ```bash
   cd terraform
   terraform init
   ```
   
   This downloads required providers and modules.

2. **Validate configuration**:
   ```bash
   terraform validate
   ```

3. **Plan deployment** (see what will be created):
   ```bash
   terraform plan
   ```
   
   Review the output carefully. You should see:
   - VPC and networking resources
   - EKS cluster
   - Node groups
   - IAM roles and policies
   - Karpenter installation
   - ALB configuration

4. **Apply configuration** (create resources):
   ```bash
   terraform apply
   ```
   
   Type `yes` when prompted.
   
   **⏱️ This will take 15-20 minutes** to complete.

## Step 4: Configure kubectl

After Terraform completes, configure kubectl to access your cluster:

```bash
# Get cluster credentials
aws eks update-kubeconfig --region ap-south-1 --name dynamic-pod-cluster

# Verify connection
kubectl get nodes
```

You should see your EKS nodes listed.

## Step 5: Deploy Vault and Redis

1. **Navigate to k8s-manifests directory**:
   ```bash
   cd ../k8s-manifests
   ```

2. **Create namespace**:
   ```bash
   kubectl create namespace vault
   kubectl create namespace redis
   kubectl create namespace sessions
   ```

3. **Deploy Vault**:
   ```bash
   # Apply Vault manifests
   kubectl apply -f vault-namespace.yaml
   kubectl apply -f vault-serviceaccount.yaml
   kubectl apply -f vault-configmap.yaml
   kubectl apply -f vault-statefulset.yaml
   kubectl apply -f vault-service.yaml
   
   # Wait for Vault pods to be ready
   kubectl wait --for=condition=ready pod -l app=vault -n vault --timeout=300s
   
   # Initialize Vault
   bash vault-init.sh
   
   # Unseal Vault
   bash vault-unseal.sh
   
   # Configure Vault
   bash vault-configure.sh
   ```

4. **Deploy Redis**:
   ```bash
   # Apply Redis manifests
   kubectl apply -f redis-namespace.yaml
   kubectl apply -f redis-secret.yaml
   kubectl apply -f redis-configmap.yaml
   kubectl apply -f redis-deployment.yaml
   kubectl apply -f redis-service.yaml
   
   # Or use the deployment script
   bash redis-deploy.sh
   ```

5. **Verify deployments**:
   ```bash
   kubectl get pods -n vault
   kubectl get pods -n redis
   ```

## Step 6: Build and Push Container Images

You need to build Docker images for:
1. Lifecycle Controller
2. API Gateway
3. Session Pod

### Create ECR Repositories

```bash
# Create ECR repositories
aws ecr create-repository --repository-name lifecycle-controller --region ap-south-1
aws ecr create-repository --repository-name api-gateway --region ap-south-1
aws ecr create-repository --repository-name session-pod --region ap-south-1

# Get ECR login
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
```

### Build and Push Images

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com"

# Build Lifecycle Controller
cd src/lifecycle-controller
docker build -t lifecycle-controller:latest .
docker tag lifecycle-controller:latest ${ECR_REGISTRY}/lifecycle-controller:latest
docker push ${ECR_REGISTRY}/lifecycle-controller:latest

# Build API Gateway (when implemented)
# cd ../api-gateway
# docker build -t api-gateway:latest .
# docker tag api-gateway:latest ${ECR_REGISTRY}/api-gateway:latest
# docker push ${ECR_REGISTRY}/api-gateway:latest

# Build Session Pod (when implemented)
# cd ../session-pod
# docker build -t session-pod:latest .
# docker tag session-pod:latest ${ECR_REGISTRY}/session-pod:latest
# docker push ${ECR_REGISTRY}/session-pod:latest
```

## Step 7: Deploy Lifecycle Controller

Create Kubernetes manifests for the Lifecycle Controller:

```bash
# Create deployment
kubectl apply -f k8s-manifests/lifecycle-controller-deployment.yaml

# Verify deployment
kubectl get pods -n sessions
kubectl logs -f deployment/lifecycle-controller -n sessions
```

## Step 8: Verify Everything is Working

```bash
# Check all pods
kubectl get pods --all-namespaces

# Check services
kubectl get svc --all-namespaces

# Check Karpenter
kubectl get pods -n karpenter

# Test Vault connection
kubectl exec -it vault-0 -n vault -- vault status

# Test Redis connection
kubectl exec -it deployment/redis -n redis -- redis-cli ping
```

## Important Files and Their Locations

### Credentials (NEVER COMMIT THESE):
- **AWS Credentials**: `~/.aws/credentials` (created by `aws configure`)
- **Terraform Variables**: `terraform/terraform.tfvars` (you create this)
- **Environment Variables**: `.env` (optional, you create this)

### Configuration Files:
- **Terraform Config**: `terraform/terraform.tfvars`
- **Kubernetes Config**: `~/.kube/config` (created automatically)

### Logs and Outputs:
- **Terraform State**: `terraform/terraform.tfstate` (DO NOT DELETE)
- **Terraform Outputs**: Run `terraform output` to see values

## Cost Optimization for Mumbai Region

Mumbai (ap-south-1) pricing is slightly different from us-east-1:

**Estimated Monthly Costs:**
- EKS Cluster: ₹5,840 (~$73)
- EC2 Instances (t3.medium spot): ₹11,200 (~$140)
- ALB: ₹1,600 (~$20)
- Data Transfer: Variable
- **Total: ~₹18,640/month (~$233/month)**

**Cost Saving Tips:**
1. Use **Spot Instances** for worker nodes (already configured in Karpenter)
2. Use **t3.medium** instead of t2.medium (better performance, similar cost)
3. Enable **Karpenter consolidation** (already configured)
4. Set up **auto-scaling** to scale down during off-hours
5. Use **Reserved Instances** for production (save up to 40%)

## Troubleshooting

### Issue: Terraform fails with authentication error
**Solution**: Verify AWS credentials:
```bash
aws sts get-caller-identity
```

### Issue: EKS cluster creation fails
**Solution**: Check IAM permissions. You need:
- `eks:*`
- `ec2:*`
- `iam:CreateRole`, `iam:AttachRolePolicy`

### Issue: kubectl can't connect to cluster
**Solution**: Update kubeconfig:
```bash
aws eks update-kubeconfig --region ap-south-1 --name dynamic-pod-cluster
```

### Issue: Pods stuck in Pending state
**Solution**: Check Karpenter logs:
```bash
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter
```

## Cleanup (Destroy Resources)

When you want to tear down everything:

```bash
# Delete Kubernetes resources first
kubectl delete namespace sessions
kubectl delete namespace redis
kubectl delete namespace vault

# Destroy Terraform infrastructure
cd terraform
terraform destroy
```

Type `yes` when prompted.

**⚠️ Warning**: This will delete ALL resources and cannot be undone!

## Security Checklist

- [ ] AWS credentials configured (not committed to Git)
- [ ] terraform.tfvars created (not committed to Git)
- [ ] .gitignore includes sensitive files
- [ ] MFA enabled on AWS account
- [ ] IAM user has minimum required permissions
- [ ] Vault initialized and sealed properly
- [ ] Redis password set from Vault
- [ ] Network policies configured
- [ ] TLS certificates configured

## Next Steps

1. ✅ Configure AWS credentials
2. ✅ Create terraform.tfvars
3. ✅ Deploy infrastructure with Terraform
4. ✅ Configure kubectl
5. ✅ Deploy Vault and Redis
6. ⏳ Build and push container images
7. ⏳ Deploy Lifecycle Controller
8. ⏳ Deploy API Gateway
9. ⏳ Test end-to-end flow
10. ⏳ Set up monitoring and alerts

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Terraform logs: `terraform.log`
3. Check Kubernetes logs: `kubectl logs <pod-name>`
4. Review AWS CloudWatch logs

## Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Karpenter Documentation](https://karpenter.sh/)
- [Vault on Kubernetes](https://www.vaultproject.io/docs/platform/k8s)
