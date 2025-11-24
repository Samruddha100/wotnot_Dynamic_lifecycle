provider "aws" {
  region = "ap-south-1"
}

data "aws_eks_cluster" "cluster" {
  name = "dynamic-pod-lifecycle"
}

data "aws_eks_cluster_auth" "cluster" {
  name = "dynamic-pod-lifecycle"
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}

resource "kubernetes_config_map_v1_data" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = {
    mapRoles = <<-EOT
      - rolearn: arn:aws:iam::557690613541:role/dynamic-pod-lifecycle-node-group-role
        username: system:node:{{EC2PrivateDNSName}}
        groups:
          - system:bootstrappers
          - system:nodes
    EOT

    mapUsers = <<-EOT
      - userarn: arn:aws:iam::557690613541:root
        username: root-admin
        groups:
          - system:masters
    EOT
  }

  force = true
}
