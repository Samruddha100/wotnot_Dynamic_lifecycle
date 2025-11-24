# 🔐 Credentials Setup - Quick Reference

## Where to Put Your AWS Credentials

### Method 1: AWS CLI Configuration (RECOMMENDED ✅)

**Step 1**: Open Command Prompt or PowerShell and run:
```bash
aws configure
```

**Step 2**: Enter your credentials when prompted:
```
AWS Access Key ID [None]: YOUR_ACCESS_KEY_HERE
AWS Secret Access Key [None]: YOUR_SECRET_KEY_HERE
Default region name [None]: ap-south-1
Default output format [None]: json
```

**Where it's stored**: 
- Windows: `C:\Users\YourUsername\.aws\credentials`
- This file is automatically created and secured

**Verify it worked**:
```bash
aws sts get-caller-identity
```

---

### Method 2: Environment Variables (ALTERNATIVE)

**For PowerShell**:
```powershell
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_HERE"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY_HERE"
$env:AWS_DEFAULT_REGION="ap-south-1"
```

**For CMD**:
```cmd
set AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_HERE
set AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY_HERE
set AWS_DEFAULT_REGION=ap-south-1
```

**Note**: These are temporary and only last for your current terminal session.

---

## Where to Put Terraform Configuration

### File: `terraform/terraform.tfvars`

**Step 1**: Copy the example file:
```bash
cd terraform
copy terraform.tfvars.example terraform.tfvars
```

**Step 2**: Edit `terraform/terraform.tfvars` with your preferred text editor:

```hcl
# terraform/terraform.tfvars
# This file is in .gitignore - safe to add your values

aws_region = "ap-south-1"

cluster_name    = "dynamic-pod-cluster"
cluster_version = "1.28"

vpc_cidr = "10.0.0.0/16"

node_group_desired_size = 2
node_group_min_size     = 1
node_group_max_size     = 5
node_instance_types     = ["t3.medium"]

karpenter_instance_types      = ["t3.medium", "t3.large"]
karpenter_capacity_types      = ["spot", "on-demand"]
karpenter_ttl_seconds_after_empty  = 300
karpenter_ttl_seconds_until_expired = 604800

enable_alb_https    = true
alb_certificate_arn = ""

tags = {
  Project     = "dynamic-pod-lifecycle"
  Environment = "dev"
  ManagedBy   = "terraform"
  Region      = "ap-south-1"
  Owner       = "YourName"
}
```

**Location**: `terraform/terraform.tfvars` (you create this file)

---

## Summary: What Goes Where

| What | Where | How |
|------|-------|-----|
| **AWS Access Key** | `~/.aws/credentials` | Run `aws configure` |
| **AWS Secret Key** | `~/.aws/credentials` | Run `aws configure` |
| **AWS Region** | `~/.aws/config` | Run `aws configure` (enter `ap-south-1`) |
| **Terraform Config** | `terraform/terraform.tfvars` | Copy from `.example` and edit |
| **Kubernetes Config** | `~/.kube/config` | Auto-created by `aws eks update-kubeconfig` |

---

## Files That Are Safe (Already in .gitignore)

These files will NOT be committed to Git:
- ✅ `~/.aws/credentials` (your AWS credentials)
- ✅ `terraform/terraform.tfvars` (your Terraform config)
- ✅ `terraform/terraform.tfstate` (Terraform state)
- ✅ `.env` (if you create one)

---

## Quick Start Commands

```bash
# 1. Configure AWS credentials
aws configure
# Enter: Access Key, Secret Key, ap-south-1, json

# 2. Verify credentials work
aws sts get-caller-identity

# 3. Create Terraform config
cd terraform
copy terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 4. Initialize Terraform
terraform init

# 5. Deploy infrastructure
terraform plan
terraform apply
```

---

## Security Reminders

🔒 **NEVER commit these files**:
- `terraform.tfvars`
- `.env`
- `~/.aws/credentials`
- Any file containing passwords or keys

✅ **These are already protected** in `.gitignore`

🔐 **Best Practices**:
- Enable MFA on your AWS account
- Use IAM roles when possible
- Rotate access keys every 90 days
- Use least-privilege IAM policies
- Never share credentials via email/chat

---

## Getting Your AWS Credentials

If you don't have AWS credentials yet:

1. **Log in to AWS Console**: https://console.aws.amazon.com/
2. **Go to IAM**: Search for "IAM" in the top search bar
3. **Click "Users"** in the left sidebar
4. **Click your username** (or create a new user)
5. **Click "Security credentials" tab**
6. **Click "Create access key"**
7. **Select "Command Line Interface (CLI)"**
8. **Click "Create access key"**
9. **Copy both**:
   - Access key ID
   - Secret access key
10. **Save them securely** (you can't see the secret key again!)

---

## Troubleshooting

### ❌ Error: "Unable to locate credentials"
**Solution**: Run `aws configure` and enter your credentials

### ❌ Error: "Access Denied"
**Solution**: Check your IAM user has required permissions (EC2, EKS, IAM, VPC)

### ❌ Error: "Invalid region"
**Solution**: Make sure you entered `ap-south-1` (not `mumbai` or `india`)

### ❌ Terraform can't find variables
**Solution**: Make sure `terraform.tfvars` exists in the `terraform/` directory

---

## Need Help?

1. Check `DEPLOYMENT_GUIDE.md` for detailed instructions
2. Check `terraform/README.md` for Terraform-specific help
3. Run `terraform validate` to check configuration
4. Run `aws sts get-caller-identity` to verify credentials

---

## Cost Estimate for Mumbai Region

**Monthly costs** (approximate):
- EKS Cluster: ₹5,840 (~$73)
- EC2 Nodes (2x t3.medium spot): ₹4,480 (~$56)
- ALB: ₹1,600 (~$20)
- Data Transfer: ₹800-1,600 (~$10-20)
- **Total: ~₹12,720-14,320/month (~$159-179/month)**

💡 **Tip**: Use spot instances and enable auto-scaling to reduce costs!
