#!/bin/bash
set -euo pipefail

AWS_REGION="eu-central-1"
TF_DIR="terraform"
TF_VAR_FILE="$TF_DIR/terraform.tfvars"

# Get AWS Account ID securely
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Generate unique image tag
IMAGE_TAG="$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD)"

# 2. Run Terraform to create infra, passing in image tag
cd "$TF_DIR"
terraform init
terraform apply -auto-approve -var="image_tag=$IMAGE_TAG"
ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/aimfiltech-ecr-repo"
if terraform output -raw ecr_repo_url > /dev/null 2>&1; then
  ECR_REPO=$(terraform output -raw ecr_repo_url)
fi
cd ..

# 3. Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$ECR_REPO"

# 4. Build and push Docker image
docker build -t "$ECR_REPO:$IMAGE_TAG" .
docker push "$ECR_REPO:$IMAGE_TAG"

echo ""
echo "✅ Deployed! ECS is running your image: $ECR_REPO:$IMAGE_TAG"
echo "To tear down everything, run: ./deploy.sh destroy $IMAGE_TAG"